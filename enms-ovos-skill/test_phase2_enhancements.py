#!/usr/bin/env python3
"""
Test script for Phase 2.1 (Multi-Machine Extraction) and Phase 2.3 (Metric Intelligence)
"""

import sys
sys.path.insert(0, '/home/ubuntu/ovos-llm/enms-ovos-skill')

from enms_ovos_skill.lib.intent_parser import HeuristicRouter

def test_phase2_1_multi_machine():
    """Test Phase 2.1: Multi-Machine Extraction"""
    print("\n" + "="*60)
    print("PHASE 2.1: Multi-Machine Extraction Tests")
    print("="*60)
    
    router = HeuristicRouter()
    
    test_cases = [
        # Individual machine pairs
        ("compare Compressor-1 and Boiler-1", ["Compressor-1", "Boiler-1"]),
        ("Compressor one vs HVAC Main", ["Compressor-1", "HVAC-Main"]),
        
        # Group patterns
        ("compare all compressors", ["Compressor-1", "Compressor-EU-1"]),
        ("all HVAC units", ["HVAC-Main", "HVAC-EU-North"]),
        ("both compressors", ["Compressor-1", "Compressor-EU-1"]),
        
        # Edge case: all machines
        ("compare all machines", router.MACHINES),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_machines in test_cases:
        print(f"\nTest: \"{query}\"")
        
        # Test group extraction
        group_machines = router._extract_machine_groups(query)
        if group_machines:
            machines = group_machines
            method = "group extraction"
        else:
            machines = router._extract_multiple_machines(query)
            method = "individual extraction"
        
        print(f"  Method: {method}")
        print(f"  Expected: {expected_machines}")
        print(f"  Got: {machines}")
        
        if set(machines) == set(expected_machines):
            print("  ✅ PASS")
            passed += 1
        else:
            print("  ❌ FAIL")
            failed += 1
    
    print(f"\n📊 Phase 2.1 Results: {passed} passed, {failed} failed")
    return passed, failed


def test_phase2_3_metric_intelligence():
    """Test Phase 2.3: Metric Intelligence"""
    print("\n" + "="*60)
    print("PHASE 2.3: Metric Intelligence Tests")
    print("="*60)
    
    router = HeuristicRouter()
    
    test_cases = [
        # Cost queries
        ("How much did Compressor-1 cost today?", "cost"),
        ("What's the energy bill for HVAC-Main?", "cost"),
        ("Show me spending for Boiler-1", "cost"),
        
        # Power queries (instantaneous)
        ("What's the current draw?", "power"),
        ("Show me power for Compressor-1 right now", "power"),
        ("HVAC Main watts currently", "power"),
        
        # Energy queries (cumulative)
        ("Total energy consumption today", "energy"),
        ("How much kWh did Compressor-1 use?", "energy"),
        ("Cumulative consumption for HVAC-Main", "energy"),
        
        # Efficiency queries
        ("What's the efficiency of Compressor-1?", "efficiency"),
        ("Show performance score for Boiler-1", "efficiency"),
        
        # Production queries
        ("How many units did Machine-1 produce?", "production"),
        ("What's the OEE for Compressor-1?", "production"),
        
        # Alert queries
        ("Show me alerts for HVAC-Main", "alerts"),
        ("Are there any anomalies?", "alerts"),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_metric in test_cases:
        print(f"\nTest: \"{query}\"")
        
        # Infer metric
        metric = router._infer_metric(query, 'energy_query')  # Default intent type
        
        print(f"  Expected: {expected_metric}")
        print(f"  Got: {metric}")
        
        if metric == expected_metric:
            print("  ✅ PASS")
            passed += 1
        else:
            print("  ❌ FAIL")
            failed += 1
    
    print(f"\n📊 Phase 2.3 Results: {passed} passed, {failed} failed")
    return passed, failed


def test_phase2_integration():
    """Test integration: Both Phase 2.1 and 2.3 together"""
    print("\n" + "="*60)
    print("PHASE 2 INTEGRATION: Multi-Machine + Metric Intelligence")
    print("="*60)
    
    router = HeuristicRouter()
    
    test_cases = [
        {
            'query': "compare energy cost for all compressors",
            'expected_machines': ["Compressor-1", "Compressor-EU-1"],
            'expected_metric': "cost"
        },
        {
            'query': "compare all HVAC units power consumption",
            'expected_machines': ["HVAC-Main", "HVAC-EU-North"],
            'expected_metric': "power"
        },
        {
            'query': "which compressor is more efficient?",
            'expected_machines': ["Compressor-1", "Compressor-EU-1"],
            'expected_metric': "efficiency"
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        query = test['query']
        print(f"\nTest: \"{query}\"")
        
        # Extract machines
        machines = router._extract_machine_groups(query) or router._extract_multiple_machines(query)
        
        # Infer metric
        metric = router._infer_metric(query, 'comparison')
        
        print(f"  Expected Machines: {test['expected_machines']}")
        print(f"  Got Machines: {machines}")
        print(f"  Expected Metric: {test['expected_metric']}")
        print(f"  Got Metric: {metric}")
        
        if set(machines) == set(test['expected_machines']) and metric == test['expected_metric']:
            print("  ✅ PASS")
            passed += 1
        else:
            print("  ❌ FAIL")
            failed += 1
    
    print(f"\n📊 Integration Results: {passed} passed, {failed} failed")
    return passed, failed


if __name__ == "__main__":
    print("\n🚀 Testing Phase 2 Enhancements (2.1 + 2.3)")
    print("="*60)
    
    # Run all tests
    p21_pass, p21_fail = test_phase2_1_multi_machine()
    p23_pass, p23_fail = test_phase2_3_metric_intelligence()
    int_pass, int_fail = test_phase2_integration()
    
    # Summary
    total_pass = p21_pass + p23_pass + int_pass
    total_fail = p21_fail + p23_fail + int_fail
    total_tests = total_pass + total_fail
    
    print("\n" + "="*60)
    print(f"FINAL RESULTS: {total_pass}/{total_tests} tests passed ({total_pass/total_tests*100:.1f}%)")
    print("="*60)
    
    if total_fail == 0:
        print("✅ All tests passed! Phase 2.1 and 2.3 working correctly.")
        sys.exit(0)
    else:
        print(f"❌ {total_fail} tests failed. Review implementation.")
        sys.exit(1)
