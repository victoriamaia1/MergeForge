"""Curated model catalog with hardware requirements (covers CPU & GPU tiers).

Each entry: id, name, family, params_b, size_gb_fp16, quantizable, quantized_size_gb,
cpu_compatible, gpu_required, tier_min, context_length, supported_methods, architectures.
size_gb_fp16 ~ params_b * 2.0; min_ram_gb ~ size_gb_fp16 * 1.6 (FP16) or quantized_size_gb * 1.3 (INT4) for CPU.
"""

# Helper to expand entries quickly
def m(_id, name, family, params, ctx=4096, methods=None, archs=None, q=True, gpu_req=False):
    size = round(params * 2.0, 2)  # FP16 size
    q_size = round(params * 0.55, 2)  # ~INT4 size
    return {
        "id": _id, "name": name, "family": family, "params_b": params,
        "size_gb_fp16": size, "quantizable": q, "quantized_size_gb": q_size,
        "cpu_compatible": params <= 13, "gpu_required": gpu_req,
        "context_length": ctx,
        "supported_methods": methods or ["linear", "ties", "dare_ties", "slerp", "passthrough"],
        "architectures": archs or [family.lower()],
    }

CATALOG = [
    # ---------- TIER 1 CAPABLE (≤ 13B) ----------
    m("microsoft/Phi-3-mini-4k-instruct", "Phi 3 Mini 4K Instruct", "Phi", 3.8, ctx=4096, archs=["phi3"]),
    m("microsoft/Phi-3.5-mini-instruct", "Phi 3.5 Mini Instruct", "Phi", 3.8, ctx=128000, archs=["phi3"]),
    m("microsoft/phi-2", "Phi 2", "Phi", 2.7, ctx=2048, archs=["phi"]),
    m("microsoft/phi-1_5", "Phi 1.5", "Phi", 1.3, ctx=2048, archs=["phi"]),
    m("TinyLlama/TinyLlama-1.1B-Chat-v1.0", "TinyLlama 1.1B Chat", "Llama", 1.1, ctx=2048),
    m("mistralai/Mistral-7B-v0.1", "Mistral 7B Base", "Mistral", 7.0),
    m("mistralai/Mistral-7B-Instruct-v0.2", "Mistral 7B Instruct v0.2", "Mistral", 7.0),
    m("mistralai/Mistral-7B-Instruct-v0.3", "Mistral 7B Instruct v0.3", "Mistral", 7.0),
    m("HuggingFaceH4/zephyr-7b-beta", "Zephyr 7B Beta", "Mistral", 7.0),
    m("teknium/OpenHermes-2.5-Mistral-7B", "OpenHermes 2.5 Mistral", "Mistral", 7.0),
    m("NousResearch/Hermes-2-Pro-Mistral-7B", "Hermes 2 Pro Mistral", "Mistral", 7.0),
    m("Open-Orca/Mistral-7B-OpenOrca", "Mistral 7B OpenOrca", "Mistral", 7.0),
    m("meta-llama/Llama-2-7b-hf", "Llama 2 7B", "Llama", 7.0),
    m("meta-llama/Llama-2-7b-chat-hf", "Llama 2 7B Chat", "Llama", 7.0),
    m("meta-llama/Meta-Llama-3-8B", "Llama 3 8B", "Llama", 8.0, ctx=8192),
    m("meta-llama/Meta-Llama-3-8B-Instruct", "Llama 3 8B Instruct", "Llama", 8.0, ctx=8192),
    m("meta-llama/Llama-3.1-8B", "Llama 3.1 8B", "Llama", 8.0, ctx=128000),
    m("meta-llama/Llama-3.1-8B-Instruct", "Llama 3.1 8B Instruct", "Llama", 8.0, ctx=128000),
    m("meta-llama/Llama-3.2-1B", "Llama 3.2 1B", "Llama", 1.2, ctx=128000),
    m("meta-llama/Llama-3.2-3B", "Llama 3.2 3B", "Llama", 3.2, ctx=128000),
    m("meta-llama/Llama-3.2-3B-Instruct", "Llama 3.2 3B Instruct", "Llama", 3.2, ctx=128000),
    m("Qwen/Qwen2-0.5B", "Qwen2 0.5B", "Qwen", 0.5, ctx=32768),
    m("Qwen/Qwen2-1.5B", "Qwen2 1.5B", "Qwen", 1.5, ctx=32768),
    m("Qwen/Qwen2-7B", "Qwen2 7B", "Qwen", 7.6, ctx=131072),
    m("Qwen/Qwen2-7B-Instruct", "Qwen2 7B Instruct", "Qwen", 7.6, ctx=131072),
    m("Qwen/Qwen2.5-0.5B", "Qwen2.5 0.5B", "Qwen", 0.5, ctx=32768),
    m("Qwen/Qwen2.5-1.5B", "Qwen2.5 1.5B", "Qwen", 1.5, ctx=32768),
    m("Qwen/Qwen2.5-3B", "Qwen2.5 3B", "Qwen", 3.0, ctx=32768),
    m("Qwen/Qwen2.5-7B", "Qwen2.5 7B", "Qwen", 7.6, ctx=131072),
    m("Qwen/Qwen2.5-7B-Instruct", "Qwen2.5 7B Instruct", "Qwen", 7.6, ctx=131072),
    m("google/gemma-2b", "Gemma 2B", "Gemma", 2.0, ctx=8192),
    m("google/gemma-2b-it", "Gemma 2B Instruct", "Gemma", 2.0, ctx=8192),
    m("google/gemma-7b", "Gemma 7B", "Gemma", 7.0, ctx=8192),
    m("google/gemma-7b-it", "Gemma 7B Instruct", "Gemma", 7.0, ctx=8192),
    m("google/gemma-2-2b", "Gemma 2 2B", "Gemma", 2.6, ctx=8192),
    m("google/gemma-2-2b-it", "Gemma 2 2B Instruct", "Gemma", 2.6, ctx=8192),
    m("google/gemma-2-9b", "Gemma 2 9B", "Gemma", 9.0, ctx=8192),
    m("google/gemma-2-9b-it", "Gemma 2 9B Instruct", "Gemma", 9.0, ctx=8192),
    m("stabilityai/stablelm-2-1_6b", "StableLM 2 1.6B", "StableLM", 1.6, ctx=4096),
    m("stabilityai/stablelm-zephyr-3b", "StableLM Zephyr 3B", "StableLM", 3.0, ctx=4096),
    m("EleutherAI/pythia-1.4b", "Pythia 1.4B", "Pythia", 1.4, ctx=2048),
    m("EleutherAI/pythia-2.8b", "Pythia 2.8B", "Pythia", 2.8, ctx=2048),
    m("EleutherAI/pythia-6.9b", "Pythia 6.9B", "Pythia", 6.9, ctx=2048),
    m("tiiuae/falcon-7b", "Falcon 7B", "Falcon", 7.0, ctx=2048),
    m("tiiuae/falcon-7b-instruct", "Falcon 7B Instruct", "Falcon", 7.0, ctx=2048),
    m("01-ai/Yi-6B", "Yi 6B", "Yi", 6.0, ctx=4096),
    m("01-ai/Yi-6B-Chat", "Yi 6B Chat", "Yi", 6.0, ctx=4096),
    m("01-ai/Yi-9B", "Yi 9B", "Yi", 9.0, ctx=4096),
    m("deepseek-ai/deepseek-llm-7b-base", "DeepSeek 7B Base", "DeepSeek", 7.0),
    m("deepseek-ai/deepseek-llm-7b-chat", "DeepSeek 7B Chat", "DeepSeek", 7.0),
    m("deepseek-ai/deepseek-coder-1.3b-base", "DeepSeek Coder 1.3B", "DeepSeek", 1.3),
    m("deepseek-ai/deepseek-coder-6.7b-base", "DeepSeek Coder 6.7B", "DeepSeek", 6.7),
    m("deepseek-ai/deepseek-coder-6.7b-instruct", "DeepSeek Coder 6.7B Instruct", "DeepSeek", 6.7),
    m("WizardLM/WizardCoder-Python-7B-V1.0", "WizardCoder Python 7B", "Llama", 7.0),
    m("WizardLM/WizardMath-7B-V1.1", "WizardMath 7B", "Mistral", 7.0),
    m("codellama/CodeLlama-7b-hf", "CodeLlama 7B", "Llama", 7.0),
    m("codellama/CodeLlama-7b-Instruct-hf", "CodeLlama 7B Instruct", "Llama", 7.0),
    m("codellama/CodeLlama-13b-hf", "CodeLlama 13B", "Llama", 13.0),
    m("codellama/CodeLlama-13b-Instruct-hf", "CodeLlama 13B Instruct", "Llama", 13.0),
    m("meta-llama/Llama-2-13b-hf", "Llama 2 13B", "Llama", 13.0),
    m("meta-llama/Llama-2-13b-chat-hf", "Llama 2 13B Chat", "Llama", 13.0),
    m("upstage/SOLAR-10.7B-v1.0", "SOLAR 10.7B", "Llama", 10.7),
    m("upstage/SOLAR-10.7B-Instruct-v1.0", "SOLAR 10.7B Instruct", "Llama", 10.7),
    m("openchat/openchat-3.5-1210", "OpenChat 3.5", "Mistral", 7.0),
    m("Intel/neural-chat-7b-v3-3", "Neural Chat 7B v3.3", "Mistral", 7.0),
    m("HuggingFaceH4/zephyr-7b-alpha", "Zephyr 7B Alpha", "Mistral", 7.0),
    m("berkeley-nest/Starling-LM-7B-alpha", "Starling LM 7B", "Mistral", 7.0),
    m("NousResearch/Nous-Hermes-2-Mistral-7B-DPO", "Nous Hermes 2 Mistral DPO", "Mistral", 7.0),
    m("teknium/OpenHermes-2-Mistral-7B", "OpenHermes 2 Mistral", "Mistral", 7.0),
    m("cognitivecomputations/dolphin-2.6-mistral-7b", "Dolphin 2.6 Mistral", "Mistral", 7.0),
    m("HuggingFaceTB/SmolLM-135M", "SmolLM 135M", "Llama", 0.135, ctx=2048),
    m("HuggingFaceTB/SmolLM-135M-Instruct", "SmolLM 135M Instruct", "Llama", 0.135, ctx=2048),
    m("HuggingFaceTB/SmolLM-360M-Instruct", "SmolLM 360M Instruct", "Llama", 0.36, ctx=2048),
    m("HuggingFaceTB/SmolLM-360M", "SmolLM 360M", "Llama", 0.36, ctx=2048),
    m("HuggingFaceTB/SmolLM-1.7B", "SmolLM 1.7B", "Llama", 1.7, ctx=2048),
    m("HuggingFaceTB/SmolLM2-1.7B-Instruct", "SmolLM2 1.7B Instruct", "Llama", 1.7, ctx=8192),
    # ---------- TIER 2 (13B-30B) ----------
    m("Qwen/Qwen2.5-14B", "Qwen2.5 14B", "Qwen", 14.7, ctx=131072),
    m("Qwen/Qwen2.5-14B-Instruct", "Qwen2.5 14B Instruct", "Qwen", 14.7, ctx=131072),
    m("Qwen/Qwen2-14B", "Qwen2 14B", "Qwen", 14.0, ctx=32768),
    m("mistralai/Mixtral-8x7B-v0.1", "Mixtral 8x7B (MoE)", "Mixtral", 46.7, ctx=32768, gpu_req=True),
    m("mistralai/Mixtral-8x7B-Instruct-v0.1", "Mixtral 8x7B Instruct", "Mixtral", 46.7, ctx=32768, gpu_req=True),
    m("01-ai/Yi-34B", "Yi 34B", "Yi", 34.0, ctx=4096, gpu_req=True),
    m("01-ai/Yi-34B-Chat", "Yi 34B Chat", "Yi", 34.0, ctx=4096, gpu_req=True),
    m("codellama/CodeLlama-34b-hf", "CodeLlama 34B", "Llama", 34.0, gpu_req=True),
    m("codellama/CodeLlama-34b-Instruct-hf", "CodeLlama 34B Instruct", "Llama", 34.0, gpu_req=True),
    m("deepseek-ai/deepseek-coder-33b-base", "DeepSeek Coder 33B", "DeepSeek", 33.0, gpu_req=True),
    m("deepseek-ai/deepseek-coder-33b-instruct", "DeepSeek Coder 33B Instruct", "DeepSeek", 33.0, gpu_req=True),
    m("Qwen/Qwen2.5-32B", "Qwen2.5 32B", "Qwen", 32.0, ctx=131072, gpu_req=True),
    m("Qwen/Qwen2.5-32B-Instruct", "Qwen2.5 32B Instruct", "Qwen", 32.0, ctx=131072, gpu_req=True),
    m("google/gemma-2-27b", "Gemma 2 27B", "Gemma", 27.0, ctx=8192, gpu_req=True),
    m("google/gemma-2-27b-it", "Gemma 2 27B Instruct", "Gemma", 27.0, ctx=8192, gpu_req=True),
    m("internlm/internlm2-20b", "InternLM 2 20B", "InternLM", 20.0, ctx=32768, gpu_req=True),
    m("internlm/internlm2-chat-20b", "InternLM 2 Chat 20B", "InternLM", 20.0, ctx=32768, gpu_req=True),
    # ---------- TIER 3 (≥70B) ----------
    m("meta-llama/Llama-2-70b-hf", "Llama 2 70B", "Llama", 70.0, gpu_req=True),
    m("meta-llama/Llama-2-70b-chat-hf", "Llama 2 70B Chat", "Llama", 70.0, gpu_req=True),
    m("meta-llama/Meta-Llama-3-70B", "Llama 3 70B", "Llama", 70.0, ctx=8192, gpu_req=True),
    m("meta-llama/Meta-Llama-3-70B-Instruct", "Llama 3 70B Instruct", "Llama", 70.0, ctx=8192, gpu_req=True),
    m("meta-llama/Llama-3.1-70B", "Llama 3.1 70B", "Llama", 70.0, ctx=131072, gpu_req=True),
    m("meta-llama/Llama-3.1-70B-Instruct", "Llama 3.1 70B Instruct", "Llama", 70.0, ctx=131072, gpu_req=True),
    m("Qwen/Qwen2.5-72B", "Qwen2.5 72B", "Qwen", 72.0, ctx=131072, gpu_req=True),
    m("Qwen/Qwen2.5-72B-Instruct", "Qwen2.5 72B Instruct", "Qwen", 72.0, ctx=131072, gpu_req=True),
    m("Qwen/Qwen2-72B", "Qwen2 72B", "Qwen", 72.0, ctx=131072, gpu_req=True),
    m("Qwen/Qwen2-72B-Instruct", "Qwen2 72B Instruct", "Qwen", 72.0, ctx=131072, gpu_req=True),
    m("codellama/CodeLlama-70b-hf", "CodeLlama 70B", "Llama", 70.0, gpu_req=True),
    m("codellama/CodeLlama-70b-Instruct-hf", "CodeLlama 70B Instruct", "Llama", 70.0, gpu_req=True),
    m("deepseek-ai/deepseek-llm-67b-base", "DeepSeek 67B Base", "DeepSeek", 67.0, gpu_req=True),
    m("deepseek-ai/deepseek-llm-67b-chat", "DeepSeek 67B Chat", "DeepSeek", 67.0, gpu_req=True),
    m("databricks/dbrx-base", "DBRX Base (132B MoE)", "DBRX", 132.0, ctx=32768, gpu_req=True),
    m("databricks/dbrx-instruct", "DBRX Instruct", "DBRX", 132.0, ctx=32768, gpu_req=True),
    m("mistralai/Mixtral-8x22B-v0.1", "Mixtral 8x22B (MoE)", "Mixtral", 141.0, ctx=65536, gpu_req=True),
    m("mistralai/Mixtral-8x22B-Instruct-v0.1", "Mixtral 8x22B Instruct", "Mixtral", 141.0, ctx=65536, gpu_req=True),
    # ---------- TIER 4 (≥150B) ----------
    m("meta-llama/Llama-3.1-405B", "Llama 3.1 405B", "Llama", 405.0, ctx=131072, gpu_req=True),
    m("meta-llama/Llama-3.1-405B-Instruct", "Llama 3.1 405B Instruct", "Llama", 405.0, ctx=131072, gpu_req=True),
    m("deepseek-ai/DeepSeek-V2", "DeepSeek V2 (236B MoE)", "DeepSeek", 236.0, ctx=131072, gpu_req=True),
    m("deepseek-ai/DeepSeek-V2-Chat", "DeepSeek V2 Chat", "DeepSeek", 236.0, ctx=131072, gpu_req=True),
    m("Qwen/Qwen2-VL-72B-Instruct", "Qwen2-VL 72B Instruct", "Qwen", 72.0, ctx=32768, gpu_req=True),
]

def build_catalog():
    """Return catalog with derived fields."""
    out = []
    for it in CATALOG:
        it = dict(it)
        it["min_ram_gb_fp16"] = round(it["size_gb_fp16"] * 1.6, 1)
        it["min_ram_gb_int4"] = round(it["quantized_size_gb"] * 1.3, 1)
        # tier_min logic
        p = it["params_b"]
        if p <= 13:
            it["tier_min"] = "TIER_1"
        elif p <= 30:
            it["tier_min"] = "TIER_2"
        elif p <= 80:
            it["tier_min"] = "TIER_3"
        else:
            it["tier_min"] = "TIER_4"
        out.append(it)
    return out

ALL = build_catalog()
