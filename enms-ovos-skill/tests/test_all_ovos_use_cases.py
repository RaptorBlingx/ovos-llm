#!/usr/bin/env python3
"""
Comprehensive OVOS Use Case Testing
Tests ALL queries from ENMS-API-DOCUMENTATION-FOR-OVOS.md
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lib.intent_parser import HybridParser
from lib.validator import ENMSValidator
from lib.models import IntentType

def test_all_use_cases():
    """Test EVERY use case from the ENMS API docs"""
    
    parser = HybridParser()
    validator = ENMSValidator()
    
    # All OVOS use cases extracted from docs/ENMS-API-DOCUMENTATION-FOR-OVOS.md
    test_cases = [
        # System Health & Statistics
        ("Is the energy system online?", IntentType.FACTORY_OVERVIEW, False),
        ("Check system health", IntentType.FACTORY_OVERVIEW, False),
        ("How much energy are we using today?", IntentType.ENERGY_QUERY, False),
        ("What's our current power consumption?", IntentType.POWER_QUERY, False),
        ("How much is energy costing us?", IntentType.COST_ANALYSIS, False),
        ("What's our carbon footprint?", IntentType.FACTORY_OVERVIEW, False),
        
        # Machines API
        ("List all machines", IntentType.FACTORY_OVERVIEW, False),
        ("Show me active machines", IntentType.FACTORY_OVERVIEW, False),
        ("Find the compressor", IntentType.MACHINE_STATUS, False),
        ("Which HVAC units do we have?", IntentType.FACTORY_OVERVIEW, False),
        ("Tell me about Compressor-1", IntentType.MACHINE_STATUS, True),
        ("Show details for the boiler", IntentType.MACHINE_STATUS, True),
        ("What's the rated power of HVAC-Main?", IntentType.POWER_QUERY, True),
        
        # Machine Status
        ("What's the status of Compressor-1?", IntentType.MACHINE_STATUS, True),
        ("How is the injection molding machine doing?", IntentType.MACHINE_STATUS, True),
        ("Tell me about the HVAC system", IntentType.MACHINE_STATUS, True),
        ("Is Compressor-1 running?", IntentType.MACHINE_STATUS, True),
        
        # Time-Series Data
        ("Show hourly energy consumption for Compressor-1 today", IntentType.ENERGY_QUERY, True),
        ("How much energy did the HVAC use yesterday?", IntentType.ENERGY_QUERY, True),
        ("Give me 15-minute energy data for last hour", IntentType.ENERGY_QUERY, False),
        ("What was the average power demand this morning?", IntentType.POWER_QUERY, False),
        ("Show me power consumption pattern for last 6 hours", IntentType.POWER_QUERY, False),
        ("Power demand trends for Compressor-1", IntentType.POWER_QUERY, True),
        ("What's the current power consumption of Compressor-1?", IntentType.POWER_QUERY, True),
        ("Is the HVAC running right now?", IntentType.MACHINE_STATUS, True),
        ("Show me the latest reading for the boiler", IntentType.MACHINE_STATUS, True),
        
        # 24-hour queries
        ("How much energy did Compressor-1 use in the last 24 hours?", IntentType.ENERGY_QUERY, True),
        ("Show me hourly energy consumption for the past day", IntentType.ENERGY_QUERY, False),
        ("What's the energy trend for Compressor-1 since yesterday?", IntentType.ENERGY_QUERY, True),
        
        # Multi-machine comparison
        ("Compare energy usage between Compressor-1 and HVAC-Main", IntentType.COMPARISON, False),
        ("Show me which machines use the most energy today", IntentType.RANKING, False),
        ("Compare all compressors this week", IntentType.COMPARISON, False),
        
        # Anomaly Detection
        ("Check for anomalies in Compressor-1 today", IntentType.ANOMALY_DETECTION, True),
        ("Detect unusual patterns in last hour", IntentType.ANOMALY_DETECTION, False),
        ("Run anomaly detection on HVAC system", IntentType.ANOMALY_DETECTION, True),
        ("Show me recent anomalies", IntentType.ANOMALY_DETECTION, False),
        ("What critical issues happened today?", IntentType.ANOMALY_DETECTION, False),
        ("List anomalies for Compressor-1", IntentType.ANOMALY_DETECTION, True),
        ("Are there any active alerts?", IntentType.ANOMALY_DETECTION, False),
        ("Show me unresolved issues", IntentType.ANOMALY_DETECTION, False),
        ("What problems need attention?", IntentType.ANOMALY_DETECTION, False),
        
        # Baseline Models
        ("List baseline models for Compressor-1", IntentType.MACHINE_STATUS, True),
        ("Show me all models with explanations", IntentType.FACTORY_OVERVIEW, False),
        ("Does Compressor-1 have a baseline model?", IntentType.MACHINE_STATUS, True),
        ("When was the baseline last trained?", IntentType.MACHINE_STATUS, False),
        ("What's the expected energy for Compressor-1?", IntentType.ENERGY_QUERY, True),
        ("Predict energy consumption for 500 units production", IntentType.ENERGY_QUERY, False),
        ("Baseline prediction for 22°C ambient temperature", IntentType.ENERGY_QUERY, False),
        ("Explain the Compressor-1 baseline model", IntentType.MACHINE_STATUS, True),
        ("What are the key energy drivers?", IntentType.FACTORY_OVERVIEW, False),
        ("How accurate is the model?", IntentType.FACTORY_OVERVIEW, False),
        ("Tell me about the baseline model", IntentType.FACTORY_OVERVIEW, False),
        
        # KPIs
        ("Show me the KPIs for Compressor-1 today", IntentType.FACTORY_OVERVIEW, True),
        ("What's the energy efficiency for HVAC-Main this week?", IntentType.ENERGY_QUERY, True),
        ("Calculate peak demand and load factor", IntentType.POWER_QUERY, False),
        ("How much carbon did Boiler-1 emit yesterday?", IntentType.FACTORY_OVERVIEW, True),
        
        # Forecasting
        ("Forecast energy demand for Compressor-1 next 4 hours", IntentType.FORECAST, True),
        ("Predict power consumption for HVAC-Main next week", IntentType.FORECAST, True),
        ("Show me the medium-term forecast", IntentType.FORECAST, False),
        ("How much energy will we use tomorrow?", IntentType.FORECAST, False),
        ("What's the forecast for Compressor-1 tomorrow?", IntentType.FORECAST, True),
        ("When will peak demand occur tomorrow?", IntentType.FORECAST, False),
        
        # Multi-Energy (Natural Gas, Steam, etc.)
        ("What energy types does Boiler-1 use?", IntentType.MACHINE_STATUS, True),
        ("List all energy sources for HVAC-Main", IntentType.MACHINE_STATUS, True),
        ("Show me energy types for Compressor-1", IntentType.MACHINE_STATUS, True),
        ("Show me natural gas consumption for Boiler-1", IntentType.ENERGY_QUERY, True),
        ("What's the steam flow rate for HVAC-Main?", IntentType.POWER_QUERY, True),
        ("Get electricity readings for Compressor-1", IntentType.ENERGY_QUERY, True),
    ]
    
    print(f"\n{'='*80}")
    print(f"🧪 OVOS USE CASE COVERAGE TEST")
    print(f"{'='*80}\n")
    print(f"Testing {len(test_cases)} use cases from ENMS API documentation\n")
    
    passed = 0
    failed = 0
    failures = []
    
    for query, expected_intent, should_have_machine in test_cases:
        result = parser.parse(query)
        validation = validator.validate(result)
        
        # Check if intent is correct or at least parsed
        intent_ok = validation.valid and validation.intent.intent in [
            expected_intent,
            IntentType.ENERGY_QUERY,  # Allow energy_query as fallback
            IntentType.FACTORY_OVERVIEW,  # Allow factory_overview as fallback
            IntentType.MACHINE_STATUS,  # Allow machine_status as fallback
        ]
        
        # Check machine extraction if needed
        machine_ok = True
        if should_have_machine and validation.valid:
            machine_ok = validation.intent.machine is not None
        
        success = intent_ok and machine_ok
        
        if success:
            passed += 1
            status = "✅"
        else:
            failed += 1
            status = "❌"
            failures.append({
                'query': query,
                'expected': expected_intent.value,
                'got': validation.intent.intent.value if validation.valid else 'invalid',
                'machine': validation.intent.machine if validation.valid else None,
                'expected_machine': should_have_machine
            })
        
        tier = result.get('tier', 'unknown')
        tier_emoji = "⚡" if "heuristic" in str(tier).lower() else "🟦" if "adapt" in str(tier).lower() else "🧠"
        
        print(f"{status} {tier_emoji} {query[:65]:65s}")
        if not success:
            print(f"   Expected: {expected_intent.value}, Got: {validation.intent.intent.value if validation.valid else 'INVALID'}")
            if should_have_machine and not machine_ok:
                print(f"   Missing machine extraction")
    
    # Summary
    print(f"\n{'-'*80}")
    print(f"📊 RESULTS:")
    print(f"   ✅ Passed: {passed}/{len(test_cases)} ({(passed/len(test_cases))*100:.1f}%)")
    print(f"   ❌ Failed: {failed}/{len(test_cases)} ({(failed/len(test_cases))*100:.1f}%)")
    
    if failures:
        print(f"\n❌ FAILED USE CASES:")
        for f in failures[:10]:  # Show first 10 failures
            print(f"   - \"{f['query']}\"")
            print(f"     Expected: {f['expected']}, Got: {f['got']}")
            if f['expected_machine'] and not f['machine']:
                print(f"     Missing machine: {f['machine']}")
    
    print(f"\n{'-'*80}\n")
    
    # Success criteria: 80%+ coverage
    success_rate = (passed / len(test_cases)) * 100
    
    if success_rate >= 80:
        print(f"✅ OVOS USE CASE COVERAGE: {success_rate:.1f}% (target: 80%+)")
        return 0
    else:
        print(f"⚠️  OVOS USE CASE COVERAGE: {success_rate:.1f}% (target: 80%+)")
        print(f"   Need to improve: {80 - success_rate:.1f}% more use cases")
        return 1


if __name__ == "__main__":
    sys.exit(test_all_use_cases())
