#!/bin/bash
run_query() {
    local q="$1"
    echo "--- BENCHMARK QUERY: $q ---"
    resp=\$(mktemp)
    curl_out=\$(curl -sS --max-time 30 -o "\$resp" -w 'HTTP:%{http_code} TIME:%{time_total}' -X POST http://localhost:5000/query -H 'Content-Type: application/json' -d "{\"text\":\"\$q\"}")
    echo "Output: \$curl_out"
    cat "\$resp"
    echo -e "\nLogs snippet:"
    docker exec ovos-enms grep -A 30 "Parsing utterance: \['\$q'\]" /var/log/ovos/skills.log | grep -E "Parsing utterance|fallback_medium match|trying_llm_tier|clarification_needed|llm_tier_failed|Intent Match|match" | tail -n 5
    rm "\$resp"
    echo ""
}
run_query "compare this week to last week"
run_query "forecast energy for tomorrow"
run_query "what is the powre of comprsor one"
run_query "is boilar one onlne"
run_query "which machines are using most electricity"
