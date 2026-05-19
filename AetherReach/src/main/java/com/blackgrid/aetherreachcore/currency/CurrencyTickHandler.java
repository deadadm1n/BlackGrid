package com.blackgrid.aetherreachcore.currency;

import net.minecraft.server.level.ServerPlayer;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;

public class CurrencyTickHandler {

    private static final int TICKS_PER_REWARD = 20 * 60 * 15;

    private int tickCounter = 0;

    @SubscribeEvent
    public void onServerTick(ServerTickEvent.Post event) {
        tickCounter++;

        if (tickCounter < TICKS_PER_REWARD) {
            return;
        }

        tickCounter = 0;

        for (ServerPlayer player : event.getServer().getPlayerList().getPlayers()) {
            CurrencyService.addPassiveReward(player);
        }
    }
}
