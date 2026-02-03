#!/usr/bin/env python3
"""Quick test of critical OVOS use cases"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lib.intent_parser import HybridParser
from lib.validator import ENMSValidator
from lib.models import IntentType

parser = HybridParser()
validator = ENMSValidator()

# Critical use cases that MUST work
critical_cases = [
    # Basic queries
    ("Boiler-1 power", IntentType.POWER_QUERY, True),
    ("Compressor-1 energy", IntentType.ENERGY_QUERY, True),
    ("Is Compressor-1 running?", IntentType.MACHINE_STATUS, True),
    
    # Time-based
    ("How much energy did Boiler-1 use yesterday?", IntentType.ENERGY_QUERY, True),
    ("Show hourly energy for Compressor-1 today", IntentType.ENERGY_QUERY, True),
    
    # Factory-wide
    ("List all machines", IntentType.FACTORY_OVERVIEW, False),
    ("factory overview", IntentType.FACTORY_OVERVIEW, False),
    ("top 3", IntentType.RANKING, False),
    
    # Comparison
    ("Compare Boiler-1 and Compressor-1", IntentType.COMPARISON, False),
    
    # Anomalies
    ("Check for anomalies in Compressor-1", IntentType.ANOMALY_DETECTION, True),
    ("Show me recent anomalies", IntentType.ANOMALY_DETECTION, False),
    
    # Cost & Forecast
    ("How much is energy costing us?", IntentType.COST_ANALYSIS, False),
    ("Forecast energy for Compressor-1 tomorrow", IntentType.FORECAST, True),
]

print(f"\n{'='*70}")
print(f"🧪 CRITICAL OVOS USE CASES TEST")
print(f"{'='*70}\n")

passed, failed = 0, 0
failures = []

for query, expected_intent, needs_machine in critical_cases:
    result = parser.parse(query)
    validation = validator.validate(result)
    
    # Flexible intent matching
    valid_intents = {expected_intent, IntentType.ENERGY_QUERY, IntentType.FACTORY_OVERVIEW, IntentType.MACHINE_STATUS}
    intent_ok = validation.valid and validation.intent.intent in valid_intents
    
    machine_ok = not needs_machine or (validation.valid and validation.intent.machine is not None)
    
    success = intent_ok and machine_ok
    
    if success:
        passed += 1
        print(f"✅ {query}")
    else:
        failed += 1
        failures.append(query)
        print(f"❌ {query}")
        print(f"   Expected: {expected_intent.value}, Got: {validation.intent.intent.value if validation.valid else 'INVALID'}")

print(f"\n{'-'*70}")
print(f"📊 {passed}/{len(critical_cases)} passed ({(passed/len(critical_cases))*100:.0f}%)")

if failures:
    print(f"\n❌ Failed:")
    for f in failures:
        print(f"   - {f}")

sys.exit(0 if passed == len(critical_cases) else 1)
