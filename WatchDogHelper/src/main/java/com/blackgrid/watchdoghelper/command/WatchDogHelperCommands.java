package com.blackgrid.watchdoghelper.command;

import com.blackgrid.watchdoghelper.Config;
import com.blackgrid.watchdoghelper.auction.AuctionHouseService;
import com.blackgrid.watchdoghelper.auction.AuctionListing;
import com.blackgrid.watchdoghelper.bridge.WatchdogEventClient;
import com.blackgrid.watchdoghelper.currency.CurrencyAccount;
import com.blackgrid.watchdoghelper.currency.CurrencyService;
import com.blackgrid.watchdoghelper.shop.ShopListing;
import com.blackgrid.watchdoghelper.shop.ShopService;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.arguments.LongArgumentType;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.permissions.PermissionCheck;
import net.minecraft.server.permissions.Permissions;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

import java.net.URI;
import java.util.Locale;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

public class WatchDogHelperCommands {

    @SubscribeEvent
    public void onRegisterCommands(RegisterCommandsEvent event) {
        CommandDispatcher<CommandSourceStack> dispatcher = event.getDispatcher();

        registerRules(dispatcher);
        registerDiscord(dispatcher);
        registerDiscordLink(dispatcher);
        registerBalance(dispatcher);
        registerPay(dispatcher);
        registerAuctionHouse(dispatcher);
        registerShop(dispatcher);
        registerCurrencyAdmin(dispatcher);
        registerAetherreachAdmin(dispatcher);
    }

    private void registerDiscordLink(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(
                Commands.literal("discordlink")
                        .executes(ctx -> {
                            ServerPlayer player = ctx.getSource().getPlayerOrException();
                            String code = generateLinkCode();
                            WatchdogEventClient.sendDiscordLinkEvent(
                                    player.getUUID().toString(),
                                    player.getName().getString(),
                                    code
                            );
                            String linkTemplate = Config.DISCORD_LINK_URL.get();

                            if (linkTemplate != null && !linkTemplate.isBlank()) {
                                String linkUrl = linkTemplate
                                        .replace("{state}", code)
                                        .replace("{code}", code);

                                player.sendSystemMessage(
                                        veilMsg("Link Discord: ")
                                                .append(Component.literal("Click here")
                                                        .withStyle(style -> style
                                                                .withColor(ChatFormatting.AQUA)
                                                                .withUnderlined(true)
                                                                .withClickEvent(new ClickEvent.OpenUrl(URI.create(linkUrl)))))
                                                .append(Component.literal(" to join and sync your role.")
                                                        .withStyle(ChatFormatting.GRAY))
                                );
                            } else {
                                player.sendSystemMessage(
                                        veilMsg("Discord link code: ")
                                                .append(Component.literal(code)
                                                        .withStyle(ChatFormatting.GOLD))
                                                .append(Component.literal("  Use !link " + code + " in Discord.")
                                                        .withStyle(ChatFormatting.GRAY))
                                );
                            }
                            return 1;
                        })
        );

        dispatcher.register(
                Commands.literal("linkdiscord")
                        .executes(ctx -> dispatcher.execute("discordlink", ctx.getSource()))
        );
    }

    private void registerRules(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(
                Commands.literal("rules")
                        .executes(ctx -> sendRules(ctx.getSource()))
        );
    }

    private void registerDiscord(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(
                Commands.literal("discord")
                        .executes(ctx -> {
                            ctx.getSource().sendSuccess(
                                    () -> veilPrefixComponent()
                                            .append(Component.literal("Join the Discord")
                                                    .withStyle(style -> style
                                                            .withColor(ChatFormatting.AQUA)
                                                            .withUnderlined(true)
                                                            .withClickEvent(new ClickEvent.OpenUrl(
                                                                    URI.create(Config.DISCORD_INVITE_URL.get()))))),
                                    false
                            );
                            return 1;
                        })
        );
    }

    private void registerBalance(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(
                Commands.literal("balance")
                        .executes(ctx -> {
                            ServerPlayer player = ctx.getSource().getPlayerOrException();
                            sendBalance(player, ctx.getSource());
                            return 1;
                        })
        );
        dispatcher.register(
                Commands.literal("shards")
                        .executes(ctx -> {
                            ServerPlayer player = ctx.getSource().getPlayerOrException();
                            sendBalance(player, ctx.getSource());
                            return 1;
                        })
        );
    }

