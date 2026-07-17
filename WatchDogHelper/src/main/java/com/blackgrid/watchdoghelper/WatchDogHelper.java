package com.blackgrid.watchdoghelper;
import com.blackgrid.watchdoghelper.player.PlayerLeaveHandler;
import com.blackgrid.watchdoghelper.bridge.WatchDogHelperChatBridgeHandler;

import com.blackgrid.watchdoghelper.bridge.BridgeLifecycleHandler;
import com.blackgrid.watchdoghelper.bridge.DiscordChatBridgeCommands;
import com.blackgrid.watchdoghelper.command.WatchDogHelperCommands;
import com.blackgrid.watchdoghelper.currency.CurrencyTickHandler;
import com.blackgrid.watchdoghelper.player.PlayerWelcomeHandler;
import com.blackgrid.watchdoghelper.protection.ChunkDestroyerPlacementHandler;
import com.mojang.logging.LogUtils;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.config.ModConfig;
import net.neoforged.neoforge.common.NeoForge;
import org.slf4j.Logger;

@Mod(WatchDogHelper.MODID)
public class WatchDogHelper {

    public static final String MODID = "watchdog_helper";
    public static final Logger LOGGER = LogUtils.getLogger();

    public WatchDogHelper(IEventBus modEventBus, ModContainer modContainer) {
        NeoForge.EVENT_BUS.register(new WatchDogHelperCommands());
        NeoForge.EVENT_BUS.register(new DiscordChatBridgeCommands());
        NeoForge.EVENT_BUS.register(new CurrencyTickHandler());
        NeoForge.EVENT_BUS.register(new BridgeLifecycleHandler());
        NeoForge.EVENT_BUS.register(new WatchDogHelperChatBridgeHandler());
        NeoForge.EVENT_BUS.register(new PlayerWelcomeHandler());
        NeoForge.EVENT_BUS.register(new PlayerLeaveHandler());
        NeoForge.EVENT_BUS.register(new ChunkDestroyerPlacementHandler());

        modContainer.registerConfig(ModConfig.Type.COMMON, com.blackgrid.watchdoghelper.Config.SPEC);
    }
}
