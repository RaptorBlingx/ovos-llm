#!/bin/bash
FILES=("/var/log/ovos/bridge.out.log" "/var/log/ovos/skills.out.log" "/var/log/ovos/skills.log")
get_counts() {
    local counts=()
    for f in "${FILES[@]}"; do
        if [ -f "$f" ]; then counts+=($(wc -l < "$f")); else counts+=(0); fi
    done
    echo "${counts[@]}"
}
show_new_logs() {
    local old_counts=($1)
    local session_id="$2"
    local utterance="$3"
    local i=0
    local patterns="($session_id|$utterance|trying_llm_tier|fallback_handler_triggered|clarification_response_returned|query_timeout|validation_failed|step8_calling_api|step8_api_returned|query_processed_successfully|Parsing utterance|fallback_medium match|speak|Timeout waiting for response)"
    for f in "${FILES[@]}"; do
        local old_count=${old_counts[$i]}
        if [ -f "$f" ]; then
            local new_count=$(wc -l < "$f")
            if [ "$new_count" -gt "$old_count" ]; then
                echo "--- New logs in $f ---"
                tail -n +$((old_count + 1)) "$f" | grep -Ei "$patterns" || true
            fi
        fi
        i=$((i + 1))
    done
}
run_query() {
    local label="$1"
    local body="$2"
    local session_id="$3"
    local utterance="$4"
    echo "===================================================="
    echo "TEST: $label"
    local counts=$(get_counts)
    response=$(curl -sS -X POST http://localhost:5000/query -H "Content-Type: application/json" -d "$body" --max-time 95 -w "\nHTTP_STATUS:%{http_code}\nTIME_TOTAL:%{time_total}\n")
    echo "Response Summary:"
    echo "$response" | grep -v "HTTP_STATUS" | grep -v "TIME_TOTAL" | head -n 5
    echo "$response" | grep -E "HTTP_STATUS|TIME_TOTAL"
    show_new_logs "$counts" "$session_id" "$utterance"
}

run_query "Legacy body alias check" '{"utterance":"forecast energy for tomorrow","session_id":"alias-forecast-001","user_id":"debug"}' "alias-forecast-001" "forecast energy for tomorrow"
run_query "Typo fallback check" '{"text":"what is the powre of comprsor one","session_id":"trace-typo-002","user_id":"debug"}' "trace-typo-002" "what is the powre of comprsor one"
run_query "Ranking/fallback check" '{"text":"which machines are using most electricity","session_id":"trace-ranking-002","user_id":"debug"}' "trace-ranking-002" "which machines are using most electricity"
