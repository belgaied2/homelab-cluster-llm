# Architecture

```
Clients      Open WebUI (chat, document search / RAG, speech-to-text), any OpenAI-compatible app
   │
Ingress      Istio Gateway (gateway-only, next to Cilium) ── NodePort
   │
Routing      llm-d router (EPP) on an InferencePool: prefix / KV-cache-aware replica choice
   │                                     (created by Kaito through Flux for each InferenceSet)
Models       Kaito InferenceSet → vLLM replica(s) on NVIDIA (CC >= 7.0)
             llama.cpp Deployments on the other cards (plain Kubernetes, no Kaito/llm-d)
   │
Sharing      HAMi: memory slices of one GPU (e.g. 6800 / 1500 / 1500 / 1200 MiB on an 11 GB card)
   │
Devices      NVIDIA GPU Operator (toolkit + feature discovery only) · HAMi device plugin · ROCm device plugin (AMD)
   │
Nodes        k3s + Cilium · GTX 1080 Ti · RX 6900 XT · RTX 3090 
Monitoring   kube-prometheus-stack + "Homelab Inference" Grafana dashboard
```

## One request through the llm-d path

`client → Istio Gateway → ext_proc call to the EPP ("which replica?") → vLLM replica → tokens stream back`

The EPP scores replicas by queue depth, KV-cache use and prefix-cache affinity. It only matters with **2+ replicas
of the same model**: with one replica it has nothing to choose between.

## What runs where in the lab

| Card | Runtime | Workloads |
|---|---|---|
| GTX 1080 Ti 11 GB | llama.cpp CUDA, Speaches, all in HAMi slices | Gemma 4 E4B chat, nomic embeddings, Whisper large-v3-turbo, Granite-Docling OCR |
| RX 6900 XT 16 GB | llama.cpp Vulkan (whole GPU) | Qwen3.6-35B-A3B, experts of 14 layers in system RAM, 64k context, KV q4_0 |
| RTX 3090 24 GB | vLLM via Kaito | Phi-4-mini behind the llm-d router |
