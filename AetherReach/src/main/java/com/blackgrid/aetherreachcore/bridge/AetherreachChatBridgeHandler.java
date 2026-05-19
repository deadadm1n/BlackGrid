package com.blackgrid.aetherreachcore.bridge;

import net.minecraft.server.level.ServerPlayer;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.event.ServerChatEvent;

public class AetherreachChatBridgeHandler {

    @SubscribeEvent
    public void onServerChat(ServerChatEvent event) {
        ServerPlayer player = event.getPlayer();

        String uuid = player.getUUID().toString();
        String playerName = player.getName().getString();
        String message = event.getRawText();

        if (message == null || message.isBlank()) {
            return;
        }

        WatchdogEventClient.sendChatEvent(uuid, playerName, message);
    }
}