"""Loyverse API sync helpers for the delivery app."""

from __future__ import annotations

from typing import Dict, List

import requests

from delivery_app.metadata import sync_delivery_customers_from_api_payload


LOYVERSE_CUSTOMERS_URL = "https://api.loyverse.com/v1.0/customers"


def fetch_all_loyverse_customers(token: str, *, timeout_seconds: int = 30) -> List[Dict[str, object]]:
    """Fetch the full customers collection from Loyverse with cursor pagination."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    cursor = None
    all_customers: List[Dict[str, object]] = []

    while True:
        params = {"limit": 250}
        if cursor:
            params["cursor"] = cursor

        response = requests.get(
            LOYVERSE_CUSTOMERS_URL,
            headers=headers,
            params=params,
            timeout=timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        all_customers.extend(payload.get("customers", []))

        cursor = payload.get("cursor")
        if not cursor:
            return all_customers


def sync_delivery_customers_from_loyverse(db_session, token: str) -> Dict[str, int]:
    """Fetch Loyverse customers and apply them to the delivery database session."""
    customers = fetch_all_loyverse_customers(token)
    return sync_delivery_customers_from_api_payload(db_session, customers)
