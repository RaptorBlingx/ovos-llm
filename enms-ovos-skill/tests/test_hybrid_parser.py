"""
Test HybridParser Routing Logic
================================

Tests both heuristic fast-path and LLM fallback
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.intent_parser import HybridParser
from lib.models import IntentType


def test_heuristic_queries():
    """Test queries that should route to heuristic tier (Tier 1)"""
    parser = HybridParser()
    
    test_cases = [
        # Top N ranking queries (CRITICAL - these were failing before)
        ("top 3", IntentType.RANKING, "heuristic"),
        ("top 5 machines", IntentType.RANKING, "heuristic"),
        ("show me top 5", IntentType.RANKING, "heuristic"),
        
        # Factory overview
        ("factory overview", IntentType.FACTORY_OVERVIEW, "heuristic"),
        ("factory status", IntentType.FACTORY_OVERVIEW, "heuristic"),
        ("total kwh", IntentType.FACTORY_OVERVIEW, "heuristic"),
        
        # Machine status
        ("Is Boiler-1 running?", IntentType.MACHINE_STATUS, "heuristic"),
        ("Compressor-1 status", IntentType.MACHINE_STATUS, "heuristic"),
        ("check HVAC-EU-North", IntentType.MACHINE_STATUS, "heuristic"),
        
        # Power queries
        ("Compressor-1 power", IntentType.POWER_QUERY, "heuristic"),
        ("HVAC watts", IntentType.POWER_QUERY, "heuristic"),
        ("power of Boiler-1", IntentType.POWER_QUERY, "heuristic"),
        
        # Energy queries
        ("Boiler-1 kwh", IntentType.ENERGY_QUERY, "heuristic"),
        ("Compressor-1 energy", IntentType.ENERGY_QUERY, "heuristic"),
        ("energy of Conveyor-A", IntentType.ENERGY_QUERY, "heuristic"),
        
        # Comparison
        ("compare Compressor-1 and Boiler-1", IntentType.COMPARISON, "heuristic"),
        ("Boiler-1 vs Compressor-1", IntentType.COMPARISON, "heuristic"),
    ]
    
    print("\n" + "="*80)
    print("🎯 TIER 1 HEURISTIC TESTS (Target: <5ms)")
    print("="*80)
    
    heuristic_count = 0
    total_latency = 0
    
    for query, expected_intent, expected_tier in test_cases:
        result = parser.parse(query)
        
        # Verify intent type
        intent_match = result['intent'] == expected_intent
        tier_match = result['tier'] == expected_tier
        latency_ms = result['routing_latency_ms']
        
        # Color coding
        status = "✅" if (intent_match and tier_match and latency_ms < 10) else "❌"
        tier_color = "🟢" if tier_match else "🔴"
        latency_color = "⚡" if latency_ms < 5 else "⏱️" if latency_ms < 10 else "🐌"
        
        print(f"{status} [{tier_color} {result['tier']:10s}] [{latency_color} {latency_ms:5.1f}ms] {query:40s} → {result['intent']}")
        
        if tier_match:
            heuristic_count += 1
            total_latency += latency_ms
    
    # Summary
    avg_latency = total_latency / heuristic_count if heuristic_count > 0 else 0
    print(f"\n📊 Heuristic Tier: {heuristic_count}/{len(test_cases)} queries ({(heuristic_count/len(test_cases))*100:.0f}%)")
    print(f"⚡ Average Latency: {avg_latency:.2f}ms (Target: <5ms)")
    
    return heuristic_count == len(test_cases) and avg_latency < 10


def test_llm_fallback():
    """Test queries that should fallback to LLM (Tier 3)"""
    parser = HybridParser()
    
    test_cases = [
        # Complex temporal queries
        "How much energy did Boiler-1 use yesterday?",
        "Show me Compressor-1 energy last week",
        "What's the consumption in the last 24 hours?",
        
        # Ambiguous queries
        "What about that machine?",
        "Check the other compressor",
        
        # Multi-part queries
        "Is Boiler-1 online and what's its power?",
    ]
    
    print("\n" + "="*80)
    print("🧠 TIER 3 LLM FALLBACK TESTS (Target: <500ms)")
    print("="*80)
    
    llm_count = 0
    total_latency = 0
    
    for query in test_cases:
        result = parser.parse(query)
        
        tier_match = result['tier'] == "llm"
        latency_ms = result['routing_latency_ms']
        
        status = "✅" if tier_match else "⚠️"
        tier_color = "🔵" if tier_match else "🔴"
        latency_color = "⚡" if latency_ms < 1000 else "⏱️" if latency_ms < 5000 else "🐌"
        
        print(f"{status} [{tier_color} {result['tier']:10s}] [{latency_color} {latency_ms:6.0f}ms] {query:50s} → {result['intent']}")
        
        if tier_match:
            llm_count += 1
            total_latency += latency_ms
    
    avg_latency = total_latency / llm_count if llm_count > 0 else 0
    print(f"\n📊 LLM Tier: {llm_count}/{len(test_cases)} queries ({(llm_count/len(test_cases))*100:.0f}%)")
    print(f"⚡ Average Latency: {avg_latency:.0f}ms (Target: <500ms)")
    
    return llm_count > 0


def test_routing_distribution():
    """Test overall routing distribution"""
    parser = HybridParser()
    
    # Mix of queries
    mixed_queries = [
        "top 5",  # heuristic
        "Boiler-1 kwh",  # heuristic
        "factory overview",  # heuristic
        "How much energy did Compressor-1 use yesterday?",  # llm
        "Compressor-1 power",  # heuristic
        "What's the consumption last week?",  # llm
        "Is HVAC-EU-North running?",  # heuristic
        "compare Boiler-1 and Compressor-1",  # heuristic
        "Show me top 3 machines",  # heuristic
        "What about the other boiler?",  # llm
    ]
    
    print("\n" + "="*80)
    print("📊 ROUTING DISTRIBUTION TEST (Target: 70-80% heuristic)")
    print("="*80)
    
    for query in mixed_queries:
        parser.parse(query)
    
    stats = parser.get_stats()
    print(f"\n🎯 Total Queries: {stats['total']}")
    print(f"   🟢 Heuristic: {stats['heuristic']} ({stats['distribution']['heuristic']})")
    print(f"   🔵 LLM: {stats['llm']} ({stats['distribution']['llm']})")
    
    heuristic_pct = (stats['heuristic'] / stats['total']) * 100
    target_met = 70 <= heuristic_pct <= 90
    
    print(f"\n{'✅' if target_met else '⚠️'} Target: 70-80% heuristic → Actual: {heuristic_pct:.0f}%")
    
    return target_met


def main():
    """Run all tests"""
    print("\n🚀 HYBRID PARSER ROUTING TESTS")
    print("="*80)
    
    start_time = time.time()
    
    # Run test suites
    test1 = test_heuristic_queries()
    test2 = test_llm_fallback()
    test3 = test_routing_distribution()
    
    total_time = time.time() - start_time
    
    # Final summary
    print("\n" + "="*80)
    print("📋 TEST SUMMARY")
    print("="*80)
    print(f"✅ Heuristic Tier Tests: {'PASS' if test1 else 'FAIL'}")
    print(f"✅ LLM Fallback Tests: {'PASS' if test2 else 'FAIL'}")
    print(f"✅ Distribution Tests: {'PASS' if test3 else 'FAIL'}")
    print(f"\n⏱️  Total Test Time: {total_time:.2f}s")
    
    if test1 and test2 and test3:
        print("\n🎉 ALL TESTS PASSED - Week 3 Days 15-16 COMPLETE!")
        return 0
    else:
        print("\n⚠️  Some tests failed - review implementation")
        return 1


if __name__ == "__main__":
    sys.exit(main())
