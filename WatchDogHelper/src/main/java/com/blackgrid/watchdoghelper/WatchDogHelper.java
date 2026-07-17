package com.blackgrid.watchdoghelper;

import com.blackgrid.watchdoghelper.bridge.WatchDogHelperChatBridgeHandler;
import com.blackgrid.watchdoghelper.bridge.BridgeLifecycleHandler;
import com.blackgrid.watchdoghelper.bridge.DiscordChatBridgeCommands;
import com.mojang.logging.LogUtils;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.config.ModConfig;
import net.neoforged.neoforge.common.NeoForge;
import org.slf4j.Logger;

/**
 * Main NeoForge entrypoint for the base WatchDog Helper mod.
 *
 * This is the generic helper BlackGrid can offer to Minecraft servers. Keep this
 * boring and portable. A random server owner installing the base helper should
 * only get bridge plumbing, not AetherReach economy/shop/rules/protection logic.
 *
 * Base runtime responsibilities:
 * - create/load the WatchDog discord chat config
 * - start/stop the small HTTP bridge when enabled
 * - catch Minecraft chat for WatchDog/Discord forwarding when enabled
 * - expose admin/debug commands for the bridge
 *
 * Developed server-specific features still live in the source tree for now, but
 * they are not registered here. They should become their own addon/profile later
 * instead of leaking into the base plugin like soup through a paper bag.
 */
@Mod(WatchDogHelper.MODID)
public class WatchDogHelper {

    public static final String MODID = "watchdog_helper";
    public static final Logger LOGGER = LogUtils.getLogger();

    public WatchDogHelper(IEventBus modEventBus, ModContainer modContainer) {
        // Admin/debug commands for the Discord chat bridge.
        NeoForge.EVENT_BUS.register(new DiscordChatBridgeCommands());

        // Starts/stops the tiny HTTP bridge when the Minecraft server starts/stops.
        NeoForge.EVENT_BUS.register(new BridgeLifecycleHandler());

        // Watches normal player chat and forwards it to WatchDog/Discord when enabled.
        NeoForge.EVENT_BUS.register(new WatchDogHelperChatBridgeHandler());

        // Base NeoForge common config. This is intentionally smaller than the
        // old AetherReach helper config. Discord chat still uses WatchDog/discord-chat.json.
        modContainer.registerConfig(ModConfig.Type.COMMON, com.blackgrid.watchdoghelper.Config.SPEC);
    }
}