    private static void sendBalance(ServerPlayer player, CommandSourceStack source) {
        long balance = CurrencyService.getBalance(player);
        String name = CurrencyService.currencyName();
        int reward = CurrencyService.getRewardPerCycle(player);

        source.sendSuccess(
                () -> veilMsg("Your Balance: ")
                        .append(Component.literal(balance + " " + name)
                                .withStyle(ChatFormatting.GOLD))
                        .append(Component.literal("  (+" + reward + "/15 min)")
                                .withStyle(ChatFormatting.DARK_GRAY)),
                false
        );
    }

    private void registerAuctionHouse(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(
                Commands.literal("ah")
                        .then(Commands.literal("sell")
                                .then(Commands.argument("price", LongArgumentType.longArg(1))
                                        .executes(ctx -> {
                                            ServerPlayer seller = ctx.getSource().getPlayerOrException();
                                            long price = LongArgumentType.getLong(ctx, "price");

                                            try {
                                                long listingId = AuctionHouseService.createListing(seller, price);
                                                ctx.getSource().sendSuccess(
                                                        () -> veilMsg("Exchange listing created. ")
                                                                .append(Component.literal("#" + listingId)
                                                                        .withStyle(ChatFormatting.AQUA))
                                                                .append(Component.literal(" for " + price + " " + CurrencyService.currencyName())
                                                                        .withStyle(ChatFormatting.GOLD)),
                                                        false
                                                );
                                                return 1;
                                            } catch (Exception e) {
                                                ctx.getSource().sendFailure(Component.literal(e.getMessage()).withStyle(ChatFormatting.RED));
                                                return 0;
                                            }
                                        })))
                        .then(Commands.literal("list")
                                .executes(ctx -> sendAuctionList(ctx.getSource(), 1))
                                .then(Commands.argument("page", IntegerArgumentType.integer(1))
                                        .executes(ctx -> sendAuctionList(
                                                ctx.getSource(),
                                                IntegerArgumentType.getInteger(ctx, "page")
                                        ))))
                        .then(Commands.literal("buy")
                                .then(Commands.argument("id", LongArgumentType.longArg(1))
                                        .executes(ctx -> {
                                            ServerPlayer buyer = ctx.getSource().getPlayerOrException();
                                            long id = LongArgumentType.getLong(ctx, "id");

                                            try {
                                                AuctionHouseService.buy(buyer, id);
                                                ctx.getSource().sendSuccess(
                                                        () -> veilMsg("Trade completed. Shards transferred."),
                                                        false
                                                );
                                                return 1;
                                            } catch (Exception e) {
                                                ctx.getSource().sendFailure(Component.literal(e.getMessage()).withStyle(ChatFormatting.RED));
                                                return 0;
                                            }
                                        })))
                        .then(Commands.literal("cancel")
                                .then(Commands.argument("id", LongArgumentType.longArg(1))
                                        .executes(ctx -> {
                                            ServerPlayer seller = ctx.getSource().getPlayerOrException();
                                            long id = LongArgumentType.getLong(ctx, "id");

                                            try {
                                                AuctionHouseService.cancel(seller, id);
                                                ctx.getSource().sendSuccess(
                                                        () -> veilMsg("Exchange listing cancelled. Item returned."),
                                                        false
                                                );
                                                return 1;
                                            } catch (Exception e) {
                                                ctx.getSource().sendFailure(Component.literal(e.getMessage()).withStyle(ChatFormatting.RED));
                                                return 0;
                                            }
                                        })))
                        .then(Commands.literal("claim")
                                .executes(ctx -> {
                                    ServerPlayer player = ctx.getSource().getPlayerOrException();
                                    int claimed = AuctionHouseService.claimExpired(player);
                                    ctx.getSource().sendSuccess(
                                            () -> veilMsg("Expired listings reclaimed: ")
                                                    .append(Component.literal(String.valueOf(claimed))
                                                            .withStyle(ChatFormatting.GOLD)),
                                            false
                                    );
                                    return 1;
                                }))
                        .then(Commands.literal("gui")
                                .executes(ctx -> {
                                    ctx.getSource().sendSuccess(
                                            () -> veilMsg(Config.EXCHANGE_NAME.get() + " interface is still stabilizing. Use /ah list for now."),
                                            false
                                    );
                                    return 1;
                                }))
        );
    }

