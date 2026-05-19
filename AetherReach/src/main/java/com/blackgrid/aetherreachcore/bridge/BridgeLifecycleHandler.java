package com.blackgrid.aetherreachcore.bridge;

import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import net.neoforged.neoforge.event.server.ServerStoppingEvent;

public class BridgeLifecycleHandler {

    @SubscribeEvent
    public void onServerStarted(ServerStartedEvent event) {
        BridgeService.start(event.getServer());
    }

    @SubscribeEvent
    public void onServerStopping(ServerStoppingEvent event) {
        BridgeService.stop();
    }
}
