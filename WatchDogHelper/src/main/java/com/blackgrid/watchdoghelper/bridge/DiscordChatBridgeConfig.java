package com.blackgrid.watchdoghelper.bridge;

import com.blackgrid.watchdoghelper.WatchDogHelper;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import net.minecraft.server.MinecraftServer;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

/**
 * Handles the plain JSON config for the optional Minecraft <-> Discord chat bridge.
 *
 * Important idea:
 * - NeoForge's normal config folder is fine for mod settings.
 * - BlackGrid/WatchDog needs an obvious server-owner file inside the actual server folder.
 * - So this creates and reads: <server root>/WatchDog/discord-chat.json
 *
 * The bridge is always default-off. Dropping the mod into a server should not suddenly
 * start sending chat to Discord like a possessed printer.
 */
public final class DiscordChatBridgeConfig {

    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();

    // Folder/file created inside the Minecraft server folder.
    private static final String CONFIG_DIR_NAME = "WatchDog";
    private static final String CONFIG_FILE_NAME = "discord-chat.json";

    // Remember where the config was loaded from so /watchdog discord status can show it.
    private static Path configPath;

    // In-memory copy of the config. Code reads this instead of touching disk every chat message.
    private static Settings settings = Settings.defaults();

    private DiscordChatBridgeConfig() {
    }

    public static synchronized void load(MinecraftServer server) {
        load(server.getServerDirectory());
    }

    public static synchronized void load(Path serverRoot) {
        Path dir = serverRoot.resolve(CONFIG_DIR_NAME);
        configPath = dir.resolve(CONFIG_FILE_NAME);

        try {
            // Make sure <server>/WatchDog exists.
            Files.createDirectories(dir);

            if (!Files.exists(configPath)) {
                // First launch: write a safe disabled config the owner can edit.
                settings = Settings.defaults();
                writeDefaultConfig();
                WatchDogHelper.LOGGER.info("[WatchDog Discord Chat] Created default config at {}", configPath);
                return;
            }

            // Existing config: read JSON and fill in any missing newer fields.
            String raw = Files.readString(configPath, StandardCharsets.UTF_8);
            Settings loaded = GSON.fromJson(raw, Settings.class);
            settings = loaded == null ? Settings.defaults() : loaded.withDefaults();
            WatchDogHelper.LOGGER.info("[WatchDog Discord Chat] Loaded config from {}", configPath);
        } catch (Exception error) {
            // Bad config should fail closed. No chat leak, no half-enabled bridge.
            settings = Settings.defaults();
            WatchDogHelper.LOGGER.warn("[WatchDog Discord Chat] Failed to load config. Bridge stays disabled: {}", error.getMessage());
        }
    }

    public static synchronized void reload(MinecraftServer server) {
        load(server);
    }

    public static synchronized Settings get() {
        return settings == null ? Settings.defaults() : settings;
    }

    public static synchronized Path path() {
        return configPath;
    }

    private static void writeDefaultConfig() throws IOException {
        Files.writeString(configPath, GSON.toJson(Settings.defaults()) + System.lineSeparator(), StandardCharsets.UTF_8);
    }

    /**
     * JSON shape for WatchDog/discord-chat.json.
     *
     * Keep these fields simple because this is meant to be edited by server owners,
     * not only by BlackGrid internals.
     */
    public static final class Settings {
        // Master kill switch. Default false means the mod does nothing Discord-related until enabled.
        public boolean enabled;

        // Currently only "watchdog_bot" is expected. This leaves room for future modes without config churn.
        public String mode;

        // Discord channel id that should receive game chat and be allowed to send chat back.
        public String gameChatChannelId;

        // Reserved for future direct-bot mode. Prefer WatchDog owning bot tokens, not the Minecraft jar.
        public String botToken;

        // Shared secret between WatchDog/the Discord bot and this helper mod.
        public String bridgeToken;

        // Where Minecraft chat gets POSTed so WatchDog/the Discord bot can send it to Discord.
        public String outboundUrl;

        // Where this mod listens for Discord -> Minecraft messages.
        public String inboundHost;
        public int inboundPort;
        public String inboundDiscordPath;
        public String statusPath;

        // Direction switches. Useful when testing one side without enabling the other side.
        public boolean sendMinecraftChatToDiscord;
        public boolean allowDiscordToMinecraft;

        // Reserved for loop protection if a future bot/webhook setup starts echoing itself.
        public boolean ignoreWebhookLikeMessages;

        // Formatting knobs for what gets sent out and what gets shown in-game.
        public String minecraftToDiscordFormat;
        public String discordToMinecraftPrefix;

        public static Settings defaults() {
            Settings settings = new Settings();
            settings.enabled = false;
            settings.mode = "watchdog_bot";
            settings.gameChatChannelId = "";
            settings.botToken = "";
            settings.bridgeToken = "change-me";
            settings.outboundUrl = "http://127.0.0.1:8081/api/discord/minecraft-chat";
            settings.inboundHost = "127.0.0.1";
            settings.inboundPort = 25590;
            settings.inboundDiscordPath = "/api/discord";
            settings.statusPath = "/api/status";
            settings.sendMinecraftChatToDiscord = true;
            settings.allowDiscordToMinecraft = true;
            settings.ignoreWebhookLikeMessages = true;
            settings.minecraftToDiscordFormat = "<{player}> {message}";
            settings.discordToMinecraftPrefix = "[Discord] ";
            return settings;
        }

        public Settings withDefaults() {
            Settings defaults = defaults();

            // These checks let old config files keep working after we add new fields.
            if (mode == null || mode.isBlank()) {
                mode = defaults.mode;
            }
            if (gameChatChannelId == null) {
                gameChatChannelId = "";
            }
            if (botToken == null) {
                botToken = "";
            }
            if (bridgeToken == null || bridgeToken.isBlank()) {
                bridgeToken = defaults.bridgeToken;
            }
            if (outboundUrl == null || outboundUrl.isBlank()) {
                outboundUrl = defaults.outboundUrl;
            }
            if (inboundHost == null || inboundHost.isBlank()) {
                inboundHost = defaults.inboundHost;
            }
            if (inboundPort < 1 || inboundPort > 65535) {
                inboundPort = defaults.inboundPort;
            }
            inboundDiscordPath = normalizePath(inboundDiscordPath, defaults.inboundDiscordPath);
            statusPath = normalizePath(statusPath, defaults.statusPath);
            if (minecraftToDiscordFormat == null || minecraftToDiscordFormat.isBlank()) {
                minecraftToDiscordFormat = defaults.minecraftToDiscordFormat;
            }
            if (discordToMinecraftPrefix == null) {
                discordToMinecraftPrefix = defaults.discordToMinecraftPrefix;
            }

            return this;
        }

        public boolean usableToken() {
            // "change-me" is intentionally treated as not configured.
            return bridgeToken != null && !bridgeToken.isBlank() && !"change-me".equalsIgnoreCase(bridgeToken.trim());
        }

        public String safeChannelLabel() {
            if (gameChatChannelId == null || gameChatChannelId.isBlank()) {
                return "not set";
            }
            return gameChatChannelId;
        }

        private static String normalizePath(String value, String fallback) {
            if (value == null || value.isBlank()) {
                return fallback;
            }

            String path = value.trim();
            if (!path.startsWith("/")) {
                path = "/" + path;
            }
            return path;
        }
    }
}
