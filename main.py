import sqlite3
import time
import random
import requests
from typing import List, Dict, Any, Optional

# --- Настройки ---
DB_NAME = "wb_products.db"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}


def init_db(db_path: str = DB_NAME) -> None:
    """Инициализация таблиц в SQLite."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Таблица основных товаров
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTO_INCREMENT,
        nm_id INTEGER UNIQUE NOT NULL,      -- Артикул WB
        name TEXT,                           -- Название товара
        brand TEXT,                          -- Бренд
        price_basic REAL,                    -- Цена до скидки (в рублях)
        price_sale REAL,                     -- Цена со скидкой (в рублях)
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Таблица SKU (размеры и цвета)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS product_skus (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nm_id INTEGER NOT NULL,              -- Внешний ключ на артикул WB
        color TEXT,                          -- Цвет
        size_name TEXT,                      -- Размер (например, XL, 48 и т.д.)
        chrt_id INTEGER,                     -- Уникальный ID размера/SKU WB
        FOREIGN KEY (nm_id) REFERENCES products (nm_id) ON DELETE CASCADE,
        UNIQUE(nm_id, color, size_name, chrt_id)
    );
    """)

    conn.commit()
    conn.close()


def fetch_search_products(query: str, page: int = 1) -> List[Dict[str, Any]]:
    """Получает список базовых карточек из поиска WB."""
    url = "https://search.wb.ru/exactmatch/ru/common/v4/search"
    params = {
        "appType": 1,
        "curr": "rub",
        "dest": -1257786,  # Стандартный регион (Москва/Центр)
        "query": query,
        "resultset": "catalog",
        "sort": "popular",
        "page": page,
    }

    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("data", {}).get("products", [])
    except requests.RequestException as e:
        print(f"[Ошибка] Не удалось получить результаты поиска: {e}")
        return []


def fetch_product_details(nm_id: int) -> Optional[Dict[str, Any]]:
    """Получает детальные данные по карточке (включая цвета и размеры)."""
    url = f"https://card.wb.ru/cards/v1/detail"
    params = {
        "appType": 1,
        "curr": "rub",
        "dest": -1257786,
        "spp": 30,
        "nm": nm_id
    }

    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        products = data.get("data", {}).get("products", [])
        return products[0] if products else None
    except requests.RequestException as e:
        print(f"[Ошибка] Не удалось получить детальную информацию для артикула {nm_id}: {e}")
        return None


def save_to_db(product_data: Dict[str, Any], db_path: str = DB_NAME) -> None:
    """Сохраняет карточку товара и её варианты в БД."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    nm_id = product_data.get("id")
    name = product_data.get("name")
    brand = product_data.get("brand")

    # Цены у WB передаются в копейках (или центах) -> делим на 100
    price_basic = product_data.get("priceU", 0) / 100
    price_sale = product_data.get("salePriceU", 0) / 100

    # 1. Вставляем или обновляем основной товар
    cursor.execute("""
    INSERT INTO products (nm_id, name, brand, price_basic, price_sale)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(nm_id) DO UPDATE SET
        name=excluded.name,
        brand=excluded.brand,
        price_basic=excluded.price_basic,
        price_sale=excluded.price_sale;
    """, (nm_id, name, brand, price_basic, price_sale))

    # 2. Обработка цветов и размеров
    # Извлекаем все доступные цвета
    colors = [c.get("name") for c in product_data.get("colors", []) if c.get("name")]
    color_str = ", ".join(colors) if colors else "Не указан"

    # Извлекаем размеры
    sizes = product_data.get("sizes", [])
    for size in sizes:
        size_name = size.get("origName") or size.get("name") or "Без размера"
        chrt_id = size.get("chrtId")

        cursor.execute("""
        INSERT INTO product_skus (nm_id, color, size_name, chrt_id)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(nm_id, color, size_name, chrt_id) DO NOTHING;
        """, (nm_id, color_str, size_name, chrt_id))

    conn.commit()
    conn.close()


def run_parser(search_query: str, max_pages: int = 1) -> None:
    """Главный цикл работы парсера."""
    init_db()
    print(f"Старт парсинга по запросу: '{search_query}'")

    total_saved = 0
    for page in range(1, max_pages + 1):
        print(f"--- Парсинг страницы {page} ---")
        items = fetch_search_products(search_query, page=page)

        if not items:
            print("Товары больше не найдены или произошла ошибка.")
            break

        for item in items:
            nm_id = item.get("id")
            if not nm_id:
                continue

            # Получаем подробную спецификацию карточки
            details = fetch_product_details(nm_id)
            if details:
                save_to_db(details)
                total_saved += 1
                print(f"[Успех] Сохранен артикул {nm_id}: {details.get('name')}")

            # Задержка между запросами к деталям карточки (1-2.5 секунды)
            time.sleep(random.uniform(1.0, 2.5))

        # Задержка между страницами поиска
        time.sleep(random.uniform(2.0, 4.0))

    print(f"\nПарсинг завершен. Всего сохранено/обновлено карточек: {total_saved}")


if __name__ == "__main__":
    # Пример запуска: ищем "мужская футболка" на 1 странице
    run_parser(search_query="мужская футболка", max_pages=1)