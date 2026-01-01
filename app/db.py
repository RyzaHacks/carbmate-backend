"""SQLite storage for CarbMate meals."""

from __future__ import annotations

import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from .schemas import MealConfirmItem, MealConfirmResponse, MealHistoryItem, MealHistoryResponse, MealStoredItem, MealTotals

logger = logging.getLogger(__name__)


def _db_path() -> str:
    configured = os.getenv("CARBMATE_DB_PATH")
    if configured:
        return configured
    return os.path.join(os.path.dirname(__file__), "data", "carbmate.db")


def _connect() -> sqlite3.Connection:
    path = _db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _connect()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS meals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            user_text TEXT,
            source TEXT,
            total_carbs_g REAL,
            total_protein_g REAL,
            total_fat_g REAL,
            total_calories REAL
        );
        CREATE TABLE IF NOT EXISTS meal_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meal_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            grams REAL NOT NULL,
            carbs_g REAL,
            protein_g REAL,
            fat_g REAL,
            calories REAL,
            confidence REAL,
            notes TEXT,
            range_min_g REAL,
            range_max_g REAL,
            FOREIGN KEY(meal_id) REFERENCES meals(id)
        );
        CREATE INDEX IF NOT EXISTS idx_meal_items_meal_id ON meal_items(meal_id);
        """
    )
    conn.commit()
    conn.close()


def insert_meal(
    user_text: Optional[str],
    source: Optional[str],
    items: List[MealConfirmItem],
    totals: MealTotals,
) -> MealConfirmResponse:
    created_at = datetime.now(timezone.utc).isoformat()

    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO meals (created_at, user_text, source, total_carbs_g, total_protein_g, total_fat_g, total_calories)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            created_at,
            user_text,
            source,
            totals.carbs_g,
            totals.protein_g,
            totals.fat_g,
            totals.calories,
        ),
    )
    meal_id = cursor.lastrowid

    stored_items: List[MealStoredItem] = []
    for item in items:
        range_min = item.range_grams[0] if item.range_grams else None
        range_max = item.range_grams[1] if item.range_grams else None
        cursor.execute(
            """
            INSERT INTO meal_items (
                meal_id, name, grams, carbs_g, protein_g, fat_g, calories, confidence, notes, range_min_g, range_max_g
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                meal_id,
                item.name,
                item.grams,
                item.carbs_g,
                item.protein_g,
                item.fat_g,
                item.calories,
                item.confidence,
                item.notes,
                range_min,
                range_max,
            ),
        )
        item_id = cursor.lastrowid
        stored_items.append(
            MealStoredItem(
                id=item_id,
                meal_id=meal_id,
                name=item.name,
                grams=item.grams,
                carbs_g=item.carbs_g,
                protein_g=item.protein_g,
                fat_g=item.fat_g,
                calories=item.calories,
                confidence=item.confidence,
                notes=item.notes,
                range_grams=item.range_grams,
            )
        )

    conn.commit()
    conn.close()

    return MealConfirmResponse(
        meal_id=meal_id,
        created_at=created_at,
        totals=totals,
        items=stored_items,
    )


def fetch_meals(limit: int, offset: int) -> MealHistoryResponse:
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM meals ORDER BY created_at DESC LIMIT ? OFFSET ?
        """,
        (limit, offset),
    )
    meal_rows = cursor.fetchall()

    meals: List[MealHistoryItem] = []
    for meal_row in meal_rows:
        cursor.execute(
            """
            SELECT * FROM meal_items WHERE meal_id = ? ORDER BY id ASC
            """,
            (meal_row["id"],),
        )
        item_rows = cursor.fetchall()
        stored_items = [
            MealStoredItem(
                id=item["id"],
                meal_id=item["meal_id"],
                name=item["name"],
                grams=item["grams"],
                carbs_g=item["carbs_g"],
                protein_g=item["protein_g"],
                fat_g=item["fat_g"],
                calories=item["calories"],
                confidence=item["confidence"],
                notes=item["notes"],
                range_grams=(
                    int(item["range_min_g"]),
                    int(item["range_max_g"]),
                )
                if item["range_min_g"] is not None and item["range_max_g"] is not None
                else None,
            )
            for item in item_rows
        ]

        totals = MealTotals(
            carbs_g=meal_row["total_carbs_g"] or 0.0,
            protein_g=meal_row["total_protein_g"] or 0.0,
            fat_g=meal_row["total_fat_g"] or 0.0,
            calories=meal_row["total_calories"] or 0.0,
            carb_exchanges=(meal_row["total_carbs_g"] or 0.0) / 15.0,
        )

        meals.append(
            MealHistoryItem(
                meal_id=meal_row["id"],
                created_at=meal_row["created_at"],
                totals=totals,
                items=stored_items,
            )
        )

    conn.close()
    return MealHistoryResponse(meals=meals)
