import sqlite3
import random
import os
from config import DB_NAME

# Словари для генерации реалистичного каталога одежды
BRANDS = ["Oodji", "ТВОЕ", "ZARA", "Mango", "Baon", "Pull&Bear", "Befree", "ASOS"]
CATEGORIES = [
    "Мужская футболка", "Худи оверсайз", "Джинсы прямые",
    "Свитшот базовый", "Куртка демисезонная", "Брюки карго"
]
COLORS = ["Черный", "Белый", "Темно-синий", "Серый меланж", "Бежевый", "Оливковый"]
SIZES = ["S (46)", "M (48)", "L (50)", "XL (52)", "XXL (54)"]

def init_db():
    os.makedirs(os.path.dirname(DB_NAME), exist_ok=True)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Таблица основных товаров
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        nm_id INTEGER PRIMARY KEY,
        name TEXT,
        brand TEXT,
        price_sale REAL
    );
    """)

    # Таблица SKU (размеры и цвета)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS product_skus (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nm_id INTEGER,
        color TEXT,
        size_name TEXT,
        chrt_id INTEGER,
        FOREIGN KEY (nm_id) REFERENCES products (nm_id)
    );
    """)
    conn.commit()
    conn.close()

def generate_catalog(num_products: int = 150):
    """Генерирует локальную базу товаров и SKU без внешних HTTP-запросов."""
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    print(f"[Mock Generator] Создание базы данных из {num_products} товаров...")

    for i in range(1, num_products + 1):
        nm_id = 10000000 + i
        brand = random.choice(BRANDS)
        category = random.choice(CATEGORIES)
        color = random.choice(COLORS)
        name = f"{category} {brand} {color.lower()}"
        price_sale = round(random.uniform(1200, 8500), 2)

        # 1. Запись в таблицу products
        cursor.execute("""
        INSERT INTO products (nm_id, name, brand, price_sale)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(nm_id) DO UPDATE SET price_sale=excluded.price_sale;
        """, (nm_id, name, brand, price_sale))

        # 2. Запись вариантов (размеров и цветов) в product_skus
        available_sizes = random.sample(SIZES, k=random.randint(2, 5))
        for idx, size in enumerate(available_sizes):
            chrt_id = nm_id * 100 + idx
            cursor.execute("""
            INSERT INTO product_skus (nm_id, color, size_name, chrt_id)
            VALUES (?, ?, ?, ?);
            """, (nm_id, color, size, chrt_id))

    conn.commit()
    conn.close()
    print(f"[Успех] База данных '{DB_NAME}' сформирована! Сохранено товаров: {num_products}.")

if __name__ == "__main__":
    generate_catalog(num_products=150)