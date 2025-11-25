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
from lib.feature_extractor import FeatureExtractor
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
        if validation.suggestions:
            print(f"  💡 Suggestions: {validation.suggestions}")
        return
    
    intent = validation.intent
    print(f"  ✅ Valid - Intent: {intent.intent.value}, Machine: {intent.machine}")
    
    # Step 3: Call API (using __init__.py logic)
    print("\n[STEP 3] Calling EnMS API (using skill logic from __init__.py)...")
    api_client = ENMSClient(base_url="http://10.33.10.109:8001/api/v1")
    
    # This is COPIED from __init__.py _call_enms_api() method (lines 372-492)
    api_data = None
    
    if intent.intent == IntentType.MACHINE_STATUS and intent.machine:
        print(f"  → Calling /machines/status/{intent.machine}")
        data = await api_client.get_machine_status(intent.machine)
        api_data = data
        
    elif intent.intent == IntentType.ENERGY_QUERY:
        if intent.machine:
            # Check if utterance mentions interval keywords (hourly, 15-minute, etc.)
            utterance_lower = query_text.lower()
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
                # Lookup machine ID
                machines_list = await api_client.list_machines(search=intent.machine)
                if not machines_list:
                    print(f"  ❌ Machine {intent.machine} not found")
                    return
                
                machine_id = machines_list[0]['id']
                
                if is_energy_types:
                    print(f"  → Calling GET /machines/{machine_id}/energy-types")
                    data = await api_client.get_energy_types(machine_id=machine_id, hours=24)
                    data['machine_name'] = intent.machine
                    api_data = data
                    custom_template = 'energy_types'
                elif is_energy_summary:
                    print(f"  → Calling GET /machines/{machine_id}/energy-summary")
                    data = await api_client.get_energy_summary(machine_id=machine_id)
                    data['machine_name'] = intent.machine
                    api_data = data
                    custom_template = 'energy_summary'
                elif specific_energy_type:
                    print(f"  → Calling GET /machines/{machine_id}/energy/{specific_energy_type}")
                    data = await api_client.get_energy_readings(
                        machine_id=machine_id,
                        energy_type=specific_energy_type,
                        hours=24
                    )
                    data['machine_name'] = intent.machine
                    data['energy_type'] = specific_energy_type
                    api_data = data
                    custom_template = 'energy_type_readings'
            elif 'hourly' in utterance_lower or 'hour by hour' in utterance_lower:
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
            
            # Check if time range is specified (beyond "today") OR if interval keywords detected
            if intent.time_range and (intent.time_range.relative not in ["today", "now", None] or needs_timeseries):
                print(f"  → Calling /timeseries/energy (time-series for {intent.machine}, {intent.time_range.relative or 'custom interval'})")
                
                # First get machine ID
                machines_list = await api_client.list_machines(search=intent.machine)
                if not machines_list:
                    print(f"  ❌ Machine {intent.machine} not found")
                    return
                
                machine_id = machines_list[0]['id']
                
                # Determine interval based on explicit request or time range
                if requested_interval:
                    interval = requested_interval
                else:
                    time_delta = intent.time_range.end - intent.time_range.start
                    if time_delta.days > 30:
                        interval = '1day'
                    elif time_delta.days > 7:
                        interval = '1day'  # API only supports: 1min, 5min, 15min, 1hour, 1day
                    elif time_delta.days > 1:
                        interval = '1hour'
                    else:
                        interval = '15min'
                
                # Get time-series data
                timeseries = await api_client.get_energy_timeseries(
                    machine_id=machine_id,
                    start_time=intent.time_range.start,
                    end_time=intent.time_range.end,
                    interval=interval
                )
                
                # Calculate total energy
                total_energy = 0
                if 'data_points' in timeseries and isinstance(timeseries['data_points'], list):
                    total_energy = sum(point.get('value', 0) for point in timeseries['data_points'])
                
                api_data = {
                    'machine': intent.machine,
                    'time_range': intent.time_range.relative or 'custom',
                    'start_time': intent.time_range.start,
                    'end_time': intent.time_range.end,
                    'timeseries_data': timeseries.get('data_points', []),
                    'total_energy_kwh': total_energy,
                    'interval': interval
                }
            else:
                # Default: today data
                print(f"  → Calling /machines/status/{intent.machine} (energy for specific machine)")
                data = await api_client.get_machine_status(intent.machine)
                api_data = data
        else:
            print("  → Calling /stats/system (factory-wide energy)")
            data = await api_client.system_stats()
            api_data = data
            
    elif intent.intent == IntentType.POWER_QUERY:
        if intent.machine:
            # Check if time range is specified
            if intent.time_range and intent.time_range.relative not in ["today", "now", None]:
                print(f"  → Calling /timeseries/power (time-series for {intent.machine}, {intent.time_range.relative})")
                
                # Get machine ID
                machines_list = await api_client.list_machines(search=intent.machine)
                if not machines_list:
                    print(f"  ❌ Machine {intent.machine} not found")
                    return
                
                machine_id = machines_list[0]['id']
                
                # Determine interval
                time_delta = intent.time_range.end - intent.time_range.start
                if time_delta.days > 30:
                    interval = '1day'
                elif time_delta.days > 7:
                    interval = '1day'
                elif time_delta.days > 1:
                    interval = '1hour'
                else:
                    interval = '15min'
                
                # Get time-series power data
                timeseries = await api_client.get_power_timeseries(
                    machine_id=machine_id,
                    start_time=intent.time_range.start,
                    end_time=intent.time_range.end,
                    interval=interval
                )
                
                # Calculate average power
                avg_power = 0
                if 'data_points' in timeseries and isinstance(timeseries['data_points'], list):
                    avg_power = sum(point.get('value', 0) for point in timeseries['data_points']) / len(timeseries['data_points'])
                
                api_data = {
                    'machine': intent.machine,
                    'time_range': intent.time_range.relative or 'custom',
                    'start_time': intent.time_range.start,
                    'end_time': intent.time_range.end,
                    'timeseries_data': timeseries.get('data_points', []),
                    'avg_power_kw': avg_power,
                    'interval': interval
                }
            else:
                print(f"  → Calling /machines/status/{intent.machine} (power for specific machine)")
                data = await api_client.get_machine_status(intent.machine)
                api_data = data
        else:
            print("  → Calling /stats/system (factory-wide power)")
            data = await api_client.system_stats()
            api_data = data
            
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
            print(f"  → Calling /machines/status/{machine} (machine-specific cost)")
            data = await api_client.get_machine_status(machine)
            api_data = data
        else:
            print("  → Calling /stats/system (factory-wide cost)")
            data = await api_client.system_stats()
            api_data = data
        
    elif intent.intent == IntentType.RANKING:
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
            import re
            for pattern in search_patterns:
                match = re.search(pattern, utterance, re.IGNORECASE)
                if match:
                    search_term = match.group(1).rstrip('s')  # Remove plural 's'
                    break
            
            if search_term:
                print(f"  → Calling /machines (search={search_term})")
                data = await api_client.list_machines(search=search_term)
            else:
                print("  → Calling /machines (list all machines)")
                data = await api_client.list_machines()
            api_data = {'machines': data, 'count': len(data)}
        else:
            limit = intent.limit or 5
            metric = getattr(intent, 'ranking_metric', 'energy') or getattr(intent, 'metric', 'energy') or 'energy'
            print(f"  → Calling /analytics/top-consumers (limit={limit}, metric={metric})")
            data = await api_client.get_top_consumers(limit=limit, metric=metric)
            api_data = data
    
    elif intent.intent == IntentType.ANOMALY_DETECTION:
        # Check what type of anomaly query this is
        utterance = getattr(intent, 'utterance', '').lower()
        is_detection_request = any(kw in utterance for kw in ['check for', 'detect', 'scan for', 'analyze for']) and intent.machine
        is_active_request = any(kw in utterance for kw in ['active', 'unresolved', 'alerts', 'need attention'])
        is_search_request = any(kw in utterance for kw in ['find', 'search']) and intent.time_range and intent.time_range.start
        
        # Extract severity from utterance
        severity = None
        if 'critical' in utterance:
            severity = 'critical'
        elif 'warning' in utterance or 'warn' in utterance:
            severity = 'warning'
        elif 'info' in utterance or 'information' in utterance:
            severity = 'info'
        
        if is_detection_request:
            print(f"  → Calling POST /anomaly/detect (ML detection for {intent.machine})")
            machines_list = await api_client.list_machines(search=intent.machine)
            if not machines_list:
                print(f"  ❌ Machine {intent.machine} not found")
                return
            
            machine_id = machines_list[0]['id']
            
            # Get time range (default: today)
            from datetime import datetime, timezone
            if intent.time_range and intent.time_range.start and intent.time_range.end:
                start_time = intent.time_range.start
                end_time = intent.time_range.end
            else:
                end_time = datetime.now(timezone.utc)
                start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
            
            data = await api_client.detect_anomalies(
                machine_id=machine_id,
                start=start_time,
                end=end_time
            )
            data['machine_name'] = intent.machine
            data['is_detection'] = True
            api_data = data
        
        elif is_active_request:
            print("  → Calling GET /anomaly/active (unresolved anomalies)")
            data = await api_client.get_active_anomalies()
            data['is_active'] = True
            api_data = data
        
        elif is_search_request:
            print(f"  → Calling GET /anomaly/search (date range: {intent.time_range.start.date()} to {intent.time_range.end.date()})")
            machine_id = None
            if intent.machine:
                machines_list = await api_client.list_machines(search=intent.machine)
                if machines_list:
                    machine_id = machines_list[0]['id']
            
            data = await api_client.search_anomalies(
                start_time=intent.time_range.start,
                end_time=intent.time_range.end,
                machine_id=machine_id,
                severity=severity,
                limit=50
            )
            if intent.machine:
                data['machine_name'] = intent.machine
            api_data = data
        
        elif intent.machine:
            print(f"  → Calling GET /anomaly/recent (list recent for {intent.machine})")
            machines_list = await api_client.list_machines(search=intent.machine)
            if not machines_list:
                print(f"  ❌ Machine {intent.machine} not found")
                return
            
            machine_id = machines_list[0]['id']
            print(f"  → Calling GET /anomaly/recent (list recent for {intent.machine}, severity={severity})")
            data = await api_client.get_recent_anomalies(
                machine_id=machine_id,
                severity=severity,
                limit=10
            )
            data['machine_name'] = intent.machine
            api_data = data
        else:
            print(f"  → Calling GET /anomaly/recent (factory-wide, severity={severity})")
            data = await api_client.get_recent_anomalies(
                severity=severity,
                limit=10
            )
            
            # Extract unique affected machines from anomalies list
            if 'anomalies' in data and isinstance(data['anomalies'], list):
                affected_machines = list(set(
                    anomaly.get('machine_name') 
                    for anomaly in data['anomalies'] 
                    if anomaly.get('machine_name')
                ))
                data['affected_machines'] = sorted(affected_machines)
            
            api_data = data
    
    elif intent.intent == IntentType.FACTORY_OVERVIEW:
        utterance = getattr(intent, 'utterance', '').lower()
        
        print(f"  [DEBUG] utterance='{utterance}', has time_range={intent.time_range is not None}")
        
        if 'performance engine' in utterance or 'engine' in utterance:
            print("  → Calling GET /performance/health (engine status)")
            data = await api_client.get_performance_health()
            api_data = data
            custom_template = 'performance_health'
        elif 'opportunities' in utterance or 'saving' in utterance:
            print("  → Calling GET /performance/opportunities")
            # Get factory_id
            machines = await api_client.list_machines()
            factory_id = machines[0]['factory_id'] if machines else None
            
            data = await api_client.get_performance_opportunities(
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
            
            api_data = data
            custom_template = 'opportunities'
        elif 'action plan' in utterance and 'list' in utterance:
            # List ISO action plans (check BEFORE create action plan)
            status_filter = None
            priority_filter = None
            
            if 'completed' in utterance or 'complete' in utterance:
                status_filter = 'completed'
            elif 'in progress' in utterance or 'active' in utterance:
                status_filter = 'in_progress'
            elif 'planned' in utterance:
                status_filter = 'planned'
            
            if 'high priority' in utterance or 'critical' in utterance:
                priority_filter = 'high' if 'high' in utterance else 'critical'
            
            machines = await api_client.list_machines()
            factory_id = machines[0]['factory_id'] if machines else "11111111-1111-1111-1111-111111111111"
            
            print(f"  → Calling GET /iso50001/action-plans (status={status_filter}, priority={priority_filter})")
            data = await api_client.list_action_plans(
                factory_id=factory_id,
                status=status_filter,
                priority=priority_filter
            )
            api_data = data
            custom_template = 'action_plans_list'
        elif 'action plan' in utterance or 'create plan' in utterance:
            print("  → Calling POST /performance/action-plan")
            if not intent.machine:
                return None, "Machine name required for action plan"
            
            # Determine issue type
            issue_type = 'inefficient_scheduling'  # default
            if 'idle' in utterance:
                issue_type = 'excessive_idle'
            elif 'drift' in utterance or 'degradation' in utterance or 'efficiency' in utterance:
                issue_type = 'baseline_drift'
            elif 'setpoint' in utterance or 'setting' in utterance:
                issue_type = 'suboptimal_setpoints'
            
            data = await api_client.create_action_plan(
                seu_name=intent.machine,
                issue_type=issue_type
            )
            api_data = data
            custom_template = 'action_plan'
        elif any(kw in utterance for kw in ['online', 'health', 'status of', 'system status', 'running', 'database']):
            print("  → Calling GET /health (health check)")
            data = await api_client.health_check()
            api_data = data
            custom_template = None
        elif 'summary' in utterance:
            print("  → Calling GET /factory/summary")
            data = await api_client.factory_summary()
            api_data = data
            custom_template = 'factory_summary'
        elif 'significant energy' in utterance or 'list seus' in utterance or 'energy uses' in utterance:
            # List SEUs
            energy_source = None
            if 'electricity' in utterance or 'electric' in utterance:
                energy_source = 'electricity'
            elif 'gas' in utterance or 'natural gas' in utterance:
                energy_source = 'natural_gas'
            elif 'steam' in utterance:
                energy_source = 'steam'
            
            print(f"  → Calling GET /seus (energy_source={energy_source or 'all'})")
            data = await api_client.list_seus(energy_source=energy_source)
            api_data = data
            custom_template = 'seus_list'
        elif 'enpi' in utterance or 'iso' in utterance or 'compliance report' in utterance or 'energy performance indicator' in utterance:
            # ISO 50001 EnPI report
            import re
            from datetime import datetime
            
            period = None
            
            # Check for quarters
            quarter_match = re.search(r'q[1-4]|quarter\s*[1-4]', utterance, re.IGNORECASE)
            if quarter_match:
                quarter_text = quarter_match.group().lower()
                quarter_num = re.search(r'[1-4]', quarter_text).group()
                year_match = re.search(r'20\d{2}', utterance)
                year = year_match.group() if year_match else str(datetime.now().year)
                period = f"{year}-Q{quarter_num}"
            else:
                year_match = re.search(r'20\d{2}', utterance)
                if year_match:
                    period = year_match.group()
                else:
                    now = datetime.now()
                    current_quarter = (now.month - 1) // 3 + 1
                    period = f"{now.year}-Q{current_quarter}"
            
            # Get factory_id
            machines = await api_client.list_machines()
            factory_id = machines[0]['factory_id'] if machines else "11111111-1111-1111-1111-111111111111"
            
            print(f"  → Calling GET /iso50001/enpi-report (factory_id={factory_id[:8]}..., period={period})")
            data = await api_client.get_enpi_report(
                factory_id=factory_id,
                period=period
            )
            api_data = data
            custom_template = 'enpi_report'
        elif 'aggregat' in utterance and intent.time_range:
            print(f"  → Calling GET /stats/aggregated (time_range={intent.time_range.relative})")
            data = await api_client.aggregated_stats(
                start_time=intent.time_range.start,
                end_time=intent.time_range.end,
                machine_ids='all'
            )
            # Use aggregated_stats template
            api_data = data
            custom_template = 'aggregated_stats'
        else:
            print("  → Calling GET /stats/system (factory stats)")
            data = await api_client.system_stats()
            api_data = data
            custom_template = None
    
    elif intent.intent == IntentType.BASELINE_MODELS:
        if not intent.machine:
            print("  ⚠️  BASELINE_MODELS requires machine name")
            return
        
        print(f"  → Calling GET /baseline/models (list models for {intent.machine})")
        
        response = await api_client.list_baseline_models(
            seu_name=intent.machine,
            energy_source="electricity"
        )
        
        # Process to match __init__.py logic
        models = response.get('models', [])
        active_model = next((m for m in models if m.get('is_active')), models[0] if models else None)
        
        api_data = {
            'seu_name': response.get('seu_name', intent.machine),
            'models': models,
            'active_version': active_model.get('model_version') if active_model else None,
            'active_r_squared': active_model.get('r_squared') if active_model else None,
            'active_samples': active_model.get('training_samples') if active_model else None
        }
    
    elif intent.intent == IntentType.BASELINE:
        machine = intent.machine
        machines = intent.machines if intent.machines else []
        
        if not machine and not machines:
            print("  ⚠️  BASELINE requires machine name")
            print("  ℹ️  OVOS would ask: 'Which machine?'")
            print("  ℹ️  Or use conversation context from previous query")
            return
        
        # Extract features from utterance (temperature, pressure, load, production)
        features = FeatureExtractor.extract_all_features(
            query_text,
            defaults={
                "total_production_count": 5000000,
                "avg_outdoor_temp_c": 22.0,
                "avg_pressure_bar": 7.0,
                "avg_load_factor": 0.85
            }
        )
        
        # Handle multiple machines (ambiguous query)
        if machines:
            print(f"  → Calling POST /baseline/predict for {len(machines)} machines: {', '.join(machines)}")
            predictions = []
            
            for seu_name in machines:
                try:
                    prediction = await api_client.predict_baseline(
                        seu_name=seu_name,
                        energy_source="electricity",
                        features=features,
                        include_message=False
                    )
                    prediction['seu_name'] = seu_name
                    predictions.append(prediction)
                except Exception as e:
                    print(f"  ⚠️  Failed to get prediction for {seu_name}: {e}")
            
            api_data = {
                'predictions': predictions,
                'features': features,
                'machine_count': len(predictions)
            }
        else:
            # Single machine
            print(f"  → Calling POST /baseline/predict (baseline prediction for {machine})")
            
            data = await api_client.predict_baseline(
                seu_name=machine,
                energy_source="electricity",
                features=features,
                include_message=False  # Don't use API message, we format with features
            )
            
            # Add SEU name and features to response for template
            data['seu_name'] = machine
            data['features'] = features
            
            api_data = data
    
    elif intent.intent == IntentType.KPI:
        machine = intent.machine
        
        if not machine:
            print("  ⚠️  KPI requires machine name")
            return
        
        print(f"  → Calling GET /kpi/all (KPIs for {machine})")
        
        # Get time range (default to today)
        if intent.time_range and intent.time_range.start:
            start_time = intent.time_range.start
            end_time = intent.time_range.end if intent.time_range.end else datetime.now(timezone.utc)
        else:
            start_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            end_time = datetime.now(timezone.utc)
        
        # Get machine ID
        machines = await api_client.list_machines(search=machine)
        if not machines or len(machines) == 0:
            print(f"  ❌ Machine {machine} not found")
            return
        
        machine_id = machines[0]['id']
        
        data = await api_client.get_all_kpis(
            machine_id=machine_id,
            start_time=start_time,
            end_time=end_time
        )
        api_data = data
    
    elif intent.intent == IntentType.PERFORMANCE:
        machine = intent.machine
        
        if not machine:
            print("  ⚠️  PERFORMANCE requires machine name")
            return
        
        print(f"  → Calling POST /performance/analyze ({machine})")
        
        # Use "energy" as default energy source
        energy_source = "energy"
        
        # Get analysis date (default: today)
        from datetime import date
        analysis_date = date.today().isoformat()
        
        data = await api_client.analyze_performance(
            seu_name=machine,
            energy_source=energy_source,
            analysis_date=analysis_date
        )
        api_data = data
    
    elif intent.intent == IntentType.FORECAST:
        # Check if this is a demand forecast
        utterance = getattr(intent, 'utterance', '').lower()
        is_demand_forecast = 'demand' in utterance or 'detailed' in utterance
        
        if is_demand_forecast and intent.machine:
            print(f"  → Calling /forecast/demand (detailed ARIMA forecast for {intent.machine})")
            # Lookup machine ID
            machines = await api_client.list_machines(search=intent.machine)
            if not machines:
                print(f"  ❌ Machine {intent.machine} not found")
                return
            machine_id = machines[0]['id']
            
            data = await api_client.forecast_demand(machine_id=machine_id, horizon="short", periods=4)
            data['machine_name'] = intent.machine
            api_data = data
            custom_template = 'demand_forecast'
        else:
            print(f"  → Calling /forecast/short-term (forecast for {intent.machine or 'factory'})")
            data = await api_client.get_forecast(machine=intent.machine, hours=24)
            api_data = data
    
    elif intent.intent == IntentType.PRODUCTION:
        if not intent.machine:
            print(f"  ⚠️  PRODUCTION requires machine name")
            return
        print(f"  → Calling /machines/status/{intent.machine} (production data)")
        data = await api_client.get_machine_status(intent.machine)
        api_data = data
    
    elif intent.intent == IntentType.COMPARISON:
        if not intent.machines or len(intent.machines) < 2:
            print(f"  ⚠️  COMPARISON requires at least 2 machines")
            return
        
        print(f"  → Calling /timeseries/multi-machine/energy (compare {intent.machines})")
        
        # Get machine IDs
        machine_ids = []
        machine_names = []
        for machine_name in intent.machines:
            machines = await api_client.list_machines(search=machine_name)
            if machines:
                machine_ids.append(machines[0]['id'])
                machine_names.append(machines[0]['name'])
        
        if len(machine_ids) < 2:
            print(f"  ⚠️  Could not find all machines")
            return
        
        # Get time range (default: today)
        from datetime import datetime, timezone
        end_time = datetime.now(timezone.utc)
        start_time = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Call API
        data = await api_client.get_multi_machine_energy(
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
        # Use custom template if specified
        if 'custom_template' in locals() and custom_template:
            print(f"  → Using custom template: {custom_template}.dialog")
            template = formatter.env.get_template(f'{custom_template}.dialog')
            response_text = template.render(**api_data).strip()
        # Special handling for health check responses within factory_overview
        elif intent.intent == IntentType.FACTORY_OVERVIEW and 'status' in api_data and 'database' in api_data:
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
                context={
                    "machine_name": intent.machine,
                    "utterance": getattr(intent, 'utterance', '').lower()
                } if intent.machine or hasattr(intent, 'utterance') else {}
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
