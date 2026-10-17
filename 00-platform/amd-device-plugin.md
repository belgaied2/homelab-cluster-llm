# AMD consumer GPU (RX 6900 XT, RDNA2) as a schedulable resource

Tested: RX 6900 XT 16 GB on Ubuntu, k3s v1.35.4 (Oct 2026).

```bash
kubectl create -f https://raw.githubusercontent.com/ROCm/k8s-device-plugin/master/k8s-ds-amdgpu-dp.yaml
kubectl label node <amd-node> gpu-vendor=amd
```

The node then advertises `amd.com/gpu: 1` (whole GPU only, no slicing). Pods request it with
`resources.limits: { amd.com/gpu: 1 }` and select the node with `nodeSelector: { gpu-vendor: amd }`.

## What does NOT work on RDNA2 (as of Oct 2026)

| Project | Status on RX 6900 XT (gfx1030) |
|---|---|
| HAMi | AMD support is Instinct-only |
| Kaito | NVIDIA only (`nvidia.com/gpu`, NVIDIA feature-discovery labels) |
| vLLM ROCm | gfx1030 is not in the supported list (gfx90a/942/950/1100/1101/1150/1151/1200/1201) |
| llm-d | its AMD path assumes vLLM on Instinct |

**What works:** llama.cpp with **Vulkan** (`ghcr.io/ggml-org/llama.cpp:server-vulkan`), see `../40-amd/`.
Kubernetes still schedules the card; the fancy layers don't.
