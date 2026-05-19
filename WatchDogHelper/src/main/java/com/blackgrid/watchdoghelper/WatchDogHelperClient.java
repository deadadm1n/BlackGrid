package com.blackgrid.watchdoghelper;

import net.minecraft.client.Minecraft;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.ModContainer;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.event.lifecycle.FMLClientSetupEvent;
import net.neoforged.neoforge.client.gui.ConfigurationScreen;
import net.neoforged.neoforge.client.gui.IConfigScreenFactory;

@Mod(value = WatchDogHelper.MODID, dist = Dist.CLIENT)
@EventBusSubscriber(modid = WatchDogHelper.MODID, value = Dist.CLIENT)
public class WatchDogHelperClient {

    public WatchDogHelperClient(ModContainer container) {
        container.registerExtensionPoint(IConfigScreenFactory.class, ConfigurationScreen::new);
    }

    @SubscribeEvent
    static void onClientSetup(FMLClientSetupEvent event) {
        WatchDogHelper.LOGGER.info("WatchDog Helper client setup complete. Hello, {}!",
                Minecraft.getInstance().getUser().getName());
    }
}
