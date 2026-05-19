package com.blackgrid.watchdoghelper.currency.storage;

import com.blackgrid.watchdoghelper.WatchDogHelper;
import com.blackgrid.watchdoghelper.currency.CurrencyAccount;
import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;

import java.io.Reader;
import java.lang.reflect.Type;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

public class SqliteCurrencyStorage implements CurrencyStorage {
    private static final Gson GSON = new Gson();
    private static final Type ACCOUNT_MAP_TYPE = new TypeToken<Map<String, CurrencyAccount>>() {}.getType();

    private final Path file;
    private final Path legacyJsonFile;

    public SqliteCurrencyStorage(Path file, Path legacyJsonFile) {
        this.file = file;
        this.legacyJsonFile = legacyJsonFile;
        reload();
    }

    @Override
    public synchronized CurrencyAccount getOrCreate(UUID uuid, String name) {
        Optional<CurrencyAccount> existing = get(uuid);
        if (existing.isPresent()) {
            updateName(uuid, name);
            return get(uuid).orElse(existing.get());
        }

        long now = System.currentTimeMillis();
        try (Connection connection = connect();
             PreparedStatement statement = connection.prepareStatement(
                     "INSERT INTO players(uuid, name, balance, total_earned, total_spent, first_seen, last_seen) VALUES(?, ?, 0, 0, 0, ?, ?)"
             )) {
            statement.setString(1, uuid.toString());
            statement.setString(2, safeName(uuid, name));
            statement.setLong(3, now);
            statement.setLong(4, now);
            statement.executeUpdate();
        } catch (Exception e) {
            WatchDogHelper.LOGGER.error("[Aetherreach] Failed to create currency account for {}", uuid, e);
        }

        return get(uuid).orElse(new CurrencyAccount(uuid, safeName(uuid, name), 0L));
    }

    @Override
    public synchronized Optional<CurrencyAccount> get(UUID uuid) {
        try (Connection connection = connect();
             PreparedStatement statement = connection.prepareStatement(
                     "SELECT uuid, name, balance, first_seen, last_seen FROM players WHERE uuid = ?"
             )) {
            statement.setString(1, uuid.toString());
            try (ResultSet result = statement.executeQuery()) {
                if (!result.next()) {
                    return Optional.empty();
                }
                CurrencyAccount account = new CurrencyAccount(
                        UUID.fromString(result.getString("uuid")),
                        result.getString("name"),
                        result.getLong("balance")
                );
                return Optional.of(account);
            }
        } catch (Exception e) {
            WatchDogHelper.LOGGER.error("[Aetherreach] Failed to load currency account for {}", uuid, e);
            return Optional.empty();
        }
    }

    @Override
    public synchronized long getBalance(UUID uuid, String name) {
        return getOrCreate(uuid, name).getBalance();
    }

    @Override
    public synchronized long setBalance(UUID uuid, String name, long amount) {
        CurrencyAccount account = getOrCreate(uuid, name);
        long safeAmount = Math.max(0L, amount);
        long now = System.currentTimeMillis();

        try (Connection connection = connect();
             PreparedStatement statement = connection.prepareStatement(
                     "UPDATE players SET name = ?, balance = ?, last_seen = ? WHERE uuid = ?"
             )) {
            statement.setString(1, safeName(uuid, name));
            statement.setLong(2, safeAmount);
            statement.setLong(3, now);
            statement.setString(4, uuid.toString());
            statement.executeUpdate();
            return safeAmount;
        } catch (Exception e) {
            WatchDogHelper.LOGGER.error("[Aetherreach] Failed to set currency balance for {}", uuid, e);
            return account.getBalance();
        }
    }

    @Override
    public synchronized long addBalance(UUID uuid, String name, long amount) {
        getOrCreate(uuid, name);
        long safeAmount = Math.max(0L, amount);
        long now = System.currentTimeMillis();

        try (Connection connection = connect();
             PreparedStatement statement = connection.prepareStatement(
                     "UPDATE players SET name = ?, balance = balance + ?, total_earned = total_earned + ?, last_seen = ? WHERE uuid = ?"
             )) {
            statement.setString(1, safeName(uuid, name));
            statement.setLong(2, safeAmount);
            statement.setLong(3, safeAmount);
            statement.setLong(4, now);
            statement.setString(5, uuid.toString());
            statement.executeUpdate();
            return getBalance(uuid, name);
        } catch (Exception e) {
            WatchDogHelper.LOGGER.error("[Aetherreach] Failed to add currency balance for {}", uuid, e);
            return getBalance(uuid, name);
        }
    }

