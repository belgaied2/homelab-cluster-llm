# Paperless-ngx OCR with paperless-gpt + docling-serve

Optional extra, runs on any Docker host on the LAN (not in the cluster). Tested Oct 2026 with
paperless-ngx 2.20.15, paperless-gpt v0.31.0, docling-serve-cpu v1.37.0.

```
Paperless-ngx ── API ── paperless-gpt ── docling-serve (CPU: EasyOCR, Markdown out)
                                    └── docling-preset proxy ── docling-serve ── Granite-Docling on a GPU (llama.cpp)
```

## Use
1. `cp paperless-gpt.env.example paperless-gpt.env && chmod 600 paperless-gpt.env`, then fill in
   `PAPERLESS_BASE_URL` and `PAPERLESS_API_TOKEN` (Paperless → My Profile → API Auth Token).
2. Replace `<docker-host-ip>` in `compose.yaml` and `<ocr-endpoint>` in `docling-config-gpu.yaml`.
3. `docker compose up -d` starts docling-serve only. `docker compose --profile gpt up -d` also starts paperless-gpt.
4. In Paperless, add the tag **`ocr-docling`** to a document. paperless-gpt replaces its text content with Markdown
   and tags it `ocr-docling-done` (or `ocr-docling-failed` after 3 attempts). It **creates these two tags** on first start.

Only hand-tagged documents are processed: no bulk run, all auto-generation options off.

## Lessons
- **TIFF scans fail in `OCR_PROCESS_MODE=pdf`**: PDF modes download the *original* file. `image` mode uses
  Paperless's archived PDF and renders every page, so it handles TIFF and PDF scans alike.
- paperless-gpt renders at **600 DPI** by default (`IMAGE_MAX_RENDER_DPI`): one page took 72 s on 2 CPU cores.
- docling-serve only applies `default_vlm_preset` when a request asks for the preset named `"default"`;
  paperless-gpt sends no preset. `preset_proxy.py` (stdlib only) injects `vlm_pipeline_preset=default`.

## Open issue: GPU route returns empty tables
Through docling-serve's API engine, Granite-Docling on the GPU processes a page in **1.5 s** (vs 12–72 s on CPU) with
correct text, but **tables come back with 0 cells**. The same model called directly returns all cells.
So the CPU route is the default. Help welcome.
