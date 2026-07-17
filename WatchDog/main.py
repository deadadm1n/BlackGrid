import argparse
import asyncio
import sys


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="watchdog",
        description="Run one WatchDog server wrapper instance.",
    )
    parser.add_argument(
        "--config",
        default="config/wrapper.yaml",
        help="Path to the WatchDog wrapper config file. Defaults to config/wrapper.yaml.",
    )
    parser.add_argument(
        "--skip-system-check",
        action="store_true",
        help="Skip the minimum server startup checks. Use only when you know which gremlin you are feeding.",
    )
    return parser.parse_args()


def run_system_check(config_path: str) -> None:
    try:
        from server_system_check import run_server_system_check
    except ModuleNotFoundError as exc:
        missing = exc.name or str(exc)
        print(
            f"Missing Python package for WatchDog system check: {missing}\n"
            "Install the wrapper requirements with:\n"
            f'  "{sys.executable}" -m pip install -r requirements.txt',
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    code = run_server_system_check(config_path)
    if code:
        raise SystemExit(code)


async def main():
    args = parse_args()

    if not args.skip_system_check:
        run_system_check(args.config)

    try:
        from wrapper.core.app import WrapperApp
    except ModuleNotFoundError as exc:
        missing = exc.name or str(exc)
        print(
            f"Missing Python package: {missing}\n"
            "Install the wrapper requirements with:\n"
            f'  "{sys.executable}" -m pip install -r requirements.txt',
            file=sys.stderr,
        )
        raise SystemExit(1) from exc

    app = WrapperApp(config_path=args.config)
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
