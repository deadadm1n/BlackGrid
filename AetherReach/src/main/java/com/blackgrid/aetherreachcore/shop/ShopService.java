package com.blackgrid.aetherreachcore.shop;

import com.blackgrid.aetherreachcore.AetherreachCore;
import com.blackgrid.aetherreachcore.Config;
import com.blackgrid.aetherreachcore.currency.CurrencyService;
import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.RegistryOps;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.util.context.ContextMap;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.Ingredient;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.display.SlotDisplayContext;

import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.Random;

public final class ShopService {
    public static final int ROTATION_SIZE = 6;

    private static final Gson GSON = new Gson();
    private static final Path DB_FILE = Path.of("aetherreach", "economy.db");
    private static final Random RANDOM = new Random();

    private static final List<ShopItemDefinition> STOCK_POOL = List.of(
            new ShopItemDefinition("minecraft:cobblestone", ShopRarity.COMMON, 32, 64, 8),
            new ShopItemDefinition("minecraft:stone", ShopRarity.COMMON, 32, 64, 10),
            new ShopItemDefinition("minecraft:deepslate", ShopRarity.COMMON, 32, 64, 10),
            new ShopItemDefinition("minecraft:oak_log", ShopRarity.COMMON, 16, 32, 14),
            new ShopItemDefinition("minecraft:spruce_log", ShopRarity.COMMON, 16, 32, 14),
            new ShopItemDefinition("minecraft:glass", ShopRarity.COMMON, 16, 32, 18),
            new ShopItemDefinition("minecraft:coal", ShopRarity.COMMON, 16, 32, 22),
            new ShopItemDefinition("minecraft:redstone", ShopRarity.COMMON, 16, 32, 24),
            new ShopItemDefinition("minecraft:lapis_lazuli", ShopRarity.COMMON, 12, 24, 24),
            new ShopItemDefinition("minecraft:clay_ball", ShopRarity.COMMON, 16, 32, 18),
            new ShopItemDefinition("minecraft:brick", ShopRarity.COMMON, 16, 32, 22),
            new ShopItemDefinition("minecraft:paper", ShopRarity.COMMON, 16, 32, 16),
            new ShopItemDefinition("minecraft:leather", ShopRarity.UNCOMMON, 8, 16, 42),
            new ShopItemDefinition("minecraft:slime_ball", ShopRarity.UNCOMMON, 8, 16, 46),
            new ShopItemDefinition("minecraft:quartz", ShopRarity.UNCOMMON, 8, 16, 48),
            new ShopItemDefinition("minecraft:amethyst_shard", ShopRarity.UNCOMMON, 8, 16, 52),
            new ShopItemDefinition("minecraft:copper_ingot", ShopRarity.COMMON, 12, 24, 28),
            new ShopItemDefinition("minecraft:iron_ingot", ShopRarity.UNCOMMON, 8, 16, 56),
            new ShopItemDefinition("minecraft:gold_ingot", ShopRarity.UNCOMMON, 6, 12, 66),
            new ShopItemDefinition("minecraft:obsidian", ShopRarity.UNCOMMON, 4, 8, 76),
            new ShopItemDefinition("minecraft:ender_pearl", ShopRarity.ADVANCED, 2, 6, 130),
            new ShopItemDefinition("minecraft:blaze_rod", ShopRarity.ADVANCED, 2, 6, 145),
            new ShopItemDefinition("ae2:certus_quartz_crystal", ShopRarity.UNCOMMON, 8, 16, 70),
            new ShopItemDefinition("ae2:certus_quartz_dust", ShopRarity.UNCOMMON, 8, 16, 76),
            new ShopItemDefinition("ae2:fluix_crystal", ShopRarity.ADVANCED, 4, 8, 135),
            new ShopItemDefinition("ae2:logic_processor", ShopRarity.ADVANCED, 2, 6, 180),
            new ShopItemDefinition("ae2:calculation_processor", ShopRarity.ADVANCED, 2, 6, 190),
            new ShopItemDefinition("ae2:engineering_processor", ShopRarity.RARE, 1, 4, 280),
            new ShopItemDefinition("mekanism:ingot_osmium", ShopRarity.UNCOMMON, 8, 16, 72),
            new ShopItemDefinition("mekanism:ingot_steel", ShopRarity.ADVANCED, 4, 12, 120),
            new ShopItemDefinition("mekanism:alloy_infused", ShopRarity.ADVANCED, 4, 8, 165),
            new ShopItemDefinition("mekanism:basic_control_circuit", ShopRarity.ADVANCED, 2, 6, 185),
            new ShopItemDefinition("immersiveengineering:ingot_steel", ShopRarity.ADVANCED, 4, 12, 120),
            new ShopItemDefinition("immersiveengineering:treated_wood_horizontal", ShopRarity.UNCOMMON, 12, 24, 80),
            new ShopItemDefinition("thermal:tin_ingot", ShopRarity.UNCOMMON, 8, 16, 62),
            new ShopItemDefinition("thermal:silver_ingot", ShopRarity.UNCOMMON, 8, 16, 68),
            new ShopItemDefinition("thermal:lead_ingot", ShopRarity.UNCOMMON, 8, 16, 70),
            new ShopItemDefinition("thermal:nickel_ingot", ShopRarity.UNCOMMON, 8, 16, 72),
            new ShopItemDefinition("ars_nouveau:source_gem", ShopRarity.ADVANCED, 4, 8, 140)
    );

