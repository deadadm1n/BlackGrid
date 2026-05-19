package com.blackgrid.watchdoghelper.shop;

record ShopItemDefinition(String itemId, ShopRarity rarity, int minQuantity, int maxQuantity, long basePrice) {
}
