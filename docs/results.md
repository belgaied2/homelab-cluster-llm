# Measured results

Everything here was measured in the lab, **13–17 Oct 2026**, with the files in this repo.
Single runs or 3-run averages; warm runs unless stated. These are homelab numbers, not lab-grade benchmarks.

## Hardware

| GPU | VRAM | Notes |
|---|---|---|
| GTX 1080 Ti (2017, Pascal, CC 6.1) | 11 GB | Shared by HAMi. Can't run vLLM (needs CC >= 7.0) |
| RX 6900 XT (2020, RDNA2, gfx1030) | 16 GB | llama.cpp Vulkan only. Host has 30 GB RAM |
| RTX 3090 (Ampere) | 24 GB | Kaito + vLLM + llm-d |

## Generation speed, single user

| Setup | Model | Generation | Method |
|---|---|---|---|
| 1080 Ti, 5 GB HAMi slice, llama.cpp CUDA | Llama 3.2 3B Q4_K_M | **94.6 tok/s** (server), 99.0 (`llama-bench` tg128) | `llama-bench`, chat completions |
| 1080 Ti, 6.8 GB HAMi slice | Gemma 4 E4B Q4_K_M (`--no-mmproj`) | **~60 tok/s** (59.4–60.3, 3 runs) | 300-token answers, temp 0 |
| 6900 XT, Vulkan | Llama 3.2 3B Q4_K_M | **177.7 tok/s** (`llama-bench` tg128) | same model as the 1080 Ti row |
| 6900 XT, Vulkan | Qwen2.5 14B Q4_K_M | ~50 tok/s | chat completions |
| 6900 XT + RAM offload, `--n-cpu-moe 14` | Qwen3.6-35B-A3B UD-Q4_K_M (21.1 GiB) | **45.3 tok/s** | 300-token answers, temp 0 |
| 3090, vLLM 0.25.1 (Kaito) | Phi-4-mini (bf16) | 22 tokens in **0.40 s** end-to-end through Istio + llm-d (29 tokens in 0.52 s direct to the pod) | single request |

## MoE offload and KV cache (Qwen3.6-35B-A3B on the 6900 XT)

| Setting | Generation | Reading a 60,218-token prompt | Correct retrieval |
|---|---|---|---|
| `--n-cpu-moe 14`, 8k context | 45.3 tok/s | n/a | n/a |
| `--n-cpu-moe 10` (more on GPU) | **22.3 tok/s** (VRAM spills to system RAM) | n/a | n/a |
| `--n-cpu-moe 14` + MTP (`--spec-type draft-mtp --spec-draft-n-max 2`) | **25.9 tok/s** (55 % draft acceptance) | n/a | n/a |
| 64k context, `-fa on`, KV **q8_0** | 23.8 tok/s (0.71 GB spilled) | 761 s (79 tok/s) | yes |
| 64k context, `-fa on`, KV **q4_0** | **44.6 tok/s** (0.15 GB spilled) | **155 s** (389 tok/s) | yes |

Method: `scripts/bench_generation.sh`, `scripts/long_prompt_test.py`.

## Many users at once (3090, Kaito's built-in start-up benchmark)

Phi-4-mini, vLLM 0.25.1, 2048 input / 256 output tokens, 40 concurrent, 60 s:
**223,622 tokens/min total**, TTFT avg 2.6 s, 89 ms per output token.

## HAMi on one GTX 1080 Ti: four workloads

| Pod | Model | Slice | Used |
|---|---|---|---|
| chat | Gemma 4 E4B | 6800 MiB | 3400 MiB |
| embeddings | nomic-embed-text v1.5 Q8_0 | 1500 MiB | 290 MiB |
| speech-to-text | faster-whisper large-v3-turbo (int8, Speaches) | 1500 MiB | 944 MiB active |
| OCR | Granite-Docling-258M Q8_0 | 1200 MiB | 638 MiB |

- Inside each pod `nvidia-smi` shows only the slice. Loading a 2nd model inside a 5 GB slice failed with
  `[HAMI-core ERROR] Device 0 OOM` while the card still had ~7 GB free.
- Whisper large-v3-turbo: a synthetic 8-second sentence transcribed word-perfect in 6.8 s (first call, incl. model load).
  Whisper small: 11 s of audio in 0.68 s warm.
- OCR: a synthetic one-page invoice, 100 % correct incl. the table, **6.5 s** (cold), 1.7 s warm.

## Cold starts (the real cost)

| What | Time |
|---|---|
| vLLM image (5.6 GB) pull | ~2.5 min on a 1 Gbps connection: it depends on the host's network (container images come from the registry, so a Hugging Face token doesn't change this) |
| Kaito replica from create to Ready, image cached, no HF token | **~5–10 min** (model download + Kaito's start-up benchmark) |
| llama.cpp CUDA image (2.6 GB) + 2 GB GGUF, nothing cached | ~6 min |
| llama.cpp Vulkan image (307 MB), model cached | ~5 min first time, 36 s for later restarts |
| Gemma 4 E4B (4.7 GB), with HF token | Ready 94 s after apply |

## Not measured

- Ollama / LM Studio on the same GPU (for the "is Kubernetes worth it?" comparison)
- 2 Kaito replicas on one GPU via HAMi (untested)
- CPU / iGPU mini-PC inference