    private void registerPay(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(
                Commands.literal("pay")
                        .then(Commands.argument("player", EntityArgument.player())
                                .then(Commands.argument("amount", LongArgumentType.longArg(1))
                                        .executes(ctx -> {
                                            ServerPlayer sender = ctx.getSource().getPlayerOrException();
                                            ServerPlayer recipient = EntityArgument.getPlayer(ctx, "player");
                                            long amount = LongArgumentType.getLong(ctx, "amount");
                                            String name = CurrencyService.currencyName();

                                            if (sender.getUUID().equals(recipient.getUUID())) {
                                                ctx.getSource().sendFailure(
                                                        Component.literal("You can't pay yourself.")
                                                                .withStyle(ChatFormatting.RED)
                                                );
                                                return 0;
                                            }

                                            String actor = sender.getName().getString() + "->" + recipient.getName().getString();

                                            if (!CurrencyService.deductBalance(sender, amount, "PAY_SEND", actor)) {
                                                ctx.getSource().sendFailure(
                                                        Component.literal("You don't have enough " + name + ". Balance: "
                                                                        + CurrencyService.getBalance(sender) + " " + name)
                                                                .withStyle(ChatFormatting.RED)
                                                );
                                                return 0;
                                            }

                                            long recipientBalance = CurrencyService.addBalance(recipient, amount, "PAY_RECEIVE", actor);
                                            long senderBalance = CurrencyService.getBalance(sender);

                                            ctx.getSource().sendSuccess(
                                                    () -> veilMsg("Sent ")
                                                            .append(Component.literal(amount + " " + name)
                                                                    .withStyle(ChatFormatting.GOLD))
                                                            .append(Component.literal(" to ")
                                                                    .withStyle(ChatFormatting.GRAY))
                                                            .append(recipient.getDisplayName().copy()
                                                                    .withStyle(ChatFormatting.AQUA))
                                                            .append(Component.literal(". New balance: " + senderBalance + " " + name)
                                                                    .withStyle(ChatFormatting.DARK_GRAY)),
                                                    false
                                            );

                                            recipient.sendSystemMessage(
                                                    veilPrefixComponent()
                                                            .append(sender.getDisplayName().copy()
                                                                    .withStyle(ChatFormatting.AQUA))
                                                            .append(Component.literal(" sent you ")
                                                                    .withStyle(ChatFormatting.GRAY))
                                                            .append(Component.literal(amount + " " + name)
                                                                    .withStyle(ChatFormatting.GOLD))
                                                            .append(Component.literal(". Balance: " + recipientBalance + " " + name)
                                                                    .withStyle(ChatFormatting.DARK_GRAY))
                                            );

                                            return 1;
                                        })))
        );
    }

    private void registerShop(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(
                Commands.literal("shop")
                        .executes(ctx -> sendShop(ctx.getSource()))
                        .then(Commands.literal("buy")
                                .then(Commands.argument("slot", IntegerArgumentType.integer(1, ShopService.ROTATION_SIZE))
                                        .executes(ctx -> {
                                            ServerPlayer player = ctx.getSource().getPlayerOrException();
                                            int slot = IntegerArgumentType.getInteger(ctx, "slot");

                                            try {
                                                ShopListing listing = ShopService.buy(player, slot);
                                                ctx.getSource().sendSuccess(
                                                        () -> veilMsg("Import secured: ")
                                                                .append(Component.literal(listing.itemName() + " x" + listing.quantity())
                                                                        .withStyle(ChatFormatting.AQUA))
                                                                .append(Component.literal(" for " + listing.price() + " " + CurrencyService.currencyName())
                                                                        .withStyle(ChatFormatting.GOLD)),
                                                        false
                                                );
                                                return 1;
                                            } catch (Exception e) {
                                                ctx.getSource().sendFailure(Component.literal(e.getMessage()).withStyle(ChatFormatting.RED));
                                                return 0;
                                            }
                                        })))
        );
    }

