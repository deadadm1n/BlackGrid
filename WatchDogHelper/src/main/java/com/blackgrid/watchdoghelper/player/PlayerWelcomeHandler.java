package com.blackgrid.watchdoghelper.player;
import java.util.concurrent.ThreadLocalRandom;
import com.blackgrid.watchdoghelper.WatchDogHelper;
import com.blackgrid.watchdoghelper.Config;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.Set;
import java.util.UUID;

public class PlayerWelcomeHandler {

    private static final Path SEEN_PLAYERS_FILE =
            Path.of("aetherreach", "players", "seen_players.json");

    private static final Set<String> SEEN_PLAYERS = new HashSet<>();
    private static boolean loaded = false;

    @SubscribeEvent
    public void onPlayerLogin(PlayerEvent.PlayerLoggedInEvent event) {
        if (!Config.WELCOME_ENABLED.get()) {
            return;
        }

        if (!(event.getEntity() instanceof ServerPlayer player)) {
            return;
        }

        loadSeenPlayers();

        UUID uuid = player.getUUID();
        String uuidText = uuid.toString();
        String playerName = player.getName().getString();

        boolean firstJoin = !SEEN_PLAYERS.contains(uuidText);

        if (firstJoin) {
            SEEN_PLAYERS.add(uuidText);
            saveSeenPlayers();
        }

        String template = firstJoin
                ? pickRandomMessage(Config.FIRST_JOIN_WELCOME_MESSAGE.get())
                : pickRandomMessage(Config.RETURNING_WELCOME_MESSAGE.get());

        String message = template.replace("{player}", playerName);

        // Run one tick later so the player is fully attached before the message is sent.
        player.level().getServer().execute(() -> {
            sendWelcome(player, message, firstJoin);
            sendMotd(player, playerName);
            sendRulesOnJoin(player);
        });
    }

    private void sendWelcome(ServerPlayer player, String message, boolean firstJoin) {
        MutableComponent formatted = Component.empty().copy();

        formatted.append(
                Component.literal(formatLore(Config.VEIL_PREFIX.get()))
                        .withStyle(ChatFormatting.LIGHT_PURPLE)
        );

        formatted.append(
                Component.literal(message)
                        .withStyle(firstJoin ? ChatFormatting.AQUA : ChatFormatting.GRAY)
        );

        if (Config.WELCOME_BROADCAST_TO_ALL.get()) {
            player.level().getServer().getPlayerList().broadcastSystemMessage(formatted, false);
            return;
        }

        player.sendSystemMessage(formatted);
    }

    private void sendMotd(ServerPlayer player, String playerName) {
        if (!Config.MOTD_ENABLED.get()) {
            return;
        }

        String motd = Config.MOTD_MESSAGE.get().replace("{player}", playerName);
        sendTitledLines(player, Config.MOTD_TITLE.get(), motd, ChatFormatting.GOLD);
    }

    private void sendRulesOnJoin(ServerPlayer player) {
        if (!Config.RULES_ON_JOIN_ENABLED.get()) {
            return;
        }

        sendTitledLines(player, Config.RULES_TITLE.get(), Config.RULES_MESSAGE.get(), ChatFormatting.AQUA);
    }

    private static void sendTitledLines(ServerPlayer player, String title, String raw, ChatFormatting titleColor) {
        if (raw == null || raw.isBlank()) {
            return;
        }

        player.sendSystemMessage(
                Component.literal(formatLore(Config.VEIL_PREFIX.get()))
                        .withStyle(ChatFormatting.LIGHT_PURPLE)
                        .append(Component.literal(title)
                                .withStyle(titleColor))
        );

        for (String line : raw.replace("\\n", "\n").split("\\R")) {
            String trimmed = line.trim();

            if (!trimmed.isBlank()) {
                player.sendSystemMessage(
                        Component.literal(" - ")
                                .withStyle(ChatFormatting.DARK_GRAY)
                                .append(Component.literal(trimmed)
                                        .withStyle(ChatFormatting.GRAY))
                );
            }
        }
    }

    private static void loadSeenPlayers() {
        if (loaded) {
            return;
        }

        loaded = true;

        try {
            Files.createDirectories(SEEN_PLAYERS_FILE.getParent());

            if (!Files.exists(SEEN_PLAYERS_FILE)) {
                return;
            }

            String content = Files.readString(SEEN_PLAYERS_FILE)
                    .replace("[", "")
                    .replace("]", "")
                    .replace("\"", "")
                    .trim();

            if (content.isBlank()) {
                return;
            }

            String[] entries = content.split(",");

            for (String entry : entries) {
                String value = entry.trim();

                if (!value.isBlank()) {
                    SEEN_PLAYERS.add(value);
                }
            }

        } catch (IOException e) {
            WatchDogHelper.LOGGER.warn("[AetherReach] Failed to load seen players: {}", e.getMessage());
        }
    }

    private static void saveSeenPlayers() {
        try {
            Files.createDirectories(SEEN_PLAYERS_FILE.getParent());

            StringBuilder builder = new StringBuilder();
            builder.append("[\n");

            int index = 0;

            for (String uuid : SEEN_PLAYERS) {
                builder.append("  \"").append(uuid).append("\"");

                if (index < SEEN_PLAYERS.size() - 1) {
                    builder.append(",");
                }

                builder.append("\n");
                index++;
            }

            builder.append("]\n");

            Files.writeString(SEEN_PLAYERS_FILE, builder.toString());

        } catch (IOException e) {
            WatchDogHelper.LOGGER.warn("[AetherReach] Failed to save seen players: {}", e.getMessage());
        }
    }
    private static String pickRandomMessage(String raw) {
        if (raw == null || raw.isBlank()) {
            return "";
        }

        String[] options = raw.split("\\|\\|");

        if (options.length == 0) {
            return raw.trim();
        }

        int index = ThreadLocalRandom.current().nextInt(options.length);

        return options[index].trim();
    }

    private static String formatLore(String template) {
        return template
                .replace("{veil}", Config.VEIL_NAME.get())
                .replace("{server}", Config.SERVER_NAME.get())
                .replace("{helper}", Config.HELPER_NAME.get());
    }
}
