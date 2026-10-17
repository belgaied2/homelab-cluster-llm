#!/usr/bin/env python3
"""Shared-prefix load generator for an OpenAI-compatible endpoint (stdlib only).

Simulates several "apps", each with its own long system prompt, sending short questions concurrently.
With 2+ vLLM replicas behind the llm-d router, each app's prompt should stick to the replica that already
holds it in its KV cache: watch vllm:prefix_cache_hits_total / vllm:prefix_cache_queries_total per pod.

Usage: shared_prefix_load.py --url http://<node-ip>:30641 --model phi-4-mini --seconds 30 --clients 8
"""
import argparse
import json
import random
import threading
import time
import urllib.request

APPS = {
    "documents": "You tag and summarise scanned household documents.",
    "voice": "You are a home-automation voice assistant. Answer in one sentence.",
    "crm": "You enrich and summarise contact records for a small consultancy.",
}
QUESTIONS = ["What should I do first?", "Summarise this in one line.", "Which tag fits best?",
             "Is anything missing?", "Give me the next step."]


def long_prompt(app, base):
    # ~2k tokens per app, identical across requests of the same app -> cacheable prefix
    return base + " " + " ".join(f"[{app} policy {i}] keep answers short, factual and polite." for i in range(150))


def worker(args, stop, stats, lock):
    prompts = {a: long_prompt(a, b) for a, b in APPS.items()}
    while not stop.is_set():
        app = random.choice(list(APPS))
        body = json.dumps({"model": args.model, "max_tokens": 40, "temperature": 0,
                           "messages": [{"role": "system", "content": prompts[app]},
                                        {"role": "user", "content": random.choice(QUESTIONS)}]}).encode()
        req = urllib.request.Request(args.url.rstrip("/") + "/v1/chat/completions", data=body,
                                     headers={"Content-Type": "application/json"})
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                r.read()
            ok = True
        except Exception:
            ok = False
        with lock:
            stats["ok" if ok else "err"] += 1
            stats["lat"].append(time.time() - t0)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--model", default="phi-4-mini")
    p.add_argument("--seconds", type=int, default=30)
    p.add_argument("--clients", type=int, default=8)
    args = p.parse_args()
    stop, lock = threading.Event(), threading.Lock()
    stats = {"ok": 0, "err": 0, "lat": []}
    threads = [threading.Thread(target=worker, args=(args, stop, stats, lock), daemon=True)
               for _ in range(args.clients)]
    for t in threads:
        t.start()
    time.sleep(args.seconds)
    stop.set()
    for t in threads:
        t.join(timeout=130)
    lat = sorted(stats["lat"]) or [0]
    print(f"requests ok={stats['ok']} err={stats['err']} | latency p50={lat[len(lat)//2]:.2f}s "
          f"p95={lat[int(len(lat)*0.95)-1 if len(lat) > 1 else 0]:.2f}s")


if __name__ == "__main__":
    main()
