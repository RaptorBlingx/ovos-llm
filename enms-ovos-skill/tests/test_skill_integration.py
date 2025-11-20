#!/usr/bin/env python3
"""
END-TO-END SKILL INTEGRATION TEST
==================================

Tests the COMPLETE production skill pipeline:
1. HybridParser (Heuristic + Adapt + LLM)
2. Validator (Zero-trust)
3. API Client (Real EnMS calls)
4. Response Formatter (Jinja2 templates)
5. Conversation Context (Multi-turn)
6. Voice Feedback (Natural responses)
7. Metrics & Observability

This is the $100K test - validates production readiness.
"""

import sys
import os
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.intent_parser import HybridParser, RoutingTier
from lib.validator import ENMSValidator
from lib.api_client import ENMSClient
from lib.response_formatter import ResponseFormatter
from lib.conversation_context import ConversationContextManager
from lib.voice_feedback import VoiceFeedbackManager
from lib.models import IntentType


# ANSI colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
MAGENTA = '\033[95m'
RESET = '\033[0m'
BOLD = '\033[1m'


class SkillIntegrationTest:
    """End-to-end skill integration tester"""
    
    def __init__(self, api_base_url: str = "http://10.33.10.109:8001/api/v1"):
        """Initialize all skill components"""
        print(f"{BOLD}{CYAN}=" * 80)
        print("🚀 END-TO-END SKILL INTEGRATION TEST")
        print(f"{'=' * 80}{RESET}\n")
        
        self.api_base_url = api_base_url
        
        # Initialize all components
        print(f"{BLUE}[1/6] Initializing HybridParser...{RESET}")
        self.parser = HybridParser()
        
        print(f"{BLUE}[2/6] Initializing Validator...{RESET}")
        self.validator = ENMSValidator(
            confidence_threshold=0.85,
            enable_fuzzy_matching=True
        )
        
        print(f"{BLUE}[3/6] Initializing API Client...{RESET}")
        self.api_client = ENMSClient(
            base_url=api_base_url,
            timeout=30
        )
        
        print(f"{BLUE}[4/6] Initializing Response Formatter...{RESET}")
        self.response_formatter = ResponseFormatter()
        
        print(f"{BLUE}[5/6] Initializing Conversation Context...{RESET}")
        self.context_manager = ConversationContextManager()
        
        print(f"{BLUE}[6/6] Initializing Voice Feedback...{RESET}")
        self.voice_feedback = VoiceFeedbackManager()
        
        # Statistics
        self.stats = {
            'total_queries': 0,
            'successful': 0,
            'failed': 0,
            'tier_heuristic': 0,
            'tier_adapt': 0,
            'tier_llm': 0,
            'total_latency_ms': 0,
            'api_calls': 0,
            'validation_failures': 0
        }
        
        print(f"{GREEN}✅ All components initialized successfully{RESET}\n")
    
    async def initialize_whitelist(self):
        """Load machine whitelist from API"""
        print(f"{BLUE}Loading machine whitelist from EnMS API...{RESET}")
        try:
            machines = await self.api_client.list_machines(is_active=True)
            machine_names = [m["name"] for m in machines]
            self.validator.update_machine_whitelist(machine_names)
            self.parser.heuristic.MACHINES = machine_names
            print(f"{GREEN}✅ Loaded {len(machine_names)} machines: {', '.join(machine_names)}{RESET}\n")
        except Exception as e:
            print(f"{RED}⚠️  Whitelist load failed: {e}{RESET}")
            print(f"{YELLOW}Using hardcoded machine list{RESET}\n")
    
    async def process_query(self, query: str, session_id: str = "test_session", 
                           expected_intent: str = None, print_details: bool = True) -> Dict[str, Any]:
        """
        Process a single query through the complete pipeline
        
        Returns:
            dict with: success, response, latency_ms, tier, intent, etc.
        """
        start_time = time.time()
        
        if print_details:
            print(f"{BOLD}{MAGENTA}{'─' * 80}")
            print(f"Query: {query}")
            print(f"{'─' * 80}{RESET}")
        
        try:
            # Step 1: Get conversation session
            session = self.context_manager.get_or_create_session(session_id)
            
            # Step 2: Parse with HybridParser
            parse_start = time.time()
            parse_result = self.parser.parse(query)
            parse_latency_ms = (time.time() - parse_start) * 1000
            
            tier = parse_result.get("tier", RoutingTier.HEURISTIC)
            # NOTE: parse_result IS the intent dict (not nested)
            llm_output = dict(parse_result)  # Copy the dict
            llm_output["utterance"] = query
            confidence = parse_result.get("confidence", 0)
            
            if print_details:
                print(f"{CYAN}├─ Tier: {BOLD}{tier.upper()}{RESET}{CYAN} (confidence: {confidence:.2f}){RESET}")
                print(f"{CYAN}├─ Parse latency: {parse_latency_ms:.2f}ms{RESET}")
            
            # Track tier
            if tier == RoutingTier.HEURISTIC:
                self.stats['tier_heuristic'] += 1
            elif tier == RoutingTier.ADAPT:
                self.stats['tier_adapt'] += 1
            else:
                self.stats['tier_llm'] += 1
            
            # Step 3: Validate
            validation_start = time.time()
            validation = self.validator.validate(llm_output)
            validation_latency_ms = (time.time() - validation_start) * 1000
            
            if not validation.valid:
                self.stats['validation_failures'] += 1
                error_msg = " ".join(validation.errors)
                if validation.suggestions:
                    error_msg += " " + validation.suggestions[0]
                
                if print_details:
                    print(f"{RED}├─ Validation FAILED: {error_msg}{RESET}")
                
                total_latency_ms = (time.time() - start_time) * 1000
                self.stats['total_latency_ms'] += total_latency_ms
                self.stats['failed'] += 1
                
                return {
                    'success': False,
                    'response': error_msg,
                    'latency_ms': round(total_latency_ms, 2),
                    'tier': tier,
                    'intent': None,
                    'error': error_msg
                }
            
            intent = validation.intent
            
            if print_details:
                print(f"{CYAN}├─ Intent: {intent.intent}{RESET}")
                if intent.machine:
                    print(f"{CYAN}├─ Machine: {intent.machine}{RESET}")
                if intent.machines:
                    print(f"{CYAN}├─ Machines: {', '.join(intent.machines)}{RESET}")
                if intent.limit:
                    print(f"{CYAN}├─ Limit: {intent.limit}{RESET}")
            
            # Step 4: Resolve context
            intent = self.context_manager.resolve_context_references(query, intent, session)
            
            # Step 5: Check clarification
            clarification = self.context_manager.needs_clarification(intent)
            if clarification:
                clarification_msg = self.context_manager.generate_clarification_response(intent, session)
                if print_details:
                    print(f"{YELLOW}├─ Clarification needed: {clarification}{RESET}")
                
                total_latency_ms = (time.time() - start_time) * 1000
                self.stats['total_latency_ms'] += total_latency_ms
                self.stats['failed'] += 1
                
                return {
                    'success': False,
                    'response': clarification_msg,
                    'latency_ms': round(total_latency_ms, 2),
                    'tier': tier,
                    'intent': intent.intent,
                    'clarification': clarification
                }
            
            # Step 6: Call EnMS API
            api_start = time.time()
            api_data = await self._call_api(intent)
            api_latency_ms = (time.time() - api_start) * 1000
            
            self.stats['api_calls'] += 1
            
            if print_details:
                print(f"{CYAN}├─ API latency: {api_latency_ms:.2f}ms{RESET}")
            
            if not api_data.get('success', False):
                if print_details:
                    print(f"{RED}├─ API call FAILED: {api_data.get('error')}{RESET}")
                
                total_latency_ms = (time.time() - start_time) * 1000
                self.stats['total_latency_ms'] += total_latency_ms
                self.stats['failed'] += 1
                
                return {
                    'success': False,
                    'response': api_data.get('error', 'API error'),
                    'latency_ms': round(total_latency_ms, 2),
                    'tier': tier,
                    'intent': intent.intent,
                    'error': api_data.get('error')
                }
            
            # Step 7: Format response
            format_start = time.time()
            response_text = self.response_formatter.format_response(intent.intent.value, api_data['data'])
            format_latency_ms = (time.time() - format_start) * 1000
            
            # Step 8: Update context
            session.add_turn(
                query=query,
                intent=intent,
                response=response_text,
                api_data=api_data['data']
            )
            
            # Step 9: Calculate total latency
            total_latency_ms = (time.time() - start_time) * 1000
            self.stats['total_latency_ms'] += total_latency_ms
            self.stats['successful'] += 1
            
            if print_details:
                print(f"{GREEN}├─ Response: {response_text[:100]}{'...' if len(response_text) > 100 else ''}{RESET}")
                print(f"{GREEN}├─ Total latency: {total_latency_ms:.2f}ms{RESET}")
                print(f"{GREEN}└─ ✅ SUCCESS{RESET}\n")
            
            return {
                'success': True,
                'response': response_text,
                'latency_ms': round(total_latency_ms, 2),
                'tier': tier,
                'intent': intent.intent,
                'machine': intent.machine,
                'breakdown': {
                    'parse_ms': round(parse_latency_ms, 2),
                    'validation_ms': round(validation_latency_ms, 2),
                    'api_ms': round(api_latency_ms, 2),
                    'format_ms': round(format_latency_ms, 2)
                }
            }
            
        except Exception as e:
            if print_details:
                import traceback
                print(f"{RED}├─ Exception: {e}{RESET}")
                print(f"{RED}├─ Traceback:{RESET}")
                traceback.print_exc()
                print(f"{RED}└─ ❌ FAILED{RESET}\n")
            
            total_latency_ms = (time.time() - start_time) * 1000
            self.stats['total_latency_ms'] += total_latency_ms
            self.stats['failed'] += 1
            
            return {
                'success': False,
                'response': str(e),
                'latency_ms': round(total_latency_ms, 2),
                'tier': None,
                'intent': None,
                'error': str(e)
            }
    
    async def _call_api(self, intent) -> Dict[str, Any]:
        """Call appropriate EnMS API based on intent"""
        try:
            if intent.intent == IntentType.MACHINE_STATUS and intent.machine:
                data = await self.api_client.get_machine_status(intent.machine)
                return {'success': True, 'data': data}
            
            elif intent.intent == IntentType.POWER_QUERY and intent.machine:
                data = await self.api_client.get_machine_status(intent.machine)
                return {'success': True, 'data': data}
            
            elif intent.intent == IntentType.ENERGY_QUERY and intent.machine:
                data = await self.api_client.get_machine_status(intent.machine)
                return {'success': True, 'data': data}
            
            elif intent.intent == IntentType.FACTORY_OVERVIEW:
                data = await self.api_client.get_factory_summary()
                return {'success': True, 'data': data}
            
            elif intent.intent == IntentType.RANKING:
                limit = intent.limit or 5
                data = await self.api_client.get_top_consumers(limit=limit)
                return {'success': True, 'data': data}
            
            elif intent.intent == IntentType.COMPARISON and intent.machines:
                machines_data = []
                for machine in intent.machines:
                    try:
                        m_data = await self.api_client.get_machine_status(machine)
                        machines_data.append(m_data)
                    except Exception as e:
                        print(f"{YELLOW}  Warning: {machine} failed - {e}{RESET}")
                
                return {'success': True, 'data': {'machines': machines_data, 'comparison': intent.machines}}
            
            elif intent.intent == IntentType.COST_QUERY:
                data = await self.api_client.get_factory_summary()
                return {'success': True, 'data': data}
            
            else:
                return {
                    'success': False,
                    'error': f"Intent {intent.intent} not yet implemented in API client"
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def test_quick_queries(self):
        """Test representative quick queries (heuristic tier)"""
        print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════")
        print("TEST 1: QUICK QUERIES (Heuristic Tier - Target <10ms)")
        print(f"═══════════════════════════════════════════════════════════════════════════════{RESET}\n")
        
        queries = [
            "top 5",
            "factory overview",
            "Compressor-1 status",
            "Boiler-1 power",
            "HVAC-Main energy",
            "compare Compressor-1 and Boiler-1"
        ]
        
        results = []
        for query in queries:
            result = await self.process_query(query, print_details=True)
            results.append(result)
            self.stats['total_queries'] += 1
        
        # Summary
        avg_latency = sum(r['latency_ms'] for r in results) / len(results)
        success_rate = sum(1 for r in results if r['success']) / len(results) * 100
        
        print(f"{BOLD}{CYAN}{'─' * 80}")
        print(f"Quick Queries Summary:")
        print(f"  Avg Latency: {avg_latency:.2f}ms")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Heuristic Coverage: {sum(1 for r in results if r.get('tier') == RoutingTier.HEURISTIC) / len(results) * 100:.1f}%")
        print(f"{'─' * 80}{RESET}\n")
    
    async def test_multi_turn_conversation(self):
        """Test multi-turn conversation context"""
        print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════")
        print("TEST 2: MULTI-TURN CONVERSATION")
        print(f"═══════════════════════════════════════════════════════════════════════════════{RESET}\n")
        
        session_id = "multi_turn_test"
        
        # Turn 1: Initial query
        print(f"{BOLD}Turn 1:{RESET}")
        result1 = await self.process_query("Compressor-1 power", session_id=session_id)
        self.stats['total_queries'] += 1
        
        # Turn 2: Follow-up (should use context)
        print(f"{BOLD}Turn 2 (Follow-up):{RESET}")
        result2 = await self.process_query("What about energy?", session_id=session_id)
        self.stats['total_queries'] += 1
        
        # Turn 3: Another machine
        print(f"{BOLD}Turn 3 (New machine):{RESET}")
        result3 = await self.process_query("What about Boiler-1?", session_id=session_id)
        self.stats['total_queries'] += 1
        
        print(f"{BOLD}{CYAN}{'─' * 80}")
        print(f"Multi-Turn Summary:")
        print(f"  Context resolution working: {result2['success'] and result3['success']}")
        print(f"{'─' * 80}{RESET}\n")
    
    async def test_stress_queries(self):
        """Test various query types for stress testing"""
        print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════════════════════════════════")
        print("TEST 3: STRESS TEST (Multiple Query Types)")
        print(f"═══════════════════════════════════════════════════════════════════════════════{RESET}\n")
        
        queries = [
            "Compressor-EU-1 consumption",
            "HVAC-EU-North status",
            "factory cost",
            "top 10 machines",
            "Boiler-1 vs Compressor-1",
            "total kwh",
            "show me factory overview",
            "highest 3",
            "Conveyor-A power"
        ]
        
        results = []
        for query in queries:
            result = await self.process_query(query, print_details=False)
            results.append(result)
            self.stats['total_queries'] += 1
            
            # Print compact result
            status = f"{GREEN}✅{RESET}" if result['success'] else f"{RED}❌{RESET}"
            tier = result.get('tier', 'unknown')
            latency = result['latency_ms']
            intent = result.get('intent', 'unknown')
            
            print(f"{status} {query:40s} | {tier:10s} | {latency:6.1f}ms | {intent}")
        
        # Summary
        avg_latency = sum(r['latency_ms'] for r in results) / len(results)
        success_rate = sum(1 for r in results if r['success']) / len(results) * 100
        p50_latency = sorted(r['latency_ms'] for r in results)[len(results)//2]
        p90_latency = sorted(r['latency_ms'] for r in results)[int(len(results)*0.9)]
        
        print(f"\n{BOLD}{CYAN}{'─' * 80}")
        print(f"Stress Test Summary:")
        print(f"  Total Queries: {len(queries)}")
        print(f"  Success Rate: {success_rate:.1f}%")
        print(f"  Avg Latency: {avg_latency:.2f}ms")
        print(f"  P50 Latency: {p50_latency:.2f}ms")
        print(f"  P90 Latency: {p90_latency:.2f}ms")
        print(f"{'─' * 80}{RESET}\n")
    
    async def print_final_statistics(self):
        """Print comprehensive test statistics"""
        print(f"{BOLD}{GREEN}═══════════════════════════════════════════════════════════════════════════════")
        print("🎯 FINAL STATISTICS")
        print(f"═══════════════════════════════════════════════════════════════════════════════{RESET}\n")
        
        total = self.stats['total_queries']
        if total == 0:
            print(f"{RED}No queries processed{RESET}")
            return
        
        success_rate = (self.stats['successful'] / total) * 100
        avg_latency = self.stats['total_latency_ms'] / total
        
        heuristic_pct = (self.stats['tier_heuristic'] / total) * 100
        adapt_pct = (self.stats['tier_adapt'] / total) * 100
        llm_pct = (self.stats['tier_llm'] / total) * 100
        
        print(f"{BOLD}Overall Performance:{RESET}")
        print(f"  Total Queries: {total}")
        print(f"  Successful: {self.stats['successful']} ({success_rate:.1f}%)")
        print(f"  Failed: {self.stats['failed']}")
        print(f"  Validation Failures: {self.stats['validation_failures']}")
        print(f"  Average Latency: {avg_latency:.2f}ms")
        print()
        
        print(f"{BOLD}Tier Distribution (Target: 80% heuristic):{RESET}")
        print(f"  🚀 Heuristic: {self.stats['tier_heuristic']} ({heuristic_pct:.1f}%)")
        print(f"  ⚡ Adapt: {self.stats['tier_adapt']} ({adapt_pct:.1f}%)")
        print(f"  🧠 LLM: {self.stats['tier_llm']} ({llm_pct:.1f}%)")
        print()
        
        print(f"{BOLD}API Performance:{RESET}")
        print(f"  Total API Calls: {self.stats['api_calls']}")
        print(f"  Calls per Query: {self.stats['api_calls'] / total:.2f}")
        print()
        
        # Performance targets
        print(f"{BOLD}Target Achievement:{RESET}")
        
        latency_target = avg_latency < 200
        success_target = success_rate >= 95
        heuristic_target = heuristic_pct >= 70
        
        print(f"  {'✅' if latency_target else '❌'} Avg Latency < 200ms: {avg_latency:.2f}ms")
        print(f"  {'✅' if success_target else '❌'} Success Rate >= 95%: {success_rate:.1f}%")
        print(f"  {'✅' if heuristic_target else '❌'} Heuristic Coverage >= 70%: {heuristic_pct:.1f}%")
        
        all_passed = latency_target and success_target and heuristic_target
        
        print()
        if all_passed:
            print(f"{BOLD}{GREEN}🎉 ALL TARGETS ACHIEVED - PRODUCTION READY! 🎉{RESET}")
        else:
            print(f"{BOLD}{YELLOW}⚠️  Some targets not met - review needed{RESET}")
        
        print(f"{BOLD}{GREEN}═══════════════════════════════════════════════════════════════════════════════{RESET}\n")
    
    async def close(self):
        """Cleanup resources"""
        await self.api_client.close()


async def main():
    """Run complete integration test suite"""
    # Initialize tester
    tester = SkillIntegrationTest()
    
    # Load whitelist from API
    await tester.initialize_whitelist()
    
    # Run test suites
    await tester.test_quick_queries()
    await tester.test_multi_turn_conversation()
    await tester.test_stress_queries()
    
    # Print final stats
    await tester.print_final_statistics()
    
    # Cleanup
    await tester.close()


if __name__ == '__main__':
    asyncio.run(main())
