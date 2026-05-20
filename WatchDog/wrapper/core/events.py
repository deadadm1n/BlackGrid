from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, List, Optional, Type


@dataclass
class Event:
    raw: str = ""


@dataclass
class ConsoleLineEvent(Event):
    line: str = ""


@dataclass
class ServerStartedEvent(Event):
    pass


@dataclass
class ServerStoppingEvent(Event):
    pass


@dataclass
class ServerStoppedEvent(Event):
    exit_code: int | None = None


@dataclass
class PlayerJoinEvent(Event):
    player: str = ""


@dataclass
class PlayerLeaveEvent(Event):
    player: str = ""


@dataclass
class ChatMessageEvent(Event):
    player: str = ""
    message: str = ""


@dataclass
class DiscordLinkEvent(Event):
    uuid: str = ""
    player: str = ""
    code: str = ""


@dataclass
class ServerCrashEvent(Event):
    reason: str = ""


class EventBus:
    """
    Event bus with plugin ownership tracking.

    Why owner tracking matters:
    - Hot-reloading a plugin must remove old event handlers.
    - Otherwise every reload duplicates events.
    """

    def __init__(self, logger):
        self.logger = logger
        self.subscribers: Dict[Type[Event], List[dict]] = {}
        self._current_owner: Optional[str] = None

    def set_current_owner(self, owner: Optional[str]):
        self._current_owner = owner

    def subscribe(
        self,
        event_type: Type[Event],
        handler: Callable[[Event], Awaitable[None]],
        owner: Optional[str] = None,
    ):
        resolved_owner = owner or self._current_owner or "unknown"

        self.subscribers.setdefault(event_type, []).append(
            {
                "owner": resolved_owner,
                "handler": handler,
            }
        )

        self.logger.debug(
            "Event subscription registered: owner=%s event=%s handler=%s",
            resolved_owner,
            event_type.__name__,
            getattr(handler, "__name__", repr(handler)),
        )

    def unsubscribe_owner(self, owner: str) -> int:
        removed = 0

        for event_type in list(self.subscribers.keys()):
            old_items = self.subscribers[event_type]
            new_items = [item for item in old_items if item.get("owner") != owner]
            removed += len(old_items) - len(new_items)

            if new_items:
                self.subscribers[event_type] = new_items
            else:
                del self.subscribers[event_type]

        self.logger.info("Removed %s event subscription(s) for plugin: %s", removed, owner)
        return removed

    async def publish(self, event: Event):
        handlers = []

        for event_type, event_handlers in list(self.subscribers.items()):
            if isinstance(event, event_type):
                handlers.extend(event_handlers)

        for item in handlers:
            handler = item["handler"]
            owner = item.get("owner", "unknown")

            try:
                await handler(event)
            except Exception:
                self.logger.exception(
                    "Event handler failed: owner=%s event=%s",
                    owner,
                    type(event).__name__,
                )
