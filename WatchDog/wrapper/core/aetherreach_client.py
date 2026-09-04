import asyncio
from http.client import RemoteDisconnected
from typing import Any, Dict, Optional

import requests
from requests import exceptions as request_exceptions


class AetherReachClient:
    """Small async wrapper around the local WatchDog Helper HTTP bridge."""

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.enabled = bool(config.get("bridges.aetherreach.enabled", config.get("aetherreach_bridge.enabled", False)))
        self.base_url = str(config.get("bridges.aetherreach.url", config.get("aetherreach_bridge.url", ""))).rstrip("/")
        self.token = str(config.get("bridges.aetherreach.token", config.get("aetherreach_bridge.token", "")))
        try:
            self.timeout = float(config.get("bridges.aetherreach.timeout_seconds", config.get("aetherreach_bridge.timeout_seconds", 3)))
        except (TypeError, ValueError):
            self.timeout = 3.0
        if self.timeout <= 0:
            self.timeout = 3.0

    def ready(self) -> bool:
        return self.enabled and bool(self.base_url) and bool(self.token) and self.token != "change-me"

    async def veil(self, message: str) -> bool:
        return await self._post("/api/veil", {"message": message})

    async def broadcast(self, message: str) -> bool:
        return await self._post("/api/broadcast", {"message": message})

    async def discord_message(self, author: str, message: str, channel_id: str = "") -> bool:
        payload = {"author": author, "message": message}
        if channel_id:
            payload["channelId"] = channel_id
        return await self._post("/api/discord", payload)

    async def status(self) -> Optional[Dict[str, Any]]:
        if not self.ready():
            return None

        def request_status():
            response = requests.post(
                f"{self.base_url}/api/status",
                json={"token": self.token},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()

        try:
            return await asyncio.to_thread(request_status)
        except Exception as exc:
            self.logger.debug("[HelperBridge] Status request failed: %s", exc)
            return None

    async def _post(self, path: str, payload: Dict[str, Any]) -> bool:
        if not self.ready():
            self.logger.debug("[HelperBridge] Bridge disabled or token not configured")
            return False

        body = dict(payload)
        body["token"] = self.token

        def send():
            response = requests.post(
                f"{self.base_url}{path}",
                json=body,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response

        try:
            await asyncio.to_thread(send)
            return True
        except (
            request_exceptions.ConnectionError,
            request_exceptions.ConnectTimeout,
            request_exceptions.ReadTimeout,
            RemoteDisconnected,
        ) as exc:
            self.logger.debug("[HelperBridge] POST %s skipped; bridge offline: %s", path, exc)
            return False
        except request_exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            self.logger.warning("[HelperBridge] POST %s rejected with HTTP %s", path, status)
            return False
        except Exception as exc:
            self.logger.warning("[HelperBridge] POST %s failed: %s", path, exc)
            return False
