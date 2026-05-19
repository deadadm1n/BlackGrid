package com.blackgrid.watchdoghelper.shop;

public record ShopListing(
        int slot,
        String itemId,
        String itemData,
        String itemName,
        int quantity,
        long price,
        String rarity,
        int recipeScore,
        long createdAt,
        long expiresAt
) {
}