    private ShopService() {
    }

    public static synchronized List<ShopListing> getCurrentRotation(MinecraftServer server) {
        try {
            initializeSchema();
            List<ShopListing> current = loadActiveRotation();
            if (current.size() == ROTATION_SIZE) {
                return current;
            }
            return reroll(server);
        } catch (Exception e) {
            AetherreachCore.LOGGER.error("[Aetherreach] Failed to load Veil Imports rotation.", e);
            return List.of();
        }
    }

    public static synchronized List<ShopListing> reroll(MinecraftServer server) {
        try {
            initializeSchema();
            List<ShopListing> generated = generateRotation(server);
            long now = System.currentTimeMillis();
            long expiresAt = now + rotationDurationMs();

            try (Connection connection = connect()) {
                connection.setAutoCommit(false);
                try (Statement clear = connection.createStatement()) {
                    clear.executeUpdate("DELETE FROM shop_rotation");
                }

                try (PreparedStatement insert = connection.prepareStatement(
                        """
                                INSERT INTO shop_rotation(
                                    slot, item_id, item_data, item_name, quantity, price,
                                    rarity, recipe_score, created_at, expires_at
                                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """
                )) {
                    for (ShopListing listing : generated) {
                        insert.setInt(1, listing.slot());
                        insert.setString(2, listing.itemId());
                        insert.setString(3, listing.itemData());
                        insert.setString(4, listing.itemName());
                        insert.setInt(5, listing.quantity());
                        insert.setLong(6, listing.price());
                        insert.setString(7, listing.rarity());
                        insert.setInt(8, listing.recipeScore());
                        insert.setLong(9, now);
                        insert.setLong(10, expiresAt);
                        insert.addBatch();
                    }
                    insert.executeBatch();
                }

                connection.commit();
            }

            return loadActiveRotation();
        } catch (Exception e) {
            AetherreachCore.LOGGER.error("[Aetherreach] Failed to reroll Veil Imports.", e);
            return List.of();
        }
    }

    public static synchronized ShopListing buy(ServerPlayer player, int slot) {
        MinecraftServer server = serverOf(player);
        ShopListing listing = getCurrentRotation(server).stream()
                .filter(item -> item.slot() == slot)
                .findFirst()
                .orElseThrow(() -> new IllegalArgumentException("No Veil Imports stock exists in slot " + slot + "."));

        if (!CurrencyService.deductBalance(player, listing.price(), "SHOP_BUY", "slot:" + listing.slot() + ":" + listing.itemId())) {
            throw new IllegalArgumentException("You do not have enough " + CurrencyService.currencyName() + ".");
        }

        try {
            giveOrDrop(player, deserializeItem(server, listing.itemData()));
            return listing;
        } catch (Exception e) {
            CurrencyService.addBalance(player, listing.price(), "SHOP_BUY_REFUND", "slot:" + listing.slot() + ":" + listing.itemId());
            AetherreachCore.LOGGER.error("[Aetherreach] Failed to complete Veil Imports purchase.", e);
            throw new RuntimeException("Import failed; Shards refunded.", e);
        }
    }

