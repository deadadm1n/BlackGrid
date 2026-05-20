package com.blackgrid.watchdoghelper.currency;

import com.blackgrid.watchdoghelper.WatchDogHelper;
import com.blackgrid.watchdoghelper.Config;
import com.blackgrid.watchdoghelper.currency.storage.CurrencyStorage;
import com.blackgrid.watchdoghelper.currency.storage.SqliteCurrencyStorage;
import dev.ftb.mods.ftbranks.api.FTBRanksAPI;
import dev.ftb.mods.ftbranks.api.PermissionValue;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.fml.ModList;

import java.nio.file.Path;
import java.util.List;
import java.util.UUID;

public class CurrencyService {

    private static final String BALANCE_KEY = "aetherreach_currency";
    public static final String REWARD_NODE = "aetherreach.currency_per_10_minutes";
    public static final String AUCTION_LIMIT_NODE = "aetherreach.auction_limit";

    private static CurrencyStorage storage = new SqliteCurrencyStorage(
            Path.of("aetherreach", "economy.db"),
            Path.of("aetherreach", "currency", "accounts.json")
    );

    private CurrencyService() {}

    public static long getBalance(ServerPlayer player) {
        migratePlayerIfNeeded(player);
        return storage.getBalance(player.getUUID(), player.getName().getString());
    }

    public static long addBalance(ServerPlayer player, long amount) {
        return addBalance(player, amount, "ADD", "system");
    }

    public static long addBalance(ServerPlayer player, long amount, String reason, String actor) {
        migratePlayerIfNeeded(player);
        long updated = storage.addBalance(player.getUUID(), player.getName().getString(), amount);
        mirrorBalanceToPlayerNbt(player, updated);
        CurrencyTransactionLogger.log(reason, actor, player.getName().getString(), amount, updated, "add");
        return updated;
    }

    public static long addBalance(UUID uuid, String name, long amount, String reason, String actor) {
        long updated = storage.addBalance(uuid, name, amount);
        CurrencyTransactionLogger.log(reason, actor, name, amount, updated, "add");
        return updated;
    }

    public static boolean deductBalance(ServerPlayer player, long amount) {
        return deductBalance(player, amount, "DEDUCT", "system");
    }

    public static boolean deductBalance(ServerPlayer player, long amount, String reason, String actor) {
        migratePlayerIfNeeded(player);
        boolean success = storage.deductBalance(player.getUUID(), player.getName().getString(), amount);
        long balance = storage.getBalance(player.getUUID(), player.getName().getString());
        mirrorBalanceToPlayerNbt(player, balance);

        if (success) {
            CurrencyTransactionLogger.log(reason, actor, player.getName().getString(), amount, balance, "deduct");
        } else {
            CurrencyTransactionLogger.log(reason + "_FAILED", actor, player.getName().getString(), amount, balance, "insufficient_funds");
        }

        return success;
    }

    public static boolean deductBalance(UUID uuid, String name, long amount, String reason, String actor) {
        boolean success = storage.deductBalance(uuid, name, amount);
        long balance = storage.getBalance(uuid, name);

        if (success) {
            CurrencyTransactionLogger.log(reason, actor, name, amount, balance, "deduct");
        } else {
            CurrencyTransactionLogger.log(reason + "_FAILED", actor, name, amount, balance, "insufficient_funds");
        }

        return success;
    }

    public static long setBalance(ServerPlayer player, long amount) {
        return setBalance(player, amount, "SET", "system");
    }

    public static long setBalance(ServerPlayer player, long amount, String reason, String actor) {
        migratePlayerIfNeeded(player);
        long updated = storage.setBalance(player.getUUID(), player.getName().getString(), amount);
        mirrorBalanceToPlayerNbt(player, updated);
        CurrencyTransactionLogger.log(reason, actor, player.getName().getString(), amount, updated, "set");
        return updated;
    }

    public static int getRewardPerCycle(ServerPlayer player) {
        int ranked = getPositiveRankInteger(player, REWARD_NODE);
        if (ranked > 0) {
            return ranked;
        }

        return Config.DEFAULT_CURRENCY_PER_TEN_MINUTES.getAsInt();
    }

    public static int getRewardPerTenMinutes(ServerPlayer player) {
        return getRewardPerCycle(player);
    }

    public static int getAuctionListingLimit(ServerPlayer player) {
        int ranked = getPositiveRankInteger(player, AUCTION_LIMIT_NODE);
        if (ranked > 0) {
            return ranked;
        }

        return Math.max(2, getRewardPerCycle(player) * 2);
    }

    private static int getPositiveRankInteger(ServerPlayer player, String node) {
        if (ModList.get().isLoaded("ftbranks")) {
            try {
                PermissionValue value = FTBRanksAPI.getPermissionValue(player, node);
                if (value != PermissionValue.MISSING) {
                    int configured = value.asInteger().orElse(0);
                    if (configured > 0) {
                        return configured;
                    }
                }
            } catch (Exception e) {
                WatchDogHelper.LOGGER.warn("[WatchDog Helper] Failed to read FTB Ranks permission '{}': {}", node, e.getMessage());
            }
        }

        return 0;
    }

    public static long addPassiveReward(ServerPlayer player) {
        int reward = getRewardPerCycle(player);
        if (reward <= 0) {
            migratePlayerIfNeeded(player);
            return getBalance(player);
        }

        long balance = getBalance(player);
        long cap = Config.PASSIVE_REWARD_BALANCE_CAP.getAsLong();
        if (cap > 0L && balance >= cap) {
            CurrencyTransactionLogger.log("REWARD_15_MIN_SKIPPED", "loyalty", player.getName().getString(), reward, balance, "passive_cap_reached");
            return balance;
        }

        long payout = reward;
        if (cap > 0L) {
            payout = Math.min(payout, cap - balance);
        }

        return addBalance(player, payout, "REWARD_15_MIN", "loyalty");
    }

    public static long addTenMinuteReward(ServerPlayer player) {
        return addPassiveReward(player);
    }

    public static List<CurrencyAccount> getTopBalances(int limit) {
        return storage.topBalances(limit);
    }

    public static void reloadStorage() {
        storage.reload();
        WatchDogHelper.LOGGER.info("[WatchDog Helper] Currency storage reloaded.");
    }

    public static String currencyName() {
        return Config.CURRENCY_NAME.get();
    }

    private static void migratePlayerIfNeeded(ServerPlayer player) {
        String name = player.getName().getString();

        if (storage.get(player.getUUID()).isPresent()) {
            storage.getOrCreate(player.getUUID(), name);
            return;
        }

        CompoundTag data = player.getPersistentData();
        long oldBalance = data.getLong(BALANCE_KEY).orElse(0L);
        long migrated = storage.setBalance(player.getUUID(), name, oldBalance);
        mirrorBalanceToPlayerNbt(player, migrated);

        if (oldBalance > 0L) {
            CurrencyTransactionLogger.log("MIGRATE_NBT", "system", name, oldBalance, migrated, "old_player_nbt_to_json_storage");
        }
    }

    private static void mirrorBalanceToPlayerNbt(ServerPlayer player, long balance) {
        player.getPersistentData().putLong(BALANCE_KEY, Math.max(0L, balance));
    }
}
