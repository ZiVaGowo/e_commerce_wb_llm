import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from sklearn.metrics import accuracy_score
from config import MODEL_NAME, OUTPUT_DIR, TEST_FILE


def load_test_data():
    data = []
    with open(TEST_FILE, "r", encoding="utf-8") as f:
        for line in f:
            data.append(json.loads(line))
    return data


def run_inference(model, tokenizer, instruction, user_input):
    prompt = f"<|im_start|>system\n{instruction}<|im_end|>\n<|im_start|>user\n{user_input}<|im_end|>\n<|im_start|>assistant\n"
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda" if torch.cuda.is_available() else "cpu")

    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=256, do_sample=False)

    response = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
    try:
        return json.loads(response)
    except Exception:
        return {}


def evaluate_model(model, tokenizer, test_data):
    cat_true, cat_pred = [], []
    prio_true, prio_pred = [], []

    for item in test_data:
        ground_truth = json.loads(item["output"])
        pred = run_inference(model, tokenizer, item["instruction"], item["input"])

        cat_true.append(ground_truth.get("category"))
        cat_pred.append(pred.get("category", "Unknown"))

        prio_true.append(ground_truth.get("priority"))
        prio_pred.append(pred.get("priority", "Unknown"))

    return {
        "cat_acc": accuracy_score(cat_true, cat_pred),
        "prio_acc": accuracy_score(prio_true, prio_pred)
    }


def main():
    test_data = load_test_data()
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    print("--- 1/2: Оценка Base Model ---")
    base_model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype=torch.float16, device_map="auto")
    base_metrics = evaluate_model(base_model, tokenizer, test_data)
    del base_model

    print("--- 2/2: Оценка Fine-Tuned Model ---")
    base_model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype=torch.float16, device_map="auto")
    ft_model = PeftModel.from_pretrained(base_model, OUTPUT_DIR)
    ft_metrics = evaluate_model(ft_model, tokenizer, test_data)

    print("\n" + "=" * 45)
    print("      РЕЗУЛЬТАТЫ СРАВНЕНИЯ (EVALUATION)")
    print("=" * 45)
    print(f"Base Model      | Cat Acc: {base_metrics['cat_acc']:.2%} | Prio Acc: {base_metrics['prio_acc']:.2%}")
    print(f"Fine-Tuned LoRA | Cat Acc: {ft_metrics['cat_acc']:.2%} | Prio Acc: {ft_metrics['prio_acc']:.2%}")


if __name__ == "__main__":
    main()