    private static List<ShopListing> generateRotation(MinecraftServer server) {
        List<ShopItemDefinition> candidates = new ArrayList<>(STOCK_POOL.stream()
                .filter(ShopService::isRegistered)
                .filter(definition -> !isBlacklisted(definition.itemId()))
                .toList());
        Collections.shuffle(candidates, RANDOM);

        long now = System.currentTimeMillis();
        long expiresAt = now + rotationDurationMs();
        List<ShopListing> listings = new ArrayList<>();

        for (ShopItemDefinition definition : candidates) {
            if (listings.size() >= ROTATION_SIZE) {
                break;
            }

            Item item = BuiltInRegistries.ITEM.getValue(Identifier.parse(definition.itemId()));
            if (item == null || item == Items.AIR) {
                continue;
            }

            int quantity = randomQuantity(definition);
            RecipePrice recipePrice = recipeAwarePrice(server, definition, quantity);
            ItemStack stack = new ItemStack(item, quantity);
            long price = clampPrice(recipePrice.price());

            listings.add(new ShopListing(
                    listings.size() + 1,
                    definition.itemId(),
                    serializeItem(server, stack),
                    stack.getHoverName().getString(),
                    quantity,
                    price,
                    definition.rarity().name(),
                    recipePrice.recipeScore(),
                    now,
                    expiresAt
            ));
        }

        return listings;
    }

    private static RecipePrice recipeAwarePrice(MinecraftServer server, ShopItemDefinition definition, int quantity) {
        long price = definition.basePrice() * Math.max(1, quantity);
        Optional<RecipeScore> recipe = findBestRecipeScore(server, definition.itemId());

        if (recipe.isPresent()) {
            RecipeScore score = recipe.get();
            double multiplier = 1.0D
                    + (score.ingredientCount() * 0.08D)
                    + (score.rarityScore() * 0.05D);
            price = Math.round(price * multiplier / Math.max(1, score.outputCount()));
            return new RecipePrice(price, score.recipeScore());
        }

        return new RecipePrice(Math.round(price * namespaceMultiplier(definition.itemId())), 0);
    }

    private static Optional<RecipeScore> findBestRecipeScore(MinecraftServer server, String itemId) {
        ContextMap context = SlotDisplayContext.fromLevel(server.overworld());
        return server.getRecipeManager().getRecipes().stream()
                .map(holder -> scoreRecipe(holder, context, itemId))
                .flatMap(Optional::stream)
                .min(Comparator.comparingLong(RecipeScore::estimatedCost));
    }

    private static Optional<RecipeScore> scoreRecipe(RecipeHolder<?> holder, ContextMap context, String itemId) {
        Recipe<?> recipe = holder.value();
        List<ItemStack> outputs = recipe.display().stream()
                .flatMap(display -> display.result().resolveForStacks(context).stream())
                .filter(stack -> !stack.isEmpty())
                .toList();

        Optional<ItemStack> matchingOutput = outputs.stream()
                .filter(stack -> itemId.equals(BuiltInRegistries.ITEM.getKey(stack.getItem()).toString()))
                .findFirst();

        if (matchingOutput.isEmpty()) {
            return Optional.empty();
        }

        int ingredientCount = 0;
        int rarityScore = 0;
        try {
            for (Ingredient ingredient : recipe.placementInfo().ingredients()) {
                if (ingredient.isEmpty()) {
                    continue;
                }
                ingredientCount++;
                rarityScore += scoreIngredient(ingredient);
            }
        } catch (Exception e) {
            rarityScore += 2;
        }

        int outputCount = Math.max(1, matchingOutput.get().getCount());
        int recipeScore = ingredientCount + rarityScore;
        long estimatedCost = Math.max(1L, recipeScore) * 100L / outputCount;
        return Optional.of(new RecipeScore(ingredientCount, rarityScore, outputCount, recipeScore, estimatedCost));
    }

    private static int scoreIngredient(Ingredient ingredient) {
        return ingredient.items()
                .map(holder -> BuiltInRegistries.ITEM.getKey(holder.value()).toString().toLowerCase(Locale.ROOT))
                .limit(24)
                .mapToInt(ShopService::scoreItemId)
                .min()
                .orElse(2);
    }

