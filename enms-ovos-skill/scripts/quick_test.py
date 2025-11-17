"""
Quick End-to-End Test
Verify LLM → Validator → API → Response pipeline before GUI testing
"""
import sys
import asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.qwen3_parser import Qwen3Parser
from lib.validator import ENMSValidator
from lib.api_client import ENMSClient
from lib.response_formatter import ResponseFormatter


async def test_pipeline():
    """Test full pipeline with one query"""
    
    print("=" * 80)
    print("EnMS Pipeline Quick Test")
    print("=" * 80)
    
    # Initialize components
    print("\n[1/4] Loading LLM (Qwen3 1.7B)...")
    parser = Qwen3Parser()
    
    print("[2/4] Initializing validator...")
    validator = ENMSValidator(confidence_threshold=0.85)
    
    print("[3/4] Connecting to API...")
    api_client = ENMSClient(base_url="http://10.33.10.109:8001/api/v1")
    
    print("[4/4] Loading templates...")
    formatter = ResponseFormatter()
    
    # Load machine whitelist
    print("\n📋 Loading machines from API...")
    machines = await api_client.list_machines(is_active=True)
    machine_names = [m["name"] for m in machines]
    validator.update_machine_whitelist(machine_names)
    print(f"✅ Loaded {len(machine_names)} machines")
    
    # Test query
    query = "What's the power consumption of Compressor-1?"
    print(f"\n🔍 Testing query: \"{query}\"")
    print("-" * 80)
    
    # Tier 1: LLM Parse
    print("\n[Tier 1] LLM parsing...")
    llm_output = parser.parse(query)
    print(f"  Intent: {llm_output.get('intent')}")
    print(f"  Confidence: {llm_output.get('confidence'):.2f}")
    print(f"  Entities: {llm_output.get('entities')}")
    
    # Tier 2: Validate
    print("\n[Tier 2] Validating...")
    llm_output['utterance'] = query
    validation = validator.validate(llm_output)
    
    if not validation.valid:
        print(f"  ❌ Validation failed: {validation.errors}")
        return
    
    print(f"  ✅ Valid - Machine: {validation.intent.machine}")
    
    # Tier 3: API Call
    print("\n[Tier 3] Calling EnMS API...")
    result = await api_client.get_machine_status(validation.intent.machine)
    
    api_data = {
        'machine': validation.intent.machine,
        'status': result['current_status']['status'],
        'power_kw': result['current_status']['power_kw'],
        'energy_kwh': result['today_stats']['energy_kwh'],
        'cost_usd': result['today_stats']['cost_usd']
    }
    
    print(f"  ✅ API Response:")
    print(f"     Status: {api_data['status']}")
    print(f"     Power: {api_data['power_kw']:.2f} kW")
    print(f"     Energy: {api_data['energy_kwh']:.2f} kWh")
    print(f"     Cost: ${api_data['cost_usd']:.2f}")
    
    # Tier 4: Format Response
    print("\n[Tier 4] Formatting response...")
    response = formatter.format_response('power_query', api_data)
    
    print("\n" + "=" * 80)
    print("FINAL RESPONSE:")
    print("=" * 80)
    print(f"\n{response}\n")
    print("=" * 80)
    print("\n✅ PIPELINE TEST: SUCCESS!")
    print("=" * 80)
    
    await api_client.close()


if __name__ == "__main__":
    asyncio.run(test_pipeline())
