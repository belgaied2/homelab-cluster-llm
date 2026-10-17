#!/usr/bin/env python3
"""Long-context check: prompt-processing time + retrieval correctness (stdlib only).

Builds a synthetic document of numbered records (~60k tokens with the default 2600 records for Qwen3.x),
asks for the value of one record, and reports how long the prompt took to process and whether the answer
is right. Used to compare KV-cache settings (e.g. -ctk/-ctv q8_0 vs q4_0) on llama.cpp.

Usage: long_prompt_test.py --url http://<node-ip>:30084 --model qwen3.6-35b-a3b [--records 2600]
"""
import argparse
import json
import random
import urllib.request

p = argparse.ArgumentParser()
p.add_argument("--url", required=True)
p.add_argument("--model", required=True)
p.add_argument("--records", type=int, default=2600)
p.add_argument("--target", type=int, default=1717)
args = p.parse_args()

random.seed(42)
lines = [f"Record {i}: the value of item {i} is {random.randint(1000, 9999)}." for i in range(1, args.records + 1)]
expected = lines[args.target - 1].split()[-1].rstrip(".")
question = "\n".join(lines) + f"\n\nQuestion: what is the value of item {args.target}? Answer with the number only."
body = json.dumps({"model": args.model, "temperature": 0, "max_tokens": 20,
                   "chat_template_kwargs": {"enable_thinking": False},
                   "messages": [{"role": "user", "content": question}]}).encode()
req = urllib.request.Request(args.url.rstrip("/") + "/v1/chat/completions", data=body,
                             headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=1800) as r:
    d = json.load(r)
t = d["timings"]
answer = d["choices"][0]["message"]["content"].strip()
print(f"prompt {t['prompt_n']} tokens in {t['prompt_ms']/1000:.1f} s ({t['prompt_per_second']:.0f} tok/s) | "
      f"answer {answer!r}, expected {expected} -> {'OK' if expected in answer else 'WRONG'}")