    private static int scoreItemId(String id) {
        int score = 1;
        if (!id.startsWith("minecraft:")) {
            score += 1;
        }
        if (id.contains("diamond") || id.contains("emerald") || id.contains("ender") || id.contains("blaze")) {
            score += 2;
        }
        if (id.contains("steel") || id.contains("circuit") || id.contains("processor") || id.contains("alloy")) {
            score += 3;
        }
        if (id.contains("netherite") || id.contains("star") || id.contains("singularit") || id.contains("creative")) {
            score += 8;
        }
        return score;
    }

    private static double namespaceMultiplier(String itemId) {
        return itemId.startsWith("minecraft:") ? 1.0D : 1.2D;
    }

    private static int randomQuantity(ShopItemDefinition definition) {
        int min = Math.max(1, definition.minQuantity());
        int max = Math.max(min, definition.maxQuantity());
        return min + RANDOM.nextInt(max - min + 1);
    }

    private static long clampPrice(long price) {
        return Math.max(5L, Math.min(5000L, price));
    }

    private static boolean isRegistered(ShopItemDefinition definition) {
        Identifier id = Identifier.tryParse(definition.itemId());
        return id != null && BuiltInRegistries.ITEM.containsKey(id);
    }

    private static boolean isBlacklisted(String itemId) {
        String id = itemId.toLowerCase(Locale.ROOT);
        return id.contains("creative")
                || id.contains("command_block")
                || id.contains("structure_block")
                || id.contains("barrier")
                || id.contains("bedrock")
                || id.contains("chunk_loader")
                || id.contains("chunkloader")
                || id.contains("ftbchunks")
                || id.contains("atm_star")
                || id.contains("singularity");
    }

    private static List<ShopListing> loadActiveRotation() throws Exception {
        long now = System.currentTimeMillis();
        List<ShopListing> listings = new ArrayList<>();

        try (Connection connection = connect();
             PreparedStatement statement = connection.prepareStatement(
                     "SELECT * FROM shop_rotation WHERE expires_at > ? ORDER BY slot ASC"
             )) {
            statement.setLong(1, now);
            try (ResultSet result = statement.executeQuery()) {
                while (result.next()) {
                    listings.add(readListing(result));
                }
            }
        }

        return listings;
    }

    private static ShopListing readListing(ResultSet result) throws Exception {
        return new ShopListing(
                result.getInt("slot"),
                result.getString("item_id"),
                result.getString("item_data"),
                result.getString("item_name"),
                result.getInt("quantity"),
                result.getLong("price"),
                result.getString("rarity"),
                result.getInt("recipe_score"),
                result.getLong("created_at"),
                result.getLong("expires_at")
        );
    }

    private static String serializeItem(MinecraftServer server, ItemStack stack) {
        RegistryOps<JsonElement> ops = RegistryOps.create(JsonOps.INSTANCE, server.registryAccess());
        JsonElement json = ItemStack.CODEC.encodeStart(ops, stack).getOrThrow(RuntimeException::new);
        return GSON.toJson(json);
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

    private static MinecraftServer serverOf(ServerPlayer player) {
        MinecraftServer server = player.level().getServer();
        if (server == null) {
            throw new IllegalStateException("Minecraft server is unavailable.");
        }
        return server;
    }

    private static long rotationDurationMs() {
        return Config.SHOP_ROTATION_HOURS.getAsInt() * 60L * 60L * 1000L;
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
                    CREATE TABLE IF NOT EXISTS shop_rotation (
                        slot INTEGER PRIMARY KEY,
                        item_id TEXT NOT NULL,
                        item_data TEXT NOT NULL,
                        item_name TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        price INTEGER NOT NULL,
                        rarity TEXT NOT NULL,
                        recipe_score INTEGER NOT NULL,
                        created_at INTEGER NOT NULL,
                        expires_at INTEGER NOT NULL
                    )
                    """);
        }
    }

    private record RecipePrice(long price, int recipeScore) {
    }

    private record RecipeScore(int ingredientCount, int rarityScore, int outputCount, int recipeScore, long estimatedCost) {
    }
}
