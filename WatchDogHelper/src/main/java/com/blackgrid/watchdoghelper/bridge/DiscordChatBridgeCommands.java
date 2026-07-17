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
 * In-game admin commands for the base WatchDog Helper mod.
 *
 * Command shape:
 * - /watchdog                    base helper status
 * - /watchdog status             base helper status
 * - /watchdog reload             reload bridge config
 * - /watchdog discord            Discord bridge status
 * - /watchdog discord status     Discord bridge status
 * - /watchdog discord reload     reload bridge config
 *
 * Aliases:
 * - /wd                          same tree as /watchdog
 * - /watchdogdiscord             legacy direct Discord bridge alias
 *
 * These are operator/debug commands, not normal player commands.
 */
public class DiscordChatBridgeCommands {

    private static final PermissionCheck.Require GAMEMASTER = new PermissionCheck.Require(Permissions.COMMANDS_GAMEMASTER);

    @SubscribeEvent
    public void onRegisterCommands(RegisterCommandsEvent event) {
        CommandDispatcher<CommandSourceStack> dispatcher = event.getDispatcher();

        registerWatchDogRoot(dispatcher, "watchdog");
        registerWatchDogRoot(dispatcher, "wd");
        registerLegacyDiscordRoot(dispatcher);
    }

    private static void registerWatchDogRoot(CommandDispatcher<CommandSourceStack> dispatcher, String rootName) {
        dispatcher.register(
                Commands.literal(rootName)
                        .requires(Commands.hasPermission(GAMEMASTER))
                        .executes(ctx -> sendStatus(ctx.getSource()))
                        .then(Commands.literal("status")
                                .executes(ctx -> sendStatus(ctx.getSource())))
                        .then(Commands.literal("reload")
                                .executes(ctx -> reload(ctx.getSource())))
                        .then(Commands.literal("discord")
                                .executes(ctx -> sendDiscordStatus(ctx.getSource()))
                                .then(Commands.literal("status")
                                        .executes(ctx -> sendDiscordStatus(ctx.getSource())))
                                .then(Commands.literal("reload")
                                        .executes(ctx -> reload(ctx.getSource()))))
        );
    }

    private static void registerLegacyDiscordRoot(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(
                Commands.literal("watchdogdiscord")
                        .requires(Commands.hasPermission(GAMEMASTER))
                        .executes(ctx -> sendDiscordStatus(ctx.getSource()))
                        .then(Commands.literal("status")
                                .executes(ctx -> sendDiscordStatus(ctx.getSource())))
                        .then(Commands.literal("reload")
                                .executes(ctx -> reload(ctx.getSource())))
        );
    }

    private static int sendStatus(CommandSourceStack source) {
        source.sendSuccess(() -> header("WatchDog Helper"), false);
        source.sendSuccess(() -> line("Base commands", "/watchdog, /wd"), false);
        source.sendSuccess(() -> line("Discord bridge", "/watchdog discord status, /watchdog discord reload"), false);
        source.sendSuccess(() -> line("Legacy alias", "/watchdogdiscord"), false);
        source.sendSuccess(() -> line("Config", configPathLabel()), false);
        source.sendSuccess(() -> line("Bridge enabled", String.valueOf(DiscordChatBridgeConfig.get().enabled)), false);
        return 1;
    }

    private static int sendDiscordStatus(CommandSourceStack source) {
        DiscordChatBridgeConfig.Settings settings = DiscordChatBridgeConfig.get();

        // Keep this output boring and useful. This is for debugging config mistakes.
        source.sendSuccess(() -> header("WatchDog Discord chat bridge"), false);
        source.sendSuccess(() -> line("Config", configPathLabel()), false);
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

        source.sendSuccess(() -> Component.literal("WatchDog Helper bridge config reloaded.")
                .withStyle(ChatFormatting.GREEN), true);
        return 1;
    }

    private static String configPathLabel() {
        Path path = DiscordChatBridgeConfig.path();
        return path == null ? "not loaded yet" : path.toString();
    }

    private static Component header(String text) {
        return Component.literal(text).withStyle(ChatFormatting.AQUA);
    }

    private static Component line(String key, String value) {
        return Component.literal(key + ": ").withStyle(ChatFormatting.GRAY)
                .append(Component.literal(value == null ? "" : value).withStyle(ChatFormatting.WHITE));
    }
}
