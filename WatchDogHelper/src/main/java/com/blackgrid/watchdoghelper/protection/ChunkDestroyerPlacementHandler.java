package com.blackgrid.watchdoghelper.protection;

import com.blackgrid.watchdoghelper.Config;
import net.minecraft.ChatFormatting;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.Level;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.event.level.BlockEvent;

public class ChunkDestroyerPlacementHandler {

    @SubscribeEvent
    public void onBlockPlaced(BlockEvent.EntityPlaceEvent event) {
        String placedBlockId = BuiltInRegistries.BLOCK.getKey(event.getPlacedBlock().getBlock()).toString();

        if (!placedBlockId.equals(Config.CHUNK_DESTROYER_BLOCK_ID.get())) {
            return;
        }

        if (!(event.getLevel() instanceof Level level)) {
            return;
        }

        String currentDimension = level.dimension().identifier().toString();
        String allowedDimension = Config.MINING_DIMENSION_ID.get();

        if (currentDimension.equals(allowedDimension)) {
            return;
        }

        event.setCanceled(true);
        Entity entity = event.getEntity();

        if (entity instanceof ServerPlayer player) {
            player.sendSystemMessage(
                    Component.literal(formatLore(Config.VEIL_PREFIX.get()))
                            .withStyle(ChatFormatting.LIGHT_PURPLE)
                            .append(Component.literal("Chunk Destroyers can only be placed in the Mining Dimension.")
                                    .withStyle(ChatFormatting.RED))
            );
        }
    }

    private static String formatLore(String template) {
        return template
                .replace("{veil}", Config.VEIL_NAME.get())
                .replace("{server}", Config.SERVER_NAME.get())
                .replace("{helper}", Config.HELPER_NAME.get());
    }
}
