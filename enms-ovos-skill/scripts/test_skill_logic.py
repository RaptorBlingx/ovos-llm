#!/usr/bin/env python3
"""
Direct Test - Calls the skill pipeline directly without instantiating OVOSSkill
Tests the CORE processing logic: _call_enms_api() and _format_response()
"""
import sys
import asyncio
from pathlib import Path

skill_dir = Path(__file__).parent.parent
sys.path.insert(0, str(skill_dir))

from lib.intent_parser import HybridParser
from lib.validator import ENMSValidator  
from lib.api_client import ENMSClient
from lib.response_formatter import ResponseFormatter
from lib.models import Intent, IntentType
import requests


async def test_full_pipeline(query_text):
    """Test full pipeline matching __init__.py logic"""
    
    print("=" * 80)
    print(f"🔍 Testing Query: \"{query_text}\"")
    print("=" * 80)
    
    # Step 1: Parse (same as skill)
    print("\n[STEP 1] Parsing...")
    parser = HybridParser()
    parse_result = parser.parse(query_text)
    parse_result['utterance'] = query_text
    print(f"  Intent: {parse_result.get('intent')}")
    print(f"  Confidence: {parse_result.get('confidence')}")
    
    # Step 2: Validate (same as skill)
    print("\n[STEP 2] Validating...")
    validator = ENMSValidator(confidence_threshold=0.85)
    
    # Load machines
    machines_resp = requests.get("http://10.33.10.109:8001/api/v1/machines?is_active=true")
    machines = machines_resp.json()
    machine_names = [m["name"] for m in machines]
    validator.update_machine_whitelist(machine_names)
    
    validation = validator.validate(parse_result)
    if not validation.valid:
        print(f"  ❌ Validation failed: {validation.errors}")
        return
    
    intent = validation.intent
    print(f"  ✅ Valid - Intent: {intent.intent.value}, Machine: {intent.machine}")
    
    # Step 3: Call API (using __init__.py logic)
    print("\n[STEP 3] Calling EnMS API (using skill logic from __init__.py)...")
    api_client = ENMSClient(base_url="http://10.33.10.109:8001/api/v1")
    
    # This is COPIED from __init__.py _call_enms_api() method (lines 372-492)
    api_data = None
    
    if intent.intent == IntentType.FACTORY_OVERVIEW:
        # Check if this is a health/status check vs stats query  
        utterance = query_text.lower()
        health_keywords = ['online', 'health', 'status of', 'system status', 'running']
        
        if any(keyword in utterance for keyword in health_keywords):
            # Health check endpoint
            print("  → Calling /health (health check detected)")
            data = await api_client.health_check()
            api_data = data
        else:
            # System stats endpoint
            print("  → Calling /stats/system (system stats)")
            data = await api_client.system_stats()
            api_data = data
            
    elif intent.intent == IntentType.MACHINE_STATUS and intent.machine:
        print(f"  → Calling /machines/status/{intent.machine}")
        data = await api_client.get_machine_status(intent.machine)
        api_data = data
        
    elif intent.intent == IntentType.ENERGY_QUERY:
        if intent.machine:
            print(f"  → Calling /machines/status/{intent.machine} (energy for specific machine)")
            data = await api_client.get_machine_status(intent.machine)
            api_data = data
        else:
            print("  → Calling /stats/system (factory-wide energy)")
            data = await api_client.system_stats()
            api_data = data
            
    elif intent.intent == IntentType.POWER_QUERY:
        if intent.machine:
            print(f"  → Calling /machines/status/{intent.machine} (power for specific machine)")
            data = await api_client.get_machine_status(intent.machine)
            api_data = data
        else:
            print("  → Calling /stats/system (factory-wide power)")
            data = await api_client.system_stats()
            api_data = data
            
    elif intent.intent == IntentType.COST_ANALYSIS:
        print("  → Calling /stats/system (cost analysis)")
        data = await api_client.system_stats()
        api_data = data
    
    if api_data:
        print(f"  ✅ API returned data")
        print(f"     Keys: {list(api_data.keys())[:10]}")
    else:
        print(f"  ⚠️  No API data (intent {intent.intent.value} not handled)")
        return
    
    # Step 4: Format Response (using __init__.py logic - EXACT copy lines 547-577)
    print("\n[STEP 4] Formatting response (using EXACT skill logic from __init__.py)...")
    formatter = ResponseFormatter()
    
    # COPIED EXACTLY from __init__.py _format_response() method (lines 547-577)
    try:
        # Special handling for health check responses within factory_overview
        if intent.intent == IntentType.FACTORY_OVERVIEW and 'status' in api_data and 'database' in api_data:
            # This is a health check response, use health_check template
            print("  → Detected health check response, using health_check.dialog template")
            template_data = {
                'status': api_data.get('status'),
                'active_machines': api_data.get('active_machines', 0),
                'baseline_models': api_data.get('baseline_models', 0),
                'database': api_data.get('database', {})
            }
            # Manually render health_check template
            template = formatter.env.get_template('health_check.dialog')
            response_text = template.render(**template_data).strip()
        else:
            print(f"  → Using standard formatter for intent: {intent.intent.value}")
            response_text = formatter.format_response(
                intent_type=intent.intent.value,
                api_data=api_data,
                context={"machine_name": intent.machine} if intent.machine else {}
            )
    except Exception as e:
        print(f"  ❌ Formatting error: {e}")
        response_text = "Error formatting response"
    
    print(f"\n{'=' * 80}")
    print("FINAL RESPONSE (from REAL skill logic):")
    print(f"{'=' * 80}")
    print(response_text)
    print(f"{'=' * 80}\n")
    
    return response_text


if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "Is the energy system online?"
    
    asyncio.run(test_full_pipeline(query))
