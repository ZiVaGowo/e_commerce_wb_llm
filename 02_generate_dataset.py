import sqlite3
import json
import random
from sklearn.model_selection import train_test_split
from config import DB_NAME, TRAIN_FILE, VAL_FILE, TEST_FILE, SYSTEM_PROMPT


def generate_samples_from_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, brand, price_sale FROM products LIMIT 100")
    rows = cursor.fetchall()
    conn.close()

    dataset = []
    templates = [
        {
            "msg": "Здравствуйте! Заказывал {name} от {brand}. Подскажите, когда ожидается доставка?",
            "cat": "Delivery", "prio": "Medium", "sent": "Neutral",
            "action": "Check logistics tracking",
            "resp": "Здравствуйте! Статус доставки вашей позиции '{name}' обновлен. Заказ поступит в пункт выдачи в ближайшее время."
        },
        {
            "msg": "Пришел товар {name}, но качество ужасное! Хочу вернуть {price} рублей!",
            "cat": "Return", "prio": "High", "sent": "Negative",
            "action": "Initiate return workflow",
            "resp": "Здравствуйте! Сожалеем о данной ситуации. Вы можете оформить возврат товара '{name}' в личном кабинете в течение 14 дней."
        },
        {
            "msg": "Подскажите пожалуйста, {name} идет размер в размер?",
            "cat": "Product Query", "prio": "Low", "sent": "Positive",
            "action": "Consult size chart",
            "resp": "Здравствуйте! Товар '{name}' от бренда {brand} соответствует стандартной размерной сетке."
        }
    ]

    for name, brand, price in rows:
        tmpl = random.choice(templates)
        customer_msg = tmpl["msg"].format(name=name, brand=brand, price=price)
        ideal_resp = tmpl["resp"].format(name=name, brand=brand)

        entry = {
            "instruction": SYSTEM_PROMPT,
            "input": customer_msg,
            "output": json.dumps({
                "category": tmpl["cat"],
                "priority": tmpl["prio"],
                "sentiment": tmpl["sent"],
                "recommended_action": tmpl["action"],
                "ideal_response": ideal_resp
            }, ensure_ascii=False)
        }
        dataset.append(entry)

    return dataset


def main():
    data = generate_samples_from_db()
    if not data:
        print("[Ошибка] База данных пуста. Сначала запустите 01_scrape_wb.py!")
        return

    train, test = train_test_split(data, test_size=0.2, random_state=42)
    val, test = train_test_split(test, test_size=0.5, random_state=42)

    def write_jsonl(filename, items):
        with open(filename, "w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")

    write_jsonl(TRAIN_FILE, train)
    write_jsonl(VAL_FILE, val)
    write_jsonl(TEST_FILE, test)
    print(f"[Dataset] Данные сформированы: Train ({len(train)}), Val ({len(val)}), Test ({len(test)})")


if __name__ == "__main__":
    main()