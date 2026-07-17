package com.blackgrid.watchdoghelper.bridge;

import com.blackgrid.watchdoghelper.WatchDogHelper;
import com.blackgrid.watchdoghelper.Config;
import com.google.gson.Gson;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.MinecraftServer;

import java.io.IOException;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.Executors;

public final class BridgeService {

    private static final Gson GSON = new Gson();

    private static HttpServer httpServer;
    private static MinecraftServer minecraftServer;

    private BridgeService() {}

    public static synchronized void start(MinecraftServer server) {
        minecraftServer = server;

        if (!Config.BRIDGE_ENABLED.get()) {
            WatchDogHelper.LOGGER.info("[WatchDog Helper Bridge] Bridge disabled in NeoForge config.");
            return;
        }

        if (httpServer != null) {
            return;
        }

        String host = Config.BRIDGE_HOST.get();
        int port = Config.BRIDGE_PORT.getAsInt();

        try {
            httpServer = HttpServer.create(new InetSocketAddress(host, port), 0);
            httpServer.createContext("/api/veil", BridgeService::handleVeil);
            httpServer.createContext("/api/broadcast", BridgeService::handleBroadcast);
            httpServer.createContext("/api/discord", BridgeService::handleDiscord);
            httpServer.createContext("/api/status", BridgeService::handleStatus);
            httpServer.setExecutor(Executors.newFixedThreadPool(2));
            httpServer.start();

            WatchDogHelper.LOGGER.info("[WatchDog Helper Bridge] Listening on http://{}:{}", host, port);
        } catch (IOException e) {
            WatchDogHelper.LOGGER.error("[WatchDog Helper Bridge] Failed to start bridge server", e);
        }
    }

    public static synchronized void stop() {
        if (httpServer != null) {
            httpServer.stop(1);
            httpServer = null;
            WatchDogHelper.LOGGER.info("[WatchDog Helper Bridge] Bridge stopped.");
        }

        minecraftServer = null;
    }

    private static void handleVeil(HttpExchange exchange) throws IOException {
        handleMessageEndpoint(exchange, "veil");
    }

    private static void handleBroadcast(HttpExchange exchange) throws IOException {
        handleMessageEndpoint(exchange, "broadcast");
    }

    private static void handleDiscord(HttpExchange exchange) throws IOException {
        if (!requirePost(exchange)) {
            return;
        }

        JsonObject body = readJson(exchange);
        if (body == null) {
            sendJson(exchange, 400, error("invalid json"));
            return;
        }

        DiscordChatBridgeConfig.Settings settings = DiscordChatBridgeConfig.get();
        if (!settings.enabled || !settings.allowDiscordToMinecraft) {
            sendJson(exchange, 503, error("discord chat bridge disabled"));
            return;
        }

        if (!isAuthorized(body, settings)) {
            sendJson(exchange, 403, error("unauthorized"));
            return;
        }

        String channelId = getString(body, "channelId", "").trim();
        if (!settings.gameChatChannelId.isBlank() && !settings.gameChatChannelId.equals(channelId)) {
            sendJson(exchange, 403, error("wrong discord channel"));
            return;
        }

        String author = getString(body, "author", "Discord");
        String message = getString(body, "message", "").trim();

        if (message.isEmpty()) {
            sendJson(exchange, 400, error("missing message"));
            return;
        }

        MinecraftServer server = minecraftServer;
        if (server == null) {
            sendJson(exchange, 503, error("minecraft server unavailable"));
            return;
        }

        server.execute(() -> broadcast(discordMessage(author, message)));
        sendJson(exchange, 202, ok("accepted"));
    }

    private static void handleStatus(HttpExchange exchange) throws IOException {
        if (!"GET".equalsIgnoreCase(exchange.getRequestMethod()) && !"POST".equalsIgnoreCase(exchange.getRequestMethod())) {
            sendJson(exchange, 405, error("method not allowed"));
            return;
        }

        if ("POST".equalsIgnoreCase(exchange.getRequestMethod())) {
            JsonObject body = readJson(exchange);
            if (body == null) {
                sendJson(exchange, 400, error("invalid json"));
                return;
            }

            if (!isAuthorized(body)) {
                sendJson(exchange, 403, error("unauthorized"));
                return;
            }
        }

        JsonObject response = new JsonObject();
        response.addProperty("ok", true);
        response.addProperty("mod", "watchdog_helper");
        response.addProperty("bridge", "online");
        response.addProperty("discordChatBridgeEnabled", DiscordChatBridgeConfig.get().enabled);
        response.addProperty("serverAvailable", minecraftServer != null);

        if (minecraftServer != null) {
            response.addProperty("playersOnline", minecraftServer.getPlayerList().getPlayerCount());
            response.addProperty("maxPlayers", minecraftServer.getPlayerList().getMaxPlayers());
        }

        sendJson(exchange, 200, response);
    }

