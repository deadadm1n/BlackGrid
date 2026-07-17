package com.blackgrid.watchdoghelper.bridge;

import com.blackgrid.watchdoghelper.WatchDogHelper;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;

/**
 * Sends Minecraft chat out of the NeoForge server.
 *
 * This class does NOT talk to Discord directly.
 * It sends HTTP JSON to WatchDog or to a Discord bot helper endpoint.
 *
 * Flow:
 * player types in Minecraft
 *   -> WatchDogHelperChatBridgeHandler catches it
 *   -> this class POSTs JSON to outboundUrl
 *   -> WatchDog/the bot posts it to Discord
 */
public final class DiscordChatBridgeClient {

    // Reuse one HTTP client instead of creating a new networking goblin every chat message.
    private static final HttpClient CLIENT = HttpClient.newHttpClient();

    private DiscordChatBridgeClient() {
    }

    public static void sendMinecraftChat(String uuid, String player, String message) {
        DiscordChatBridgeConfig.Settings settings = DiscordChatBridgeConfig.get();

        // Master switch and direction switch. If either says no, do nothing.
        if (!settings.enabled || !settings.sendMinecraftChatToDiscord) {
            return;
        }

        // Do not send chat if the shared secret is missing or still "change-me".
        if (!settings.usableToken()) {
            WatchDogHelper.LOGGER.warn("[WatchDog Discord Chat] Minecraft -> Discord skipped because bridgeToken is not configured.");
            return;
        }

        // outboundUrl is where WatchDog/the Discord bot is listening for Minecraft chat.
        if (settings.outboundUrl == null || settings.outboundUrl.isBlank()) {
            return;
        }

        // Build the human-facing version the bot can post into Discord.
        String formatted = settings.minecraftToDiscordFormat
                .replace("{player}", player)
                .replace("{uuid}", uuid)
                .replace("{message}", message);

        // Keep the payload boring: token, channel, player info, raw message, formatted message.
        String json = "{"
                + "\"token\":\"" + escapeJson(settings.bridgeToken) + "\","
                + "\"type\":\"minecraft_chat\"," 
                + "\"channelId\":\"" + escapeJson(settings.gameChatChannelId) + "\","
                + "\"uuid\":\"" + escapeJson(uuid) + "\","
                + "\"player\":\"" + escapeJson(player) + "\","
                + "\"message\":\"" + escapeJson(message) + "\","
                + "\"formatted\":\"" + escapeJson(formatted) + "\""
                + "}";

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(settings.outboundUrl))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json, StandardCharsets.UTF_8))
                .build();

        // Fire async so Minecraft chat is not blocked by Discord/WatchDog being slow or dead.
        CLIENT.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                .exceptionally(error -> {
                    WatchDogHelper.LOGGER.warn("[WatchDog Discord Chat] Failed to send Minecraft chat to Discord bridge: {}", error.getMessage());
                    return null;
                });
    }

    /**
     * Tiny JSON string escaper because this payload is hand-built.
     * Later we can replace this with Gson if this grows more tentacles.
     */
    private static String escapeJson(String value) {
        if (value == null) {
            return "";
        }

        StringBuilder out = new StringBuilder();

        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);

            switch (c) {
                case '"' -> out.append("\\\"");
                case '\\' -> out.append("\\\\");
                case '\b' -> out.append("\\b");
                case '\f' -> out.append("\\f");
                case '\n' -> out.append("\\n");
                case '\r' -> out.append("\\r");
                case '\t' -> out.append("\\t");
                default -> {
                    if (c < 0x20) {
                        out.append(String.format("\\u%04x", (int) c));
                    } else {
                        out.append(c);
                    }
                }
            }
        }

        return out.toString();
    }
}
