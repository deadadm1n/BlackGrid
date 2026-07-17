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

/**
 * Tiny HTTP server that runs inside the NeoForge Minecraft server.
 *
 * Why this exists:
 * - Discord cannot directly talk to Minecraft chat.
 * - WatchDog/the Discord bot can send HTTP to this mod.
 * - This mod can safely schedule work back onto Minecraft's server thread.
 *
 * There are two bridge families here:
 * 1. Legacy WatchDog helper endpoints: /api/veil and /api/broadcast
 * 2. Discord chat endpoint: /api/discord
 *
 * The Discord endpoint is controlled by WatchDog/discord-chat.json.
 */
public final class BridgeService {

    private static final Gson GSON = new Gson();

    // The embedded HTTP server. Null means it is not running.
    private static HttpServer httpServer;

    // The live Minecraft server instance. Needed so HTTP requests can broadcast messages in-game.
    private static MinecraftServer minecraftServer;

    private BridgeService() {}

    public static synchronized void start(MinecraftServer server) {
        minecraftServer = server;

        DiscordChatBridgeConfig.Settings discordSettings = DiscordChatBridgeConfig.get();

        // Old helper bridge toggle from NeoForge config.
        boolean legacyBridgeEnabled = Config.BRIDGE_ENABLED.get();

        // New Discord bridge toggle from <server>/WatchDog/discord-chat.json.
        boolean discordBridgeEnabled = discordSettings.enabled && discordSettings.allowDiscordToMinecraft;

        // If both bridge systems are off, do not open a port at all.
        if (!legacyBridgeEnabled && !discordBridgeEnabled) {
            WatchDogHelper.LOGGER.info("[WatchDog Helper Bridge] Bridge disabled. Enable NeoForge config bridgeEnabled or WatchDog/discord-chat.json enabled.");
            return;
        }

        // Do not start two HTTP servers on the same port.
        if (httpServer != null) {
            return;
        }

        // Discord bridge gets first pick because it owns the new server-folder config.
        String host = discordBridgeEnabled ? discordSettings.inboundHost : Config.BRIDGE_HOST.get();
        int port = discordBridgeEnabled ? discordSettings.inboundPort : Config.BRIDGE_PORT.getAsInt();

        try {
            httpServer = HttpServer.create(new InetSocketAddress(host, port), 0);

            // Legacy endpoints for old WatchDog helper behavior.
            if (legacyBridgeEnabled) {
                httpServer.createContext("/api/veil", BridgeService::handleVeil);
                httpServer.createContext("/api/broadcast", BridgeService::handleBroadcast);
            }

            // Discord -> Minecraft endpoint.
            if (discordBridgeEnabled) {
                httpServer.createContext(discordSettings.inboundDiscordPath, BridgeService::handleDiscord);

                // Keep /api/discord available as a fallback if the config uses a custom path.
                if (!"/api/discord".equals(discordSettings.inboundDiscordPath)) {
                    httpServer.createContext("/api/discord", BridgeService::handleDiscord);
                }
            }

            // Status endpoint is handy for WatchDog health checks and human debugging.
            httpServer.createContext(discordSettings.statusPath, BridgeService::handleStatus);
            if (!"/api/status".equals(discordSettings.statusPath)) {
                httpServer.createContext("/api/status", BridgeService::handleStatus);
            }

            // Small worker pool because these requests should be tiny.
            httpServer.setExecutor(Executors.newFixedThreadPool(2));
            httpServer.start();

            WatchDogHelper.LOGGER.info("[WatchDog Helper Bridge] Listening on http://{}:{}", host, port);
        } catch (IOException e) {
            WatchDogHelper.LOGGER.error("[WatchDog Helper Bridge] Failed to start bridge server", e);
        }
    }

    public static synchronized void restart(MinecraftServer server) {
        stop();
        start(server);
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

    /**
     * Discord -> Minecraft endpoint.
     *
     * Expected JSON:
     * {
     *   "token": "shared secret",
     *   "channelId": "discord channel id",
     *   "author": "Discord name",
     *   "message": "text to show in Minecraft"
     * }
     */
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

        // Feature switch check. Disabled means no Discord messages go into Minecraft.
        if (!settings.enabled || !settings.allowDiscordToMinecraft) {
            sendJson(exchange, 503, error("discord chat bridge disabled"));
            return;
        }

        // Shared-token check. This is the basic lock on the door.
        if (!isAuthorized(body, settings)) {
            sendJson(exchange, 403, error("unauthorized"));
            return;
        }

        // Channel check. Prevents a bot from forwarding the wrong Discord channel into game chat.
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

        // Minecraft objects should be touched on the Minecraft server thread.
        server.execute(() -> broadcast(discordMessage(author, message)));
        sendJson(exchange, 202, ok("accepted"));
    }

    /**
     * Debug/health endpoint.
     *
     * GET is open because it only reports harmless status.
     * POST requires the legacy bridge token because old WatchDog health checks may use POST.
     */
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

        DiscordChatBridgeConfig.Settings settings = DiscordChatBridgeConfig.get();
        JsonObject response = new JsonObject();
        response.addProperty("ok", true);
        response.addProperty("mod", "watchdog_helper");
        response.addProperty("bridge", httpServer == null ? "offline" : "online");
        response.addProperty("discordChatBridgeEnabled", settings.enabled);
        response.addProperty("discordToMinecraftEnabled", settings.allowDiscordToMinecraft);
        response.addProperty("minecraftToDiscordEnabled", settings.sendMinecraftChatToDiscord);
        response.addProperty("configuredChannel", !settings.gameChatChannelId.isBlank());
        response.addProperty("configPath", DiscordChatBridgeConfig.path() == null ? "" : DiscordChatBridgeConfig.path().toString());
        response.addProperty("serverAvailable", minecraftServer != null);

        if (minecraftServer != null) {
            response.addProperty("playersOnline", minecraftServer.getPlayerList().getPlayerCount());
            response.addProperty("maxPlayers", minecraftServer.getPlayerList().getMaxPlayers());
        }

        sendJson(exchange, 200, response);
    }

    /**
     * Legacy message endpoints used by old helper features.
     * These are not the new Discord chat bridge, but they share the same tiny HTTP server.
     */
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

    /**
     * Legacy auth check that uses the NeoForge helper config token.
     */
    private static boolean isAuthorized(JsonObject body) {
        String configuredToken = Config.BRIDGE_TOKEN.get();
        if (configuredToken == null || configuredToken.isBlank() || "change-me".equals(configuredToken)) {
            WatchDogHelper.LOGGER.warn("[WatchDog Helper Bridge] bridgeToken is not configured securely.");
            return false;
        }

        String suppliedToken = getString(body, "token", "");
        return configuredToken.equals(suppliedToken);
    }

    /**
     * Discord chat auth check that uses WatchDog/discord-chat.json.
     */
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
