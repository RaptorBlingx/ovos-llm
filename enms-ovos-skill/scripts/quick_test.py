"""
Quick End-to-End Test
Verify LLM → Validator → API → Response pipeline before GUI testing
"""
import sys
import asyncio
import argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.qwen3_parser import Qwen3Parser
from lib.validator import ENMSValidator
from lib.api_client import ENMSClient
from lib.response_formatter import ResponseFormatter


async def test_pipeline(query=None):
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
    
    # Test query (use CLI arg if provided, else default)
    if query is None:
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
    
    print(f"  ✅ Valid - Intent: {validation.intent.intent}")
    if validation.intent.machine:
        print(f"     Machine: {validation.intent.machine}")
    
    # Tier 3: API Call (depends on intent type)
    print("\n[Tier 3] Calling EnMS API...")
    
    intent_type = validation.intent.intent
    if intent_type == "factory_overview":
        # Check if health check or stats
        if any(kw in query.lower() for kw in ['online', 'health', 'status']):
            result = await api_client.health_check()
            api_data = {
                'status': result.get('status'),
                'active_machines': result.get('active_machines'),
                'baseline_models': result.get('baseline_models'),
                'database': result.get('database')
            }
            print(f"  ✅ API Response (Health Check):")
            print(f"     Status: {api_data['status']}")
            print(f"     Active Machines: {api_data['active_machines']}")
            print(f"     Baseline Models: {api_data['baseline_models']}")
        else:
            result = await api_client.system_stats()
            api_data = {
                'total_energy': result.get('total_energy'),
                'active_machines': result.get('active_machines_today'),
                'estimated_cost': result.get('estimated_cost')
            }
            print(f"  ✅ API Response (System Stats):")
            print(f"     Total Energy: {api_data['total_energy']:.2f} kWh")
            print(f"     Cost: ${api_data['estimated_cost']:.2f}")
    
    elif intent_type == "energy_query" or intent_type == "power_query":
        if validation.intent.machine:
            # Machine-specific query
            result = await api_client.get_machine_status(validation.intent.machine)
            api_data = {
                'machine': validation.intent.machine,
                'status': result['current_status']['status'],
                'power_kw': result['current_status']['power_kw'],
                'energy_kwh': result['today_stats']['energy_kwh'],
                'cost_usd': result['today_stats']['cost_usd']
            }
            print(f"  ✅ API Response (Machine Status):")
            print(f"     Machine: {api_data['machine']}")
            print(f"     Status: {api_data['status']}")
            print(f"     Power: {api_data['power_kw']:.2f} kW")
            print(f"     Energy: {api_data['energy_kwh']:.2f} kWh")
        else:
            # Factory-wide energy/power query
            result = await api_client.system_stats()
            api_data = {
                'total_energy': result.get('total_energy'),
                'peak_power': result.get('peak_power'),
                'avg_power': result.get('avg_power'),
                'estimated_cost': result.get('estimated_cost')
            }
            print(f"  ✅ API Response (Factory Stats - {intent_type}):")
            print(f"     Total Energy: {api_data['total_energy']:.2f} kWh")
            print(f"     Peak Power: {api_data['peak_power']:.2f} kW")
            print(f"     Avg Power: {api_data['avg_power']:.2f} kW")
    
    elif validation.intent.machine:
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
    else:
        print(f"  ⚠️  Intent {intent_type} not fully implemented in test script")
        api_data = {}
    
    # Tier 4: Format Response (using actual ResponseFormatter)
    print("\n[Tier 4] Formatting response using templates...")
    
    if api_data:
        print(f"  ✅ Data retrieved successfully")
        
        # Use ResponseFormatter exactly like the skill does
        try:
            # Special handling for health check (matches skill's _format_response)
            if intent_type == "factory_overview" and 'status' in api_data and 'database' in api_data:
                # Health check - use health_check template
                template = formatter.env.get_template('health_check.dialog')
                response = template.render(**api_data).strip()
                print(f"  📄 Template used: health_check.dialog")
            else:
                # Use ResponseFormatter.format() for all other intents
                response = formatter.format(validation.intent, api_data)
                print(f"  📄 Template used: {intent_type}.dialog")
            
            print("\n" + "=" * 80)
            print("FINAL RESPONSE (would be spoken):")
            print("=" * 80)
            print(f"\n{response}\n")
            print("=" * 80)
            print("\n✅ PIPELINE TEST: SUCCESS!")
            print("=" * 80)
            
        except Exception as e:
            print(f"  ❌ Template formatting failed: {e}")
            print(f"  API Data: {api_data}")
            import traceback
            traceback.print_exc()
    else:
        print("  ⚠️  No API data to format")
    
    await api_client.close()


if __name__ == "__main__":
    parser_cli = argparse.ArgumentParser(description="Test EnMS OVOS pipeline")
    parser_cli.add_argument("--query", "-q", type=str, help="Query to test")
    args = parser_cli.parse_args()
    
    asyncio.run(test_pipeline(query=args.query))
