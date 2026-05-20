package com.blackgrid.watchdoghelper.currency.storage;

import com.blackgrid.watchdoghelper.WatchDogHelper;
import com.blackgrid.watchdoghelper.currency.CurrencyAccount;
import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.reflect.TypeToken;

import java.io.IOException;
import java.io.Reader;
import java.io.Writer;
import java.lang.reflect.Type;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

public class JsonCurrencyStorage implements CurrencyStorage {
    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final Type ACCOUNT_MAP_TYPE = new TypeToken<Map<String, CurrencyAccount>>() {}.getType();

    private final Path file;
    private final Map<String, CurrencyAccount> accounts = new HashMap<>();

    public JsonCurrencyStorage(Path file) {
        this.file = file;
        reload();
    }

    @Override
    public synchronized CurrencyAccount getOrCreate(UUID uuid, String name) {
        String key = uuid.toString();
        CurrencyAccount account = accounts.get(key);

        if (account == null) {
            account = new CurrencyAccount(uuid, name, 0L);
            accounts.put(key, account);
            save();
            return account;
        }

        account.setName(name);
        save();
        return account;
    }

    @Override
    public synchronized Optional<CurrencyAccount> get(UUID uuid) {
        return Optional.ofNullable(accounts.get(uuid.toString()));
    }

    @Override
    public synchronized long getBalance(UUID uuid, String name) {
        return getOrCreate(uuid, name).getBalance();
    }

    @Override
    public synchronized long setBalance(UUID uuid, String name, long amount) {
        CurrencyAccount account = getOrCreate(uuid, name);
        account.setBalance(amount);
        save();
        return account.getBalance();
    }

    @Override
    public synchronized long addBalance(UUID uuid, String name, long amount) {
        CurrencyAccount account = getOrCreate(uuid, name);
        account.setBalance(account.getBalance() + Math.max(0L, amount));
        save();
        return account.getBalance();
    }

    @Override
    public synchronized boolean deductBalance(UUID uuid, String name, long amount) {
        CurrencyAccount account = getOrCreate(uuid, name);
        long safeAmount = Math.max(0L, amount);

        if (account.getBalance() < safeAmount) {
            return false;
        }

        account.setBalance(account.getBalance() - safeAmount);
        save();
        return true;
    }

    @Override
    public synchronized List<CurrencyAccount> topBalances(int limit) {
        int safeLimit = Math.max(1, Math.min(limit, 50));

        return accounts.values().stream()
                .sorted(Comparator.comparingLong(CurrencyAccount::getBalance).reversed())
                .limit(safeLimit)
                .toList();
    }

    @Override
    public synchronized void reload() {
        accounts.clear();

        try {
            Files.createDirectories(file.getParent());

            if (!Files.exists(file)) {
                save();
                return;
            }

            try (Reader reader = Files.newBufferedReader(file)) {
                Map<String, CurrencyAccount> loaded = GSON.fromJson(reader, ACCOUNT_MAP_TYPE);
                if (loaded != null) {
                    accounts.putAll(loaded);
                }
            }
        } catch (Exception e) {
            WatchDogHelper.LOGGER.error("[WatchDog Helper] Failed to load currency storage '{}'. Backing up and starting empty.", file, e);
            backupCorruptFile();
            accounts.clear();
            save();
        }
    }

    @Override
    public synchronized void save() {
        try {
            Files.createDirectories(file.getParent());

            Path tmpFile = file.resolveSibling(file.getFileName() + ".tmp");
            try (Writer writer = Files.newBufferedWriter(tmpFile)) {
                GSON.toJson(accounts, ACCOUNT_MAP_TYPE, writer);
            }

            Files.move(tmpFile, file, StandardCopyOption.REPLACE_EXISTING, StandardCopyOption.ATOMIC_MOVE);
        } catch (IOException atomicMoveFailed) {
            try {
                Path tmpFile = file.resolveSibling(file.getFileName() + ".tmp");
                Files.move(tmpFile, file, StandardCopyOption.REPLACE_EXISTING);
            } catch (Exception e) {
                WatchDogHelper.LOGGER.error("[WatchDog Helper] Failed to save currency storage '{}'.", file, e);
            }
        } catch (Exception e) {
            WatchDogHelper.LOGGER.error("[WatchDog Helper] Failed to save currency storage '{}'.", file, e);
        }
    }

    private void backupCorruptFile() {
        try {
            if (Files.exists(file)) {
                Path backup = file.resolveSibling(file.getFileName() + ".corrupt-" + System.currentTimeMillis() + ".bak");
                Files.copy(file, backup, StandardCopyOption.REPLACE_EXISTING);
            }
        } catch (Exception e) {
            WatchDogHelper.LOGGER.error("[WatchDog Helper] Failed to back up corrupt currency storage '{}'.", file, e);
        }
    }
}
