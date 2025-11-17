"""
Test LLM pipeline end-to-end
Validates: Qwen3 Parser → Validator → EnMS API → Response
"""
import sys
import asyncio
from pathlib import Path

# Add skill to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.qwen3_parser import Qwen3Parser
from lib.validator import ENMSValidator
from lib.api_client import ENMSClient


# 20 Core Test Queries from test-questions.md
TEST_QUERIES = [
    # Easy - Energy queries
    "What's the power consumption of Compressor-1?",
    "How much energy did Boiler-1 use?",
    "Show me Conveyor-A energy",
    "HVAC-EU-North power",
    "Compressor-1 kwh",
    
    # Easy - Machine status
    "Is Boiler-1 running?",
    "What's the status of Compressor-1?",
    "Check HVAC-EU-North",
    
    # Medium - Time-based
    "How much energy did Compressor-1 use in the last 24 hours?",
    "Boiler-1 consumption yesterday",
    "Show me Conveyor-A energy last week",
    
    # Medium - Comparisons
    "Compare Compressor-1 and Boiler-1",
    "Boiler vs Compressor",
    
    # Medium - Cost
    "What's the energy cost today?",
    "Energy cost for Compressor-1",
    
    # Challenge - Factory-wide
    "Show me factory overview",
    "Total factory consumption",
    
    # Challenge - Top consumers
    "top 3",
    "top 5 machines",
    "which machine uses most energy?",
]


async def test_pipeline():
    """Test full LLM pipeline"""
    
    print("=" * 80)
    print("LLM Pipeline Test - Week 1 Days 5-7")
    print("=" * 80)
    
    # Initialize components
    print("\n[1] Initializing components...")
    model_path = Path(__file__).parent.parent / "models" / "Qwen_Qwen3-1.7B-Q4_K_M.gguf"
    parser = Qwen3Parser(model_path=str(model_path))
    validator = ENMSValidator(confidence_threshold=0.85)
    api_client = ENMSClient(base_url="http://10.33.10.109:8001/api/v1")
    
    # Refresh machine whitelist
    print("[2] Refreshing machine whitelist from EnMS API...")
    machines = await api_client.list_machines(is_active=True)
    machine_names = [m["name"] for m in machines]
    validator.update_machine_whitelist(machine_names)
    print(f"✓ Loaded {len(machine_names)} machines: {', '.join(machine_names[:3])}...")
    
    # Test queries
    print(f"\n[3] Testing {len(TEST_QUERIES)} queries...\n")
    
    passed = 0
    failed = 0
    
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\nQuery #{i}: \"{query}\"")
        print("-" * 80)
        
        try:
            # Tier 1: LLM Parse
            llm_output = parser.parse(query)
            llm_output["utterance"] = query
            
            print(f"  LLM Output: intent={llm_output.get('intent')}, "
                  f"conf={llm_output.get('confidence', 0):.2f}, "
                  f"entities={llm_output.get('entities')}")
            
            # Tier 2: Validate
            validation = validator.validate(llm_output)
            
            if not validation.valid:
                print(f"  ❌ VALIDATION FAILED:")
                for error in validation.errors:
                    print(f"     - {error}")
                if validation.suggestions:
                    for suggestion in validation.suggestions:
                        print(f"     💡 {suggestion}")
                failed += 1
                continue
            
            intent = validation.intent
            print(f"  ✅ VALIDATED: {intent.intent.value} (conf={intent.confidence:.2f})")
            
            # Tier 3: API Call (simple test - just fetch machine status)
            if intent.machine:
                result = await api_client.get_machine_status(intent.machine)
                power = result["current_status"]["power_kw"]
                energy = result["today_stats"]["energy_kwh"]
                print(f"  📊 API Result: power={power:.1f}kW, energy={energy:.1f}kWh")
            
            # Tier 4: Response (simplified - full templates in Week 2)
            print(f"  💬 Response: [Placeholder - templates in Week 2]")
            
            passed += 1
            print(f"  ✅ PASSED")
            
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # Summary
    print("\n" + "=" * 80)
    print(f"TEST SUMMARY: {passed}/{len(TEST_QUERIES)} passed ({passed/len(TEST_QUERIES)*100:.1f}%)")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print("=" * 80)
    
    await api_client.close()
    
    return passed == len(TEST_QUERIES)


if __name__ == "__main__":
    success = asyncio.run(test_pipeline())
    sys.exit(0 if success else 1)
