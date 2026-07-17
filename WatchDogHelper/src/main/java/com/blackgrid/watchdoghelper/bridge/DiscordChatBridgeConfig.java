package com.blackgrid.watchdoghelper.bridge;

import com.blackgrid.watchdoghelper.WatchDogHelper;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import net.minecraft.server.MinecraftServer;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;

public final class DiscordChatBridgeConfig {

    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final String CONFIG_DIR_NAME = "WatchDog";
    private static final String CONFIG_FILE_NAME = "discord-chat.json";

    private static Path configPath;
    private static Settings settings = Settings.defaults();

    private DiscordChatBridgeConfig() {
    }

    public static synchronized void load(MinecraftServer server) {
        Path serverRoot = server.getServerDirectory();
        Path dir = serverRoot.resolve(CONFIG_DIR_NAME);
        configPath = dir.resolve(CONFIG_FILE_NAME);

        try {
            Files.createDirectories(dir);

            if (!Files.exists(configPath)) {
                settings = Settings.defaults();
                writeDefaultConfig();
                WatchDogHelper.LOGGER.info("[WatchDog Discord Chat] Created default config at {}", configPath);
                return;
            }

            String raw = Files.readString(configPath, StandardCharsets.UTF_8);
            Settings loaded = GSON.fromJson(raw, Settings.class);
            settings = loaded == null ? Settings.defaults() : loaded.withDefaults();
            WatchDogHelper.LOGGER.info("[WatchDog Discord Chat] Loaded config from {}", configPath);
        } catch (Exception error) {
            settings = Settings.defaults();
            WatchDogHelper.LOGGER.warn("[WatchDog Discord Chat] Failed to load config. Bridge stays disabled: {}", error.getMessage());
        }
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

    public static final class Settings {
        public boolean enabled;
        public String mode;
        public String gameChatChannelId;
        public String botToken;
        public String bridgeToken;
        public String outboundUrl;
        public boolean sendMinecraftChatToDiscord;
        public boolean allowDiscordToMinecraft;
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
            settings.sendMinecraftChatToDiscord = true;
            settings.allowDiscordToMinecraft = true;
            settings.minecraftToDiscordFormat = "<{player}> {message}";
            settings.discordToMinecraftPrefix = "[Discord] ";
            return settings;
        }

        public Settings withDefaults() {
            Settings defaults = defaults();

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
            if (minecraftToDiscordFormat == null || minecraftToDiscordFormat.isBlank()) {
                minecraftToDiscordFormat = defaults.minecraftToDiscordFormat;
            }
            if (discordToMinecraftPrefix == null) {
                discordToMinecraftPrefix = defaults.discordToMinecraftPrefix;
            }

            return this;
        }

        public boolean usableToken() {
            return bridgeToken != null && !bridgeToken.isBlank() && !"change-me".equalsIgnoreCase(bridgeToken.trim());
        }
    }
}
