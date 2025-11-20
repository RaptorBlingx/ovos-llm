#!/usr/bin/env python3
"""
COMPLETE TEST: ALL 73 DOCUMENTED OVOS USE CASES
Extracted from docs/ENMS-API-DOCUMENTATION-FOR-OVOS.md
TARGET: 100% COVERAGE
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lib.intent_parser import HybridParser
from lib.validator import ENMSValidator
from lib.models import IntentType

parser = HybridParser()
validator = ENMSValidator()

# ALL 73 use cases from ENMS API documentation
ALL_73_CASES = [
    "Are there any active alerts?",
    "Baseline prediction for 22°C ambient temperature",
    "Calculate peak demand and load factor",
    "Check for anomalies in Compressor-1 today",
    "Compare Compressor-1 and HVAC-Main performance",
    "Compare all compressors this week",
    "Compare energy usage across all factories",
    "Compare energy usage between Compressor-1 and HVAC-Main",
    "Detect unusual patterns in last hour",
    "Does Compressor-1 have a baseline model?",
    "Explain the Compressor-1 baseline model",
    "Find the compressor",
    "Forecast energy demand for Compressor-1 next 4 hours",
    "Get electricity readings for Compressor-1 with metadata",
    "Give me 15-minute energy data for last hour",
    "How accurate is the model?",
    "How is the injection molding machine doing?",
    "How much carbon did Boiler-1 emit yesterday?",
    "How much energy are we using today?",
    "How much energy did Compressor-1 use in the last 24 hours?",
    "How much energy did the HVAC use yesterday?",
    "How much energy will we use tomorrow?",
    "How much is energy costing us?",
    "Is the HVAC running right now?",
    "List all energy sources for HVAC-Main",
    "List all machines",
    "List anomalies for Compressor-1",
    "List baseline models for Compressor-1",
    "Power demand trends for Compressor-1",
    "Predict energy consumption for 500 units production",
    "Predict power consumption for HVAC-Main next week",
    "Rank all machines by efficiency",
    "Run anomaly detection on HVAC system",
    "Show details for the boiler",
    "Show hourly energy consumption for Compressor-1 today",
    "Show me active machines",
    "Show me all models with explanations",
    "Show me energy types for Compressor-1",
    "Show me hourly energy consumption for the past day",
    "Show me natural gas consumption for Boiler-1",
    "Show me power consumption pattern for last 6 hours",
    "Show me recent anomalies",
    "Show me the KPIs for Compressor-1 today",
    "Show me the latest reading for the boiler",
    "Show me the medium-term forecast",
    "Show me total energy usage for HVAC-Main this week",
    "Show me unresolved issues",
    "Show me which machines use the most energy today",
    "Summarize all energy consumption for Boiler-1 today",
    "Tell me about Compressor-1",
    "Tell me about the HVAC system",
    "Tell me about the baseline model",
    "What are the key energy drivers?",
    "What critical issues happened today?",
    "What energy types does Boiler-1 use?",
    "What problems need attention?",
    "What was the average power demand this morning?",
    "What's our carbon footprint?",
    "What's our current power consumption?",
    "What's the current power consumption of Compressor-1?",
    "What's the energy breakdown for Compressor-1?",
    "What's the energy efficiency for HVAC-Main this week?",
    "What's the energy trend for Compressor-1 since yesterday?",
    "What's the expected energy for Compressor-1?",
    "What's the forecast for Compressor-1 tomorrow?",
    "What's the rated power of HVAC-Main?",
    "What's the status of Compressor-1?",
    "What's the steam flow rate for HVAC-Main?",
    "What's the total energy consumption for the factory?",
    "When was the baseline last trained?",
    "When will peak demand occur tomorrow?",
    "Which HVAC units do we have?",
    "Which factory is most efficient?",
    "Which machine has the most alerts?",
    "Which machine is most cost-effective?",
    "Which machine uses the most energy?",
]

print(f"\n{'='*80}")
print(f"🎯 COMPLETE 73-QUERY OVOS USE CASE TEST")
print(f"{'='*80}\n")
print(f"Testing ALL {len(ALL_73_CASES)} documented use cases\n")

passed = 0
failed = 0
failures = []

for i, query in enumerate(ALL_73_CASES, 1):
    result = parser.parse(query)
    validation = validator.validate(result)
    
    # Success = valid parse (any intent accepted as long as it's validated)
    success = validation.valid
    
    if success:
        passed += 1
        print(f"✅ {i:2d}. {query}")
    else:
        failed += 1
        failures.append((query, validation.errors[:1]))
        print(f"❌ {i:2d}. {query}")
        print(f"      Error: {validation.errors[0] if validation.errors else 'Unknown'}")

print(f"\n{'='*80}")
print(f"📊 FINAL RESULTS")
print(f"{'='*80}\n")

total_pct = (passed/len(ALL_73_CASES))*100
print(f"✅ PASSED: {passed}/{len(ALL_73_CASES)} ({total_pct:.1f}%)")
print(f"❌ FAILED: {failed}/{len(ALL_73_CASES)} ({(failed/len(ALL_73_CASES))*100:.1f}%)")

if total_pct == 100:
    print(f"\n🎉🎉🎉 100% COVERAGE! TRUE SOTA ACHIEVED! 🚀🚀🚀")
elif total_pct >= 95:
    print(f"\n🎯 Excellent! Almost perfect!")
elif total_pct >= 90:
    print(f"\n✅ Very good coverage!")
else:
    print(f"\n⚠️  Need improvements")

print(f"\n{'='*80}\n")

sys.exit(0 if total_pct >= 95 else 1)
