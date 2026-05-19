from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass
class CommandResult:
    ok: bool = True
    message: str = ""
    data: dict | None = None

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "message": self.message,
            "data": self.data or {},
        }


@dataclass
class CommandSpec:
    name: str
    help: str
    handler: Callable
    owner: str = "core"
    usage: str = ""
    permission: str = "admin"


class CommandRegistry:
    def __init__(self, logger):
        self.logger = logger
        self.commands: dict[str, CommandSpec] = {}

    def register(
        self,
        name: str,
        handler: Callable[[list[str]], Awaitable[CommandResult] | CommandResult],
        help: str,
        *,
        owner: str = "core",
        usage: str = "",
        permission: str = "admin",
    ):
        normalized = self.normalize_name(name)
        self.commands[normalized] = CommandSpec(
            name=normalized,
            help=help,
            handler=handler,
            owner=owner,
            usage=usage,
            permission=permission,
        )
        self.logger.debug("Command registered: owner=%s name=%s", owner, normalized)

    def unregister_owner(self, owner: str) -> int:
        names = [
            name
            for name, spec in self.commands.items()
            if spec.owner == owner
        ]

        for name in names:
            del self.commands[name]

        if names:
            self.logger.info("Removed %s command(s) for plugin: %s", len(names), owner)

        return len(names)

    def list_commands(self) -> list[dict]:
        return [
            {
                "name": spec.name,
                "owner": spec.owner,
                "help": spec.help,
                "usage": spec.usage,
                "permission": spec.permission,
            }
            for spec in sorted(self.commands.values(), key=lambda item: item.name)
        ]

    async def execute(self, raw: str) -> CommandResult:
        tokens = raw.strip().split()

        if not tokens:
            return CommandResult(ok=False, message="No command provided")

        if tokens[0].lower() == "wrapper":
            tokens = tokens[1:]

        if not tokens:
            return CommandResult(ok=False, message="Missing wrapper command")

        command_name, args = self.resolve(tokens)

        if not command_name:
            return CommandResult(
                ok=False,
                message=f"Unknown wrapper command: {' '.join(tokens)}",
                data={"available": self.list_commands()},
            )

        spec = self.commands[command_name]
        result = spec.handler(args)

        if hasattr(result, "__await__"):
            result = await result

        if isinstance(result, CommandResult):
            return result

        if isinstance(result, dict):
            return CommandResult(ok=True, data=result)

        return CommandResult(ok=True, message=str(result) if result is not None else "")

    def resolve(self, tokens: list[str]) -> tuple[str | None, list[str]]:
        lowered = [token.lower() for token in tokens]

        for length in range(len(lowered), 0, -1):
            candidate = self.normalize_name(" ".join(lowered[:length]))
            if candidate in self.commands:
                return candidate, tokens[length:]

        return None, tokens

    @staticmethod
    def normalize_name(name: str) -> str:
        return " ".join(str(name).strip().lower().split())
