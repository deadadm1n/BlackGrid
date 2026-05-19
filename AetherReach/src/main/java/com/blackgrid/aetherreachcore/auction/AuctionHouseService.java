package com.blackgrid.aetherreachcore.auction;

import com.blackgrid.aetherreachcore.AetherreachCore;
import com.blackgrid.aetherreachcore.currency.CurrencyService;
import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.RegistryOps;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.item.ItemStack;

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
import java.util.Optional;
import java.util.UUID;

public final class AuctionHouseService {
    public static final int LISTINGS_PER_PAGE = 8;
    private static final Gson GSON = new Gson();
    private static final Path DB_FILE = Path.of("aetherreach", "economy.db");
    private static final long LISTING_DURATION_MS = 7L * 24L * 60L * 60L * 1000L;
    private static final long MIN_PRICE = 1L;

    private AuctionHouseService() {
    }

    public static synchronized long createListing(ServerPlayer seller, long price) {
        if (price < MIN_PRICE) {
            throw new IllegalArgumentException("Price must be at least " + MIN_PRICE + " Shard.");
        }

        ItemStack held = seller.getMainHandItem();
        if (held.isEmpty()) {
            throw new IllegalArgumentException("Hold an item in your main hand to list it.");
        }

        if (isBlacklisted(held)) {
            throw new IllegalArgumentException("The Veil refuses this item within The Exchange.");
        }

        int limit = CurrencyService.getAuctionListingLimit(seller);
        int active = countActiveListings(seller.getUUID());
        if (active >= limit) {
            throw new IllegalArgumentException("Listing limit reached: " + active + "/" + limit);
        }

        ItemStack listed = held.copy();
        String itemData = serializeItem(serverOf(seller), listed);
        String itemName = listed.getHoverName().getString();
        long now = System.currentTimeMillis();
        long expiresAt = now + LISTING_DURATION_MS;

        try {
            initializeSchema();
            seller.setItemInHand(InteractionHand.MAIN_HAND, ItemStack.EMPTY);

            try (Connection connection = connect();
                 PreparedStatement statement = connection.prepareStatement(
                         """
                                 INSERT INTO auction_listings(
                                     seller_uuid, seller_name, item_data, item_name, quantity, price,
                                     created_at, expires_at, status
                                 ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE')
                                 """,
                         Statement.RETURN_GENERATED_KEYS
                 )) {
                statement.setString(1, seller.getUUID().toString());
                statement.setString(2, seller.getName().getString());
                statement.setString(3, itemData);
                statement.setString(4, itemName);
                statement.setInt(5, listed.getCount());
                statement.setLong(6, price);
                statement.setLong(7, now);
                statement.setLong(8, expiresAt);
                statement.executeUpdate();

                try (ResultSet keys = statement.getGeneratedKeys()) {
                    if (keys.next()) {
                        return keys.getLong(1);
                    }
                }
            }
        } catch (Exception e) {
            seller.setItemInHand(InteractionHand.MAIN_HAND, listed);
            AetherreachCore.LOGGER.error("[Aetherreach] Failed to create auction listing.", e);
            throw new RuntimeException("Listing creation failed; item returned.", e);
        }

        seller.setItemInHand(InteractionHand.MAIN_HAND, listed);
        throw new RuntimeException("Listing creation failed; item returned.");
    }

    public static synchronized List<AuctionListing> listActive(int page) {
        int safePage = Math.max(1, page);
        int offset = (safePage - 1) * LISTINGS_PER_PAGE;
        long now = System.currentTimeMillis();
        List<AuctionListing> listings = new ArrayList<>();

        try {
            initializeSchema();
            try (Connection connection = connect();
                 PreparedStatement statement = connection.prepareStatement(
                         """
                                 SELECT * FROM auction_listings
                                 WHERE status = 'ACTIVE' AND expires_at > ?
                                 ORDER BY created_at DESC
                                 LIMIT ? OFFSET ?
                                 """
                 )) {
                statement.setLong(1, now);
                statement.setInt(2, LISTINGS_PER_PAGE);
                statement.setInt(3, offset);

                try (ResultSet result = statement.executeQuery()) {
                    while (result.next()) {
                        listings.add(readListing(result));
                    }
                }
            }
        } catch (Exception e) {
            AetherreachCore.LOGGER.error("[Aetherreach] Failed to list auction listings.", e);
        }

        return listings;
    }

