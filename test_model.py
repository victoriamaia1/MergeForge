import time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_DIR = "/home/ubuntu/llm_fusion_studio/workspace/merges/a08da669-716b-498a-a098-17c1daf80de2"

print("Loading model...")

tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_DIR,
    torch_dtype=torch.float32,
    low_cpu_mem_usage=True
)

model.eval()

while True:
    prompt = input("\nYou: ")

    if prompt.lower() in ["exit", "quit"]:
        break

    inputs = tokenizer(prompt, return_tensors="pt")

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=100,
            do_sample=True,
            temperature=0.7,
            pad_token_id=tokenizer.eos_token_id
        )

    response = tokenizer.decode(
        outputs[0],
        skip_special_tokens=True
    )

    print("\nModel:", response)
