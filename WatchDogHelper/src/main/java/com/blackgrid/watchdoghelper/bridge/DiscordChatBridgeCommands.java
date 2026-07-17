package com.blackgrid.watchdoghelper.bridge;

import com.mojang.brigadier.CommandDispatcher;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.permissions.PermissionCheck;
import net.minecraft.server.permissions.Permissions;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

import java.nio.file.Path;

/**
 * In-game admin commands for the Discord chat bridge.
 *
 * These are not player commands. They require gamemaster permission.
 *
 * Useful commands:
 * /watchdog discord status  - show what the bridge thinks its config is
 * /watchdog discord reload  - reload WatchDog/discord-chat.json without restarting Minecraft
 * /watchdogdiscord status   - same status command, shorter cursed alias
 * /watchdogdiscord reload   - same reload command, shorter cursed alias
 */
public class DiscordChatBridgeCommands {

    @SubscribeEvent
    public void onRegisterCommands(RegisterCommandsEvent event) {
        CommandDispatcher<CommandSourceStack> dispatcher = event.getDispatcher();

        // Direct command alias. Easy to type when debugging the bridge.
        dispatcher.register(
                Commands.literal("watchdogdiscord")
                        .requires(Commands.hasPermission(new PermissionCheck.Require(Permissions.COMMANDS_GAMEMASTER)))
                        .executes(ctx -> sendStatus(ctx.getSource()))
                        .then(Commands.literal("status")
                                .executes(ctx -> sendStatus(ctx.getSource())))
                        .then(Commands.literal("reload")
                                .executes(ctx -> reload(ctx.getSource())))
        );

        // Nested command style that fits the rest of WatchDog.
        dispatcher.register(
                Commands.literal("watchdog")
                        .requires(Commands.hasPermission(new PermissionCheck.Require(Permissions.COMMANDS_GAMEMASTER)))
                        .then(Commands.literal("discord")
                                .executes(ctx -> sendStatus(ctx.getSource()))
                                .then(Commands.literal("status")
                                        .executes(ctx -> sendStatus(ctx.getSource())))
                                .then(Commands.literal("reload")
                                        .executes(ctx -> reload(ctx.getSource()))))
        );
    }

    private static int sendStatus(CommandSourceStack source) {
        DiscordChatBridgeConfig.Settings settings = DiscordChatBridgeConfig.get();
        Path path = DiscordChatBridgeConfig.path();

        // Keep this output boring and useful. This is for debugging config mistakes.
        source.sendSuccess(() -> header("WatchDog Discord chat bridge"), false);
        source.sendSuccess(() -> line("Config", path == null ? "not loaded yet" : path.toString()), false);
        source.sendSuccess(() -> line("Enabled", String.valueOf(settings.enabled)), false);
        source.sendSuccess(() -> line("Minecraft -> Discord", String.valueOf(settings.sendMinecraftChatToDiscord)), false);
        source.sendSuccess(() -> line("Discord -> Minecraft", String.valueOf(settings.allowDiscordToMinecraft)), false);
        source.sendSuccess(() -> line("Channel", settings.safeChannelLabel()), false);
        source.sendSuccess(() -> line("Inbound", settings.inboundHost + ":" + settings.inboundPort + settings.inboundDiscordPath), false);
        source.sendSuccess(() -> line("Outbound", settings.outboundUrl), false);
        source.sendSuccess(() -> line("Token configured", String.valueOf(settings.usableToken())), false);
        return 1;
    }

    private static int reload(CommandSourceStack source) {
        MinecraftServer server = source.getServer();

        // Re-read the JSON file, then restart the little HTTP listener so host/port/path changes apply.
        DiscordChatBridgeConfig.reload(server);
        BridgeService.restart(server);

        source.sendSuccess(() -> Component.literal("WatchDog Discord chat bridge config reloaded.")
                .withStyle(ChatFormatting.GREEN), true);
        return 1;
    }

    private static Component header(String text) {
        return Component.literal(text).withStyle(ChatFormatting.AQUA);
    }

    private static Component line(String key, String value) {
        return Component.literal(key + ": ").withStyle(ChatFormatting.GRAY)
                .append(Component.literal(value == null ? "" : value).withStyle(ChatFormatting.WHITE));
    }
}