    private void registerCurrencyAdmin(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(
                Commands.literal("currency")
                        .requires(Commands.hasPermission(
                                new PermissionCheck.Require(Permissions.COMMANDS_GAMEMASTER)
                        ))

                        .then(Commands.literal("give")
                                .then(Commands.argument("player", EntityArgument.player())
                                        .then(Commands.argument("amount", LongArgumentType.longArg(1))
                                                .executes(ctx -> {
                                                    ServerPlayer target = EntityArgument.getPlayer(ctx, "player");
                                                    long amount = LongArgumentType.getLong(ctx, "amount");
                                                    String actor = commandActor(ctx.getSource());
                                                    long balance = CurrencyService.addBalance(target, amount, "ADMIN_GIVE", actor);
                                                    String name = CurrencyService.currencyName();

                                                    ctx.getSource().sendSuccess(
                                                            () -> adminMsg("Gave " + amount + " " + name + " to "
                                                                    + target.getName().getString()
                                                                    + ". New balance: " + balance),
                                                            true
                                                    );

                                                    target.sendSystemMessage(
                                                            veilMsg("An admin granted you ")
                                                                    .append(Component.literal(amount + " " + name)
                                                                            .withStyle(ChatFormatting.GOLD))
                                                    );

                                                    return 1;
                                                }))))

                        .then(Commands.literal("take")
                                .then(Commands.argument("player", EntityArgument.player())
                                        .then(Commands.argument("amount", LongArgumentType.longArg(1))
                                                .executes(ctx -> {
                                                    ServerPlayer target = EntityArgument.getPlayer(ctx, "player");
                                                    long amount = LongArgumentType.getLong(ctx, "amount");
                                                    String name = CurrencyService.currencyName();
                                                    String actor = commandActor(ctx.getSource());

                                                    boolean ok = CurrencyService.deductBalance(target, amount, "ADMIN_TAKE", actor);

                                                    if (!ok) {
                                                        ctx.getSource().sendFailure(
                                                                Component.literal(target.getName().getString()
                                                                        + " only has "
                                                                        + CurrencyService.getBalance(target)
                                                                        + " " + name + ".")
                                                        );
                                                        return 0;
                                                    }

                                                    long balance = CurrencyService.getBalance(target);

                                                    ctx.getSource().sendSuccess(
                                                            () -> adminMsg("Took " + amount + " " + name + " from "
                                                                    + target.getName().getString()
                                                                    + ". New balance: " + balance),
                                                            true
                                                    );

                                                    return 1;
                                                }))))

                        .then(Commands.literal("set")
                                .then(Commands.argument("player", EntityArgument.player())
                                        .then(Commands.argument("amount", LongArgumentType.longArg(0))
                                                .executes(ctx -> {
                                                    ServerPlayer target = EntityArgument.getPlayer(ctx, "player");
                                                    long amount = LongArgumentType.getLong(ctx, "amount");
                                                    String actor = commandActor(ctx.getSource());
                                                    long balance = CurrencyService.setBalance(target, amount, "ADMIN_SET", actor);
                                                    String name = CurrencyService.currencyName();

                                                    ctx.getSource().sendSuccess(
                                                            () -> adminMsg("Set " + target.getName().getString()
                                                                    + "'s balance to " + balance + " " + name),
                                                            true
                                                    );

                                                    return 1;
                                                }))))

                        .then(Commands.literal("check")
                                .then(Commands.argument("player", EntityArgument.player())
                                        .executes(ctx -> {
                                            ServerPlayer target = EntityArgument.getPlayer(ctx, "player");
                                            long balance = CurrencyService.getBalance(target);
                                            int reward = CurrencyService.getRewardPerTenMinutes(target);
                                            String name = CurrencyService.currencyName();

                                            ctx.getSource().sendSuccess(
                                                    () -> adminMsg(target.getName().getString()
                                                            + " - Balance: " + balance + " " + name
                                                            + "  (+" + reward + "/15 min)"),
                                                    false
                                            );

                                            return 1;
                                        })))

                        .then(Commands.literal("top")
                                .executes(ctx -> sendTopBalances(ctx.getSource(), Config.TOP_LIMIT_DEFAULT.getAsInt()))
                                .then(Commands.argument("limit", IntegerArgumentType.integer(1, 50))
                                        .executes(ctx -> sendTopBalances(
                                                ctx.getSource(),
                                                IntegerArgumentType.getInteger(ctx, "limit")
                                        ))))

                        .then(Commands.literal("reload")
                                .executes(ctx -> {
                                    CurrencyService.reloadStorage();
                                    ctx.getSource().sendSuccess(
                                            () -> adminMsg("Currency storage reloaded from disk."),
                                            true
                                    );
                                    return 1;
                                }))
        );
    }

