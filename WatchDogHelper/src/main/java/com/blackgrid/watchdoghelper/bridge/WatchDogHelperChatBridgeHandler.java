package com.blackgrid.watchdoghelper.bridge;

import net.minecraft.server.level.ServerPlayer;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.event.ServerChatEvent;

/**
 * Catches normal Minecraft chat from NeoForge.
 *
 * This is the first hop of Minecraft -> Discord:
 * player says something in-game
 *   -> NeoForge fires ServerChatEvent
 *   -> this handler grabs player/name/message
 *   -> sends it to the existing WatchDog event bridge
 *   -> also sends it to the optional Discord chat bridge
 */
public class WatchDogHelperChatBridgeHandler {

    @SubscribeEvent
    public void onServerChat(ServerChatEvent event) {
        ServerPlayer player = event.getPlayer();

        String uuid = player.getUUID().toString();
        String playerName = player.getName().getString();
        String message = event.getRawText();

        // Ignore empty garbage so the bridge does not forward blank messages.
        if (message == null || message.isBlank()) {
            return;
        }

        // Existing WatchDog event callback path.
        WatchdogEventClient.sendChatEvent(uuid, playerName, message);

        // New optional Discord chat path. It is safe to call because the client checks the config first.
        DiscordChatBridgeClient.sendMinecraftChat(uuid, playerName, message);
    }
}
