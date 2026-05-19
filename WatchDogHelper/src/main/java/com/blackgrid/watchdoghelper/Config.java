package com.blackgrid.watchdoghelper;

import net.neoforged.neoforge.common.ModConfigSpec;

/**
 * Server config for WatchDog Helper, the Minecraft-side helper for the AetherReach server.
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
            .comment("Display name of the server currency, for example: Shards, Coins, Gold.")
            .define("currencyName", "Shards");

    public static final ModConfigSpec.IntValue DEFAULT_CURRENCY_PER_TEN_MINUTES = BUILDER
            .comment(
                    "Fallback currency earned every passive reward cycle when the player's FTB Rank has no",
                    "'aetherreach.currency_per_10_minutes' permission node set.",
                    "The reward cycle is currently 15 minutes. The config key keeps its old name for compatibility."
            )
            .defineInRange("defaultCurrencyPerTenMinutes", 2, 0, Integer.MAX_VALUE);

    public static final ModConfigSpec.LongValue PASSIVE_REWARD_BALANCE_CAP = BUILDER
            .comment(
                    "Passive Shard generation stops once a player's balance reaches this value.",
                    "Trading, auction sales, and admin grants can still move balances above this cap.",
                    "Set to 0 to disable the passive cap."
            )
            .defineInRange("passiveRewardBalanceCap", 10000L, 0L, Long.MAX_VALUE);

    public static final ModConfigSpec.IntValue TOP_LIMIT_DEFAULT = BUILDER
            .comment("Default number of players shown by /currency top.")
            .defineInRange("currencyTopDefaultLimit", 10, 1, 50);

    public static final ModConfigSpec.IntValue SHOP_ROTATION_HOURS = BUILDER
            .comment("How often Veil Imports automatically rotates its stock.")
            .defineInRange("shopRotationHours", 12, 1, 168);

    public static final ModConfigSpec.ConfigValue<String> SERVER_NAME = BUILDER
            .comment("Lore/display name of the ATM11 server.")
            .define("serverName", "AetherReach");

    public static final ModConfigSpec.ConfigValue<String> HELPER_NAME = BUILDER
            .comment("Display name of this Minecraft-side WatchDog helper mod.")
            .define("helperName", "WatchDog Helper");

    public static final ModConfigSpec.ConfigValue<String> VEIL_NAME = BUILDER
            .comment("Lore name used for helper messages.")
            .define("veilName", "The Veil");

    public static final ModConfigSpec.ConfigValue<String> VEIL_PREFIX = BUILDER
            .comment("Prefix for lore/helper messages. Supports {veil}, {server}, and {helper}.")
            .define("veilPrefix", "[{veil}] ");

    public static final ModConfigSpec.ConfigValue<String> SERVER_PREFIX = BUILDER
            .comment("Prefix for normal server broadcasts. Supports {veil}, {server}, and {helper}.")
            .define("serverPrefix", "[{server}] ");

    public static final ModConfigSpec.ConfigValue<String> DISCORD_PREFIX = BUILDER
            .comment("Prefix for Discord messages sent into Minecraft. Supports {veil}, {server}, and {helper}.")
            .define("discordPrefix", "[Discord] ");

    public static final ModConfigSpec.ConfigValue<String> MOTD_TITLE = BUILDER
            .comment("Title shown above the configured MOTD.")
            .define("motdTitle", "MOTD");

    public static final ModConfigSpec.ConfigValue<String> RULES_TITLE = BUILDER
            .comment("Title shown above /rules and rules-on-join output.")
            .define("rulesTitle", "Rules");

    public static final ModConfigSpec.ConfigValue<String> SHOP_NAME = BUILDER
            .comment("Lore name for the rotating shop.")
            .define("shopName", "Veil Imports");

    public static final ModConfigSpec.ConfigValue<String> EXCHANGE_NAME = BUILDER
            .comment("Lore name for the auction house/player exchange.")
            .define("exchangeName", "The Exchange");

    public static final ModConfigSpec.ConfigValue<String> DISCORD_INVITE_URL = BUILDER
            .comment("Discord invite opened by /discord.")
            .define("discordInviteUrl", "https://discord.gg/pMfEksZ4Xk");


    public static final ModConfigSpec.BooleanValue WELCOME_ENABLED = BUILDER
            .comment("Enable in-game welcome messages when players join.")
            .define("welcomeEnabled", true);

    public static final ModConfigSpec.BooleanValue WELCOME_BROADCAST_TO_ALL = BUILDER
            .comment("If true, welcome messages are broadcast to all players. If false, only the joining player sees them.")
            .define("welcomeBroadcastToAll", true);

    public static final ModConfigSpec.BooleanValue MOTD_ENABLED = BUILDER
            .comment("Show the server MOTD to players when they join.")
            .define("motdEnabled", true);

    public static final ModConfigSpec.ConfigValue<String> MOTD_MESSAGE = BUILDER
            .comment(
                    "Message of the day shown on join.",
                    "Use {player} as the player name.",
                    "Supports real TOML multiline strings and escaped \\n new lines."
            )
            .define("motdMessage", "Welcome to AetherReach, {player}.\\nUse /rules to view the server rules.");

    public static final ModConfigSpec.BooleanValue RULES_ON_JOIN_ENABLED = BUILDER
            .comment("Send the configured rules to players when they join.")
            .define("rulesOnJoinEnabled", true);

    public static final ModConfigSpec.ConfigValue<String> RULES_MESSAGE = BUILDER
            .comment(
                    "Rules shown by /rules and optionally on join.",
                    "Supports real TOML multiline strings and escaped \\n new lines."
            )
            .define("rulesMessage", "1. Be respectful.\\n2. Keep destructive machines in the Mining Dimension.\\n3. No griefing or stealing.");

    public static final ModConfigSpec.ConfigValue<String> FIRST_JOIN_WELCOME_MESSAGE = BUILDER
            .comment("Message shown when a player joins the server for the first time. Use {player} as the player name.")
            .define("firstJoinWelcomeMessage", "A new soul has entered the Reach. Welcome, {player}.");

    public static final ModConfigSpec.ConfigValue<String> RETURNING_WELCOME_MESSAGE = BUILDER
            .comment("Message shown when a known player returns. Use {player} as the player name.")
            .define("returningWelcomeMessage", "{player} has returned to AetherReach.");

    public static final ModConfigSpec.BooleanValue LEAVE_MESSAGES_ENABLED = BUILDER
            .comment("Enable player leave messages.")
            .define("leaveMessagesEnabled", true);

    public static final ModConfigSpec.BooleanValue LEAVE_BROADCAST_TO_ALL = BUILDER
            .comment("If true, leave messages are broadcast to all players. If false, they are disabled for everyone except logs/future hooks.")
            .define("leaveBroadcastToAll", true);

    public static final ModConfigSpec.ConfigValue<String> PLAYER_LEAVE_MESSAGE = BUILDER
            .comment("Message shown when a player leaves. Use {player} for the player name.")
            .define("playerLeaveMessage", "{player} has faded beyond The Veil.");

    public static final ModConfigSpec.BooleanValue BRIDGE_ENABLED = BUILDER
            .comment("Enable the local WatchDog <-> WatchDog Helper HTTP bridge.")
            .define("bridgeEnabled", true);

    public static final ModConfigSpec.ConfigValue<String> BRIDGE_HOST = BUILDER
            .comment("Local bridge bind host. Keep this as 127.0.0.1. Do not expose it publicly.")
            .define("bridgeHost", "127.0.0.1");

    public static final ModConfigSpec.IntValue BRIDGE_PORT = BUILDER
            .comment("Local bridge port used by WatchDog to talk to WatchDog Helper.")
            .defineInRange("bridgePort", 25590, 1, 65535);

    public static final ModConfigSpec.ConfigValue<String> BRIDGE_TOKEN = BUILDER
            .comment("Shared secret token for Watchdog bridge requests. Change this before using the bridge.")
            .define("bridgeToken", "change-me");

    public static final ModConfigSpec.BooleanValue WATCHDOG_CALLBACK_ENABLED = BUILDER
            .comment("Enable Aether Reach sending Minecraft events back to Watchdog.")
            .define("watchdogCallbackEnabled", true);

    public static final ModConfigSpec.ConfigValue<String> WATCHDOG_CALLBACK_URL = BUILDER
            .comment("Watchdog event receiver URL.")
            .define("watchdogCallbackUrl", "http://127.0.0.1:25591/api/minecraft/event");

    public static final ModConfigSpec.ConfigValue<String> CHUNK_DESTROYER_BLOCK_ID = BUILDER
            .comment("Block id of the Chunk Destroyer that is restricted to the Mining Dimension.")
            .define("chunkDestroyerBlockId", "quarryplus:adv_quarry");

    public static final ModConfigSpec.ConfigValue<String> MINING_DIMENSION_ID = BUILDER
            .comment("Dimension id where the Chunk Destroyer is allowed to be placed.")
            .define("miningDimensionId", "allthemodium:mining");

    static final ModConfigSpec SPEC = BUILDER.build();
}
