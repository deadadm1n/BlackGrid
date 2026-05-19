package com.blackgrid.aetherreachcore;
import com.blackgrid.aetherreachcore.player.PlayerLeaveHandler;
import com.blackgrid.aetherreachcore.bridge.AetherreachChatBridgeHandler;

import com.blackgrid.aetherreachcore.bridge.BridgeLifecycleHandler;
import com.blackgrid.aetherreachcore.command.AetherreachCommands;
import com.blackgrid.aetherreachcore.currency.CurrencyTickHandler;
import com.blackgrid.aetherreachcore.player.PlayerWelcomeHandler;
import com.blackgrid.aetherreachcore.protection.ChunkDestroyerPlacementHandler;
import com.mojang.logging.LogUtils;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.config.ModConfig;
import net.neoforged.neoforge.common.NeoForge;
import org.slf4j.Logger;

@Mod(AetherreachCore.MODID)
public class AetherreachCore {

    public static final String MODID = "aetherreachcore";
    public static final Logger LOGGER = LogUtils.getLogger();

    public AetherreachCore(IEventBus modEventBus, ModContainer modContainer) {
        NeoForge.EVENT_BUS.register(new AetherreachCommands());
        NeoForge.EVENT_BUS.register(new CurrencyTickHandler());
        NeoForge.EVENT_BUS.register(new BridgeLifecycleHandler());
        NeoForge.EVENT_BUS.register(new AetherreachChatBridgeHandler());
        NeoForge.EVENT_BUS.register(new PlayerWelcomeHandler());
        NeoForge.EVENT_BUS.register(new PlayerLeaveHandler());
        NeoForge.EVENT_BUS.register(new ChunkDestroyerPlacementHandler());

        modContainer.registerConfig(ModConfig.Type.COMMON, com.blackgrid.aetherreachcore.Config.SPEC);
    }
}
