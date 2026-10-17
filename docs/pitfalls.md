# Pitfalls (each one cost real time in the lab)

## GPU discovery and device plugins
- **Exactly one device plugin per GPU vendor.** HAMi replaces NVIDIA's device plugin. Turn NVIDIA's off
  (GPU Operator `devicePlugin.enabled: false`) and Kaito's off (`nvidiaDevicePlugin.enabled: false`).
- **Exactly one Node Feature Discovery.** Kaito's chart bundles NFD + GFD. Next to the GPU Operator's, the second
  NFD master **wiped the `nvidia.com/gpu.*` labels** Kaito itself needs to size vLLM. Disable Kaito's, then restart
  the GPU Operator's NFD master/worker and GFD pods to restore the labels.
- **Removed hardware leaves ghost labels.** A GPU moved to another machine leaves a `NodeFeature` object
  (`gpu-operator/nvidia-features-for-<node>`). NFD re-applies the old labels from it. Delete the object.
- **Driver upgraded but not rebooted** = `Driver/library version mismatch`, HAMi's device plugin crash-loops.

## Kaito on your own nodes (chart 0.12.0)
- `featureGates.disableNodeAutoProvisioning=true` is **not enough**: also set **`nodeProvisioner: byo`**, otherwise
  every Workspace is rejected with `instanceType is required when node auto-provisioning is enabled`.
  `byo` is only documented as a controller flag in the source.
- **llm-d routing needs an `InferenceSet`.** A `Workspace` runs fine but gets no InferencePool / router.
- The **served model name is the InferenceSet name** (`phi-4-mini`), not the preset name (404 otherwise).
- Kaito requests whole GPUs (`nvidia.com/gpu` without `gpumem`): under HAMi a Kaito pod gets the full card.
  Kaito's `resource.partition` is MIG-only (not on consumer GPUs).
- Kaito runs a start-up benchmark in every new replica: free data, but 1–2 extra minutes of cold start.
- Open WebUI sends `tool_choice: "auto"`; vLLM rejects it unless started with `--enable-auto-tool-choice
  --tool-call-parser ...` (Kaito doesn't set these).

## Gateway
- Cilium's gateway and Traefik don't implement the **Gateway API Inference Extension**. Run Istio gateway-only next
  to Cilium (no sidecars). `500 no pods available in datastore` = routing works, no replica is Ready yet.

## llama.cpp tuning (MoE models with RAM offload)
- **More layers on the GPU can be slower**: when the GPU part no longer fits, the driver spills to system RAM.
  For Qwen3.6-35B-A3B on 16 GB: `--n-cpu-moe 14` = 45 tok/s, `--n-cpu-moe 10` = 22 tok/s.
- **MTP / speculative decoding can hurt** with experts in system RAM: verifying drafted tokens touches more experts
  on the CPU per step (45 → 26 tok/s).
- **KV cache quantisation decides long-context usability**: at 64k, q8_0 spilled and needed 761 s for a 60k-token
  prompt; q4_0 fit, needed 155 s, and still retrieved the right fact.
- Right after a rollout, the NodePort can briefly route nowhere: the first request fails, retry.

## HAMi
- Memory isolation, not performance isolation: a busy pod slows its neighbours.
- GPU Deployments on a fully sliced card need `strategy: Recreate`.
- Resize slices in the right order (shrink others first) so the scheduler has room.
- HAMi-core printed `ERROR: driverInitFileInfo …` on a node with driver 575, while still enforcing the limit; the
  580 node was clean.

## Pascal (GTX 1080 Ti) specifics
- No vLLM (needs CC >= 7.0). The official whisper.cpp CUDA image isn't built for Pascal either;
  faster-whisper (CTranslate2, via Speaches) works. llama.cpp CUDA works.