    public static synchronized Optional<AuctionListing> getActive(long listingId) {
        long now = System.currentTimeMillis();
        try {
            initializeSchema();
            try (Connection connection = connect();
                 PreparedStatement statement = connection.prepareStatement(
                         "SELECT * FROM auction_listings WHERE id = ? AND status = 'ACTIVE' AND expires_at > ?"
                 )) {
                statement.setLong(1, listingId);
                statement.setLong(2, now);

                try (ResultSet result = statement.executeQuery()) {
                    if (result.next()) {
                        return Optional.of(readListing(result));
                    }
                }
            }
        } catch (Exception e) {
            AetherreachCore.LOGGER.error("[Aetherreach] Failed to load auction listing {}.", listingId, e);
        }

        return Optional.empty();
    }

    public static synchronized void buy(ServerPlayer buyer, long listingId) {
        AuctionListing listing = getActive(listingId)
                .orElseThrow(() -> new IllegalArgumentException("Listing not found or expired."));

        if (listing.sellerUuid().equals(buyer.getUUID())) {
            throw new IllegalArgumentException("You cannot buy your own listing.");
        }

        String buyerName = buyer.getName().getString();
        if (!CurrencyService.deductBalance(buyer, listing.price(), "AH_BUY", "listing:" + listing.id())) {
            throw new IllegalArgumentException("You do not have enough " + CurrencyService.currencyName() + ".");
        }

        try {
            initializeSchema();
            try (Connection connection = connect();
                 PreparedStatement statement = connection.prepareStatement(
                         "UPDATE auction_listings SET status = 'SOLD', buyer_uuid = ?, buyer_name = ?, sold_at = ? WHERE id = ? AND status = 'ACTIVE'"
                 )) {
                statement.setString(1, buyer.getUUID().toString());
                statement.setString(2, buyerName);
                statement.setLong(3, System.currentTimeMillis());
                statement.setLong(4, listing.id());

                if (statement.executeUpdate() == 0) {
                    CurrencyService.addBalance(buyer, listing.price(), "AH_BUY_REFUND", "listing:" + listing.id());
                    throw new IllegalArgumentException("Listing is no longer available.");
                }
            }

            CurrencyService.addBalance(listing.sellerUuid(), listing.sellerName(), listing.price(), "AH_SELL", "listing:" + listing.id());
            giveOrDrop(buyer, deserializeItem(serverOf(buyer), listing.itemData()));
            logTransaction(listing, buyer);
        } catch (IllegalArgumentException e) {
            throw e;
        } catch (Exception e) {
            CurrencyService.addBalance(buyer, listing.price(), "AH_BUY_REFUND", "listing:" + listing.id());
            AetherreachCore.LOGGER.error("[Aetherreach] Failed to complete auction purchase {}.", listing.id(), e);
            throw new RuntimeException("Purchase failed; Shards refunded.", e);
        }
    }

    public static synchronized ItemStack cancel(ServerPlayer player, long listingId) {
        AuctionListing listing = getOwnedListing(player.getUUID(), listingId)
                .orElseThrow(() -> new IllegalArgumentException("Listing not found."));

        try {
            initializeSchema();
            try (Connection connection = connect();
                 PreparedStatement statement = connection.prepareStatement(
                         "UPDATE auction_listings SET status = 'CANCELLED' WHERE id = ? AND status = 'ACTIVE'"
                 )) {
                statement.setLong(1, listingId);
                if (statement.executeUpdate() == 0) {
                    throw new IllegalArgumentException("Listing can no longer be cancelled.");
                }
            }

            ItemStack stack = deserializeItem(serverOf(player), listing.itemData());
            giveOrDrop(player, stack);
            return stack;
        } catch (IllegalArgumentException e) {
            throw e;
        } catch (Exception e) {
            AetherreachCore.LOGGER.error("[Aetherreach] Failed to cancel listing {}.", listingId, e);
            throw new RuntimeException("Cancel failed.", e);
        }
    }

