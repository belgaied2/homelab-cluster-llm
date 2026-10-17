# Untested experiments

Files here were written but **never applied**. They document an idea, not a result.

- `vllm-rocm-unlimited-ocr-6900xt.yaml`: baidu/Unlimited-OCR on vLLM ROCm on an RX 6900 XT, spoofing RDNA3 with
  `HSA_OVERRIDE_GFX_VERSION=11.0.0`. gfx1030 is not supported by vLLM ROCm, so this is expected to fail.
  Abandoned in favour of an NVIDIA GPU.
