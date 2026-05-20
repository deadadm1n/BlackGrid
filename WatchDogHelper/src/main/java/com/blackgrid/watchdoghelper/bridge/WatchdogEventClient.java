package com.blackgrid.watchdoghelper.bridge;

import com.blackgrid.watchdoghelper.WatchDogHelper;
import com.blackgrid.watchdoghelper.Config;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;

public final class WatchdogEventClient {

    private static final HttpClient CLIENT = HttpClient.newHttpClient();

    private WatchdogEventClient() {
    }

    public static void sendChatEvent(String uuid, String player, String message) {
        sendEvent("\"type\":\"chat\","
                + "\"uuid\":\"" + escapeJson(uuid) + "\","
                + "\"player\":\"" + escapeJson(player) + "\","
                + "\"message\":\"" + escapeJson(message) + "\"");
    }

    public static void sendDiscordLinkEvent(String uuid, String player, String code) {
        sendEvent("\"type\":\"discord_link\","
                + "\"uuid\":\"" + escapeJson(uuid) + "\","
                + "\"player\":\"" + escapeJson(player) + "\","
                + "\"code\":\"" + escapeJson(code) + "\"");
    }

    private static void sendEvent(String jsonFields) {
        if (!Config.WATCHDOG_CALLBACK_ENABLED.get()) {
            return;
        }

        String callbackUrl = Config.WATCHDOG_CALLBACK_URL.get();
        String token = Config.BRIDGE_TOKEN.get();

        if (callbackUrl == null || callbackUrl.isBlank()) {
            return;
        }

        if (token == null || token.isBlank() || "change-me".equals(token)) {
            WatchDogHelper.LOGGER.warn("[AetherReach] Watchdog callback skipped because bridgeToken is not configured.");
            return;
        }

        String json = "{"
                + "\"token\":\"" + escapeJson(token) + "\","
                + jsonFields
                + "}";

        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(callbackUrl))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json, StandardCharsets.UTF_8))
                .build();

        CLIENT.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                .exceptionally(error -> {
                    WatchDogHelper.LOGGER.warn("[AetherReach] Failed to send chat event to Watchdog: {}", error.getMessage());
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
