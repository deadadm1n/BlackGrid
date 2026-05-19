package com.blackgrid.aetherreachcore.currency.storage;

import com.blackgrid.aetherreachcore.currency.CurrencyAccount;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface CurrencyStorage {
    CurrencyAccount getOrCreate(UUID uuid, String name);

    Optional<CurrencyAccount> get(UUID uuid);

    long getBalance(UUID uuid, String name);

    long setBalance(UUID uuid, String name, long amount);

    long addBalance(UUID uuid, String name, long amount);

    boolean deductBalance(UUID uuid, String name, long amount);

    List<CurrencyAccount> topBalances(int limit);

    void reload();

    void save();
}
