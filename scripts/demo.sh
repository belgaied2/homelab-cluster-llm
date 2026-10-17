# Source me:  source scripts/demo.sh
# Demo helpers for the talk. Configure with environment variables before sourcing.
#   GATEWAY_URL   llm-d gateway (Istio NodePort), e.g. http://<node-ip>:30641
#   MODEL         served model name (= InferenceSet name), default phi-4-mini
#   GPU_NODE      NVIDIA node running Kaito, HAMI_NODE: node with the HAMi demo
: "${GATEWAY_URL:=http://localhost:30641}"
: "${MODEL:=phi-4-mini}"
: "${GPU_NODE:=<nvidia-kaito-node>}"
: "${HAMI_NODE:=<nvidia-hami-node>}"
export NS=llm

alias k=kubectl
alias nodes='kubectl get nodes -L gpu,gpu-vendor,nvidia.com/gpu.product'
alias gpu='kubectl describe node "$GPU_NODE" | grep -A8 "Allocated resources"'
alias gpuhami='kubectl describe node "$HAMI_NODE" | grep -A8 "Allocated resources"'
alias ws='kubectl get inferenceset,workspace,inferencepool,pods -n $NS -o wide'

# ask "<question>": same ~2k-token system prompt every time -> prefix-cache hits on the replica that has it
ask() {
  python3 - "$1" <<'PY' | curl -s "$GATEWAY_URL/v1/chat/completions" -H 'Content-Type: application/json' -d @- \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["choices"][0]["message"]["content"])'
import json, os, sys
system = " ".join(f"Rule {i}: answer briefly, in plain language, and stay on topic." for i in range(1, 180))
print(json.dumps({"model": os.environ.get("MODEL", "phi-4-mini"), "max_tokens": 120,
                  "messages": [{"role": "system", "content": system}, {"role": "user", "content": sys.argv[1]}]}))
PY
}

# load [seconds] [clients]: shared-prefix load from 3 "apps" (3 different long system prompts)
load() { python3 "$(dirname "${BASH_SOURCE[0]:-$0}")/shared_prefix_load.py" --url "$GATEWAY_URL" --model "$MODEL" \
           --seconds "${1:-30}" --clients "${2:-8}"; }
