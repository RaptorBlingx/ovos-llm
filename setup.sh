#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

REQUESTED_ENMS_API_URL="${ENMS_API_URL:-}"
REQUESTED_NETWORK="${ENMS_NETWORK:-enms-network}"
REQUESTED_BRIDGE_PORT="${OVOS_BRIDGE_EXTERNAL_PORT:-5000}"
REQUESTED_MESSAGEBUS_PORT="${OVOS_MESSAGEBUS_PORT:-8181}"
NO_BUILD=false
NO_START=false

usage() {
  cat <<'EOF'
Usage: ./setup.sh [--enms-api-url URL] [--network NAME] [--bridge-port PORT] [--messagebus-port PORT] [--no-build] [--no-start]

Starts a headless OVOS runtime with the HumanEnerDIA skill and REST bridge.
The skill requires a reachable HumanEnerDIA analytics API.

Examples:
  ./setup.sh --enms-api-url http://192.168.1.50:8001/api/v1
  ./setup.sh --enms-api-url http://host.docker.internal:8001/api/v1
  ./setup.sh --enms-api-url http://enms-analytics:8001/api/v1 --network enms-network
  ./setup.sh --enms-api-url http://192.168.1.50:8001/api/v1 --bridge-port 5500

If HumanEnerDIA is running on another laptop/server, use that machine's IP or
DNS name in --enms-api-url. If OVOS joins the same Docker network as
HumanEnerDIA, use the analytics service name, usually enms-analytics.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --enms-api-url)
      REQUESTED_ENMS_API_URL="${2:?--enms-api-url requires a URL}"
      shift 2
      ;;
    --network)
      REQUESTED_NETWORK="${2:?--network requires a Docker network name}"
      shift 2
      ;;
    --bridge-port)
      REQUESTED_BRIDGE_PORT="${2:?--bridge-port requires a port}"
      shift 2
      ;;
    --messagebus-port)
      REQUESTED_MESSAGEBUS_PORT="${2:?--messagebus-port requires a port}"
      shift 2
      ;;
    --no-build)
      NO_BUILD=true
      shift
      ;;
    --no-start)
      NO_START=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

require_command() {
  local command_name="$1"
  local install_hint="$2"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "$command_name is required. $install_hint" >&2
    exit 1
  fi
}

set_env_value() {
  local key="$1"
  local value="$2"
  local escaped
  escaped="$(printf '%s' "$value" | sed -e 's/[\/&]/\\&/g')"

  if grep -qE "^${key}=" .env; then
    sed -i "s|^${key}=.*|${key}=${escaped}|" .env
  else
    printf '%s=%s\n' "$key" "$value" >> .env
  fi
}

get_env_value() {
  local key="$1"
  grep -E "^${key}=" .env | tail -n 1 | cut -d= -f2- || true
}

require_command docker "Install Docker Engine 20.10+ and Docker Compose v2."
docker compose version >/dev/null

if [[ ! -f .env ]]; then
  if [[ ! -f .env.example ]]; then
    echo ".env is missing and .env.example was not found." >&2
    exit 1
  fi
  cp .env.example .env
  echo "Created .env from .env.example"
fi

if [[ -n "$REQUESTED_ENMS_API_URL" ]]; then
  set_env_value ENMS_API_URL "$REQUESTED_ENMS_API_URL"
elif [[ -z "$(get_env_value ENMS_API_URL)" ]]; then
  set_env_value ENMS_API_URL "http://host.docker.internal:8001/api/v1"
fi

set_env_value ENMS_NETWORK "$REQUESTED_NETWORK"
set_env_value OVOS_BRIDGE_EXTERNAL_PORT "$REQUESTED_BRIDGE_PORT"
set_env_value OVOS_MESSAGEBUS_PORT "$REQUESTED_MESSAGEBUS_PORT"

if ! docker network inspect "$REQUESTED_NETWORK" >/dev/null 2>&1; then
  docker network create "$REQUESTED_NETWORK" >/dev/null
  echo "Created Docker network: $REQUESTED_NETWORK"
fi

docker compose config >/dev/null

if [[ "$NO_BUILD" != "true" ]]; then
  docker compose build
fi

if [[ "$NO_START" != "true" ]]; then
  if docker compose up --help 2>/dev/null | grep -q -- '--wait'; then
    docker compose up -d --wait --wait-timeout 180
  else
    docker compose up -d
  fi
fi

if [[ "$NO_START" == "true" ]]; then
  runtime_state="Prepared HumanEnerDIA OVOS runtime. Start was skipped because --no-start was used."
else
  runtime_state="Started HumanEnerDIA OVOS runtime."
fi

cat <<EOF
$runtime_state

Backend API:   $(get_env_value ENMS_API_URL)
Docker network: $(get_env_value ENMS_NETWORK)

Open:
  REST bridge: http://localhost:$(get_env_value OVOS_BRIDGE_EXTERNAL_PORT)
  Health:      http://localhost:$(get_env_value OVOS_BRIDGE_EXTERNAL_PORT)/health
  API docs:    http://localhost:$(get_env_value OVOS_BRIDGE_EXTERNAL_PORT)/docs

Smoke test:
  curl -sS -X POST http://localhost:$(get_env_value OVOS_BRIDGE_EXTERNAL_PORT)/query \\
    -H 'Content-Type: application/json' \\
    -d '{"text":"what is the power of compressor one","session_id":"ovos-release-smoke"}'
EOF
