#!/usr/bin/env python3
"""
Single Query Tester - Synchronous version for 1by1.md testing
Tests: Parser → Validator → API → Formatter (all real components)
"""
import sys
import requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.intent_parser import HybridParser
from lib.validator import ENMSValidator
from lib.response_formatter import ResponseFormatter

def test_query(query_text):
    """Test a single query through the pipeline"""
    
    print("=" * 80)
    print(f"🔍 Testing: \"{query_text}\"")
    print("=" * 80)
    
    # Step 1: Parse
    print("\n[STEP 1] Parsing with HybridParser...")
    parser = HybridParser()
    parse_result = parser.parse(query_text)
    
    print(f"  Intent: {parse_result.get('intent')}")
    print(f"  Confidence: {parse_result.get('confidence', 0):.2f}")
    print(f"  Entities: {parse_result.get('entities', {})}")
    
    # Step 2: Validate
    print("\n[STEP 2] Validating...")
    validator = ENMSValidator(confidence_threshold=0.6)
    
    # Load machine whitelist from API
    try:
        response = requests.get("http://10.33.10.109:8001/api/v1/machines?is_active=true", timeout=5)
        machines = response.json()
        machine_names = [m["name"] for m in machines]
        validator.update_machine_whitelist(machine_names)
        print(f"  ✅ Loaded {len(machine_names)} machines")
    except Exception as e:
        print(f"  ⚠️  Could not load machines: {e}")
    
    validation_result = validator.validate(parse_result)
    
    if not validation_result.valid:
        print(f"  ❌ INVALID: {validation_result.errors}")
        return False
    
    print(f"  ✅ Valid - Intent: {validation_result.intent.intent}")
    print(f"     Machine: {validation_result.intent.machine}")
    
    # Step 3: Call API (simplified - direct HTTP)
    print("\n[STEP 3] Calling EnMS API...")
    
    intent = validation_result.intent.intent.value
    machine = validation_result.intent.machine
    
    # Map intent to API endpoint
    api_data = None
    api_endpoint = None
    template_name = None  # Override template if needed
    
    if intent == "factory_overview":
        # Factory overview can call /health or /stats/system depending on query
        # For "Is the system online?" type queries, use /health
        # For detailed stats, use /stats/system
        
        # Check if this is a health/status check query
        utterance_lower = parse_result.get('utterance', '').lower()
        is_health_check = any(word in utterance_lower for word in ['online', 'health', 'status of', 'working'])
        
        if is_health_check or not machine:
            # Use health endpoint
            api_endpoint = "/health"
            template_name = "health_check"  # Override to use health_check.dialog
            try:
                response = requests.get("http://10.33.10.109:8001/api/v1/health", timeout=5)
                api_data = response.json()
                print(f"  ✅ API Response (Health Check):")
                print(f"     Status: {api_data.get('status')}")
                print(f"     Active Machines: {api_data.get('active_machines')}")
                print(f"     Baseline Models: {api_data.get('baseline_models')}")
            except Exception as e:
                print(f"  ❌ API Error: {e}")
                return False
        else:
            # Use stats/system endpoint for detailed overview
            api_endpoint = "/stats/system"
            try:
                response = requests.get("http://10.33.10.109:8001/api/v1/stats/system", timeout=5)
                api_data = response.json()
                print(f"  ✅ API Response (System Stats):")
                print(f"     Total Energy: {api_data.get('total_energy')} kWh")
                print(f"     Active Machines: {api_data.get('active_machines_today')}")
            except Exception as e:
                print(f"  ❌ API Error: {e}")
                return False
    
    elif intent == "ranking":
        # Ranking queries like "How many machines are active?"
        # Should call /health or /stats/system
        api_endpoint = "/health"
        template_name = "health_check"
        try:
            response = requests.get("http://10.33.10.109:8001/api/v1/health", timeout=5)
            api_data = response.json()
            print(f"  ✅ API Response (Health Check for Ranking):")
            print(f"     Active Machines: {api_data.get('active_machines')}")
        except Exception as e:
            print(f"  ❌ API Error: {e}")
            return False
    
    elif intent == "machine_status" and machine:
        api_endpoint = f"/machines/status/{machine}"
        try:
            response = requests.get(f"http://10.33.10.109:8001/api/v1/machines/status/{machine}", timeout=5)
            if response.status_code == 200:
                api_data = response.json()
                print(f"  ✅ API Response (Machine Status):")
                print(f"     Machine: {api_data.get('machine_name')}")
                print(f"     Status: {api_data.get('current_status', {}).get('status')}")
                print(f"     Power: {api_data.get('current_status', {}).get('power_kw')} kW")
            else:
                print(f"  ❌ API returned {response.status_code}")
                return False
        except Exception as e:
            print(f"  ❌ API Error: {e}")
            return False
    
    else:
        print(f"  ⚠️  Intent '{intent}' not yet implemented in test script")
        print(f"     (Add implementation for this intent)")
        return False
    
    # Step 4: Format Response
    print("\n[STEP 4] Formatting response using templates...")
    
    formatter = ResponseFormatter()
    
    try:
        # Use formatter.format_response (not format)
        # Use template override if specified, otherwise use intent name
        final_intent = template_name if template_name else intent
        
        response_text = formatter.format_response(
            intent_type=final_intent,
            api_data=api_data,
            context={"machine_name": machine} if machine else {}
        )
        
        print(f"  ✅ Response formatted successfully")
        print(f"\n{'=' * 80}")
        print("FINAL RESPONSE (would be spoken):")
        print(f"{'=' * 80}")
        print(response_text)
        print(f"{'=' * 80}\n")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Formatting Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "Is the energy system online?"
    
    success = test_query(query)
    sys.exit(0 if success else 1)
