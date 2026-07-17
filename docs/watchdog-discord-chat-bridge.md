# WatchDog Discord chat bridge

The WatchDog Helper NeoForge mod has a small optional Minecraft chat bridge.

It is designed for this flow:

```text
Minecraft / NeoForge chat
  -> WatchDog Helper mod
  -> WatchDog or Discord bot HTTP endpoint
  -> Discord channel

Discord bot message
  -> WatchDog Helper HTTP bridge
  -> Minecraft / NeoForge chat
```

The mod does **not** enable this by default. A server operator has to turn it on.

## Config location

On server start, the helper creates this folder and file inside the Minecraft server folder:

```text
WatchDog/discord-chat.json
```

Default config:

```json
{
  "enabled": false,
  "mode": "watchdog_bot",
  "gameChatChannelId": "",
  "botToken": "",
  "bridgeToken": "change-me",
  "outboundUrl": "http://127.0.0.1:8081/api/discord/minecraft-chat",
  "inboundHost": "127.0.0.1",
  "inboundPort": 25590,
  "inboundDiscordPath": "/api/discord",
  "statusPath": "/api/status",
  "sendMinecraftChatToDiscord": true,
  "allowDiscordToMinecraft": true,
  "ignoreWebhookLikeMessages": true,
  "minecraftToDiscordFormat": "<{player}> {message}",
  "discordToMinecraftPrefix": "[Discord] "
}
```

`enabled` is the kill switch. It defaults to `false`.

## Fields

| Field | Purpose |
| --- | --- |
| `enabled` | Master enable/disable switch. Default off. |
| `mode` | Intended bridge mode. Currently `watchdog_bot`. |
| `gameChatChannelId` | Discord channel ID for game chat. Used so the bot and mod agree on the target channel. |
| `botToken` | Reserved for future direct bot mode. Prefer keeping the bot token in WatchDog, not inside the Minecraft mod. |
| `bridgeToken` | Shared secret used between WatchDog/the Discord bot and the helper mod. Must not be `change-me`. |
| `outboundUrl` | HTTP endpoint that receives Minecraft chat and forwards it to Discord. |
| `inboundHost` | Local host/IP where the helper listens for Discord -> Minecraft messages. Default `127.0.0.1`. |
| `inboundPort` | Local port where the helper listens. Default `25590`. |
| `inboundDiscordPath` | HTTP path for Discord -> Minecraft messages. Default `/api/discord`. |
| `statusPath` | HTTP path for helper status checks. Default `/api/status`. |
| `sendMinecraftChatToDiscord` | Enables Minecraft -> Discord messages when the bridge is enabled. |
| `allowDiscordToMinecraft` | Enables Discord -> Minecraft messages when the bridge is enabled. |
| `ignoreWebhookLikeMessages` | Reserved safety switch for loop prevention when the bot side is added. |
| `minecraftToDiscordFormat` | Message format sent outbound. Supports `{player}`, `{uuid}`, and `{message}`. |
| `discordToMinecraftPrefix` | Prefix shown in Minecraft for Discord messages. |

## NeoForge-side HTTP bridge

The Discord chat bridge can start the helper HTTP server from `WatchDog/discord-chat.json` alone.

That means the old NeoForge common config does not have to enable the generic helper bridge just for chat. The old config still works for legacy endpoints like `/api/veil` and `/api/broadcast`, but Discord chat has its own server-folder config now.

## Inbound Discord -> Minecraft

The Discord bot or WatchDog can post to the helper bridge:

```http
POST /api/discord
Content-Type: application/json
```

```json
{
  "token": "shared-secret",
  "channelId": "123456789012345678",
  "author": "DiscordUser",
  "message": "hello from Discord"
}
```

The helper rejects the message if:

```text
- enabled=false
- allowDiscordToMinecraft=false
- token does not match
- channelId does not match gameChatChannelId
```

## Outbound Minecraft -> Discord

When a player chats in-game, the NeoForge chat event sends this payload to `outboundUrl`:

```json
{
  "token": "shared-secret",
  "type": "minecraft_chat",
  "channelId": "123456789012345678",
  "uuid": "player-uuid",
  "player": "PlayerName",
  "message": "hello from Minecraft",
  "formatted": "<PlayerName> hello from Minecraft"
}
```

The Discord bot side still needs to consume that endpoint and post to Discord. That belongs in WatchDog/the bot, not inside the Minecraft mod, so the server jar does not have to carry a Discord gateway client.

## Commands

Operators can inspect or reload the server-folder bridge config without restarting Minecraft:

```text
/watchdog discord status
/watchdog discord reload
/watchdogdiscord status
/watchdogdiscord reload
```

Reloading re-reads `WatchDog/discord-chat.json` and restarts the helper HTTP listener if needed.

## Rule

The base Minecraft server should not include this by default.

BlackGrid should offer it as an optional addon only when the detected loader supports it:

```text
Minecraft -> NeoForge/Forge -> optional BlackGrid Minecraft helper -> optional Discord chat bridge
```
