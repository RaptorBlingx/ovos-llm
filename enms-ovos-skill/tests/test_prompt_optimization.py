"""
Week 2 Days 8-10: Prompt Optimization Testing
Test LLM accuracy on representative queries to guide prompt refinement
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.qwen3_parser import Qwen3Parser
from lib.validator import ENMSValidator

# Representative test queries (faster than full 20-query suite)
TEST_QUERIES = {
    # Easy queries (should be 95%+ accuracy)
    "easy": [
        ("What's the power of Compressor-1?", "power_query", "Compressor-1"),
        ("Boiler-1 energy", "energy_query", "Boiler-1"),
        ("Is HVAC-EU-North running?", "machine_status", "HVAC-EU-North"),
    ],
    
    # Medium queries (should be 90%+ accuracy)
    "medium": [
        ("Show me top 5 energy consumers", "ranking", None),
        ("Compare Compressor-1 and Boiler-1", "comparison", None),
        ("Factory overview", "factory_overview", None),
    ],
    
    # Challenge queries (should be 85%+ accuracy)  
    "challenge": [
        ("How much did Compressor-1 use yesterday?", "energy_query", "Compressor-1"),
        ("Any anomalies detected?", "anomaly_detection", None),
    ]
}


async def test_prompt_accuracy():
    """Test accuracy of current prompt on representative queries"""
    
    print("=" * 80)
    print("Week 2: Prompt Optimization Testing")
    print("=" * 80)
    
    parser = Qwen3Parser()
    
    results = {"easy": [], "medium": [], "challenge": []}
    
    for difficulty, queries in TEST_QUERIES.items():
        print(f"\n[{difficulty.upper()}] Testing {len(queries)} queries...")
        
        for query, expected_intent, expected_machine in queries:
            print(f"\nQuery: \"{query}\"")
            print(f"Expected: {expected_intent}, machine={expected_machine}")
            
            result = parser.parse(query)
            
            # Check accuracy
            intent_correct = result.get("intent") == expected_intent
            machine_correct = (expected_machine is None or 
                              result.get("entities", {}).get("machine") == expected_machine)
            
            accuracy = intent_correct and machine_correct
            
            print(f"Got: {result.get('intent')}, machine={result.get('entities', {}).get('machine')}")
            print(f"Confidence: {result.get('confidence')}")
            print(f"✓ PASS" if accuracy else "❌ FAIL")
            
            results[difficulty].append({
                "query": query,
                "expected": expected_intent,
                "actual": result.get("intent"),
                "confidence": result.get("confidence"),
                "correct": accuracy
            })
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    for difficulty, res in results.items():
        total = len(res)
        correct = sum(1 for r in res if r["correct"])
        accuracy = (correct / total * 100) if total > 0 else 0
        
        print(f"\n{difficulty.upper()}: {correct}/{total} ({accuracy:.1f}%)")
        
        # Show failures
        failures = [r for r in res if not r["correct"]]
        if failures:
            print("  Failures:")
            for f in failures:
                print(f"    - \"{f['query']}\"")
                print(f"      Expected: {f['expected']}, Got: {f['actual']}")
    
    overall_correct = sum(len([r for r in res if r["correct"]]) for res in results.values())
    overall_total = sum(len(res) for res in results.values())
    overall_accuracy = (overall_correct / overall_total * 100) if overall_total > 0 else 0
    
    print(f"\nOVERALL: {overall_correct}/{overall_total} ({overall_accuracy:.1f}%)")
    print(f"Target: 90%+ accuracy")
    print(f"Status: {'✓ PASS' if overall_accuracy >= 90 else '❌ NEEDS IMPROVEMENT'}")


if __name__ == "__main__":
    asyncio.run(test_prompt_accuracy())
