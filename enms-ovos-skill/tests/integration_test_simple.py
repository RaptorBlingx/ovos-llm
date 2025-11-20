#!/usr/bin/env python3
"""
Simplified Integration Test - Days 38-39
Tests actual functionality without tier expectations
"""
import sys
import os
import time
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lib.intent_parser import HybridParser
from lib.validator import ENMSValidator
from lib.models import IntentType


def test_queries():
    """Test representative queries from each category"""
    
    parser = HybridParser()
    validator = ENMSValidator()
    
    test_cases = [
        # (query, expected_intent, should_have_machine)
        ("Boiler-1 power", IntentType.POWER_QUERY, True),
        ("top 3", IntentType.RANKING, False),
        ("factory overview", IntentType.FACTORY_OVERVIEW, False),
        ("Is Compressor-1 running?", IntentType.MACHINE_STATUS, True),
        ("Compare Compressor-1 and Boiler-1", IntentType.COMPARISON, False),
        ("What's the power of HVAC-Main?", IntentType.POWER_QUERY, True),
        ("Compressor-1 kwh", IntentType.ENERGY_QUERY, True),
        ("total kwh", IntentType.FACTORY_OVERVIEW, False),
        ("How much energy did Boiler-1 use yesterday?", IntentType.ENERGY_QUERY, True),
        ("show me top 5", IntentType.RANKING, False),
    ]
    
    passed = 0
    failed = 0
    latencies = []
    tier_distribution = defaultdict(int)
    
    print(f"\n{'='*70}")
    print(f"🧪 INTEGRATION TEST - Days 38-39")
    print(f"{'='*70}\n")
    
    for query, expected_intent, should_have_machine in test_cases:
        start = time.time()
        
        # Parse
        result = parser.parse(query)
        tier = result.get('tier', 'unknown')
        tier_distribution[tier] += 1
        
        # Validate
        validation = validator.validate(result)
        
        latency_ms = (time.time() - start) * 1000
        latencies.append(latency_ms)
        
        # Check results
        success = validation.valid and validation.intent.intent == expected_intent
        
        if should_have_machine:
            success = success and validation.intent.machine is not None
        
        # Display
        status = "✅" if success else "❌"
        tier_emoji = "⚡" if tier == "heuristic" else "🟦" if tier == "adapt" else "🧠"
        
        print(f"{status} [{tier_emoji} {tier:10s}] {latency_ms:6.1f}ms | {query[:50]:50s}")
        
        if validation.valid:
            print(f"   → Intent: {validation.intent.intent.value}, Machine: {validation.intent.machine}")
        else:
            print(f"   → INVALID: {validation.errors}")
        
        if success:
            passed += 1
        else:
            failed += 1
    
    # Statistics
    print(f"\n{'-'*70}")
    print(f"📊 RESULTS:")
    print(f"   ✅ Passed: {passed}/{len(test_cases)} ({(passed/len(test_cases))*100:.1f}%)")
    print(f"   ❌ Failed: {failed}/{len(test_cases)} ({(failed/len(test_cases))*100:.1f}%)")
    
    print(f"\n📈 LATENCY:")
    print(f"   P50: {sorted(latencies)[len(latencies)//2]:.1f}ms")
    print(f"   P90: {sorted(latencies)[int(len(latencies)*0.9)]:.1f}ms")
    print(f"   P99: {sorted(latencies)[int(len(latencies)*0.99)]:.1f}ms")
    print(f"   Avg: {sum(latencies)/len(latencies):.1f}ms")
    
    print(f"\n🎯 TIER DISTRIBUTION:")
    for tier, count in sorted(tier_distribution.items()):
        pct = (count / len(test_cases)) * 100
        print(f"   {tier:10s}: {count:2d} ({pct:5.1f}%)")
    
    print(f"\n{'-'*70}\n")
    
    # Success criteria
    success_rate = (passed / len(test_cases)) * 100
    p50_latency = sorted(latencies)[len(latencies)//2]
    
    if success_rate >= 90 and p50_latency < 200:
        print(f"✅ INTEGRATION TEST PASSED!")
        print(f"   Success Rate: {success_rate:.1f}% (target: 90%+)")
        print(f"   P50 Latency: {p50_latency:.1f}ms (target: <200ms)")
        return 0
    else:
        print(f"⚠️  INTEGRATION TEST NEEDS IMPROVEMENT")
        print(f"   Success Rate: {success_rate:.1f}% (target: 90%+)")
        print(f"   P50 Latency: {p50_latency:.1f}ms (target: <200ms)")
        return 1


if __name__ == "__main__":
    sys.exit(test_queries())
