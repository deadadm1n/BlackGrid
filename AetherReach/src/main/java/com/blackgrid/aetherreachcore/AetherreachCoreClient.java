package com.blackgrid.aetherreachcore;

import net.minecraft.client.Minecraft;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.event.lifecycle.FMLClientSetupEvent;
import net.neoforged.neoforge.client.gui.ConfigurationScreen;
import net.neoforged.neoforge.client.gui.IConfigScreenFactory;

@Mod(value = AetherreachCore.MODID, dist = Dist.CLIENT)
@EventBusSubscriber(modid = AetherreachCore.MODID, value = Dist.CLIENT)
public class AetherreachCoreClient {

    public AetherreachCoreClient(ModContainer container) {
        // Registers the NeoForge config screen (Mods → Aetherreach Core → Config).
        container.registerExtensionPoint(IConfigScreenFactory.class, ConfigurationScreen::new);
    }

    @SubscribeEvent
    static void onClientSetup(FMLClientSetupEvent event) {
        AetherreachCore.LOGGER.info("Aetherreach client setup complete. Hello, {}!",
                Minecraft.getInstance().getUser().getName());
    }
}
