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
  "sendMinecraftChatToDiscord": true,
  "allowDiscordToMinecraft": true,
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
| `sendMinecraftChatToDiscord` | Enables Minecraft -> Discord messages when the bridge is enabled. |
| `allowDiscordToMinecraft` | Enables Discord -> Minecraft messages when the bridge is enabled. |
| `minecraftToDiscordFormat` | Message format sent outbound. Supports `{player}`, `{uuid}`, and `{message}`. |
| `discordToMinecraftPrefix` | Prefix shown in Minecraft for Discord messages. |

## NeoForge config still matters

The existing NeoForge config still controls whether the helper HTTP bridge starts:

```text
bridgeEnabled=true
bridgeHost=127.0.0.1
bridgePort=25590
bridgeToken=<same shared secret>
```

`WatchDog/discord-chat.json` controls the Discord chat feature itself.

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

## Rule

The base Minecraft server should not include this by default.

BlackGrid should offer it as an optional addon only when the detected loader supports it:

```text
Minecraft -> NeoForge/Forge -> optional BlackGrid Minecraft helper -> optional Discord chat bridge
```
