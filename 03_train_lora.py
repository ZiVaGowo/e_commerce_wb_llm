import torch
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig
from config import MODEL_NAME, OUTPUT_DIR, TRAIN_FILE, VAL_FILE

def formatting_func(example):
    """
    Преобразует строку из JSONL в готовый текст.
    Автоматически обрабатывает варианты structures:
    1. Поле 'text'
    2. Поля 'prompt' / 'completion' или 'instruction' / 'output'
    3. Массив диалогов 'messages'
    """
    if "text" in example:
        return example["text"]
    elif "messages" in example:
        # Если датасет в формате ChatML
        text = ""
        for msg in example["messages"]:
            text += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
        return text
    elif "prompt" in example and "completion" in example:
        return f"{example['prompt']}\n{example['completion']}"
    elif "instruction" in example and "output" in example:
        return f"{example['instruction']}\n{example['output']}"
    else:
        # Резервный вариант: объединяем все строковые значения
        return "\n".join([str(v) for v in example.values()])

def train():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    use_cuda = torch.cuda.is_available()

    if use_cuda:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            llm_int8_enable_fp32_cpu_offload=True
        )
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            quantization_config=bnb_config,
            device_map="auto"
        )
        model = prepare_model_for_kbit_training(model)
    else:
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            dtype=torch.float32,
            device_map="cpu"
        )

    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM"
    )

    dataset = load_dataset("json", data_files={
        "train": TRAIN_FILE,
        "validation": VAL_FILE
    })

    sft_config = SFTConfig(
        output_dir=OUTPUT_DIR,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        logging_steps=5,
        num_train_epochs=3,
        save_strategy="epoch",
        eval_strategy="epoch",
        max_length=512,
        fp16=use_cuda,
        use_cpu=not use_cuda,
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        peft_config=peft_config,
        processing_class=tokenizer,
        formatting_func=formatting_func,
        args=sft_config,
    )

    print("[Training] Запуск Fine-Tuning...")
    trainer.train()
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"[Training] Модель и адаптеры успешно сохранены в: {OUTPUT_DIR}")

if __name__ == "__main__":
    train()