    private static void handleMessageEndpoint(HttpExchange exchange, String mode) throws IOException {
        if (!requirePost(exchange)) {
            return;
        }

        JsonObject body = readJson(exchange);
        if (body == null) {
            sendJson(exchange, 400, error("invalid json"));
            return;
        }

        if (!isAuthorized(body)) {
            sendJson(exchange, 403, error("unauthorized"));
            return;
        }

        String message = getString(body, "message", "").trim();
        if (message.isEmpty()) {
            sendJson(exchange, 400, error("missing message"));
            return;
        }

        MinecraftServer server = minecraftServer;
        if (server == null) {
            sendJson(exchange, 503, error("minecraft server unavailable"));
            return;
        }

        server.execute(() -> {
            if ("veil".equals(mode)) {
                broadcast(veilMessage(message));
            } else {
                broadcast(aetherMessage(message));
            }
        });

        sendJson(exchange, 202, ok("accepted"));
    }

    private static boolean requirePost(HttpExchange exchange) throws IOException {
        if (!"POST".equalsIgnoreCase(exchange.getRequestMethod())) {
            sendJson(exchange, 405, error("method not allowed"));
            return false;
        }

        return true;
    }

    private static JsonObject readJson(HttpExchange exchange) throws IOException {
        String raw = new String(exchange.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
        if (raw.isBlank()) {
            return new JsonObject();
        }

        try {
            return JsonParser.parseString(raw).getAsJsonObject();
        } catch (Exception e) {
            WatchDogHelper.LOGGER.warn("[WatchDog Helper Bridge] Invalid JSON request body: {}", e.getMessage());
            return null;
        }
    }

    private static boolean isAuthorized(JsonObject body) {
        String configuredToken = Config.BRIDGE_TOKEN.get();
        if (configuredToken == null || configuredToken.isBlank() || "change-me".equals(configuredToken)) {
            WatchDogHelper.LOGGER.warn("[WatchDog Helper Bridge] bridgeToken is not configured securely.");
            return false;
        }

        String suppliedToken = getString(body, "token", "");
        return configuredToken.equals(suppliedToken);
    }

    private static boolean isAuthorized(JsonObject body, DiscordChatBridgeConfig.Settings settings) {
        if (!settings.usableToken()) {
            WatchDogHelper.LOGGER.warn("[WatchDog Discord Chat] bridgeToken is not configured securely.");
            return false;
        }

        String suppliedToken = getString(body, "token", "");
        return settings.bridgeToken.equals(suppliedToken);
    }

    private static String getString(JsonObject body, String key, String fallback) {
        if (body == null || !body.has(key) || body.get(key).isJsonNull()) {
            return fallback;
        }

        try {
            return body.get(key).getAsString();
        } catch (Exception ignored) {
            return fallback;
        }
    }

    private static JsonObject ok(String message) {
        JsonObject response = new JsonObject();
        response.addProperty("ok", true);
        response.addProperty("message", message);
        return response;
    }

    private static JsonObject error(String message) {
        JsonObject response = new JsonObject();
        response.addProperty("ok", false);
        response.addProperty("error", message);
        return response;
    }

    private static void sendJson(HttpExchange exchange, int status, JsonObject body) throws IOException {
        byte[] data = GSON.toJson(body).getBytes(StandardCharsets.UTF_8);
        exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
        exchange.sendResponseHeaders(status, data.length);

        try (OutputStream output = exchange.getResponseBody()) {
            output.write(data);
        }
    }

    private static void broadcast(Component message) {
        MinecraftServer server = minecraftServer;
        if (server == null) {
            return;
        }

        server.getPlayerList().broadcastSystemMessage(message, false);
    }

    private static MutableComponent veilMessage(String text) {
        return Component.literal(formatLore(Config.VEIL_PREFIX.get()))
                .withStyle(ChatFormatting.LIGHT_PURPLE)
                .append(Component.literal(text).withStyle(ChatFormatting.GRAY));
    }

    private static MutableComponent aetherMessage(String text) {
        return Component.literal(formatLore(Config.SERVER_PREFIX.get()))
                .withStyle(ChatFormatting.LIGHT_PURPLE)
                .append(Component.literal(text).withStyle(ChatFormatting.GRAY));
    }

    private static MutableComponent discordMessage(String author, String text) {
        DiscordChatBridgeConfig.Settings settings = DiscordChatBridgeConfig.get();
        String prefix = settings.discordToMinecraftPrefix == null ? "[Discord] " : settings.discordToMinecraftPrefix;
        return Component.literal(prefix)
                .withStyle(ChatFormatting.DARK_AQUA)
                .append(Component.literal(author).withStyle(ChatFormatting.AQUA))
                .append(Component.literal(": ").withStyle(ChatFormatting.GRAY))
                .append(Component.literal(text).withStyle(ChatFormatting.WHITE));
    }

    private static String formatLore(String template) {
        return template
                .replace("{veil}", Config.VEIL_NAME.get())
                .replace("{server}", Config.SERVER_NAME.get())
                .replace("{helper}", Config.HELPER_NAME.get());
    }
}
