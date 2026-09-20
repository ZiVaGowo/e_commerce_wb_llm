import os

DB_NAME = os.path.join("data", "wb_products.db")
TRAIN_FILE = os.path.join("data", "train.jsonl")
VAL_FILE = os.path.join("data", "val.jsonl")
TEST_FILE = os.path.join("data", "test.jsonl")

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
OUTPUT_DIR = "fine_tuned_model"

SYSTEM_PROMPT = """Ты — интеллектуальный ассистент поддержки E-Commerce платформы.
Твоя задача — проанализировать обращение клиента и вернуть JSON со следующими полями:
- category: (Delivery, Product Query, Return, Refund, General)
- priority: (Low, Medium, High)
- sentiment: (Positive, Neutral, Negative)
- recommended_action: краткое системное действие для оператора
- ideal_response: вежливый и точный ответ клиенту на русском языке
"""