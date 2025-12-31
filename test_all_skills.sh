#!/bin/bash
# Comprehensive test of all OVOS voice query skills

echo "🧪 Testing All OVOS EnMS Skills"
echo "================================"
echo ""

test_query() {
    local category="$1"
    local query="$2"
    local expected_keyword="$3"
    
    echo "[$category] Testing: \"$query\""
    response=$(curl -s -X POST http://localhost:5000/query \
        -H "Content-Type: application/json" \
        -d "{\"text\":\"$query\"}" | jq -r '.response')
    
    if [[ "$response" == *"error"* ]]; then
        echo "  ❌ FAIL: $response"
        return 1
    elif [[ -n "$expected_keyword" ]] && [[ "$response" != *"$expected_keyword"* ]]; then
        echo "  ⚠️  UNEXPECTED: $response"
        return 1
    else
        echo "  ✅ PASS: ${response:0:80}..."
        return 0
    fi
    echo ""
}

passed=0
failed=0

# 1. Energy Queries
echo "=== 1. ENERGY QUERIES ==="
test_query "Energy" "what is the current energy consumption of Compressor-1?" "consumed" && ((passed++)) || ((failed++))
test_query "Energy" "energy consumption last 48 hours Compressor-1" "kWh" && ((passed++)) || ((failed++))
test_query "Energy" "how much energy did the factory use today?" "" && ((passed++)) || ((failed++))
echo ""

# 2. Machine Status
echo "=== 2. MACHINE STATUS ==="
test_query "Status" "what is the status of Compressor-1?" "status" && ((passed++)) || ((failed++))
test_query "Status" "is Compressor-1 running?" "" && ((passed++)) || ((failed++))
echo ""

# 3. Machine List
echo "=== 3. MACHINE LIST ==="
test_query "List" "list all machines" "machine" && ((passed++)) || ((failed++))
test_query "List" "show me all equipment" "" && ((passed++)) || ((failed++))
echo ""

# 4. KPI Queries
echo "=== 4. KPI QUERIES ==="
test_query "KPI" "what are the KPIs of Compressor-1?" "SEC\|kW\|load factor" && ((passed++)) || ((failed++))
test_query "KPI" "show me key performance indicators for Boiler-1" "" && ((passed++)) || ((failed++))
echo ""

# 5. Power Queries
echo "=== 5. POWER QUERIES ==="
test_query "Power" "what is the power consumption of Compressor-1?" "kilowatt\|kW" && ((passed++)) || ((failed++))
test_query "Power" "current power draw factory" "" && ((passed++)) || ((failed++))
echo ""

# 6. Factory Overview
echo "=== 6. FACTORY OVERVIEW ==="
test_query "Factory" "factory overview" "" && ((passed++)) || ((failed++))
test_query "Factory" "give me factory summary" "" && ((passed++)) || ((failed++))
echo ""

# 7. Anomaly Detection
echo "=== 7. ANOMALY DETECTION ==="
test_query "Anomaly" "any anomalies in Compressor-1?" "" && ((passed++)) || ((failed++))
test_query "Anomaly" "detect anomalies" "" && ((passed++)) || ((failed++))
echo ""

# 8. Baseline Queries
echo "=== 8. BASELINE PREDICTION ==="
test_query "Baseline" "what is the baseline for Compressor-1?" "" && ((passed++)) || ((failed++))
test_query "Baseline" "predict energy consumption Compressor-1" "" && ((passed++)) || ((failed++))
echo ""

# 9. Forecast
echo "=== 9. FORECAST ==="
test_query "Forecast" "forecast energy for tomorrow" "" && ((passed++)) || ((failed++))
echo ""

# 10. SEU Queries
echo "=== 10. SEU QUERIES ==="
test_query "SEU" "what are the significant energy users?" "" && ((passed++)) || ((failed++))
test_query "SEU" "show me SEUs" "" && ((passed++)) || ((failed++))
echo ""

# 11. Performance
echo "=== 11. PERFORMANCE ANALYSIS ==="
test_query "Performance" "analyze performance of Compressor-1" "" && ((passed++)) || ((failed++))
echo ""

# 12. Production
echo "=== 12. PRODUCTION QUERIES ==="
test_query "Production" "what is the production of Compressor-1 today?" "" && ((passed++)) || ((failed++))
echo ""

# 13. SEC (Specific Energy Consumption)
echo "=== 13. SEC QUERIES ==="
test_query "SEC" "what is the SEC of Compressor-1?" "" && ((passed++)) || ((failed++))
test_query "SEC" "specific energy consumption Boiler-1" "" && ((passed++)) || ((failed++))
echo ""

# 14. Load Factor
echo "=== 14. LOAD FACTOR ==="
test_query "LoadFactor" "what is the load factor of Compressor-1?" "" && ((passed++)) || ((failed++))
echo ""

# 15. Peak Demand
echo "=== 15. PEAK DEMAND ==="
test_query "PeakDemand" "what is the peak demand?" "" && ((passed++)) || ((failed++))
echo ""

# 16. Cost Analysis
echo "=== 16. COST ANALYSIS ==="
test_query "Cost" "how much did Compressor-1 cost today?" "" && ((passed++)) || ((failed++))
test_query "Cost" "energy cost analysis" "" && ((passed++)) || ((failed++))
echo ""

# 17. Ranking/Comparison
echo "=== 17. RANKING/COMPARISON ==="
test_query "Ranking" "rank machines by energy consumption" "" && ((passed++)) || ((failed++))
test_query "Comparison" "compare Compressor-1 with Boiler-1" "" && ((passed++)) || ((failed++))
echo ""

# 18. Report Generation
echo "=== 18. REPORT GENERATION ==="
test_query "Report" "generate December report" "Generating\|report" && ((passed++)) || ((failed++))
echo ""

# 19. System Health
echo "=== 19. SYSTEM HEALTH ==="
test_query "Health" "system health check" "healthy\|operational" && ((passed++)) || ((failed++))
echo ""

# 20. Help
echo "=== 20. HELP ==="
test_query "Help" "help" "" && ((passed++)) || ((failed++))
echo ""

# Summary
echo "================================"
echo "📊 TEST RESULTS"
echo "================================"
echo "✅ Passed: $passed"
echo "❌ Failed: $failed"
echo "📈 Success Rate: $(( passed * 100 / (passed + failed) ))%"
echo ""

if [ $failed -eq 0 ]; then
    echo "🎉 All tests passed!"
    exit 0
else
    echo "⚠️  Some tests failed. Check output above."
    exit 1
fi