    private void registerAetherreachAdmin(CommandDispatcher<CommandSourceStack> dispatcher) {
        dispatcher.register(
                Commands.literal("aetherreach")
                        .requires(Commands.hasPermission(
                                new PermissionCheck.Require(Permissions.COMMANDS_GAMEMASTER)
                        ))
                        .then(Commands.literal("economy")
                                .then(Commands.literal("give")
                                        .then(Commands.argument("player", EntityArgument.player())
                                                .then(Commands.argument("amount", LongArgumentType.longArg(1))
                                                        .executes(ctx -> {
                                                            ServerPlayer target = EntityArgument.getPlayer(ctx, "player");
                                                            long amount = LongArgumentType.getLong(ctx, "amount");
                                                            long balance = CurrencyService.addBalance(target, amount, "ADMIN_GIVE", commandActor(ctx.getSource()));
                                                            ctx.getSource().sendSuccess(
                                                                    () -> adminMsg("Granted " + amount + " " + CurrencyService.currencyName()
                                                                            + " to " + target.getName().getString()
                                                                            + ". Balance: " + balance),
                                                                    true
                                                            );
                                                            return 1;
                                                        }))))
                                .then(Commands.literal("take")
                                        .then(Commands.argument("player", EntityArgument.player())
                                                .then(Commands.argument("amount", LongArgumentType.longArg(1))
                                                        .executes(ctx -> {
                                                            ServerPlayer target = EntityArgument.getPlayer(ctx, "player");
                                                            long amount = LongArgumentType.getLong(ctx, "amount");
                                                            boolean ok = CurrencyService.deductBalance(target, amount, "ADMIN_TAKE", commandActor(ctx.getSource()));
                                                            if (!ok) {
                                                                ctx.getSource().sendFailure(Component.literal("Insufficient balance.").withStyle(ChatFormatting.RED));
                                                                return 0;
                                                            }
                                                            ctx.getSource().sendSuccess(
                                                                    () -> adminMsg("Removed " + amount + " " + CurrencyService.currencyName()
                                                                            + " from " + target.getName().getString()),
                                                                    true
                                                            );
                                                            return 1;
                                                        }))))
                                .then(Commands.literal("set")
                                        .then(Commands.argument("player", EntityArgument.player())
                                                .then(Commands.argument("amount", LongArgumentType.longArg(0))
                                                        .executes(ctx -> {
                                                            ServerPlayer target = EntityArgument.getPlayer(ctx, "player");
                                                            long amount = LongArgumentType.getLong(ctx, "amount");
                                                            long balance = CurrencyService.setBalance(target, amount, "ADMIN_SET", commandActor(ctx.getSource()));
                                                            ctx.getSource().sendSuccess(
                                                                    () -> adminMsg("Set " + target.getName().getString()
                                                                            + "'s balance to " + balance + " " + CurrencyService.currencyName()),
                                                                    true
                                                            );
                                                            return 1;
                                                        }))))
                                .then(Commands.literal("reload")
                                        .executes(ctx -> {
                                            CurrencyService.reloadStorage();
                                            ctx.getSource().sendSuccess(
                                                    () -> adminMsg("Economy storage reloaded."),
                                                    true
                                            );
                                            return 1;
                                        })))
                        .then(Commands.literal("ah")
                                .then(Commands.literal("remove")
                                        .then(Commands.argument("listing_id", LongArgumentType.longArg(1))
                                                .executes(ctx -> {
                                                    long listingId = LongArgumentType.getLong(ctx, "listing_id");
                                                    boolean removed = AuctionHouseService.adminRemove(listingId);
                                                    ctx.getSource().sendSuccess(
                                                            () -> adminMsg(removed
                                                                    ? "Removed Exchange listing #" + listingId
                                                                    : "No active listing found for #" + listingId),
                                                            true
                                                    );
                                                    return removed ? 1 : 0;
                                                }))))
                        .then(Commands.literal("shop")
                                .then(Commands.literal("reroll")
                                        .executes(ctx -> {
                                            List<ShopListing> listings = ShopService.reroll(ctx.getSource().getServer());
                                            ctx.getSource().sendSuccess(
                                                    () -> adminMsg(Config.SHOP_NAME.get() + " rerolled. Active stock: " + listings.size()),
                                                    true
                                            );
                                            return 1;
                                        })))
        );
    }

    private static int sendTopBalances(CommandSourceStack source, int limit) {
        List<CurrencyAccount> accounts = CurrencyService.getTopBalances(limit);
        String name = CurrencyService.currencyName();

        source.sendSuccess(
                () -> adminMsg("Top " + accounts.size() + " " + name + " Balances"),
                false
        );

        if (accounts.isEmpty()) {
            source.sendSuccess(
                    () -> Component.literal("No currency accounts found.").withStyle(ChatFormatting.GRAY),
                    false
            );
            return 1;
        }

        for (int i = 0; i < accounts.size(); i++) {
            CurrencyAccount account = accounts.get(i);
            int rank = i + 1;
            source.sendSuccess(
                    () -> Component.literal(rank + ". ")
                            .withStyle(ChatFormatting.GRAY)
                            .append(Component.literal(account.getName())
                                    .withStyle(ChatFormatting.AQUA))
                            .append(Component.literal(" - ")
                                    .withStyle(ChatFormatting.GRAY))
                            .append(Component.literal(account.getBalance() + " " + name)
                                    .withStyle(ChatFormatting.GOLD)),
                    false
            );
        }

        return 1;
    }

