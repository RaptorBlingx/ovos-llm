#!/usr/bin/env python3
"""
Interactive Chat Tester - REAL Skill Testing
Tests the ACTUAL skill logic from __init__.py in an interactive terminal chat

Usage:
    python3 scripts/test_skill_chat.py
    
Then type queries one at a time. Press Ctrl+C to exit and restart to test updates.
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


class SkillChatTester:
    """Interactive chat tester for REAL skill"""
    
    def __init__(self):
        """Initialize skill components"""
        print("\n" + "="*80)
        print("🤖 EnMS OVOS Skill - Interactive Chat Tester")
        print("="*80)
        print("Testing REAL skill logic from __init__.py")
        print("\nInitializing components...")
        
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Initialize real components
        self.parser = HybridParser()
        self.validator = ENMSValidator(confidence_threshold=0.85)
        self.api_client = ENMSClient(base_url="http://10.33.10.109:8001/api/v1")
        self.formatter = ResponseFormatter()
        
        # Load machine whitelist
        machines = self.loop.run_until_complete(self.api_client.list_machines(is_active=True))
        machine_names = [m["name"] for m in machines]
        self.validator.update_machine_whitelist(machine_names)
        
        print(f"✅ Loaded {len(machine_names)} machines")
        print("\n" + "="*80)
        print("Ready! Type your queries below. Press Ctrl+C to exit.")
        print("="*80 + "\n")
    
    async def process_query(self, query_text):
        """Process query through REAL skill pipeline"""
        
        print(f"\n{'─'*80}")
        print(f"You: {query_text}")
        print(f"{'─'*80}")
        
        try:
            # Step 1: Parse
            parse_result = self.parser.parse(query_text)
            parse_result['utterance'] = query_text
            
            print(f"[Parse] Intent: {parse_result.get('intent')} (confidence: {parse_result.get('confidence'):.2f})")
            
            # Step 2: Validate
            validation = self.validator.validate(parse_result)
            
            if not validation.valid:
                print(f"[Validate] ❌ {' '.join(validation.errors)}")
                print(f"\nSkill: I couldn't understand that. {validation.errors[0]}")
                return
            
            intent = validation.intent
            print(f"[Validate] ✅ Intent: {intent.intent.value}, Machine: {intent.machine}")
            
            # Step 3: Call API (using EXACT __init__.py logic)
            api_data = await self._call_api(intent, query_text)
            
            if not api_data:
                print(f"[API] ⚠️  No data returned")
                print(f"\nSkill: I couldn't retrieve that information.")
                return
            
            print(f"[API] ✅ Data retrieved")
            
            # Step 4: Format Response (using EXACT __init__.py logic)
            response = self._format_response(intent, api_data)
            
            print(f"\n{'─'*80}")
            print(f"Skill: {response}")
            print(f"{'─'*80}\n")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    async def _call_api(self, intent: Intent, utterance: str):
        """Call API using EXACT logic from __init__.py lines 372-492"""
        
        if intent.intent == IntentType.FACTORY_OVERVIEW:
            # Check if this is a health/status check vs stats query  
            utterance_lower = utterance.lower()
            health_keywords = ['online', 'health', 'status of', 'system status', 'running']
            
            if any(keyword in utterance_lower for keyword in health_keywords):
                print(f"[API] Calling /health")
                data = await self.api_client.health_check()
                return data
            else:
                print(f"[API] Calling /stats/system")
                data = await self.api_client.system_stats()
                return data
                
        elif intent.intent == IntentType.MACHINE_STATUS and intent.machine:
            print(f"[API] Calling /machines/status/{intent.machine}")
            data = await self.api_client.get_machine_status(intent.machine)
            return data
            
        elif intent.intent == IntentType.ENERGY_QUERY:
            if intent.machine:
                print(f"[API] Calling /machines/status/{intent.machine}")
                data = await self.api_client.get_machine_status(intent.machine)
                return data
            else:
                print(f"[API] Calling /stats/system")
                data = await self.api_client.system_stats()
                return data
                
        elif intent.intent == IntentType.POWER_QUERY:
            if intent.machine:
                print(f"[API] Calling /machines/status/{intent.machine}")
                data = await self.api_client.get_machine_status(intent.machine)
                return data
            else:
                print(f"[API] Calling /stats/system")
                data = await self.api_client.system_stats()
                return data
        
        elif intent.intent == IntentType.RANKING:
            limit = intent.limit or 5
            print(f"[API] Calling /analytics/top-consumers (limit={limit})")
            data = await self.api_client.get_top_consumers(limit=limit)
            return data
        
        elif intent.intent == IntentType.COST_ANALYSIS:
            print(f"[API] Calling /stats/system")
            data = await self.api_client.system_stats()
            return data
        
        else:
            print(f"[API] ⚠️  Intent '{intent.intent.value}' not yet implemented")
            return None
    
    def _format_response(self, intent: Intent, api_data: dict) -> str:
        """Format response using EXACT logic from __init__.py lines 547-577"""
        
        try:
            # Special handling for health check responses within factory_overview
            if intent.intent == IntentType.FACTORY_OVERVIEW and 'status' in api_data and 'database' in api_data:
                print(f"[Format] Using health_check.dialog")
                template_data = {
                    'status': api_data.get('status'),
                    'active_machines': api_data.get('active_machines', 0),
                    'baseline_models': api_data.get('baseline_models', 0),
                    'database': api_data.get('database', {})
                }
                template = self.formatter.env.get_template('health_check.dialog')
                return template.render(**template_data).strip()
            
            print(f"[Format] Using {intent.intent.value}.dialog")
            return self.formatter.format_response(
                intent_type=intent.intent.value,
                api_data=api_data,
                context={"machine_name": intent.machine} if intent.machine else {}
            )
        except Exception as e:
            print(f"[Format] ❌ Template error: {e}")
            # Fallback to simple response
            if intent.intent == IntentType.MACHINE_STATUS and 'machine_name' in api_data:
                status = api_data.get('current_status', {})
                return f"{api_data['machine_name']} is {status.get('status', 'unknown')}"
            elif intent.intent == IntentType.POWER_QUERY and 'current_status' in api_data:
                power = api_data['current_status'].get('power_kw', 0)
                return f"Current power consumption is {power:.1f} kilowatts"
            else:
                return "I found the information you requested. Please check the screen for details."
    
    def run(self):
        """Run interactive chat loop"""
        try:
            while True:
                # Get user input
                query = input("You: ").strip()
                
                if not query:
                    continue
                
                if query.lower() in ['exit', 'quit', 'bye']:
                    print("\nGoodbye! 👋\n")
                    break
                
                # Process query
                self.loop.run_until_complete(self.process_query(query))
                
        except KeyboardInterrupt:
            print("\n\nExiting... 👋\n")
        except EOFError:
            print("\n\nExiting... 👋\n")


if __name__ == "__main__":
    tester = SkillChatTester()
    tester.run()