    public static synchronized int claimExpired(ServerPlayer player) {
        long now = System.currentTimeMillis();
        int claimed = 0;

        try {
            initializeSchema();
            List<AuctionListing> expired = new ArrayList<>();

            try (Connection connection = connect();
                 PreparedStatement statement = connection.prepareStatement(
                         "SELECT * FROM auction_listings WHERE seller_uuid = ? AND status = 'ACTIVE' AND expires_at <= ?"
                 )) {
                statement.setString(1, player.getUUID().toString());
                statement.setLong(2, now);

                try (ResultSet result = statement.executeQuery()) {
                    while (result.next()) {
                        expired.add(readListing(result));
                    }
                }
            }

            for (AuctionListing listing : expired) {
                try (Connection connection = connect();
                     PreparedStatement statement = connection.prepareStatement(
                             "UPDATE auction_listings SET status = 'EXPIRED_CLAIMED' WHERE id = ? AND status = 'ACTIVE'"
                     )) {
                    statement.setLong(1, listing.id());
                    if (statement.executeUpdate() > 0) {
                        giveOrDrop(player, deserializeItem(serverOf(player), listing.itemData()));
                        claimed++;
                    }
                }
            }
        } catch (Exception e) {
            AetherreachCore.LOGGER.error("[Aetherreach] Failed to claim expired listings for {}.", player.getName().getString(), e);
        }

        return claimed;
    }

    public static synchronized boolean adminRemove(long listingId) {
        try {
            initializeSchema();
            try (Connection connection = connect();
                 PreparedStatement statement = connection.prepareStatement(
                         "UPDATE auction_listings SET status = 'ADMIN_REMOVED' WHERE id = ? AND status = 'ACTIVE'"
                 )) {
                statement.setLong(1, listingId);
                return statement.executeUpdate() > 0;
            }
        } catch (Exception e) {
            AetherreachCore.LOGGER.error("[Aetherreach] Failed to admin-remove listing {}.", listingId, e);
            return false;
        }
    }

    private static Optional<AuctionListing> getOwnedListing(UUID sellerUuid, long listingId) {
        try {
            initializeSchema();
            try (Connection connection = connect();
                 PreparedStatement statement = connection.prepareStatement(
                         "SELECT * FROM auction_listings WHERE id = ? AND seller_uuid = ? AND status = 'ACTIVE'"
                 )) {
                statement.setLong(1, listingId);
                statement.setString(2, sellerUuid.toString());

                try (ResultSet result = statement.executeQuery()) {
                    if (result.next()) {
                        return Optional.of(readListing(result));
                    }
                }
            }
        } catch (Exception e) {
            AetherreachCore.LOGGER.error("[Aetherreach] Failed to load owned listing {}.", listingId, e);
        }

        return Optional.empty();
    }

    private static int countActiveListings(UUID sellerUuid) {
        long now = System.currentTimeMillis();
        try {
            initializeSchema();
            try (Connection connection = connect();
                 PreparedStatement statement = connection.prepareStatement(
                         "SELECT COUNT(*) FROM auction_listings WHERE seller_uuid = ? AND status = 'ACTIVE' AND expires_at > ?"
                 )) {
                statement.setString(1, sellerUuid.toString());
                statement.setLong(2, now);

                try (ResultSet result = statement.executeQuery()) {
                    if (result.next()) {
                        return result.getInt(1);
                    }
                }
            }
        } catch (Exception e) {
            AetherreachCore.LOGGER.error("[Aetherreach] Failed to count active listings for {}.", sellerUuid, e);
        }

        return 0;
    }