    private static int sendShop(CommandSourceStack source) {
        List<ShopListing> listings = ShopService.getCurrentRotation(source.getServer());
        source.sendSuccess(
                () -> veilMsg(Config.SHOP_NAME.get() + " - Current Rotation"),
                false
        );

        if (listings.isEmpty()) {
            source.sendSuccess(
                    () -> Component.literal("The import lattice is quiet. Try again after the next synchronization.")
                            .withStyle(ChatFormatting.GRAY),
                    false
            );
            return 1;
        }

        for (ShopListing listing : listings) {
            source.sendSuccess(
                    () -> Component.literal("[" + listing.slot() + "] ")
                            .withStyle(ChatFormatting.AQUA)
                            .append(Component.literal(listing.itemName() + " x" + listing.quantity())
                                    .withStyle(ChatFormatting.WHITE))
                            .append(Component.literal(" - " + listing.price() + " " + CurrencyService.currencyName())
                                    .withStyle(ChatFormatting.GOLD)),
                    false
            );
        }

        return 1;
    }

    private static int sendRules(CommandSourceStack source) {
        source.sendSuccess(
                () -> veilMsg(Config.RULES_TITLE.get()),
                false
        );

        String rules = Config.RULES_MESSAGE.get();

        if (rules == null || rules.isBlank()) {
            source.sendSuccess(
                    () -> Component.literal("No rules are configured yet.").withStyle(ChatFormatting.GRAY),
                    false
            );
            return 1;
        }

        for (String line : rules.replace("\\n", "\n").split("\\R")) {
            String trimmed = line.trim();

            if (!trimmed.isBlank()) {
                source.sendSuccess(
                        () -> Component.literal(" - ")
                                .withStyle(ChatFormatting.DARK_GRAY)
                                .append(Component.literal(trimmed)
                                        .withStyle(ChatFormatting.GRAY)),
                        false
                );
            }
        }

        return 1;
    }

    private static int sendAuctionList(CommandSourceStack source, int page) {
        List<AuctionListing> listings = AuctionHouseService.listActive(page);
        source.sendSuccess(
                () -> veilMsg(Config.EXCHANGE_NAME.get() + " - Page " + page),
                false
        );

        if (listings.isEmpty()) {
            source.sendSuccess(
                    () -> Component.literal("No active listings found.").withStyle(ChatFormatting.GRAY),
                    false
            );
            return 1;
        }

        for (AuctionListing listing : listings) {
            source.sendSuccess(
                    () -> Component.literal("#" + listing.id() + " ")
                            .withStyle(ChatFormatting.AQUA)
                            .append(Component.literal(listing.itemName() + " x" + listing.quantity())
                                    .withStyle(ChatFormatting.WHITE))
                            .append(Component.literal(" - " + listing.price() + " " + CurrencyService.currencyName())
                                    .withStyle(ChatFormatting.GOLD))
                            .append(Component.literal(" - " + listing.sellerName())
                                    .withStyle(ChatFormatting.GRAY)),
                    false
            );
        }

        return 1;
    }

    private static String commandActor(CommandSourceStack source) {
        try {
            return source.getTextName();
        } catch (Exception ignored) {
            return "console";
        }
    }

    private static MutableComponent veilMsg(String text) {
        return veilPrefixComponent()
                .append(Component.literal(text)
                        .withStyle(ChatFormatting.GRAY));
    }

    private static MutableComponent adminMsg(String text) {
        return veilMsg(text);
    }

    private static String generateLinkCode() {
        int value = ThreadLocalRandom.current().nextInt(0x1000000);
        return String.format(Locale.ROOT, "%06X", value);
    }

    private static MutableComponent veilPrefixComponent() {
        return Component.literal(formatLore(Config.VEIL_PREFIX.get()))
                .withStyle(ChatFormatting.LIGHT_PURPLE);
    }

    private static String formatLore(String template) {
        return template
                .replace("{veil}", Config.VEIL_NAME.get())
                .replace("{server}", Config.SERVER_NAME.get())
                .replace("{helper}", Config.HELPER_NAME.get());
    }
}
