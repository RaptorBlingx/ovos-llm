#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_DIR="$ROOT_DIR/enms-ovos-skill"
RELEASE_DIR="$ROOT_DIR/releases"
VERSION="${1:-1.0.0}"
ARTIFACT_NAME="HumanEnerDIA-OVOS-skill-v${VERSION}.zip"
ARTIFACT_PATH="$RELEASE_DIR/$ARTIFACT_NAME"
MODEL_PATH="$SKILL_DIR/models/Qwen3.5-2B-Q4_K_M.gguf"
MODEL_SHA_PATH="$RELEASE_DIR/Qwen3.5-2B-Q4_K_M.gguf.sha256"
NOTES_PATH="$RELEASE_DIR/HumanEnerDIA-OVOS-skill-v${VERSION}-release-notes.md"

mkdir -p "$RELEASE_DIR"
rm -f "$ARTIFACT_PATH" "$ARTIFACT_PATH.sha256" "$MODEL_SHA_PATH" "$NOTES_PATH"

(
  cd "$SKILL_DIR"
  python3 - "$ARTIFACT_PATH" <<'PY'
import fnmatch
import os
import sys
import zipfile

artifact_path = sys.argv[1]
exclude_patterns = (
    ".gitignore",
    "pytest.ini",
    "models/*",
    "docs/*",
    "scripts/*",
    "tests/*",
    "enms_ovos_skill/tests/*",
    "*/__pycache__/*",
    "*.pyc",
    ".pytest_cache/*",
    "htmlcov/*",
    "build/*",
    "dist/*",
    "*.egg-info/*",
    "*.bak",
    "*.backup",
    "*.backup_*",
    "*.phase*",
    "*.pre-*",
    "test_*.py",
    "*_test.py",
    "run_gui.sh",
    "bridge/README.md",
    "bridge/pdf_download_example.html",
    "bridge/test_*",
    "bridge/*windows*",
    "bridge/*wsl*",
    "bridge/*.bat",
    "bridge/hey_mycroft.tflite",
    ".env",
    "*.log",
)

def excluded(path):
    return any(fnmatch.fnmatch(path, pattern) for pattern in exclude_patterns)

with zipfile.ZipFile(artifact_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk("."):
        dirs[:] = [
            d for d in dirs
            if not excluded(os.path.relpath(os.path.join(root, d), ".") + "/")
        ]
        for name in files:
            relpath = os.path.relpath(os.path.join(root, name), ".")
            if excluded(relpath):
                continue
            zf.write(relpath)
PY
)

sha256sum "$ARTIFACT_PATH" > "$ARTIFACT_PATH.sha256"
if [[ -f "$MODEL_PATH" ]]; then
  sha256sum "$MODEL_PATH" > "$MODEL_SHA_PATH"
fi

{
  echo "# HumanEnerDIA OVOS Skill v${VERSION} Release Notes"
  echo
  echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  echo "## WASABI Shop Artifact"
  echo
  echo "- Upload file: \`$ARTIFACT_NAME\`"
  echo "- SHA256: \`$(cut -d ' ' -f1 "$ARTIFACT_PATH.sha256")\`"
  echo "- License: Apache-2.0 OR GPL-3.0-or-later"
  echo "- Product name: HumanEnerDIA OVOS Skill for Industrial Energy Management"
  echo
  echo "## Artifact Contents"
  echo
  echo "The ZIP contains the OVOS skill package, REST bridge code, release license,"
  echo "and safe configuration templates. It intentionally excludes tests, helper"
  echo "scripts, internal docs, GGUF model weights, local environments, caches, logs,"
  echo "and build outputs."
  echo
  echo "## Runtime Requirements"
  echo
  echo "This artifact is the standalone skill package. It requires an OVOS runtime,"
  echo "an OVOS messagebus/REST bridge, and a reachable HumanEnerDIA/EnMS analytics"
  echo "API endpoint. For a clean-machine OVOS runtime experiment, use the companion"
  echo "\`ovos-llm\` Docker repository and set \`ENMS_API_URL\` to the backend URL."
  echo
  echo "## Optional Local LLM Model"
  echo
  if [[ -f "$MODEL_SHA_PATH" ]]; then
    echo "- Validated filename: \`Qwen3.5-2B-Q4_K_M.gguf\`"
    echo "- SHA256: \`$(cut -d ' ' -f1 "$MODEL_SHA_PATH")\`"
    echo "- Install path after extraction: \`models/Qwen3.5-2B-Q4_K_M.gguf\`"
  else
    echo "- Model file was not present when this package was built."
    echo "- Provide \`Qwen3.5-2B-Q4_K_M.gguf\` separately if Tier-3 fallback is required."
  fi
  echo
  echo "## Smoke Test"
  echo
  echo "\`\`\`bash"
  echo "curl -sS -X POST http://localhost:5000/query \\"
  echo "  -H 'Content-Type: application/json' \\"
  echo "  -d '{\"text\":\"what is the power of compressor one\",\"session_id\":\"release-smoke\"}'"
  echo "\`\`\`"
  echo
  echo "## Known Limitations"
  echo
  echo "- Standard fast-path operational queries are release-ready."
  echo "- Tier-3 local LLM fallback remains slower than heuristic and Adapt routing."
  echo "- Loosely phrased fallback queries should be presented as improving, not solved."
} > "$NOTES_PATH"

echo "Created $ARTIFACT_PATH"
echo "Created $ARTIFACT_PATH.sha256"
[[ -f "$MODEL_SHA_PATH" ]] && echo "Created $MODEL_SHA_PATH"
echo "Created $NOTES_PATH"
