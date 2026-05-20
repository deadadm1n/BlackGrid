package com.blackgrid.watchdoghelper.currency;

import com.blackgrid.watchdoghelper.WatchDogHelper;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.Instant;

public final class CurrencyTransactionLogger {
    private static final Path LOG_FILE = Path.of("aetherreach", "logs", "currency-transactions.log");

    private CurrencyTransactionLogger() {}

    public static synchronized void log(String type, String actor, String target, long amount, long balance, String note) {
        String line = String.format(
                "%s type=%s actor=%s target=%s amount=%d balance=%d note=%s%n",
                Instant.now(), sanitize(type), sanitize(actor), sanitize(target), amount, balance, sanitize(note)
        );

        try {
            Files.createDirectories(LOG_FILE.getParent());
            Files.writeString(LOG_FILE, line, StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (IOException e) {
            WatchDogHelper.LOGGER.error("[WatchDog Helper] Failed to write currency transaction log.", e);
        }
    }

    private static String sanitize(String value) {
        if (value == null || value.isBlank()) {
            return "-";
        }
        return value.replace('\n', '_').replace('\r', '_').replace(' ', '_');
    }
}
