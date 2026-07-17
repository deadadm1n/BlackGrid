package com.blackgrid.watchdoghelper.bridge;

import com.blackgrid.watchdoghelper.WatchDogHelper;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;

public final class DiscordChatBridgeClient {

    private static final HttpClient CLIENT = HttpClient.newHttpClient();

    private DiscordChatBridgeClient() {
    }

    public static void sendMinecraftChat(String uuid, String player, String message) {
        DiscordChatBridgeConfig.Settings settings = DiscordChatBridgeConfig.get();

        if (!settings.enabled || !settings.sendMinecraftChatToDiscord) {
            return;
        }

        if (!settings.usableToken()) {
            WatchDogHelper.LOGGER.warn("[WatchDog Discord Chat] Minecraft -> Discord skipped because bridgeToken is not configured.");
            return;
        }

        if (settings.outboundUrl == null || settings.outboundUrl.isBlank()) {
            return;
        }

        String formatted = settings.minecraftToDiscordFormat
                .replace("{player}", player)
                .replace("{uuid}", uuid)
                .replace("{message}", message);

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

        CLIENT.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                .exceptionally(error -> {
                    WatchDogHelper.LOGGER.warn("[WatchDog Discord Chat] Failed to send Minecraft chat to Discord bridge: {}", error.getMessage());
                    return null;
                });
    }

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
