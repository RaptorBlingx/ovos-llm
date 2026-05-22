# OVOS-EnMS LLM Fallback Model Guide

The OVOS skill can optionally use a local GGUF model as a fallback parser when
heuristic and Adapt parsing cannot confidently resolve a query.

The model is not required for standard operation and is not bundled in this
repository.

## Default Behavior

Default Docker builds do not install `llama-cpp-python` or ship model files.
This keeps the image smaller and avoids distributing large model artifacts.

Fast-path queries continue to work through heuristic and Adapt routing.

## When to Enable the Fallback

Enable the fallback when you need better handling for:

- loose real-user phrasing
- spelling errors
- unusual wording
- unsupported sentence structures that still map to known intents

The fallback is slower than the fast path and should be treated as a recovery
layer, not the primary parser.

## Build with LLM Dependencies

```bash
docker compose build --build-arg INSTALL_LLM_FALLBACK=true
```

## Model Location

The source configuration references:

```text
enms-ovos-skill/models/Qwen3.5-2B-Q4_K_M.gguf
```

The Docker settings reference:

```text
/models/Qwen_Qwen3-1.7B-Q4_K_M.gguf
```

Before enabling fallback in production, choose one model path and align:

- mounted Docker volume path
- `settings.docker.json`
- runtime environment
- release notes/checksum

## Downloading a Model

Example command for a GGUF model:

```bash
huggingface-cli download unsloth/Qwen3.5-2B-GGUF \
  Qwen3.5-2B-Q4_K_M.gguf \
  --local-dir ./enms-ovos-skill/models
```

Confirm the model license before distribution or production use.

## Checksums

For release artifacts, publish a SHA256 checksum:

```bash
sha256sum enms-ovos-skill/models/Qwen3.5-2B-Q4_K_M.gguf
```

## Operational Notes

- Keep model files out of git.
- Expect higher memory and CPU usage when fallback is enabled.
- Test fallback queries separately from fast-path queries.
- Monitor bridge timeouts; the REST bridge waits up to 90 seconds.

## Known Limitation

The fallback improves resilience for messy phrasing, but it is still constrained
by the validator and by the backend API capabilities. It cannot create a valid
answer if the target machine, time range, or backend data is unavailable.
