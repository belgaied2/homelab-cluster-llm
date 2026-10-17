# Gateway: Istio (gateway only) for the Gateway API Inference Extension

Tested: Istio 1.28.3, Gateway API v1.5.1 (installed by Cilium), GWIE v1 CRDs, k3s v1.35.4 + Cilium (Oct 2026).

**Why Istio next to Cilium?** llm-d's cache-aware routing needs a gateway that implements the
[Gateway API Inference Extension](https://gateway-api-inference-extension.sigs.k8s.io/) (GWIE):
it asks an Endpoint Picker (EPP) which replica should serve each request. Neither Cilium's gateway nor Traefik
implements GWIE, and Kaito only documents Istio 1.28 as tested. So Istio runs **gateway-only** (no sidecars, no
ambient), which avoids conflicts with Cilium's kube-proxy replacement.

```bash
# 1. GWIE CRDs (InferencePool)
kubectl apply --server-side -f https://github.com/kubernetes-sigs/gateway-api-inference-extension/releases/latest/download/v1-manifests.yaml
# (Gateway API CRDs themselves were already installed by Cilium; llm-d v0.10 needs Gateway API >= 1.5)

# 2. Istio, gateway only, with GWIE enabled
helm repo add istio https://istio-release.storage.googleapis.com/charts
helm install istio-base istio/base -n istio-system --create-namespace --version 1.28.3
helm install istiod istio/istiod -n istio-system --version 1.28.3 -f istiod-values.yaml --wait

# 3. The gateway (NodePort, because the lab has no LoadBalancer IP pool)
kubectl create namespace llm
kubectl apply -f inference-gateway.yaml
curl http://<node-ip>:30641/        # 404 until a route exists = gateway is reachable
```

Istio assigns the NodePort automatically; pin it in the generated Service if you need a fixed port.
Before any replica is ready, requests return `500 no pods available in datastore`: that message comes from
the EPP, which proves the routing path is wired.
