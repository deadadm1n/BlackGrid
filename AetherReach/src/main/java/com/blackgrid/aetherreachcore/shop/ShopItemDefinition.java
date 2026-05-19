package com.blackgrid.aetherreachcore.shop;

record ShopItemDefinition(String itemId, ShopRarity rarity, int minQuantity, int maxQuantity, long basePrice) {
}
