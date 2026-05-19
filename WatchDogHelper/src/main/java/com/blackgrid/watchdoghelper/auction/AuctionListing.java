package com.blackgrid.watchdoghelper.auction;

import java.util.UUID;

public record AuctionListing(
        long id,
        UUID sellerUuid,
        String sellerName,
        String itemData,
        String itemName,
        int quantity,
        long price,
        long createdAt,
        long expiresAt
) {
}