    private static String serializeItem(MinecraftServer server, ItemStack stack) {
        RegistryOps<JsonElement> ops = RegistryOps.create(JsonOps.INSTANCE, server.registryAccess());
        JsonElement json = ItemStack.CODEC.encodeStart(ops, stack).getOrThrow(RuntimeException::new);
        return GSON.toJson(json);
    }

    private static MinecraftServer serverOf(ServerPlayer player) {
        MinecraftServer server = player.level().getServer();
        if (server == null) {
            throw new IllegalStateException("Minecraft server is unavailable.");
        }
        return server;
    }

    private static ItemStack deserializeItem(MinecraftServer server, String itemData) {
        RegistryOps<JsonElement> ops = RegistryOps.create(JsonOps.INSTANCE, server.registryAccess());
        return ItemStack.CODEC.parse(ops, JsonParser.parseString(itemData)).getOrThrow(RuntimeException::new);
    }

    private static void giveOrDrop(ServerPlayer player, ItemStack stack) {
        if (!player.getInventory().add(stack)) {
            player.drop(stack, false);
        }
    }

    private static boolean isBlacklisted(ItemStack stack) {
        String id = BuiltInRegistries.ITEM.getKey(stack.getItem()).toString();
        return id.contains("creative")
                || id.contains("command_block")
                || id.contains("structure_block")
                || id.contains("barrier")
                || id.contains("bedrock")
                || id.contains("chunk_loader")
                || id.contains("chunkloader")
                || id.contains("ftbchunks");
    }

    private static AuctionListing readListing(ResultSet result) throws Exception {
        return new AuctionListing(
                result.getLong("id"),
                UUID.fromString(result.getString("seller_uuid")),
                result.getString("seller_name"),
                result.getString("item_data"),
                result.getString("item_name"),
                result.getInt("quantity"),
                result.getLong("price"),
                result.getLong("created_at"),
                result.getLong("expires_at")
        );
    }

    private static void logTransaction(AuctionListing listing, ServerPlayer buyer) {
        try (Connection connection = connect();
             PreparedStatement statement = connection.prepareStatement(
                     "INSERT INTO auction_transactions(listing_id, seller_uuid, buyer_uuid, price, timestamp) VALUES(?, ?, ?, ?, ?)"
             )) {
            statement.setLong(1, listing.id());
            statement.setString(2, listing.sellerUuid().toString());
            statement.setString(3, buyer.getUUID().toString());
            statement.setLong(4, listing.price());
            statement.setString(5, Instant.now().toString());
            statement.executeUpdate();
        } catch (Exception e) {
            AetherreachCore.LOGGER.warn("[Aetherreach] Failed to log auction transaction {}.", listing.id(), e);
        }
    }

    private static Connection connect() throws Exception {
        Class.forName("org.sqlite.JDBC");
        Files.createDirectories(DB_FILE.getParent());
        return DriverManager.getConnection("jdbc:sqlite:" + DB_FILE.toAbsolutePath());
    }

    private static void initializeSchema() throws Exception {
        Files.createDirectories(DB_FILE.getParent());

        try (Connection connection = connect();
             Statement statement = connection.createStatement()) {
            statement.executeUpdate("""
                    CREATE TABLE IF NOT EXISTS auction_listings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        seller_uuid TEXT NOT NULL,
                        seller_name TEXT NOT NULL,
                        item_data TEXT NOT NULL,
                        item_name TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        price INTEGER NOT NULL,
                        created_at INTEGER NOT NULL,
                        expires_at INTEGER NOT NULL,
                        status TEXT NOT NULL DEFAULT 'ACTIVE',
                        buyer_uuid TEXT,
                        buyer_name TEXT,
                        sold_at INTEGER
                    )
                    """);
            statement.executeUpdate("""
                    CREATE TABLE IF NOT EXISTS auction_transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        listing_id INTEGER NOT NULL,
                        seller_uuid TEXT NOT NULL,
                        buyer_uuid TEXT NOT NULL,
                        price INTEGER NOT NULL,
                        timestamp TEXT NOT NULL
                    )
                    """);
        }
    }
}
