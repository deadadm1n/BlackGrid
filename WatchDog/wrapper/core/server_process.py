import asyncio
import os
import re
import signal
import shutil
import subprocess
from pathlib import Path

import psutil

from wrapper.core.console_parser import parse_console_line
from wrapper.core.events import ServerStartedEvent, ServerStoppingEvent, ServerStoppedEvent


class ServerProcess:

    def log_mc_line(self, line: str):
        show_console = bool(
            self.ctx.config.get("server.show_minecraft_console", True)
        )

        save_console_log = bool(
            self.ctx.config.get("server.save_minecraft_console_log", True)
        )

        if show_console:
            print(f"[MC] {line}", flush=True)

        if save_console_log:
            try:
                with self.ctx.minecraft_console_log.open("a", encoding="utf-8") as f:
                    f.write(line + "\n")
            except Exception as e:
                self.ctx.logger.warning(
                    "Failed to write minecraft_console.log: %s",
                    e,
                )

    async def read_output_forever(self):
        if not self.process or not self.process.stdout:
            return

        while True:
            line = await self.process.stdout.readline()

            if not line:
                break

            decoded = line.decode(errors="replace").rstrip()
            self.log_mc_line(decoded)
            for event in parse_console_line(decoded):
                await self.ctx.event_bus.publish(event)

    async def send_command(self, command: str):
        if not self.process:
            return

        if self.process.returncode is not None:
            return

        if not self.process.stdin or self.process.stdin.is_closing():
            return

        self.process.stdin.write((command.strip() + "\n").encode())
        await self.process.stdin.drain()

    def __init__(self, ctx):
        self.ctx = ctx
        self.process = None
        self.startup_validated = False
        self.last_start_failure_reason = None
        self.startup_output_tail = []

    def _record_startup_line(self, line: str):
        self.startup_output_tail.append(line)
        self.startup_output_tail = self.startup_output_tail[-80:]

        tail = "\n".join(self.startup_output_tail)
        has_windows_lock = "locked a portion of the file" in tail
        has_minecraft_lock = "DirectoryLock" in tail or "session.lock" in tail

        if has_windows_lock and has_minecraft_lock:
            self.last_start_failure_reason = "world_locked"
        elif "session.lock: already locked" in tail:
            self.last_start_failure_reason = "world_locked"

    def _select_start_script(self, server_dir: Path, configured_script: str) -> Path:
        configured_script = str(configured_script or "auto").strip()

        candidates = []

        if configured_script.lower() != "auto":
            requested = server_dir / configured_script
            candidates.append(requested)

            suffix = requested.suffix.lower()
            if os.name == "nt" and suffix in {".sh", ""}:
                candidates.extend([
                    requested.with_suffix(".bat"),
                    requested.with_suffix(".cmd"),
                    server_dir / "startserver.bat",
                    server_dir / "run.bat",
                ])
            elif os.name != "nt" and suffix in {".bat", ".cmd", ""}:
                candidates.extend([
                    requested.with_suffix(".sh"),
                    server_dir / "startserver.sh",
                    server_dir / "run.sh",
                ])
        elif os.name == "nt":
            candidates.extend([
                server_dir / "startserver.bat",
                server_dir / "run.bat",
                server_dir / "start.bat",
                server_dir / "startserver.cmd",
                server_dir / "run.cmd",
            ])
        else:
            candidates.extend([
                server_dir / "startserver.sh",
                server_dir / "run.sh",
                server_dir / "start.sh",
            ])

        seen = set()
        for candidate in candidates:
            candidate = candidate.resolve()
            if candidate in seen:
                continue
            seen.add(candidate)
            if candidate.exists():
                return candidate

        searched = ", ".join(str(path) for path in candidates)
        raise FileNotFoundError(f"Start script not found. Searched: {searched}")

    def _build_start_command(self, start_path: Path):
        suffix = start_path.suffix.lower()

        if suffix in {".bat", ".cmd"}:
            if os.name != "nt":
                raise RuntimeError(
                    f"Cannot run Windows batch script on this platform: {start_path.name}"
                )
            return ["cmd.exe", "/c", start_path.name]

        if suffix in {".sh", ""}:
            bash_path = shutil.which("bash")
            if not bash_path:
                raise RuntimeError(
                    f"bash is required to run {start_path.name}; use a .bat/.cmd script on Windows or install bash"
                )
            return [bash_path, start_path.name]

        return [str(start_path)]

    def _subprocess_kwargs(self, server_dir: Path, env: dict[str, str]) -> dict:
        kwargs = {
            "cwd": server_dir,
            "stdout": asyncio.subprocess.PIPE,
            "stderr": asyncio.subprocess.STDOUT,
            "stdin": asyncio.subprocess.PIPE,
            "env": env,
        }

        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        else:
            kwargs["start_new_session"] = True

        return kwargs

    def _resolve_java_executable(self, env: dict[str, str]) -> str:
        configured = str(self.ctx.config.get("server.java_executable", "auto") or "auto").strip()

        if configured and configured.lower() != "auto":
            return str(self.ctx.resolve_path(configured) if not Path(configured).is_absolute() else Path(configured))

        atm11_java = env.get("ATM11_JAVA")
        if atm11_java:
            return atm11_java

        java_home = env.get("JAVA_HOME")
        if java_home:
            java_name = "java.exe" if os.name == "nt" else "java"
            java_path = Path(java_home) / "bin" / java_name
            if java_path.exists():
                return str(java_path)

        return shutil.which("java") or "java"

    def _java_major_version(self, java_executable: str) -> int | None:
        try:
            result = subprocess.run(
                [java_executable, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=15,
                check=False,
            )
        except Exception as exc:
            raise RuntimeError(f"Could not run Java executable '{java_executable}': {exc}") from exc

        output = result.stdout or ""
        match = re.search(r'version "(\d+)(?:[._]\d+)?', output)
        if not match:
            match = re.search(r"\b(\d+)(?:[._]\d+)?(?:\.\d+)*", output)

        if not match:
            self.ctx.logger.warning("Could not parse Java version output: %s", output.strip())
            return None

        return int(match.group(1))

    def _prepare_environment(self) -> dict[str, str]:
        env = os.environ.copy()

        for key, value in self.ctx.config.get("server.environment", {}).items():
            env[str(key)] = str(value)

        java_executable = self._resolve_java_executable(env)
        env["ATM11_JAVA"] = java_executable

        required_major = int(self.ctx.config.get("server.required_java_major", 0) or 0)
        if required_major:
            detected_major = self._java_major_version(java_executable)
            if detected_major is not None and detected_major < required_major:
                raise RuntimeError(
                    f"Java {required_major}+ is required, but '{java_executable}' is Java {detected_major}. "
                    "Install a newer JDK and set ATM11_JAVA, JAVA_HOME, or server.java_executable."
                )

        self.ctx.logger.info("Using Java executable: %s", java_executable)
        return env

    async def start(self) -> bool:
        server_dir: Path = self.ctx.server_dir
        configured_script = self.ctx.config.get("server.start_script", "auto")
        timeout = int(self.ctx.config.get("server.startup_timeout_seconds", 1800))
        self.startup_validated = False
        self.last_start_failure_reason = None
        self.startup_output_tail = []

        success_patterns = self.ctx.config.get(
            "server.startup_success_patterns",
            ['For help, type "help"'],
        )

        failure_patterns = self.ctx.config.get(
            "server.startup_failure_patterns",
            [
                "Failed to start the minecraft server",
                "Crash report saved",
                "This crash report has been saved",
                "A fatal error has been detected",
                "FatalStartupException",
                "session.lock: already locked",
            ],
        )

        if not server_dir.exists():
            raise FileNotFoundError(f"Server directory does not exist: {server_dir}")

        start_path = self._select_start_script(server_dir, configured_script)

        env = self._prepare_environment()

        self.ctx.logger.info("Starting server: %s", start_path)
        command = self._build_start_command(start_path)

        self.process = await asyncio.create_subprocess_exec(
            *command,
            **self._subprocess_kwargs(server_dir, env),
        )

        self.ctx.server_process = self

        loop = asyncio.get_running_loop()
        startup_deadline = loop.time() + timeout
        failure_matched = False
        failure_drain_deadline = None

        try:
            while True:
                now = loop.time()
                deadline = failure_drain_deadline if failure_matched else startup_deadline
                remaining = deadline - now

                if remaining <= 0:
                    if failure_matched:
                        self.ctx.logger.error("Server did not exit after startup failure; killing process")
                    else:
                        self.ctx.logger.error("Server startup timed out after %s seconds", timeout)
                    await self.kill()
                    return False

                line = await asyncio.wait_for(
                    self.process.stdout.readline(),
                    timeout=remaining,
                )

                if not line:
                    rc = await self.process.wait()
                    self.ctx.logger.error("Server exited during startup. code=%s", rc)
                    return False

                decoded = line.decode(errors="replace").rstrip()
                self._record_startup_line(decoded)
                self.log_mc_line(decoded)
                for event in parse_console_line(decoded):
                    await self.ctx.event_bus.publish(event)

                if not failure_matched and any(pattern in decoded for pattern in failure_patterns):
                    self.ctx.logger.error("Startup failure pattern matched: %s", decoded)
                    failure_matched = True
                    failure_drain_deadline = loop.time() + 10
                    continue

                if not failure_matched and any(pattern in decoded for pattern in success_patterns):
                    self.ctx.logger.info("Server startup validated")
                    self.startup_validated = True
                    await self.ctx.event_bus.publish(ServerStartedEvent(raw=decoded))
                    return True

        except asyncio.CancelledError:
            self.ctx.logger.warning("Startup task cancelled; stopping server")
            await self.ctx.event_bus.publish(ServerStoppingEvent(raw="Wrapper stopping server"))
            await self.stop()
            raise

        except KeyboardInterrupt:
            self.ctx.logger.warning("Keyboard interrupt during startup; stopping server")
            await self.ctx.event_bus.publish(ServerStoppingEvent(raw="Wrapper stopping server"))
            await self.stop()
            raise

    async def wait(self):
        if not self.process:
            return None

        return await self.process.wait()

    async def stop(self):
        if not self.process:
            return

        if self.process.returncode is not None:
            self.startup_validated = False
            return

        stop_command = self.ctx.config.get("server.stop_command", "stop")
        timeout = int(self.ctx.config.get("server.shutdown_timeout_seconds", 180))

        self.startup_validated = False
        self.ctx.logger.info("Stopping server gracefully with command: %s", stop_command)

        try:
            await self.ctx.event_bus.publish(ServerStoppingEvent(raw="Wrapper stopping server"))

            if self.process.stdin and not self.process.stdin.is_closing():
                self.process.stdin.write((stop_command + "\n").encode())
                await self.process.stdin.drain()

            rc = await asyncio.wait_for(self.process.wait(), timeout=timeout)
            self.ctx.logger.info("Server stopped cleanly")
            await self.ctx.event_bus.publish(
                ServerStoppedEvent(raw="Server stopped cleanly", exit_code=rc)
            )

        except asyncio.TimeoutError:
            self.ctx.logger.warning(
                "Server did not stop within %s seconds; killing process tree",
                timeout,
            )
            await self.kill()

        except Exception as e:
            self.ctx.logger.warning(
                "Graceful stop failed; killing process tree. Reason: %s",
                e,
            )
            await self.kill()

    async def terminate(self):
        if not self.process:
            return

        if self.process.returncode is not None:
            self.startup_validated = False
            return

        self.startup_validated = False
        self.ctx.logger.warning("Terminating server process tree")

        try:
            self._terminate_process_tree()
            rc = await asyncio.wait_for(self.process.wait(), timeout=20)
            await self.ctx.event_bus.publish(
                ServerStoppedEvent(raw="Server process terminated", exit_code=rc)
            )
        except Exception:
            await self.kill()

    async def kill(self):
        if not self.process:
            return

        if self.process.returncode is not None:
            self.startup_validated = False
            return

        self.startup_validated = False
        self.ctx.logger.error("Killing server process tree")

        self._kill_process_tree()

        try:
            await self.process.wait()
        except Exception:
            pass

        await self.ctx.event_bus.publish(
            ServerStoppedEvent(raw="Server process killed", exit_code=self.process.returncode)
        )

    def _process_tree(self):
        try:
            parent = psutil.Process(self.process.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return []

        try:
            children = parent.children(recursive=True)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            children = []

        return children + [parent]

    def _terminate_process_tree(self):
        if os.name != "nt":
            try:
                os.killpg(self.process.pid, signal.SIGTERM)
                return
            except ProcessLookupError:
                return
            except Exception as exc:
                self.ctx.logger.debug("POSIX process group terminate failed: %s", exc)

        for proc in self._process_tree():
            try:
                proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

    def _kill_process_tree(self):
        if os.name != "nt":
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
                return
            except ProcessLookupError:
                return
            except Exception as exc:
                self.ctx.logger.debug("POSIX process group kill failed: %s", exc)

        for proc in self._process_tree():
            try:
                proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
