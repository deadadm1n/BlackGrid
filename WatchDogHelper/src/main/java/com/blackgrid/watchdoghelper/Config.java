package com.blackgrid.watchdoghelper;

import net.neoforged.neoforge.common.ModConfigSpec;

/**
 * Server config for WatchDog Helper.
 *
 * Rank-based passive currency rewards are configured in FTB Ranks with:
 *   "aetherreach.currency_per_10_minutes": <integer>
 *
 * The legacy node name is kept for compatibility, but rewards are currently paid every 15 minutes.
 * If a player has no rank value set, defaultCurrencyPerTenMinutes is used.
 */
public class Config {

    private static final ModConfigSpec.Builder BUILDER = new ModConfigSpec.Builder();

    public static final ModConfigSpec.ConfigValue<String> CURRENCY_NAME = BUILDER
            .comment("Currency display name.")
            .define("currencyName", "");

    public static final ModConfigSpec.IntValue DEFAULT_CURRENCY_PER_TEN_MINUTES = BUILDER
            .comment("Fallback passive reward.")
            .defineInRange("defaultCurrencyPerTenMinutes", 0, 0, Integer.MAX_VALUE);

    public static final ModConfigSpec.LongValue PASSIVE_REWARD_BALANCE_CAP = BUILDER
            .comment("Passive reward balance cap.")
            .defineInRange("passiveRewardBalanceCap", 0L, 0L, Long.MAX_VALUE);

    public static final ModConfigSpec.IntValue TOP_LIMIT_DEFAULT = BUILDER
            .comment("Default /currency top limit.")
            .defineInRange("currencyTopDefaultLimit", 10, 1, 50);

    public static final ModConfigSpec.IntValue SHOP_ROTATION_HOURS = BUILDER
            .comment("Shop rotation hours.")
            .defineInRange("shopRotationHours", 12, 1, 168);

    public static final ModConfigSpec.ConfigValue<String> SERVER_NAME = BUILDER
            .comment("Server display name.")
            .define("serverName", "");

    public static final ModConfigSpec.ConfigValue<String> HELPER_NAME = BUILDER
            .comment("Helper display name.")
            .define("helperName", "");

    public static final ModConfigSpec.ConfigValue<String> VEIL_NAME = BUILDER
            .comment("Lore display name.")
            .define("veilName", "");

    public static final ModConfigSpec.ConfigValue<String> VEIL_PREFIX = BUILDER
            .comment("Helper message prefix.")
            .define("veilPrefix", "");

    public static final ModConfigSpec.ConfigValue<String> SERVER_PREFIX = BUILDER
            .comment("Server broadcast prefix.")
            .define("serverPrefix", "");

    public static final ModConfigSpec.ConfigValue<String> DISCORD_PREFIX = BUILDER
            .comment("Discord chat prefix.")
            .define("discordPrefix", "");

    public static final ModConfigSpec.ConfigValue<String> MOTD_TITLE = BUILDER
            .comment("MOTD title.")
            .define("motdTitle", "");

    public static final ModConfigSpec.ConfigValue<String> RULES_TITLE = BUILDER
            .comment("Rules title.")
            .define("rulesTitle", "");

    public static final ModConfigSpec.ConfigValue<String> SHOP_NAME = BUILDER
            .comment("Shop display name.")
            .define("shopName", "");

    public static final ModConfigSpec.ConfigValue<String> EXCHANGE_NAME = BUILDER
            .comment("Exchange display name.")
            .define("exchangeName", "");

    public static final ModConfigSpec.ConfigValue<String> DISCORD_INVITE_URL = BUILDER
            .comment("Discord invite URL.")
            .define("discordInviteUrl", "");


    public static final ModConfigSpec.BooleanValue WELCOME_ENABLED = BUILDER
            .comment("Enable join messages.")
            .define("welcomeEnabled", false);

    public static final ModConfigSpec.BooleanValue WELCOME_BROADCAST_TO_ALL = BUILDER
            .comment("Broadcast join messages.")
            .define("welcomeBroadcastToAll", false);

    public static final ModConfigSpec.BooleanValue MOTD_ENABLED = BUILDER
            .comment("Enable join MOTD.")
            .define("motdEnabled", false);

    public static final ModConfigSpec.ConfigValue<String> MOTD_MESSAGE = BUILDER
            .comment("MOTD message.")
            .define("motdMessage", "");

    public static final ModConfigSpec.BooleanValue RULES_ON_JOIN_ENABLED = BUILDER
            .comment("Show rules on join.")
            .define("rulesOnJoinEnabled", false);

    public static final ModConfigSpec.ConfigValue<String> RULES_MESSAGE = BUILDER
            .comment("Rules message.")
            .define("rulesMessage", "");

    public static final ModConfigSpec.ConfigValue<String> FIRST_JOIN_WELCOME_MESSAGE = BUILDER
            .comment("First join message.")
            .define("firstJoinWelcomeMessage", "");

    public static final ModConfigSpec.ConfigValue<String> RETURNING_WELCOME_MESSAGE = BUILDER
            .comment("Returning join message.")
            .define("returningWelcomeMessage", "");

    public static final ModConfigSpec.BooleanValue LEAVE_MESSAGES_ENABLED = BUILDER
            .comment("Enable leave messages.")
            .define("leaveMessagesEnabled", false);

    public static final ModConfigSpec.BooleanValue LEAVE_BROADCAST_TO_ALL = BUILDER
            .comment("Broadcast leave messages.")
            .define("leaveBroadcastToAll", false);

    public static final ModConfigSpec.ConfigValue<String> PLAYER_LEAVE_MESSAGE = BUILDER
            .comment("Leave message.")
            .define("playerLeaveMessage", "");

    public static final ModConfigSpec.BooleanValue BRIDGE_ENABLED = BUILDER
            .comment("Enable HTTP bridge.")
            .define("bridgeEnabled", false);

    public static final ModConfigSpec.ConfigValue<String> BRIDGE_HOST = BUILDER
            .comment("HTTP bridge host.")
            .define("bridgeHost", "");

    public static final ModConfigSpec.IntValue BRIDGE_PORT = BUILDER
            .comment("HTTP bridge port.")
            .defineInRange("bridgePort", 25590, 1, 65535);

    public static final ModConfigSpec.ConfigValue<String> BRIDGE_TOKEN = BUILDER
            .comment("HTTP bridge token.")
            .define("bridgeToken", "");

    public static final ModConfigSpec.BooleanValue WATCHDOG_CALLBACK_ENABLED = BUILDER
            .comment("Enable WatchDog callback.")
            .define("watchdogCallbackEnabled", false);

    public static final ModConfigSpec.ConfigValue<String> WATCHDOG_CALLBACK_URL = BUILDER
            .comment("WatchDog callback URL.")
            .define("watchdogCallbackUrl", "");

    public static final ModConfigSpec.ConfigValue<String> CHUNK_DESTROYER_BLOCK_ID = BUILDER
            .comment("Restricted block ID.")
            .define("chunkDestroyerBlockId", "");

    public static final ModConfigSpec.ConfigValue<String> MINING_DIMENSION_ID = BUILDER
            .comment("Allowed dimension ID.")
            .define("miningDimensionId", "");

    static final ModConfigSpec SPEC = BUILDER.build();
}
