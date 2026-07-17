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

/**
 * Main NeoForge entrypoint for the WatchDog Helper mod.
 *
 * NeoForge creates this class when the mod loads. This is where we hook all of
 * our event handlers into NeoForge's global event bus.
 *
 * Plain English:
 * - commands go through WatchDogHelperCommands / DiscordChatBridgeCommands
 * - economy ticks go through CurrencyTickHandler
 * - HTTP bridge lifecycle goes through BridgeLifecycleHandler
 * - Minecraft chat forwarding goes through WatchDogHelperChatBridgeHandler
 * - join/leave messages go through PlayerWelcomeHandler / PlayerLeaveHandler
 * - placement restrictions go through ChunkDestroyerPlacementHandler
 */
@Mod(WatchDogHelper.MODID)
public class WatchDogHelper {

    public static final String MODID = "watchdog_helper";
    public static final Logger LOGGER = LogUtils.getLogger();

    public WatchDogHelper(IEventBus modEventBus, ModContainer modContainer) {
        // Register command handlers first so admin/debug commands are available.
        NeoForge.EVENT_BUS.register(new WatchDogHelperCommands());
        NeoForge.EVENT_BUS.register(new DiscordChatBridgeCommands());

        // Pays passive currency rewards on a timer.
        NeoForge.EVENT_BUS.register(new CurrencyTickHandler());

        // Starts/stops the tiny HTTP bridge when the Minecraft server starts/stops.
        NeoForge.EVENT_BUS.register(new BridgeLifecycleHandler());

        // Watches normal player chat and forwards it to WatchDog/Discord when enabled.
        NeoForge.EVENT_BUS.register(new WatchDogHelperChatBridgeHandler());

        // Player join/leave helper messages.
        NeoForge.EVENT_BUS.register(new PlayerWelcomeHandler());
        NeoForge.EVENT_BUS.register(new PlayerLeaveHandler());

        // Blocks restricted chunk destroyer placement outside the allowed dimension.
        NeoForge.EVENT_BUS.register(new ChunkDestroyerPlacementHandler());

        // NeoForge common config. This is separate from WatchDog/discord-chat.json.
        modContainer.registerConfig(ModConfig.Type.COMMON, com.blackgrid.watchdoghelper.Config.SPEC);
    }
}
