# LLMs in the homelab cluster: HAMi + Kaito + llm-d

Companion repo for the talk at **KCD Edinburgh 2026** (Mon 19 Oct 2026) by Mohamed Belgaied Hassine.

Can a homelab Kubernetes cluster run *useful* LLMs, the same way it runs your photo library and your password
manager? This repo holds the manifests, Helm values, scripts and measurements behind the talk: a k3s cluster
with three very different GPUs, and an honest look at where the CNCF inference stack helps at home and where it
doesn't.

| Card | What it runs | Stack |
|---|---|---|
| GTX 1080 Ti 11 GB (2017) | 4 AI services on one card: chat (Gemma 4 E4B), embeddings, speech-to-text, OCR | **HAMi** memory slices + llama.cpp CUDA |
| RX 6900 XT 16 GB (2020) | Qwen3.6-35B-A3B with RAM offload, 64k context, ~45 tok/s | llama.cpp Vulkan (no HAMi/Kaito/llm-d support on RDNA2) |
| RTX 3090 24 GB | Phi-4-mini behind a cache-aware router | **Kaito** InferenceSet + vLLM + **llm-d** via Istio |

See [docs/architecture.md](docs/architecture.md), [docs/results.md](docs/results.md) (every number measured)
and [docs/pitfalls.md](docs/pitfalls.md) (what broke and why).

## Repository layout

| Path | What | Status |
|---|---|---|
| `00-platform/` | GPU Operator (discovery only), HAMi, AMD device plugin | tested |
| `10-gateway/` | GWIE CRDs, Istio gateway-only, inference Gateway | tested |
| `20-kaito/` | Kaito values for bring-your-own nodes, InferenceSet + route | tested (1 replica) |
| `30-hami-demo/` | 4 workloads sharing one GTX 1080 Ti | tested |
| `40-amd/` | llama.cpp Vulkan on an RX 6900 XT, MoE RAM offload | tested |
| `50-monitoring/` | kube-prometheus-stack values + "Homelab Inference" dashboard | tested |
| `scripts/` | demo helpers, shared-prefix load generator, benchmarks | tested |
| `extras/paperless-ocr/` | Paperless-ngx OCR via paperless-gpt + docling-serve | CPU route tested; GPU route has an open issue |
| `extras/untested/` | experiments that were never applied | **untested** |

Nodes are selected by **labels**, so set them on your own nodes: `gpu=on` (HAMi device plugin), `homelab/hami-demo=true` (the GPU shared by the HAMi demo), `gpu-vendor=amd` (AMD card), `apps=llm-inference` (Kaito GPU nodes). Replace the remaining placeholders (`<amd-node-ip>`, `<hami-gpu-node>`, `<node-ip>`, `<docker-host-ip>`, `<ocr-endpoint>`) with your own values.

## Install, in the order I'd do it tonight

1. **Join your gaming PC to the cluster** (`k3s agent`), NVIDIA driver + container toolkit on the host first.
2. **GPU Operator for discovery only** (`00-platform/gpu-operator-values.yaml`), then **HAMi**
   (`00-platform/hami-values.yaml`). Label the node `gpu=on`.
3. **Several small AI services on one GPU**: `30-hami-demo/` (one card, four slices). This is where most homelabs
   get the most value.
4. **AMD consumer card?** llama.cpp on Vulkan, `40-amd/`. Skip the rest for that card.
5. **Kaito** on your own nodes (`20-kaito/kaito-values.yaml`): mind the four chart defaults that break BYO clusters.
6. **Two or more replicas of the same model?** Then Istio gateway-only + Kaito's GWIE feature gate give you llm-d's
   cache-aware routing (`10-gateway/`, `20-kaito/inferenceset-phi-4-mini.yaml`). With one replica it's plumbing only.

## Should you? (verdict)

The conclusion is simple. As with Kubernetes in the homelab: do it mostly for learning, and because it's cool!
Your second good reason is privacy. You will **not** save money, and you won't get the best models.

If learning isn't your priority, ask yourself two questions.

**Does AI inference need to be local?**
- Am I happy with online endpoints (AI labs, OpenRouter, my cloud provider)?
- Do I only trust my own network and hardware with my data?
- Do I have the time and the hardware?

**If it does, does it need Kubernetes?**
- One GPU, one user: use Ollama or LM Studio. Don't overthink it.
- Several AI services on one GPU: **HAMi** is worth installing tonight.
- Ephemeral compute (rented GPUs, gaming PCs that join and leave): why not, but cache images and model weights first.
- Many GPUs, many users, 2+ replicas of the same model: that's where **Kaito** and **llm-d** start to pay off.

## Next steps (not done)

- An AI gateway in front of everything (per-app keys, budgets, rate limits, fallback to a smaller model):
  LiteLLM, or Kubernetes-native options such as Envoy AI Gateway or agentgateway.
- 2 Kaito replicas on one GPU through HAMi slicing (untested).
- Ollama on the same GPU, for a like-for-like comparison.

## License

Apache-2.0, see [LICENSE](LICENSE). Model weights and container images keep their own licenses.
