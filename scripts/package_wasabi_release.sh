#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_DIR="$ROOT_DIR/enms-ovos-skill"
RELEASE_DIR="$ROOT_DIR/releases"
VERSION="${1:-1.0.0}"
ARTIFACT_BASE="HumanEnerDIA-OVOS-skill-v${VERSION}"
ARTIFACT_NAME="${ARTIFACT_BASE}.zip"
ARTIFACT_PATH="$RELEASE_DIR/$ARTIFACT_NAME"
MODEL_PATH="$SKILL_DIR/models/Qwen3.5-2B-Q4_K_M.gguf"
MODEL_SHA_PATH="$RELEASE_DIR/Qwen3.5-2B-Q4_K_M.gguf.sha256"
NOTES_PATH="$RELEASE_DIR/${ARTIFACT_BASE}-release-notes.md"
STAGE_ROOT="$(mktemp -d)"
BUNDLE_DIR="$STAGE_ROOT/$ARTIFACT_BASE"

cleanup() {
  rm -rf "$STAGE_ROOT"
}
trap cleanup EXIT

mkdir -p "$RELEASE_DIR" "$BUNDLE_DIR"
rm -f "$ARTIFACT_PATH" "$ARTIFACT_PATH.sha256" "$MODEL_SHA_PATH" "$NOTES_PATH"

copy_root() {
  rsync -a \
    --exclude '.git/' \
    --exclude '.gitignore' \
    --exclude '.env' \
    --exclude '__pycache__/' \
    --exclude '.pytest_cache/' \
    --exclude 'htmlcov/' \
    --exclude 'logs/' \
    --exclude 'models/' \
    --exclude 'releases/' \
    --exclude 'documentation/' \
    --exclude 'scripts/' \
    --exclude 'benchmark.sh' \
    --exclude 'compare_parsers.py' \
    --exclude 'run_validation.sh' \
    --exclude 'validate_ovos.sh' \
    --exclude 'humanergy-ovos-llm.code-workspace' \
    --exclude 'query*_time.txt' \
    --exclude '*.log' \
    --exclude '.gitkeep' \
    --exclude '*.gitkeep' \
    --exclude '*.pyc' \
    --exclude '*.bak' \
    --exclude '*.backup' \
    --exclude '*.phase*' \
    --exclude '*.pre-*' \
    --exclude 'enms-ovos-skill/' \
    "$ROOT_DIR/" "$BUNDLE_DIR/"
}

copy_skill() {
  mkdir -p "$BUNDLE_DIR/enms-ovos-skill"
  rsync -a \
    --exclude '.gitignore' \
    --exclude '.env' \
    --exclude '__pycache__/' \
    --exclude '.pytest_cache/' \
    --exclude 'htmlcov/' \
    --exclude 'docs/' \
    --exclude 'scripts/' \
    --exclude 'tests/' \
    --exclude 'enms_ovos_skill/tests/' \
    --exclude 'models/' \
    --exclude 'pytest.ini' \
    --exclude 'run_gui.sh' \
    --exclude 'test_*.py' \
    --exclude '*_test.py' \
    --exclude '.gitkeep' \
    --exclude '*.gitkeep' \
    --exclude '*.pyc' \
    --exclude '*.bak' \
    --exclude '*.backup' \
    --exclude '*.phase*' \
    --exclude '*.pre-*' \
    --exclude 'bridge/README.md' \
    --exclude 'bridge/pdf_download_example.html' \
    --exclude 'bridge/test_*' \
    --exclude 'bridge/*windows*' \
    --exclude 'bridge/*wsl*' \
    --exclude 'bridge/*.bat' \
    --exclude 'bridge/hey_mycroft.tflite' \
    "$SKILL_DIR/" "$BUNDLE_DIR/enms-ovos-skill/"
}

copy_root
copy_skill
chmod 755 "$BUNDLE_DIR/setup.sh" "$BUNDLE_DIR/enms-ovos-skill/bridge/start_rest_bridge.sh" "$BUNDLE_DIR/enms-ovos-skill/setup_ovos_skill.sh"

(
  cd "$STAGE_ROOT"
  python3 - "$ARTIFACT_PATH" "$ARTIFACT_BASE" <<'PY'
import os
import sys
import zipfile

artifact_path = sys.argv[1]
artifact_base = sys.argv[2]

with zipfile.ZipFile(artifact_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, _, files in os.walk(artifact_base):
        for name in files:
            path = os.path.join(root, name)
            zf.write(path)
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
  echo "The ZIP contains a headless OVOS Docker runtime, Docker Compose file,"
  echo "setup helper, REST bridge, HumanEnerDIA OVOS skill source, release license,"
  echo "and end-user install documentation. It intentionally excludes tests,"
  echo "internal development docs, helper/dev scripts, GGUF model weights, local"
  echo "environments, caches, logs, and build outputs."
  echo
  echo "## Runtime Requirements"
  echo
  echo "This artifact runs only the OVOS assistant layer. It requires a reachable"
  echo "HumanEnerDIA analytics API, for example \`http://<host>:8001/api/v1\`."
  echo "Users who need the backend too should install the full-stack product."
  echo
  echo "## Guided Install"
  echo
  echo "\`\`\`bash"
  echo "unzip $ARTIFACT_NAME"
  echo "cd $ARTIFACT_BASE"
  echo "./setup.sh --enms-api-url http://<humanerdia-host>:8001/api/v1"
  echo "\`\`\`"
  echo
  echo "## Smoke Test"
  echo
  echo "\`\`\`bash"
  echo "curl -fsS http://localhost:5000/health"
  echo "curl -sS -X POST http://localhost:5000/query \\"
  echo "  -H 'Content-Type: application/json' \\"
  echo "  -d '{\"text\":\"what is the power of compressor one\",\"session_id\":\"release-smoke\"}'"
  echo "\`\`\`"
  echo
  echo "## Optional Local LLM Model"
  if [[ -f "$MODEL_SHA_PATH" ]]; then
    echo "- Validated filename: \`Qwen3.5-2B-Q4_K_M.gguf\`"
    echo "- SHA256: \`$(cut -d ' ' -f1 "$MODEL_SHA_PATH")\`"
    echo "- Install path after extraction: \`enms-ovos-skill/models/Qwen3.5-2B-Q4_K_M.gguf\`"
  else
    echo "- Model file was not present when this package was built."
    echo "- Provide \`Qwen3.5-2B-Q4_K_M.gguf\` separately if Tier-3 fallback is required."
  fi
} > "$NOTES_PATH"

echo "Created $ARTIFACT_PATH"
echo "Created $ARTIFACT_PATH.sha256"
[[ -f "$MODEL_SHA_PATH" ]] && echo "Created $MODEL_SHA_PATH"
echo "Created $NOTES_PATH"
