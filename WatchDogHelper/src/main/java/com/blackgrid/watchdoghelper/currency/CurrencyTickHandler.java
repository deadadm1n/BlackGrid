package com.blackgrid.watchdoghelper.currency;

import net.minecraft.server.level.ServerPlayer;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;

/**
 * Pays passive currency rewards on a timer.
 *
 * Minecraft runs at roughly 20 ticks per second.
 * This waits 15 minutes, then loops through online players and pays each one.
 *
 * The actual reward amount is handled by CurrencyService, because it may depend
 * on config, FTB Ranks permissions, and balance caps.
 */
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
