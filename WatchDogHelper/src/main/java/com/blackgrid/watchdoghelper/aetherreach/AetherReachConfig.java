package com.blackgrid.watchdoghelper.aetherreach;

import net.neoforged.neoforge.common.ModConfigSpec;

/**
 * Config for the developed AetherReach/ATM11 helper features.
 *
 * This is NOT the base WatchDog Helper config.
 *
 * Keep economy, shop, welcome text, rules, and server-specific protection knobs
 * over here so the base plugin can stay generic. Later this should become its
 * own addon/module instead of living beside the base helper forever.
 */
public class AetherReachConfig {

    private static final ModConfigSpec.Builder BUILDER = new ModConfigSpec.Builder();

    // ---------------------------------------------------------------------
    // Economy config
    // ---------------------------------------------------------------------

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

    // ---------------------------------------------------------------------
    // Display names and prefixes
    // ---------------------------------------------------------------------

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

    // ---------------------------------------------------------------------
    // Discord invite/link text for the developed server command set
    // ---------------------------------------------------------------------

    public static final ModConfigSpec.ConfigValue<String> DISCORD_INVITE_URL = BUILDER
            .comment("Discord invite URL.")
            .define("discordInviteUrl", "");

    public static final ModConfigSpec.ConfigValue<String> DISCORD_LINK_URL = BUILDER
            .comment("Discord account link URL. Use {state} where the one-time token belongs.")
            .define("discordLinkUrl", "");

    // ---------------------------------------------------------------------
    // Join / MOTD / rules / leave messages
    // ---------------------------------------------------------------------

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

    // ---------------------------------------------------------------------
    // Gameplay restriction config
    // ---------------------------------------------------------------------

    public static final ModConfigSpec.ConfigValue<String> CHUNK_DESTROYER_BLOCK_ID = BUILDER
            .comment("Restricted block ID.")
            .define("chunkDestroyerBlockId", "");

    public static final ModConfigSpec.ConfigValue<String> MINING_DIMENSION_ID = BUILDER
            .comment("Allowed dimension ID.")
            .define("miningDimensionId", "");

    public static final ModConfigSpec SPEC = BUILDER.build();

    private AetherReachConfig() {}
}
