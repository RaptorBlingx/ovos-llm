#!/usr/bin/env python3
"""
Interactive Chat Tester - Standalone Component Testing
Tests skill components directly without importing ENMSSkill class

Usage:
    python3 scripts/test_skill_chat.py
    
Then type queries one at a time. Press Ctrl+C or type 'exit' to quit.

NOTE: This copies EXACT logic from __init__.py handle_enms_query() method
to avoid relative import issues when running standalone.
"""
import sys
import asyncio
import re
from pathlib import Path

skill_dir = Path(__file__).parent.parent / "enms_ovos_skill"
sys.path.insert(0, str(skill_dir))

# Import components directly (not the skill class)
from lib.intent_parser import HybridParser, RoutingTier
from lib.validator import ENMSValidator
from lib.api_client import ENMSClient
from lib.response_formatter import ResponseFormatter
from lib.feature_extractor import FeatureExtractor
from lib.conversation_context import ConversationContextManager
from lib.models import IntentType, Intent


class SkillChatTester:
    """Interactive chat tester using skill components directly"""
    
    def __init__(self):
        """Initialize skill components"""
        print("\n" + "="*80)
        print("🤖 EnMS OVOS Skill - Interactive Chat Tester")
        print("="*80)
        print("Testing skill components: Parser → Validator → API → Formatter")
        print("\nInitializing components...")
        
        # Initialize components directly
        self.parser = HybridParser()
        self.validator = ENMSValidator()
        self.api_client = ENMSClient()
        self.formatter = ResponseFormatter()
        self.context_manager = ConversationContextManager()
        
        # Create persistent event loop for async operations
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Refresh machine whitelist from API (like production skill does)
        machines = self.loop.run_until_complete(self.api_client.list_machines(is_active=True))
        machine_names = [m["name"] for m in machines]
        self.validator.update_machine_whitelist(machine_names)
        
        # Create persistent session for multi-turn conversation
        self.session = self.context_manager.get_or_create_session("test_user")
        
        print(f"✅ Components initialized with {len(self.validator.machine_whitelist)} machines")
        print("✅ Conversation context manager enabled (multi-turn support)")
        print("\n" + "="*80)
        print("Ready! Type your queries below. Type 'exit' to quit.")
        print("="*80 + "\n")
    
    async def process_query(self, query_text):
        """Process query through REAL skill pipeline"""
        
        print(f"\n{'─'*80}")
        print(f"You: {query_text}")
        print(f"{'─'*80}")
        print(f"[Session ID] {self.session.session_id}")
        print(f"[Session] Pending clarification: {self.session.pending_clarification}")
        
        try:
            # Step 1: Parse
            parse_result = self.parser.parse(query_text)
            parse_result['utterance'] = query_text
            
            print(f"[Parse] Intent: {parse_result.get('intent')} (confidence: {parse_result.get('confidence'):.2f})")
            
            # Step 1.5: Check for pending clarification BEFORE validation
            # If query is just a machine name answering clarification
            if self.session.pending_clarification:
                print(f"[Context] Pending clarification exists: {self.session.pending_clarification}")
                
                # Check if query matches any machine (case-insensitive)
                matched_machine = None
                for valid_machine in self.validator.machine_whitelist:
                    if query_text.lower() == valid_machine.lower():
                        matched_machine = valid_machine
                        break
                
                if matched_machine:
                    print(f"[Context] Resolving pending clarification with machine: {matched_machine}")
                    
                    # Override parse result with pending intent
                    parse_result['intent'] = self.session.pending_clarification['intent'].value
                    parse_result['entities'] = {'machine': matched_machine}
                    parse_result['machine'] = matched_machine
                    
                    # Update confidence (user provided clarification)
                    parse_result['confidence'] = 0.99
            
            # Step 2: Validate
            validation = self.validator.validate(parse_result)
            
            if not validation.valid:
                print(f"[Validate] ❌ {' '.join(validation.errors)}")
                print(f"\nSkill: I couldn't understand that. {validation.errors[0]}")
                return
            
            intent = validation.intent
            print(f"[Validate] ✅ Intent: {intent.intent.value}, Machine: {intent.machine}")
            
            # Step 3: Resolve context references (multi-turn support)
            intent = self.context_manager.resolve_context_references(query_text, intent, self.session)
            
            # Clear pending clarification if it was resolved
            if self.session.pending_clarification and intent.machine:
                print(f"[Context] Cleared pending clarification")
                self.session.pending_clarification = None
            
            # Check if clarification needed
            clarification = self.context_manager.needs_clarification(intent)
            if clarification:
                # Store pending clarification
                self.session.pending_clarification = {
                    'intent': intent.intent,
                    'metric': intent.metric,
                    'time_range': intent.time_range
                }
                
                print(f"[Session] STORED pending clarification: {self.session.pending_clarification}")
                
                clarification_response = self.context_manager.generate_clarification_response(
                    intent, self.session, validation.suggestions
                )
                
                print(f"[API] ⚠️  {clarification}")
                print(f"[API] ℹ️  Needs clarification")
                print(f"\n{'─'*80}")
                print(f"Skill: {clarification_response}")
                print(f"{'─'*80}\n")
                return
            
            # Step 4: Call API (using EXACT __init__.py logic)
            result = await self._call_api(intent, query_text)
            
            if not result:
                print(f"[API] ⚠️  No data returned")
                print(f"\nSkill: I couldn't retrieve that information.")
                return
            
            # Extract data and optional template
            if isinstance(result, tuple):
                api_data, custom_template = result
            else:
                api_data = result
                custom_template = None
            
            # Handle clarification requests
            if isinstance(api_data, dict) and api_data.get('needs_clarification'):
                print(f"[API] ℹ️  Needs clarification")
                print(f"\n{'─'*80}")
                print(f"Skill: {api_data.get('message', 'Could you clarify?')}")
                print(f"{'─'*80}\n")
                return
            
            print(f"[API] ✅ Data retrieved")
            
            # Step 4: Format Response (using EXACT __init__.py logic)
            response = self._format_response(intent, api_data, custom_template)
            
            print(f"\n{'─'*80}")
            print(f"Skill: {response}")
            
            # For report generation, show PDF info
            if intent.intent == IntentType.REPORT and api_data.get('action') == 'generate':
                data = api_data.get('data', {})
                if data.get('pdf_base64'):
                    print(f"[PDF] 📄 Base64 PDF ready ({len(data['pdf_base64'])} chars)")
                    print(f"[PDF] 📎 Filename: {data.get('filename', 'report.pdf')}")
                    print(f"[PDF] ℹ️  In browser, this would trigger automatic download")
            
            print(f"{'─'*80}\n")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    async def _get_factory_wide_drivers(self):
        """Get aggregated key energy drivers across ALL machines with baseline models."""
        all_drivers = []
        machines_analyzed = []
        
        machines = list(self.validator.machine_whitelist)
        
        for machine_name in machines:
            try:
                models_response = await self.api_client.list_baseline_models(
                    seu_name=machine_name,
                    energy_source="electricity"
                )
                
                models = models_response.get('models', [])
                active_model = next((m for m in models if m.get('is_active')), models[0] if models else None)
                
                if not active_model:
                    continue
                
                explanation_response = await self.api_client.get_baseline_model_explanation(
                    model_id=active_model.get('id'),
                    include_explanation=True
                )
                
                explanation = explanation_response.get('explanation', {})
                key_drivers = explanation.get('key_drivers', [])
                
                for driver in key_drivers:
                    driver['machine'] = machine_name
                    all_drivers.append(driver)
                
                machines_analyzed.append(machine_name)
                
            except Exception as e:
                print(f"[API] ⚠️ Failed to get drivers for {machine_name}: {e}")
                continue
        
        if not all_drivers:
            return {'error': 'No baseline models found across factory'}
        
        # Aggregate drivers by feature
        driver_summary = {}
        for driver in all_drivers:
            feature = driver.get('human_name', driver.get('feature'))
            if feature not in driver_summary:
                driver_summary[feature] = {
                    'human_name': feature,
                    'total_impact': 0,
                    'machines': [],
                    'direction': driver.get('direction', 'affects')
                }
            driver_summary[feature]['total_impact'] += abs(driver.get('absolute_impact', 0))
            driver_summary[feature]['machines'].append(driver['machine'])
        
        # Sort by total impact and get top 5
        sorted_drivers = sorted(
            driver_summary.values(),
            key=lambda x: x['total_impact'],
            reverse=True
        )[:5]
        
        print(f"[API] ✅ Analyzed {len(machines_analyzed)} machines with baseline models")
        
        return {
            'factory_wide': True,
            'machines_analyzed': len(machines_analyzed),
            'top_drivers': sorted_drivers,
            'machines_list': machines_analyzed
        }
    
    async def _call_api(self, intent: Intent, utterance: str):
        """Call API using EXACT logic from __init__.py lines 372-610"""
        
        if intent.intent == IntentType.SEUS:
            # Significant Energy Uses (SEUs) queries
            utterance_lower = utterance.lower()
            
            # Extract energy source from intent or utterance
            energy_source = intent.energy_source
            if not energy_source:
                if 'electricity' in utterance_lower or 'electric' in utterance_lower:
                    energy_source = 'electricity'
                elif 'gas' in utterance_lower or 'natural gas' in utterance_lower:
                    energy_source = 'natural_gas'
                elif 'steam' in utterance_lower:
                    energy_source = 'steam'
                elif 'compressed air' in utterance_lower:
                    energy_source = 'compressed_air'
            
            # Check for baseline filtering
            asking_without_baseline = any(phrase in utterance_lower for phrase in [
                "don't have", "doesn't have", "do not have", "does not have",
                "without baseline", "without basline",
                "no baseline", "no basline",
                "need baseline", "need basline",
                "missing baseline", "missing basline"
            ])
            asking_with_baseline = any(phrase in utterance_lower for phrase in [
                "have baseline", "have basline",
                "has baseline", "has basline",
                "with baseline", "with basline"
            ])
            
            print(f"[API] Calling /seus (energy_source={energy_source or 'all'})")
            data = await self.api_client.list_seus(energy_source=energy_source)
            
            # Filter by baseline status if requested
            if asking_without_baseline:
                data['seus'] = [seu for seu in data.get('seus', []) if not seu.get('has_baseline')]
                data['total_count'] = len(data['seus'])
                data['filter_type'] = 'without_baseline'
            elif asking_with_baseline:
                data['seus'] = [seu for seu in data.get('seus', []) if seu.get('has_baseline')]
                data['total_count'] = len(data['seus'])
                data['filter_type'] = 'with_baseline'
            
            return (data, 'seus')
        
        elif intent.intent == IntentType.FACTORY_OVERVIEW:
            # Check if this is a health/status check vs stats query  
            utterance_lower = utterance.lower()
            
            # Check for carbon/emissions queries
            if 'carbon' in utterance_lower or 'emission' in utterance_lower or 'co2' in utterance_lower:
                print(f"[API] Calling /stats/system (carbon query)")
                data = await self.api_client.system_stats()
                data['is_carbon_query'] = True
                return data
            
            # Check for active/offline machine queries
            if re.search(r'\b(?:active|online|running|inactive|offline|stopped)\b.*?\b(?:machines?|equipment)\b', utterance_lower):
                is_active = bool(re.search(r'\b(?:active|online|running)\b', utterance_lower))
                print(f"[API] Calling /machines (is_active={is_active})")
                machines = await self.api_client.list_machines(is_active=is_active)
                
                data = {
                    'machines': machines,
                    'total_count': len(machines),
                    'filter_type': 'active' if is_active else 'offline'
                }
                return (data, 'machines_by_status')
            
            # Check for SEU queries BEFORE other checks
            if 'seu' in utterance_lower or 'significant energy' in utterance_lower or 'energy uses' in utterance_lower:
                # Check if asking about baseline status (with typo tolerance)
                asking_without_baseline = any(phrase in utterance_lower for phrase in [
                    "don't have", "doesn't have", "do not have", "does not have",
                    "without baseline", "without basline",  # typo tolerance
                    "no baseline", "no basline",  # typo tolerance
                    "need baseline", "need basline",  # typo tolerance
                    "missing baseline", "missing basline"  # typo tolerance
                ])
                asking_with_baseline = any(phrase in utterance_lower for phrase in [
                    "have baseline", "have basline",  # typo tolerance
                    "has baseline", "has basline",  # typo tolerance
                    "with baseline", "with basline"  # typo tolerance
                ])
                
                energy_source = None
                if 'electricity' in utterance_lower or 'electric' in utterance_lower:
                    energy_source = 'electricity'
                elif 'gas' in utterance_lower or 'natural gas' in utterance_lower:
                    energy_source = 'natural_gas'
                elif 'steam' in utterance_lower:
                    energy_source = 'steam'
                
                print(f"[API] Calling /seus (energy_source={energy_source or 'all'})")
                data = await self.api_client.list_seus(energy_source=energy_source)
                
                # Filter by baseline status if requested
                if asking_without_baseline:
                    data['seus'] = [seu for seu in data.get('seus', []) if not seu.get('has_baseline')]
                    data['total_count'] = len(data['seus'])
                    data['filter_type'] = 'without_baseline'
                elif asking_with_baseline:
                    data['seus'] = [seu for seu in data.get('seus', []) if seu.get('has_baseline')]
                    data['total_count'] = len(data['seus'])
                    data['filter_type'] = 'with_baseline'
                
                return (data, 'seus')
            
            if 'performance engine' in utterance_lower or ('engine' in utterance_lower and 'running' in utterance_lower):
                print(f"[API] Calling /performance/health")
                data = await self.api_client.get_performance_health()
                return (data, 'performance_health')
            elif 'opportunities' in utterance_lower or 'saving' in utterance_lower:
                print(f"[API] Calling /performance/opportunities")
                # Get factory_id
                machines = await self.api_client.list_machines()
                factory_id = machines[0]['factory_id'] if machines else None
                
                data = await self.api_client.get_performance_opportunities(
                    factory_id=factory_id,
                    period='week'
                )
                
                # Filter by SEU name if specified (API doesn't support filtering)
                if intent.machine:
                    filtered_opps = [opp for opp in data.get('opportunities', []) 
                                    if opp.get('seu_name') == intent.machine]
                    
                    if filtered_opps:
                        data['opportunities'] = filtered_opps
                        data['total_opportunities'] = len(filtered_opps)
                        data['total_potential_savings_kwh'] = sum(o.get('potential_savings_kwh', 0) for o in filtered_opps)
                        data['total_potential_savings_usd'] = sum(o.get('potential_savings_usd', 0) for o in filtered_opps)
                    else:
                        data['opportunities'] = []
                        data['total_opportunities'] = 0
                        data['total_potential_savings_kwh'] = 0
                        data['total_potential_savings_usd'] = 0
                
                return (data, 'opportunities')
            elif 'action plan' in utterance_lower or 'create plan' in utterance_lower:
                print(f"[API] Calling POST /performance/action-plan")
                if not intent.machine:
                    return {'error': 'Machine name required for action plan'}
                
                # Determine issue type
                issue_type = 'inefficient_scheduling'  # default
                if 'idle' in utterance_lower:
                    issue_type = 'excessive_idle'
                elif 'drift' in utterance_lower or 'degradation' in utterance_lower or 'efficiency' in utterance_lower:
                    issue_type = 'baseline_drift'
                elif 'setpoint' in utterance_lower or 'setting' in utterance_lower:
                    issue_type = 'suboptimal_setpoints'
                
                data = await self.api_client.create_action_plan(
                    seu_name=intent.machine,
                    issue_type=issue_type
                )
                return (data, 'action_plan')
            elif 'summary' in utterance_lower or 'overview' in utterance_lower:
                print(f"[API] Calling /factory/summary")
                data = await self.api_client.factory_summary()
                return (data, 'factory_summary')
            elif 'enpi' in utterance_lower or 'iso' in utterance_lower or 'compliance report' in utterance_lower or 'energy performance indicator' in utterance_lower:
                # ISO 50001 EnPI report
                from datetime import datetime
                
                period = None
                
                # Check for quarters
                quarter_match = re.search(r'q[1-4]|quarter\s*[1-4]', utterance_lower, re.IGNORECASE)
                if quarter_match:
                    quarter_text = quarter_match.group().lower()
                    quarter_num = re.search(r'[1-4]', quarter_text).group()
                    year_match = re.search(r'20\d{2}', utterance_lower)
                    year = year_match.group() if year_match else str(datetime.now().year)
                    period = f"{year}-Q{quarter_num}"
                else:
                    year_match = re.search(r'20\d{2}', utterance_lower)
                    if year_match:
                        period = year_match.group()
                    else:
                        now = datetime.now()
                        current_quarter = (now.month - 1) // 3 + 1
                        period = f"{now.year}-Q{current_quarter}"
                
                # Get factory_id
                machines = await self.api_client.list_machines()
                factory_id = machines[0]['factory_id'] if machines else "11111111-1111-1111-1111-111111111111"
                
                print(f"[API] Calling /iso50001/enpi-report (period={period})")
                data = await self.api_client.get_enpi_report(
                    factory_id=factory_id,
                    period=period
                )
                return (data, 'enpi_report')
            elif 'action plan' in utterance_lower and 'list' in utterance_lower:
                # List ISO action plans
                status_filter = None
                priority_filter = None
                
                if 'completed' in utterance_lower or 'complete' in utterance_lower:
                    status_filter = 'completed'
                elif 'in progress' in utterance_lower or 'active' in utterance_lower:
                    status_filter = 'in_progress'
                elif 'planned' in utterance_lower:
                    status_filter = 'planned'
                
                if 'high priority' in utterance_lower or 'critical' in utterance_lower:
                    priority_filter = 'high' if 'high' in utterance_lower else 'critical'
                
                machines = await self.api_client.list_machines()
                factory_id = machines[0]['factory_id'] if machines else "11111111-1111-1111-1111-111111111111"
                
                print(f"[API] Calling /iso50001/action-plans (status={status_filter}, priority={priority_filter})")
                data = await self.api_client.list_action_plans(
                    factory_id=factory_id,
                    status=status_filter,
                    priority=priority_filter
                )
                return (data, 'action_plans_list')
            else:
                print(f"[API] Calling /stats/system")
                data = await self.api_client.system_stats()
                return data
                
        elif intent.intent == IntentType.MACHINE_STATUS and intent.machine:
            # Check for multiple matching machines
            all_matches = self.validator.find_all_matching_machines(intent.machine)
            
            if len(all_matches) > 1:
                # Multiple machines match - fetch status for ALL of them
                print(f"[API] Multiple matches for '{intent.machine}': {all_matches}")
                print(f"[API] Calling /machines/status for {len(all_matches)} machines")
                
                machine_statuses = []
                for machine_name in all_matches:
                    status_data = await self.api_client.get_machine_status(machine_name)
                    machine_statuses.append(status_data)
                
                return ({
                    'machines': machine_statuses,
                    'count': len(machine_statuses),
                    'query_term': intent.machine
                }, 'multi_machine_status')
            else:
                # Single machine match
                print(f"[API] Calling /machines/status/{intent.machine}")
                data = await self.api_client.get_machine_status(intent.machine)
                return data
            
        elif intent.intent == IntentType.ENERGY_QUERY:
            # Check if utterance mentions interval keywords (hourly, 15-minute, etc.)
            utterance_lower = utterance.lower()
            needs_timeseries = False
            requested_interval = None
            
            # Check for multi-energy queries
            is_energy_types = 'energy types' in utterance_lower or 'energy sources' in utterance_lower or 'what energy' in utterance_lower
            is_energy_summary = 'energy summary' in utterance_lower or 'all energy' in utterance_lower
            specific_energy_type = None
            
            if 'electricity' in utterance_lower or 'electric' in utterance_lower:
                specific_energy_type = 'electricity'
            elif 'natural gas' in utterance_lower or 'gas' in utterance_lower:
                specific_energy_type = 'natural_gas'
            elif 'steam' in utterance_lower:
                specific_energy_type = 'steam'
            elif 'compressed air' in utterance_lower or 'air' in utterance_lower:
                specific_energy_type = 'compressed_air'
            
            # Handle multi-energy queries
            if is_energy_types or is_energy_summary or specific_energy_type:
                if not intent.machine:
                    print(f"[API] ⚠️  Multi-energy query requires machine name")
                    return None
                
                # Lookup machine ID
                print(f"[API] Looking up machine ID for {intent.machine}")
                machines = await self.api_client.list_machines(search=intent.machine)
                if not machines:
                    print(f"[API] ❌ Machine {intent.machine} not found")
                    return None
                
                machine_id = machines[0]['id']
                
                if is_energy_types:
                    print(f"[API] Calling /machines/{machine_id}/energy-types")
                    data = await self.api_client.get_energy_types(machine_id=machine_id, hours=24)
                    data['machine_name'] = intent.machine
                    return (data, 'energy_types')
                elif is_energy_summary:
                    print(f"[API] Calling /machines/{machine_id}/energy-summary")
                    data = await self.api_client.get_energy_summary(machine_id=machine_id)
                    data['machine_name'] = intent.machine
                    return (data, 'energy_summary')
                elif specific_energy_type:
                    print(f"[API] Calling /machines/{machine_id}/energy/{specific_energy_type}")
                    data = await self.api_client.get_energy_readings(
                        machine_id=machine_id,
                        energy_type=specific_energy_type,
                        hours=24
                    )
                    data['machine_name'] = intent.machine
                    data['energy_type'] = specific_energy_type
                    return (data, 'energy_type_readings')
            
            if 'hourly' in utterance_lower or 'hour by hour' in utterance_lower:
                needs_timeseries = True
                requested_interval = '1hour'
            elif '15-minute' in utterance_lower or '15 minute' in utterance_lower or 'fifteen minute' in utterance_lower:
                needs_timeseries = True
                requested_interval = '15min'
            elif '5-minute' in utterance_lower or '5 minute' in utterance_lower:
                needs_timeseries = True
                requested_interval = '5min'
            elif 'daily' in utterance_lower or 'day by day' in utterance_lower:
                needs_timeseries = True
                requested_interval = '1day'
            
            # Check if this is a time-series query (last week, this month, etc.) OR interval keywords detected
            if intent.time_range and (intent.time_range.relative not in ["today", "now", None] or needs_timeseries):
                if not intent.machine:
                    print(f"[API] ⚠️  Time-series query requires machine name")
                    return None
                
                # First get machine ID
                print(f"[API] Looking up machine ID for {intent.machine}")
                machines = await self.api_client.list_machines(search=intent.machine)
                if not machines:
                    print(f"[API] ❌ Machine {intent.machine} not found")
                    return None
                machine_id = machines[0]['id']
                
                # Determine interval based on explicit request or time range
                if requested_interval:
                    interval = requested_interval
                else:
                    time_diff = intent.time_range.end - intent.time_range.start
                    if time_diff.days > 30:
                        interval = "1day"
                    elif time_diff.days > 7:
                        interval = "1day"  # API only supports: 1min, 5min, 15min, 1hour, 1day
                    elif time_diff.days > 1:
                        interval = "1hour"
                    else:
                        interval = "15min"
                
                print(f"[API] Calling /timeseries/energy (machine_id={machine_id}, interval={interval})")
                timeseries = await self.api_client.get_energy_timeseries(
                    machine_id=machine_id,
                    start_time=intent.time_range.start,
                    end_time=intent.time_range.end,
                    interval=interval
                )
                
                # Calculate total energy and parse timestamps (matching __init__.py logic)
                total_energy = 0
                data_points_parsed = []
                if 'data_points' in timeseries and isinstance(timeseries['data_points'], list):
                    for point in timeseries['data_points']:
                        total_energy += point.get('value', 0)
                        # Parse timestamp string to datetime for voice_time filter
                        timestamp_str = point.get('timestamp')
                        if timestamp_str:
                            try:
                                from dateutil import parser as date_parser
                                timestamp_dt = date_parser.parse(timestamp_str)
                            except:
                                timestamp_dt = timestamp_str
                            data_points_parsed.append({
                                'timestamp': timestamp_dt,
                                'value': point.get('value', 0),
                                'unit': point.get('unit', 'kWh')
                            })
                
                # Detect trend/pattern queries (matching __init__.py)
                is_trend_query = 'trend' in utterance.lower() or 'pattern' in utterance.lower()
                
                # Calculate trend analysis if requested
                trend_periods = None
                if is_trend_query and len(data_points_parsed) > 3:
                    # Divide into 3-4 periods based on data density
                    num_periods = 3 if len(data_points_parsed) <= 24 else 4
                    period_size = len(data_points_parsed) // num_periods
                    trend_periods = []
                    
                    for i in range(num_periods):
                        start_idx = i * period_size
                        end_idx = start_idx + period_size if i < num_periods - 1 else len(data_points_parsed)
                        period_data = data_points_parsed[start_idx:end_idx]
                        
                        if period_data:
                            period_total = sum(p['value'] for p in period_data)
                            period_avg = period_total / len(period_data)
                            period_start = period_data[0]['timestamp']
                            period_end = period_data[-1]['timestamp']
                            
                            # Find peak hour in this period
                            peak_point = max(period_data, key=lambda p: p['value'])
                            
                            trend_periods.append({
                                'start_time': period_start,
                                'end_time': period_end,
                                'total_kwh': round(period_total, 2),
                                'avg_kwh': round(period_avg, 1),
                                'peak_kwh': round(peak_point['value'], 1),
                                'peak_time': peak_point['timestamp']
                            })
                
                # Structure response for template (matching __init__.py)
                return {
                    'machine': intent.machine,
                    'time_range': intent.time_range.relative or 'custom',
                    'start_time': intent.time_range.start,
                    'end_time': intent.time_range.end,
                    'timeseries_data': data_points_parsed,
                    'total_energy_kwh': total_energy,
                    'interval': interval,
                    'is_trend_query': is_trend_query,
                    'trend_periods': trend_periods
                }
            else:
                # Today/now query - use status endpoint
                if intent.machine:
                    print(f"[API] Calling /machines/status/{intent.machine}")
                    data = await self.api_client.get_machine_status(intent.machine)
                    
                    # Check if user asked for average per hour
                    if 'average' in utterance.lower() or 'per hour' in utterance.lower() or 'hourly average' in utterance.lower():
                        data['is_average_query'] = True
                    
                    return data
                else:
                    print(f"[API] Calling /stats/system")
                    data = await self.api_client.system_stats()
                    return data
                
        elif intent.intent == IntentType.POWER_QUERY:
            # Check if this is a time-series query (yesterday, last week, etc.)
            if intent.time_range and intent.time_range.relative not in ["today", "now", None]:
                if not intent.machine:
                    print(f"[API] ⚠️  Time-series query requires machine name")
                    return None
                
                # First get machine ID
                print(f"[API] Looking up machine ID for {intent.machine}")
                machines = await self.api_client.list_machines(search=intent.machine)
                if not machines:
                    print(f"[API] ❌ Machine {intent.machine} not found")
                    return None
                machine_id = machines[0]['id']
                
                # Determine interval based on time range
                time_diff = intent.time_range.end - intent.time_range.start
                if time_diff.days > 30:
                    interval = "1day"
                elif time_diff.days > 7:
                    interval = "1day"
                elif time_diff.days > 1:
                    interval = "1hour"
                else:
                    interval = "15min"
                
                print(f"[API] Calling /timeseries/power (machine_id={machine_id}, interval={interval})")
                timeseries = await self.api_client.get_power_timeseries(
                    machine_id=machine_id,
                    start_time=intent.time_range.start,
                    end_time=intent.time_range.end,
                    interval=interval
                )
                
                # Calculate average power from timeseries
                total_power = 0
                count = 0
                if 'data_points' in timeseries and isinstance(timeseries['data_points'], list):
                    for point in timeseries['data_points']:
                        if point.get('value') is not None:
                            total_power += point.get('value', 0)
                            count += 1
                
                avg_power = total_power / count if count > 0 else 0
                
                # Structure response for template
                return {
                    'machine': intent.machine,
                    'time_range': intent.time_range.relative or 'custom',
                    'start_time': intent.time_range.start,
                    'end_time': intent.time_range.end,
                    'timeseries_data': timeseries.get('data_points', []),
                    'avg_power_kw': avg_power,
                    'interval': interval
                }
            else:
                # Today/now query - use status endpoint
                if intent.machine:
                    print(f"[API] Calling /machines/status/{intent.machine}")
                    data = await self.api_client.get_machine_status(intent.machine)
                    return data
                else:
                    print(f"[API] Calling /stats/system")
                    data = await self.api_client.system_stats()
                    return data
        
        elif intent.intent == IntentType.RANKING:
            # Check if this is a machine list request vs top consumers ranking
            if not intent.limit and not intent.metric:
                # Extract search term from utterance (e.g., "HVAC", "Boiler")
                utterance = getattr(intent, 'utterance', '').lower()
                search_term = None
                search_patterns = [
                    r'\b(HVAC|Boiler|Compressor|Conveyor|Turbine|Hydraulic|Injection)s?\b',  # Match plural forms
                    r'\bfind.*?(?:the\s+)?(\w+)\b',
                    r'\bwhich\s+(\w+)\s+(?:units?|machines?)',
                    r'\bhow\s+many\s+(\w+)\b',  # "how many compressors"
                ]
                for pattern in search_patterns:
                    match = re.search(pattern, utterance, re.IGNORECASE)
                    if match:
                        search_term = match.group(1).rstrip('s')  # Remove plural 's'
                        break
                
                if search_term:
                    print(f"[API] Calling /machines (search={search_term})")
                    machines = await self.api_client.list_machines(search=search_term)
                else:
                    print(f"[API] Calling /machines (list all machines)")
                    machines = await self.api_client.list_machines()
                return {'machines': machines, 'count': len(machines)}
            else:
                # This is top N ranking by metric
                limit = intent.limit or 5
                print(f"[API] Calling /analytics/top-consumers (limit={limit})")
                data = await self.api_client.get_top_consumers(limit=limit)
                return data
        
        elif intent.intent == IntentType.COST_ANALYSIS:
            # Extract machine if not provided
            machine = intent.machine
            if not machine:
                # Try to extract from utterance
                common_machines = ['Compressor-1', 'Boiler-1', 'HVAC-Main', 'Conveyor-Belt-1', 'Injection-Molder-1']
                for machine_name in common_machines:
                    if machine_name.lower() in query.lower():
                        machine = machine_name
                        break
            
            if machine:
                print(f"[API] Calling /machines/status/{machine}")
                data = await self.api_client.get_machine_status(machine)
            else:
                print(f"[API] Calling /stats/system")
                data = await self.api_client.system_stats()
            return data
        
        elif intent.intent == IntentType.COMPARISON:
            if not intent.machines or len(intent.machines) < 2:
                print(f"[API] ⚠️  Comparison requires at least 2 machines")
                return None
            
            print(f"[API] Calling /timeseries/multi-machine/energy (machines={intent.machines})")
            
            # Get machine IDs
            machine_ids = []
            machine_names = []
            for machine_name in intent.machines:
                machines = await self.api_client.list_machines(search=machine_name)
                if machines:
                    machine_ids.append(machines[0]['id'])
                    machine_names.append(machines[0]['name'])
            
            if len(machine_ids) < 2:
                print(f"[API] ⚠️  Could not find all machines")
                return None
            
            # Get time range (default: today)
            from datetime import datetime, timezone
            end_time = datetime.now(timezone.utc)
            start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # Call API
            data = await self.api_client.get_multi_machine_energy(
                machine_ids=machine_ids,
                start_time=start_time,
                end_time=end_time,
                interval="1hour"
            )
            
            # Calculate totals
            machines_with_totals = []
            for machine in data.get('machines', []):
                total_energy = sum(dp['value'] for dp in machine.get('data_points', []))
                machines_with_totals.append({
                    'machine_name': machine['machine_name'],
                    'total_energy': total_energy
                })
            
            data['machines'] = machines_with_totals
            data['machine_names'] = machine_names
            data['time_period'] = f"today ({start_time.strftime('%Y-%m-%d')})"
            
            return data
        
        elif intent.intent == IntentType.BASELINE_MODELS:
            if not intent.machine:
                print(f"[API] ⚠️  Baseline models requires machine name")
                return None
            
            print(f"[API] Calling GET /baseline/models (machine={intent.machine})")
            response = await self.api_client.list_baseline_models(
                seu_name=intent.machine,
                energy_source="electricity"
            )
            
            # Process to match __init__.py logic
            models = response.get('models', [])
            active_model = next((m for m in models if m.get('is_active')), models[0] if models else None)
            
            data = {
                'seu_name': response.get('seu_name', intent.machine),
                'models': models,
                'active_version': active_model.get('model_version') if active_model else None,
                'active_r_squared': active_model.get('r_squared') if active_model else None,
                'active_samples': active_model.get('training_samples') if active_model else None
            }
            return data
        
        elif intent.intent == IntentType.BASELINE_EXPLANATION:
            if not intent.machine:
                # Factory-wide key drivers (no machine specified)
                print(f"[API] Getting factory-wide key energy drivers")
                return await self._get_factory_wide_drivers()
            
            print(f"[API] Getting baseline explanation for {intent.machine}")
            
            # First get the list of models to find the active model ID
            models_response = await self.api_client.list_baseline_models(
                seu_name=intent.machine,
                energy_source="electricity"
            )
            
            models = models_response.get('models', [])
            active_model = next((m for m in models if m.get('is_active')), models[0] if models else None)
            
            if not active_model:
                print(f"[API] ⚠️  No baseline model found for {intent.machine}")
                return {'error': f'No baseline model found for {intent.machine}'}
            
            # Get detailed explanation for the active model
            model_id = active_model.get('id')
            print(f"[API] Calling GET /baseline/model/{model_id}?include_explanation=true")
            explanation_response = await self.api_client.get_baseline_model_explanation(
                model_id=model_id,
                include_explanation=True
            )
            
            # Extract explanation data for template
            explanation = explanation_response.get('explanation', {})
            data = {
                'machine_name': explanation_response.get('machine_name', intent.machine),
                'seu_name': intent.machine,
                'r_squared': explanation_response.get('r_squared'),
                'model_version': explanation_response.get('model_version'),
                'explanation': explanation,
                'key_drivers': explanation.get('key_drivers', []),
                'accuracy_explanation': explanation.get('accuracy_explanation'),
                'formula_explanation': explanation.get('formula_explanation')
            }
            return data
        
        elif intent.intent == IntentType.BASELINE:
            machine = intent.machine
            machines = intent.machines if intent.machines else []
            
            # If no machine specified, try conversation context
            if not machine and not machines:
                session = self.context_manager.get_or_create_session("test_user")
                machine = session.get_last_machine()
                if machine:
                    print(f"[API] ℹ️  Using machine from context: {machine}")
            
            if not machine and not machines:
                print(f"[API] ⚠️  Baseline prediction requires machine name")
                print(f"[API] ℹ️  OVOS would ask: 'Which machine?'")
                return {'needs_clarification': True, 'message': 'Which machine? Please specify a machine name.'}
            
            # Extract features from utterance (temperature, pressure, load, production)
            features = FeatureExtractor.extract_all_features(
                utterance,
                defaults={
                    "total_production_count": 5000000,
                    "avg_outdoor_temp_c": 22.0,
                    "avg_pressure_bar": 7.0,
                    "avg_load_factor": 0.85
                }
            )
            
            print(f"[API] Extracted features: {features}")
            
            # Handle multiple machines (ambiguous query)
            if machines:
                print(f"[API] Calling /baseline/predict for {len(machines)} machines: {', '.join(machines)}")
                predictions = []
                
                for seu_name in machines:
                    try:
                        prediction = await self.api_client.predict_baseline(
                            seu_name=seu_name,
                            energy_source="electricity",
                            features=features,
                            include_message=False
                        )
                        prediction['seu_name'] = seu_name
                        predictions.append(prediction)
                    except Exception as e:
                        print(f"[API] ⚠️  Failed to get prediction for {seu_name}: {e}")
                
                return {
                    'predictions': predictions,
                    'features': features,
                    'machine_count': len(predictions)
                }
            
            # Single machine
            print(f"[API] Calling /baseline/predict (machine={machine}, features={features})")
            data = await self.api_client.predict_baseline(
                seu_name=machine,
                energy_source="electricity",
                features=features,
                include_message=False  # Don't use API message, we format with features
            )
            
            # Add SEU name and features to response for template
            data['seu_name'] = machine
            data['features'] = features
            
            # Update conversation context with this machine
            session = self.context_manager.get_or_create_session("test_user")
            session.update_machine(machine)
            print(f"[Context] Saved machine '{machine}' to conversation context")
            
            return data
        
        elif intent.intent == IntentType.KPI:
            from datetime import datetime, timezone
            
            machine = intent.machine
            
            if not machine:
                print(f"[API] ⚠️  KPI query requires machine name")
                return {'needs_clarification': True, 'message': 'Which machine? Please specify a machine name for KPIs.'}
            
            print(f"[API] Calling GET /kpi/all (machine={machine})")
            
            # Get time range (default to today)
            if intent.time_range and intent.time_range.start:
                start_time = intent.time_range.start
                end_time = intent.time_range.end if intent.time_range.end else datetime.now(timezone.utc)
            else:
                start_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                end_time = datetime.now(timezone.utc)
            
            # Get machine ID
            machines = await self.api_client.list_machines(search=machine)
            if not machines or len(machines) == 0:
                print(f"[API] ❌ Machine {machine} not found")
                return {'error': f'Machine {machine} not found'}
            
            machine_id = machines[0]['id']
            
            data = await self.api_client.get_all_kpis(
                machine_id=machine_id,
                start_time=start_time,
                end_time=end_time
            )
            return data
        
        elif intent.intent == IntentType.PERFORMANCE:
            # Performance analysis
            machine = intent.machine
            
            if not machine:
                print(f"[API] ⚠️  PERFORMANCE requires machine name")
                return None
            
            print(f"[API] Calling POST /performance/analyze ({machine})")
            
            # Use "energy" as default energy source
            energy_source = "energy"
            
            # Get analysis date (default: today)
            from datetime import date
            analysis_date = date.today().isoformat()
            
            data = await self.api_client.analyze_performance(
                seu_name=machine,
                energy_source=energy_source,
                analysis_date=analysis_date
            )
            return data
        
        elif intent.intent == IntentType.FORECAST:
            # Check if this is a demand forecast
            utterance = getattr(intent, 'utterance', '').lower()
            is_demand_forecast = 'demand' in utterance or 'detailed' in utterance
            
            if is_demand_forecast and intent.machine:
                print(f"[API] Calling /forecast/demand (detailed ARIMA forecast for {intent.machine})")
                # Lookup machine ID
                machines = await self.api_client.list_machines(search=intent.machine)
                if not machines:
                    print(f"[API] ❌ Machine {intent.machine} not found")
                    return None
                machine_id = machines[0]['id']
                
                data = await self.api_client.forecast_demand(machine_id=machine_id, horizon="short", periods=4)
                data['machine_name'] = intent.machine
                return (data, 'demand_forecast')
            else:
                print(f"[API] Calling /forecast/short-term (machine={intent.machine}, hours=24)")
                data = await self.api_client.get_forecast(
                    machine=intent.machine,
                    hours=24
                )
                return data
        
        elif intent.intent == IntentType.PRODUCTION:
            if not intent.machine:
                print(f"[API] ⚠️  Production query requires machine name")
                return None
            
            print(f"[API] Calling /machines/status/{intent.machine} (production data)")
            data = await self.api_client.get_machine_status(intent.machine)
            return data
        
        elif intent.intent == IntentType.ANOMALY_DETECTION:
            # Check what type of anomaly query this is
            utterance = getattr(intent, 'utterance', '').lower()
            is_detection_request = any(kw in utterance for kw in ['check for', 'detect', 'find', 'scan for', 'analyze for'])
            is_active_request = any(kw in utterance for kw in ['active', 'unresolved', 'alerts', 'need attention'])
            
            if is_detection_request and intent.machine:
                # RUN ML anomaly detection
                print(f"[API] Looking up machine ID for {intent.machine}")
                machines = await self.api_client.list_machines(search=intent.machine)
                if not machines:
                    print(f"[API] ❌ Machine {intent.machine} not found")
                    return None
                
                machine_id = machines[0]['id']
                
                # Get time range (default: today)
                from datetime import datetime, timezone
                if intent.time_range and intent.time_range.start and intent.time_range.end:
                    start_time = intent.time_range.start
                    end_time = intent.time_range.end
                else:
                    end_time = datetime.now(timezone.utc)
                    start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
                
                print(f"[API] Calling POST /anomaly/detect (ML detection)")
                data = await self.api_client.detect_anomalies(
                    machine_id=machine_id,
                    start=start_time,
                    end=end_time
                )
                data['machine_name'] = intent.machine
                data['is_detection'] = True
                return data
            
            elif is_active_request:
                # GET active (unresolved) anomalies
                print("[API] Calling GET /anomaly/active (unresolved anomalies)")
                data = await self.api_client.get_active_anomalies()
                data['is_active'] = True
                return data
            
            # LIST recent anomalies
            limit = intent.limit or 10
            machine_id = None
            
            # Get machine ID if machine specified
            if intent.machine:
                print(f"[API] Looking up machine ID for {intent.machine}")
                machines = await self.api_client.list_machines(search=intent.machine)
                if machines:
                    machine_id = machines[0]['id']
                    data = await self.api_client.get_recent_anomalies(limit=limit, machine_id=machine_id)
                    data['machine_name'] = intent.machine
                    return data
            
            if intent.time_range:
                # Time-range based anomaly search
                print(f"[API] Calling /anomaly/search (time range, limit={limit})")
                data = await self.api_client.search_anomalies(
                    start_time=intent.time_range.start,
                    end_time=intent.time_range.end,
                    machine_id=machine_id,
                    limit=limit
                )
            else:
                # Recent anomalies (factory-wide)
                print(f"[API] Calling /anomaly/recent (factory-wide, limit={limit})")
                data = await self.api_client.get_recent_anomalies(limit=limit, machine_id=machine_id)
                
                # Extract unique affected machines from anomalies list
                if 'anomalies' in data and isinstance(data['anomalies'], list):
                    affected_machines = list(set(
                        anomaly.get('machine_name') 
                        for anomaly in data['anomalies'] 
                        if anomaly.get('machine_name')
                    ))
                    data['affected_machines'] = sorted(affected_machines)
            
            return data
        
        elif intent.intent == IntentType.REPORT:
            # Report generation - generate/preview/list reports
            action = intent.params.get('action', 'generate') if intent.params else 'generate'
            report_type = intent.params.get('report_type', 'monthly_enpi') if intent.params else 'monthly_enpi'
            year = intent.params.get('year') if intent.params else None
            month = intent.params.get('month') if intent.params else None
            
            print(f"[API] Report action: {action}, type: {report_type}, year: {year}, month: {month}")
            
            if action == 'list_types':
                print("[API] Calling GET /reports/types")
                data = await self.api_client.get_report_types()
                return {'data': data, 'action': 'list_types'}
                
            elif action == 'preview':
                print("[API] Calling GET /reports/preview")
                data = await self.api_client.preview_report(
                    report_type=report_type,
                    year=year,
                    month=month
                )
                return {'data': data, 'action': 'preview', 'month': month, 'year': year, 'report_type': report_type}
                
            else:  # generate
                print("[API] Calling POST /reports/generate")
                data = await self.api_client.generate_report(
                    report_type=report_type,
                    year=year,
                    month=month
                )
                return {'data': data, 'action': 'generate'}
        
        else:
            print(f"[API] ⚠️  Intent '{intent.intent.value}' not yet implemented")
            return None
    
    def _format_response(self, intent: Intent, api_data: dict, custom_template: str = None) -> str:
        """Format response using EXACT logic from __init__.py lines 547-577"""
        
        try:
            # Use custom template if specified
            if custom_template:
                print(f"[Format] Using {custom_template}.dialog")
                template = self.formatter.env.get_template(f'{custom_template}.dialog')
                return template.render(**api_data).strip()
            
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
            
            # Special handling for REPORT intent
            if intent.intent == IntentType.REPORT:
                action = api_data.get('action', 'generate')
                month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                              'July', 'August', 'September', 'October', 'November', 'December']
                
                if action == 'list_types':
                    print(f"[Format] Using report_types.dialog")
                    template = self.formatter.env.get_template('report_types.dialog')
                    return template.render(**api_data.get('data', {})).strip()
                elif action == 'preview':
                    print(f"[Format] Using report_preview.dialog")
                    template = self.formatter.env.get_template('report_preview.dialog')
                    data = api_data.get('data', {})
                    month = api_data.get('month', 1)
                    year = api_data.get('year', 2024)
                    return template.render(
                        data=data,
                        report_type=api_data.get('report_type', 'monthly_enpi'),
                        month_name=month_names[month] if month and 1 <= month <= 12 else 'this month',
                        year=year
                    ).strip()
                else:  # generate
                    print(f"[Format] Using report_generated.dialog")
                    template = self.formatter.env.get_template('report_generated.dialog')
                    data = api_data.get('data', {})
                    month = data.get('month', 1)
                    year = data.get('year', 2024)
                    return template.render(
                        success=data.get('success', False),
                        file_path=data.get('file_path', ''),
                        report_type=data.get('report_type', 'monthly_enpi'),
                        month_name=month_names[month] if month and 1 <= month <= 12 else 'this month',
                        year=year,
                        error=data.get('error')
                    ).strip()
            
            print(f"[Format] Using {intent.intent.value}.dialog")
            return self.formatter.format_response(
                intent_type=intent.intent.value,
                api_data=api_data,
                context={
                    "machine_name": intent.machine,
                    "utterance": getattr(intent, 'utterance', '').lower()
                } if intent.machine or hasattr(intent, 'utterance') else {}
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
                
                # Process query with persistent event loop
                self.loop.run_until_complete(self.process_query(query))
                
        except KeyboardInterrupt:
            print("\n\nExiting... 👋\n")
        except EOFError:
            print("\n\nExiting... 👋\n")
        finally:
            # Clean up event loop
            self.loop.close()


if __name__ == "__main__":
    import sys
    
    tester = SkillChatTester()
    
    # Check if query provided as command-line argument
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        # Process single query and exit
        tester.loop.run_until_complete(tester.process_query(query))
        tester.loop.close()
    else:
        # Interactive mode
        tester.run()
