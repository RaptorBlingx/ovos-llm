"""
Test Suite for Phase 3.3 - Smart Defaults Enhancement

Tests that intelligent defaults are properly applied:
- Default time ranges based on intent type
- Default metrics based on intent type
- Factory-wide defaults when no machine specified
- Default aggregation for ranking/comparison
- Default limit for ranking queries
- Integration with session context

Run with:
    python3 tests/test_phase3_3_smart_defaults.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from enms_ovos_skill.lib.conversation_context import ConversationContextManager, ConversationSession
from enms_ovos_skill.lib.models import Intent, IntentType, TimeRange
from datetime import datetime, timezone

# ANSI color codes for pretty output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def test_default_time_range_energy():
    """Test default time range for energy queries (today)"""
    print(f"\n{BLUE}Test 1: Default Time Range - Energy Query{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    # Intent without time range
    intent = Intent(
        intent=IntentType.ENERGY_QUERY,
        machine="Compressor-1",
        confidence=0.95,
        utterance="Energy for Compressor-1"
    )
    
    # Apply smart defaults
    intent_with_defaults = manager.apply_smart_defaults(intent, session)
    
    assert intent_with_defaults.time_range is not None, "Time range should be set"
    assert intent_with_defaults.time_range.relative == 'today', \
        f"Expected 'today', got '{intent_with_defaults.time_range.relative}'"
    
    print(f"{GREEN}✓ Default time range applied: 'today' for ENERGY_QUERY{RESET}")
    return True


def test_default_time_range_power():
    """Test default time range for power queries (now/real-time)"""
    print(f"\n{BLUE}Test 2: Default Time Range - Power Query{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    intent = Intent(
        intent=IntentType.POWER_QUERY,
        machine="HVAC-Main",
        confidence=0.95,
        utterance="Power for HVAC-Main"
    )
    
    intent_with_defaults = manager.apply_smart_defaults(intent, session)
    
    assert intent_with_defaults.time_range is not None
    assert intent_with_defaults.time_range.relative == 'now', \
        f"Expected 'now', got '{intent_with_defaults.time_range.relative}'"
    
    print(f"{GREEN}✓ Default time range applied: 'now' for POWER_QUERY{RESET}")
    return True


def test_default_time_range_anomaly():
    """Test default time range for anomaly detection (last 24 hours)"""
    print(f"\n{BLUE}Test 3: Default Time Range - Anomaly Detection{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    intent = Intent(
        intent=IntentType.ANOMALY_DETECTION,
        machine="Compressor-1",
        confidence=0.95,
        utterance="Any anomalies for Compressor-1?"
    )
    
    intent_with_defaults = manager.apply_smart_defaults(intent, session)
    
    assert intent_with_defaults.time_range is not None
    assert intent_with_defaults.time_range.relative == 'last_24_hours', \
        f"Expected 'last_24_hours', got '{intent_with_defaults.time_range.relative}'"
    
    print(f"{GREEN}✓ Default time range applied: 'last_24_hours' for ANOMALY_DETECTION{RESET}")
    return True


def test_default_time_range_cost():
    """Test default time range for cost analysis (this month)"""
    print(f"\n{BLUE}Test 4: Default Time Range - Cost Analysis{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    intent = Intent(
        intent=IntentType.COST_ANALYSIS,
        machine="Compressor-1",
        confidence=0.95,
        utterance="What's the cost for Compressor-1?"
    )
    
    intent_with_defaults = manager.apply_smart_defaults(intent, session)
    
    assert intent_with_defaults.time_range is not None
    assert intent_with_defaults.time_range.relative == 'this_month', \
        f"Expected 'this_month', got '{intent_with_defaults.time_range.relative}'"
    
    print(f"{GREEN}✓ Default time range applied: 'this_month' for COST_ANALYSIS{RESET}")
    return True


def test_no_override_existing_time_range():
    """Test that existing time range is not overridden"""
    print(f"\n{BLUE}Test 5: No Override of Existing Time Range{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    # Intent with explicit time range
    existing_time_range = TimeRange(
        start=datetime.now(timezone.utc),
        end=datetime.now(timezone.utc),
        relative='yesterday'
    )
    
    intent = Intent(
        intent=IntentType.ENERGY_QUERY,
        machine="Compressor-1",
        time_range=existing_time_range,
        confidence=0.95,
        utterance="Energy for Compressor-1 yesterday"
    )
    
    intent_with_defaults = manager.apply_smart_defaults(intent, session)
    
    assert intent_with_defaults.time_range.relative == 'yesterday', \
        "Existing time range should not be overridden"
    
    print(f"{GREEN}✓ Existing time range preserved: 'yesterday'{RESET}")
    return True


def test_default_metric_energy_query():
    """Test default metric for energy queries"""
    print(f"\n{BLUE}Test 6: Default Metric - Energy Query{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    intent = Intent(
        intent=IntentType.ENERGY_QUERY,
        machine="Compressor-1",
        confidence=0.95,
        utterance="Compressor-1 consumption"
    )
    
    intent_with_defaults = manager.apply_smart_defaults(intent, session)
    
    assert intent_with_defaults.metric == 'energy', \
        f"Expected 'energy', got '{intent_with_defaults.metric}'"
    
    print(f"{GREEN}✓ Default metric applied: 'energy' for ENERGY_QUERY{RESET}")
    return True


def test_default_metric_power_query():
    """Test default metric for power queries"""
    print(f"\n{BLUE}Test 7: Default Metric - Power Query{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    intent = Intent(
        intent=IntentType.POWER_QUERY,
        machine="HVAC-Main",
        confidence=0.95,
        utterance="HVAC-Main status"
    )
    
    intent_with_defaults = manager.apply_smart_defaults(intent, session)
    
    assert intent_with_defaults.metric == 'power', \
        f"Expected 'power', got '{intent_with_defaults.metric}'"
    
    print(f"{GREEN}✓ Default metric applied: 'power' for POWER_QUERY{RESET}")
    return True


def test_default_metric_cost():
    """Test default metric for cost analysis"""
    print(f"\n{BLUE}Test 8: Default Metric - Cost Analysis{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    intent = Intent(
        intent=IntentType.COST_ANALYSIS,
        machine="Compressor-1",
        confidence=0.95,
        utterance="Compressor-1 expenses"
    )
    
    intent_with_defaults = manager.apply_smart_defaults(intent, session)
    
    assert intent_with_defaults.metric == 'cost', \
        f"Expected 'cost', got '{intent_with_defaults.metric}'"
    
    print(f"{GREEN}✓ Default metric applied: 'cost' for COST_ANALYSIS{RESET}")
    return True


def test_no_override_existing_metric():
    """Test that existing metric is not overridden"""
    print(f"\n{BLUE}Test 9: No Override of Existing Metric{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    intent = Intent(
        intent=IntentType.ENERGY_QUERY,
        machine="Compressor-1",
        metric="power",  # Explicit metric different from default
        confidence=0.95,
        utterance="Compressor-1 power consumption"
    )
    
    intent_with_defaults = manager.apply_smart_defaults(intent, session)
    
    assert intent_with_defaults.metric == 'power', \
        "Existing metric should not be overridden"
    
    print(f"{GREEN}✓ Existing metric preserved: 'power'{RESET}")
    return True


def test_factory_wide_default():
    """Test factory-wide default when no machine specified"""
    print(f"\n{BLUE}Test 10: Factory-Wide Default{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    intent = Intent(
        intent=IntentType.ENERGY_QUERY,
        machine=None,  # No machine specified
        confidence=0.95,
        utterance="What's our energy consumption?"
    )
    
    intent_with_defaults = manager.apply_smart_defaults(intent, session)
    
    assert intent_with_defaults.params is not None, "Params should be set"
    assert intent_with_defaults.params.get('factory_wide') is True, \
        "Factory-wide flag should be set"
    
    print(f"{GREEN}✓ Factory-wide default applied for query without machine{RESET}")
    return True


def test_no_factory_wide_for_machine_specific():
    """Test that factory-wide is NOT applied when machine specified"""
    print(f"\n{BLUE}Test 11: No Factory-Wide for Machine-Specific Query{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    intent = Intent(
        intent=IntentType.ENERGY_QUERY,
        machine="Compressor-1",
        confidence=0.95,
        utterance="Compressor-1 energy"
    )
    
    intent_with_defaults = manager.apply_smart_defaults(intent, session)
    
    # Should NOT have factory_wide flag
    factory_wide = intent_with_defaults.params.get('factory_wide') if intent_with_defaults.params else None
    assert factory_wide is None or factory_wide is False, \
        "Factory-wide should not be set for machine-specific query"
    
    print(f"{GREEN}✓ Factory-wide NOT applied for machine-specific query{RESET}")
    return True


def test_default_aggregation_ranking():
    """Test default aggregation for ranking queries"""
    print(f"\n{BLUE}Test 12: Default Aggregation - Ranking{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    intent = Intent(
        intent=IntentType.RANKING,
        confidence=0.95,
        utterance="Top energy consumers"
    )
    
    intent_with_defaults = manager.apply_smart_defaults(intent, session)
    
    assert intent_with_defaults.aggregation == 'total', \
        f"Expected 'total', got '{intent_with_defaults.aggregation}'"
    
    print(f"{GREEN}✓ Default aggregation applied: 'total' for RANKING{RESET}")
    return True


def test_default_limit_ranking():
    """Test default limit for ranking queries"""
    print(f"\n{BLUE}Test 13: Default Limit - Ranking{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    intent = Intent(
        intent=IntentType.RANKING,
        confidence=0.95,
        utterance="Top consumers"
    )
    
    intent_with_defaults = manager.apply_smart_defaults(intent, session)
    
    assert intent_with_defaults.limit == 5, \
        f"Expected limit=5, got {intent_with_defaults.limit}"
    
    print(f"{GREEN}✓ Default limit applied: 5 for RANKING{RESET}")
    return True


def test_no_override_existing_limit():
    """Test that existing limit is not overridden"""
    print(f"\n{BLUE}Test 14: No Override of Existing Limit{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    intent = Intent(
        intent=IntentType.RANKING,
        limit=10,  # Explicit limit
        confidence=0.95,
        utterance="Top 10 consumers"
    )
    
    intent_with_defaults = manager.apply_smart_defaults(intent, session)
    
    assert intent_with_defaults.limit == 10, \
        "Existing limit should not be overridden"
    
    print(f"{GREEN}✓ Existing limit preserved: 10{RESET}")
    return True


def test_multiple_defaults_applied():
    """Test that multiple defaults can be applied simultaneously"""
    print(f"\n{BLUE}Test 15: Multiple Defaults Applied{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    # Intent with no time range, no metric, no limit
    intent = Intent(
        intent=IntentType.RANKING,
        confidence=0.95,
        utterance="Top consumers"
    )
    
    intent_with_defaults = manager.apply_smart_defaults(intent, session)
    
    # Should have all defaults applied
    assert intent_with_defaults.metric == 'energy', "Metric should default to 'energy'"
    assert intent_with_defaults.aggregation == 'total', "Aggregation should default to 'total'"
    assert intent_with_defaults.limit == 5, "Limit should default to 5"
    
    print(f"{GREEN}✓ Multiple defaults applied:{RESET}")
    print(f"  - metric: energy")
    print(f"  - aggregation: total")
    print(f"  - limit: 5")
    return True


def test_defaults_with_context():
    """Test smart defaults interaction with session context"""
    print(f"\n{BLUE}Test 16: Defaults with Session Context{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    # Set context from previous query
    intent_prev = Intent(
        intent=IntentType.ENERGY_QUERY,
        machine="Compressor-1",
        metric="energy",
        confidence=0.95,
        utterance="Compressor-1 energy"
    )
    session.add_turn("Compressor-1 energy", intent_prev, "120 kWh", {'energy_kwh': 120})
    
    # New query without time range
    intent_new = Intent(
        intent=IntentType.ENERGY_QUERY,
        machine="Compressor-1",  # From context
        confidence=0.95,
        utterance="How much?"
    )
    
    intent_with_defaults = manager.apply_smart_defaults(intent_new, session)
    
    # Should have default time range applied
    assert intent_with_defaults.time_range is not None, "Time range should be set by default"
    assert intent_with_defaults.time_range.relative == 'today', "Should default to 'today'"
    
    # Should have default metric
    assert intent_with_defaults.metric == 'energy', "Should have default metric"
    
    print(f"{GREEN}✓ Defaults applied alongside context:{RESET}")
    print(f"  - machine from context: Compressor-1")
    print(f"  - time_range default: today")
    print(f"  - metric default: energy")
    return True


def test_intent_without_defaults():
    """Test that intents without defined defaults are not modified"""
    print(f"\n{BLUE}Test 17: Intent Without Defaults{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    # HELP intent has no defaults
    intent = Intent(
        intent=IntentType.HELP,
        confidence=0.95,
        utterance="Help"
    )
    
    intent_with_defaults = manager.apply_smart_defaults(intent, session)
    
    # Should remain unchanged
    assert intent_with_defaults.time_range is None, "No time range default for HELP"
    assert intent_with_defaults.metric is None, "No metric default for HELP"
    
    print(f"{GREEN}✓ Intent without defaults unchanged{RESET}")
    return True


def run_all_tests():
    """Run all Phase 3.3 tests"""
    print(f"\n{YELLOW}{'='*70}{RESET}")
    print(f"{YELLOW}Phase 3.3 - Smart Defaults Enhancement Tests{RESET}")
    print(f"{YELLOW}{'='*70}{RESET}")
    
    tests = [
        ("Default Time Range - Energy", test_default_time_range_energy),
        ("Default Time Range - Power", test_default_time_range_power),
        ("Default Time Range - Anomaly", test_default_time_range_anomaly),
        ("Default Time Range - Cost", test_default_time_range_cost),
        ("No Override Existing Time Range", test_no_override_existing_time_range),
        ("Default Metric - Energy", test_default_metric_energy_query),
        ("Default Metric - Power", test_default_metric_power_query),
        ("Default Metric - Cost", test_default_metric_cost),
        ("No Override Existing Metric", test_no_override_existing_metric),
        ("Factory-Wide Default", test_factory_wide_default),
        ("No Factory-Wide for Machine-Specific", test_no_factory_wide_for_machine_specific),
        ("Default Aggregation - Ranking", test_default_aggregation_ranking),
        ("Default Limit - Ranking", test_default_limit_ranking),
        ("No Override Existing Limit", test_no_override_existing_limit),
        ("Multiple Defaults Applied", test_multiple_defaults_applied),
        ("Defaults with Session Context", test_defaults_with_context),
        ("Intent Without Defaults", test_intent_without_defaults),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
        except AssertionError as e:
            print(f"{RED}✗ Test failed: {e}{RESET}")
            failed += 1
        except Exception as e:
            print(f"{RED}✗ Test error: {e}{RESET}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # Summary
    print(f"\n{YELLOW}{'='*70}{RESET}")
    total = passed + failed
    percentage = (passed / total * 100) if total > 0 else 0
    
    if failed == 0:
        print(f"{GREEN}All tests passed! {passed}/{total} ({percentage:.1f}%){RESET}")
    else:
        print(f"{RED}Some tests failed. {passed}/{total} passed ({percentage:.1f}%){RESET}")
    
    print(f"{YELLOW}{'='*70}{RESET}\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
