#!/bin/bash
FILES=("/var/log/ovos/bridge.out.log" "/var/log/ovos/skills.out.log" "/var/log/ovos/skills.log")
get_counts() {
    for f in "${FILES[@]}"; do
        if [ -f "$f" ]; then wc -l < "$f"; else echo 0; fi
    done
}
show_logs() {
    local old_counts=($1)
    local patterns="($2|$3|trying_llm_tier|fallback_handler_triggered|clarification_response_returned|query_timeout|validation_failed|step8_calling_api|step8_api_returned|query_processed_successfully|Parsing utterance|fallback_medium match|speak|Timeout waiting for response)"
    local i=0
    for f in "${FILES[@]}"; do
        local old=${old_counts[$i]}
        if [ -f "$f" ]; then
            echo "--- $f ---"
            tail -n +$((old + 1)) "$f" | grep -Ei "$patterns" || true
        fi
        i=$((i+1))
    done
}
# Q1
C1=($(get_counts))
echo "Q1 START"
curl -sS -X POST http://localhost:5000/query -H "Content-Type: application/json" -d '{"utterance":"forecast energy for tomorrow","session_id":"alias-forecast-001","user_id":"debug"}' --max-time 95 -w "\nHTTP_STATUS:%{http_code}\nTIME_TOTAL:%{time_total}\n"
show_logs "${C1[*]}" "alias-forecast-001" "forecast energy for tomorrow"
# Q2
C2=($(get_counts))
echo "Q2 START"
curl -sS -X POST http://localhost:5000/query -H "Content-Type: application/json" -d '{"text":"what is the powre of comprsor one","session_id":"trace-typo-002","user_id":"debug"}' --max-time 95 -w "\nHTTP_STATUS:%{http_code}\nTIME_TOTAL:%{time_total}\n"
show_logs "${C2[*]}" "trace-typo-002" "what is the powre of comprsor one"
# Q3
C3=($(get_counts))
echo "Q3 START"
curl -sS -X POST http://localhost:5000/query -H "Content-Type: application/json" -d '{"text":"which machines are using most electricity","session_id":"trace-ranking-002","user_id":"debug"}' --max-time 95 -w "\nHTTP_STATUS:%{http_code}\nTIME_TOTAL:%{time_total}\n"
show_logs "${C3[*]}" "trace-ranking-002" "which machines are using most electricity"