    @Override
    public synchronized boolean deductBalance(UUID uuid, String name, long amount) {
        getOrCreate(uuid, name);
        long safeAmount = Math.max(0L, amount);
        long now = System.currentTimeMillis();

        try (Connection connection = connect();
             PreparedStatement statement = connection.prepareStatement(
                     "UPDATE players SET name = ?, balance = balance - ?, total_spent = total_spent + ?, last_seen = ? WHERE uuid = ? AND balance >= ?"
             )) {
            statement.setString(1, safeName(uuid, name));
            statement.setLong(2, safeAmount);
            statement.setLong(3, safeAmount);
            statement.setLong(4, now);
            statement.setString(5, uuid.toString());
            statement.setLong(6, safeAmount);
            return statement.executeUpdate() > 0;
        } catch (Exception e) {
            WatchDogHelper.LOGGER.error("[Aetherreach] Failed to deduct currency balance for {}", uuid, e);
            return false;
        }
    }

    @Override
    public synchronized List<CurrencyAccount> topBalances(int limit) {
        int safeLimit = Math.max(1, Math.min(limit, 50));
        List<CurrencyAccount> accounts = new ArrayList<>();

        try (Connection connection = connect();
             PreparedStatement statement = connection.prepareStatement(
                     "SELECT uuid, name, balance FROM players ORDER BY balance DESC LIMIT ?"
             )) {
            statement.setInt(1, safeLimit);
            try (ResultSet result = statement.executeQuery()) {
                while (result.next()) {
                    accounts.add(new CurrencyAccount(
                            UUID.fromString(result.getString("uuid")),
                            result.getString("name"),
                            result.getLong("balance")
                    ));
                }
            }
        } catch (Exception e) {
            WatchDogHelper.LOGGER.error("[Aetherreach] Failed to list top balances.", e);
        }

        return accounts;
    }

    @Override
    public synchronized void reload() {
        try {
            Class.forName("org.sqlite.JDBC");
            Files.createDirectories(file.getParent());
            initializeSchema();
            migrateLegacyJsonIfNeeded();
        } catch (Exception e) {
            WatchDogHelper.LOGGER.error("[Aetherreach] Failed to initialize SQLite economy storage '{}'.", file, e);
        }
    }

    @Override
    public synchronized void save() {
        // SQLite writes are committed per operation.
    }

    private Connection connect() throws Exception {
        return DriverManager.getConnection("jdbc:sqlite:" + file.toAbsolutePath());
    }

    private void initializeSchema() throws Exception {
        try (Connection connection = connect();
             Statement statement = connection.createStatement()) {
            statement.executeUpdate("""
                    CREATE TABLE IF NOT EXISTS players (
                        uuid TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        balance INTEGER NOT NULL DEFAULT 0,
                        total_earned INTEGER NOT NULL DEFAULT 0,
                        total_spent INTEGER NOT NULL DEFAULT 0,
                        first_seen INTEGER NOT NULL,
                        last_seen INTEGER NOT NULL
                    )
                    """);
            statement.executeUpdate("""
                    CREATE TABLE IF NOT EXISTS currency_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        player_uuid TEXT,
                        amount INTEGER NOT NULL,
                        reason TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    )
                    """);
        }
    }

    private void migrateLegacyJsonIfNeeded() {
        if (legacyJsonFile == null || !Files.exists(legacyJsonFile)) {
            return;
        }

        try (Connection connection = connect();
             Statement countStatement = connection.createStatement();
             ResultSet count = countStatement.executeQuery("SELECT COUNT(*) FROM players")) {
            if (count.next() && count.getInt(1) > 0) {
                return;
            }
        } catch (Exception e) {
            WatchDogHelper.LOGGER.warn("[Aetherreach] Could not check SQLite migration state.", e);
            return;
        }

        try (Reader reader = Files.newBufferedReader(legacyJsonFile)) {
            Map<String, CurrencyAccount> accounts = GSON.fromJson(reader, ACCOUNT_MAP_TYPE);
            if (accounts == null || accounts.isEmpty()) {
                return;
            }

            for (CurrencyAccount account : accounts.values()) {
                setBalance(account.getUuid(), account.getName(), account.getBalance());
            }

            Path migrated = legacyJsonFile.resolveSibling(legacyJsonFile.getFileName() + ".migrated-" + Instant.now().toEpochMilli());
            Files.move(legacyJsonFile, migrated);
            WatchDogHelper.LOGGER.info("[Aetherreach] Migrated {} currency account(s) from JSON to SQLite.", accounts.size());
        } catch (Exception e) {
            WatchDogHelper.LOGGER.error("[Aetherreach] Failed to migrate legacy JSON currency storage.", e);
        }
    }

    private void updateName(UUID uuid, String name) {
        long now = System.currentTimeMillis();
        try (Connection connection = connect();
             PreparedStatement statement = connection.prepareStatement(
                     "UPDATE players SET name = ?, last_seen = ? WHERE uuid = ?"
             )) {
            statement.setString(1, safeName(uuid, name));
            statement.setLong(2, now);
            statement.setString(3, uuid.toString());
            statement.executeUpdate();
        } catch (Exception e) {
            WatchDogHelper.LOGGER.warn("[Aetherreach] Failed to update currency account name for {}", uuid, e);
        }
    }

    private static String safeName(UUID uuid, String name) {
        return name == null || name.isBlank() ? uuid.toString() : name;
    }
}
