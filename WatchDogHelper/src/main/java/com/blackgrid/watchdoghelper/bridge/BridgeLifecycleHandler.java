package com.blackgrid.watchdoghelper.bridge;

import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import net.neoforged.neoforge.event.server.ServerStoppingEvent;

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
