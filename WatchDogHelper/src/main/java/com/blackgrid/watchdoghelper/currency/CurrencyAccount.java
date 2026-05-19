package com.blackgrid.watchdoghelper.currency;

import java.util.UUID;

public class CurrencyAccount {
    private String uuid;
    private String name;
    private long balance;
    private long createdAtEpochMs;
    private long updatedAtEpochMs;

    public CurrencyAccount() {
        // Required for Gson.
    }

    public CurrencyAccount(UUID uuid, String name, long balance) {
        long now = System.currentTimeMillis();
        this.uuid = uuid.toString();
        this.name = name;
        this.balance = Math.max(0L, balance);
        this.createdAtEpochMs = now;
        this.updatedAtEpochMs = now;
    }

    public UUID getUuid() {
        return UUID.fromString(uuid);
    }

    public String getUuidString() {
        return uuid;
    }

    public String getName() {
        return name == null || name.isBlank() ? uuid : name;
    }

    public void setName(String name) {
        if (name != null && !name.isBlank()) {
            this.name = name;
            touch();
        }
    }

    public long getBalance() {
        return balance;
    }

    public void setBalance(long balance) {
        this.balance = Math.max(0L, balance);
        touch();
    }

    public long getCreatedAtEpochMs() {
        return createdAtEpochMs;
    }

    public long getUpdatedAtEpochMs() {
        return updatedAtEpochMs;
    }

    public void touch() {
        long now = System.currentTimeMillis();
        if (createdAtEpochMs <= 0L) {
            createdAtEpochMs = now;
        }
        updatedAtEpochMs = now;
    }
}
