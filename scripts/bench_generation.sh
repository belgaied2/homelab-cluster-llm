#!/bin/sh
# Single-user generation speed against an OpenAI-compatible llama.cpp server (uses llama.cpp's "timings").
# Usage: bench_generation.sh <base-url> <model> [runs=3]
#   e.g. bench_generation.sh http://<node-ip>:30084 qwen3.6-35b-a3b
# The first run includes warm-up; report the warm runs. Thinking is disabled for Qwen3.x models.
set -e
URL=${1:?base url}; MODEL=${2:?model}; RUNS=${3:-3}
i=1
while [ "$i" -le "$RUNS" ]; do
  curl -s --max-time 300 "$URL/v1/chat/completions" -H 'Content-Type: application/json' \
    -d "{\"model\":\"$MODEL\",\"temperature\":0,\"max_tokens\":300,\"chat_template_kwargs\":{\"enable_thinking\":false},\"messages\":[{\"role\":\"user\",\"content\":\"Explain in about 200 words why someone would run a language model on a home server instead of using a cloud API.\"}]}" \
  | python3 -c "import json,sys; t=json.load(sys.stdin)['timings']; print(f\"run $i: gen {t['predicted_n']} tok @ {t['predicted_per_second']:.1f} tok/s | prompt {t['prompt_n']} tok @ {t['prompt_per_second']:.0f} tok/s\")"
  i=$((i + 1))
done
