package com.blackgrid.watchdoghelper.command;

import com.mojang.brigadier.CommandDispatcher;
import net.minecraft.commands.CommandSourceStack;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

/**
 * Legacy command bucket from the developed AetherReach helper.
 *
 * This class used to register every random server-specific command under the
 * base WatchDog Helper mod:
 *
 * - /rules
 * - /discord
 * - /discordlink
 * - /linkdiscord
 * - /balance
 * - /shards
 * - /pay
 * - /ah
 * - /shop
 * - /currency
 * - /aetherreach
 *
 * That was wrong for the base helper. The base helper is supposed to provide
 * generic BlackGrid/WatchDog bridge plumbing only. Economy, shop, auction,
 * rules, welcome text, and AetherReach admin tools belong in an addon/profile,
 * not in the default helper jar that every generated server may receive.
 *
 * This class is intentionally kept as a no-op compatibility shell for now so
 * old imports or references fail softly while the developed server commands are
 * moved into their own addon module later.
 *
 * Current base command tree lives in:
 *   com.blackgrid.watchdoghelper.bridge.DiscordChatBridgeCommands
 */
@Deprecated(forRemoval = true)
public class WatchDogHelperCommands {

    @SubscribeEvent
    public void onRegisterCommands(RegisterCommandsEvent event) {
        CommandDispatcher<CommandSourceStack> dispatcher = event.getDispatcher();

        // Intentionally empty.
        // Do not add base helper commands here. Use the /watchdog and /wd tree
        // from DiscordChatBridgeCommands for generic WatchDog helper commands.
        // Server-specific commands should live in a server addon/profile.
        dispatcher.getRoot();
    }
}
