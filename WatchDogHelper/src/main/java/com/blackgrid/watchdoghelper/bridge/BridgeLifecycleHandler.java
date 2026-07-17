package com.blackgrid.watchdoghelper.bridge;

import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import net.neoforged.neoforge.event.server.ServerStoppingEvent;

/**
 * Starts and stops the helper bridge with the Minecraft server lifecycle.
 *
 * Server start:
 * - load/create WatchDog/discord-chat.json
 * - start the tiny HTTP bridge if config says it should run
 *
 * Server stop:
 * - shut the HTTP bridge down cleanly so the port is released
 */
public class BridgeLifecycleHandler {

    @SubscribeEvent
    public void onServerStarted(ServerStartedEvent event) {
        DiscordChatBridgeConfig.load(event.getServer());
        BridgeService.start(event.getServer());
    }

    @SubscribeEvent
    public void onServerStopping(ServerStoppingEvent event) {
        BridgeService.stop();
    }
}
