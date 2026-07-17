package com.blackgrid.watchdoghelper.player;

import java.util.concurrent.ThreadLocalRandom;
import com.blackgrid.watchdoghelper.Config;
import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;

/**
 * Handles optional player leave broadcasts.
 *
 * This is deliberately simple:
 * - player logs out
 * - if leave messages are enabled and broadcasts are enabled
 * - build a formatted message
 * - broadcast it to everyone still online
 */
public class PlayerLeaveHandler {

    @SubscribeEvent
    public void onPlayerLogout(PlayerEvent.PlayerLoggedOutEvent event) {
        // Master switch. Default false.
        if (!Config.LEAVE_MESSAGES_ENABLED.get()) {
            return;
        }

        // Current behavior only supports broadcast leave messages.
        // If this is false, do nothing.
        if (!Config.LEAVE_BROADCAST_TO_ALL.get()) {
            return;
        }

        if (!(event.getEntity() instanceof ServerPlayer player)) {
            return;
        }

        MinecraftServer server = player.level().getServer();

        if (server == null) {
            return;
        }

        String playerName = player.getName().getString();

        // Multiple leave message options can be split with || in config.
        String rawMessage = pickRandomMessage(Config.PLAYER_LEAVE_MESSAGE.get())
                .replace("{player}", playerName);

        MutableComponent message = Component.empty().copy();

        message.append(
                Component.literal(formatLore(Config.VEIL_PREFIX.get()))
                        .withStyle(ChatFormatting.DARK_PURPLE)
        );

        message.append(
                Component.literal(rawMessage)
                        .withStyle(ChatFormatting.GRAY)
        );

        server.getPlayerList().broadcastSystemMessage(message, false);
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
