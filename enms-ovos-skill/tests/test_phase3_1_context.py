"""
Test Suite for Phase 3.1 - Session Context Management

Tests that conversation context is properly maintained across queries:
- Context storage after successful queries
- Context retrieval for follow-up queries
- Machine context carryover
- Metric context carryover
- Time range context carryover
- Multi-turn conversations

Run with:
    python3 tests/test_phase3_1_context.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from enms_ovos_skill.lib.conversation_context import ConversationContextManager, ConversationSession
from enms_ovos_skill.lib.models import Intent, IntentType, TimeRange
from datetime import datetime, timedelta

# ANSI color codes for pretty output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def test_context_storage():
    """Test that context is stored after queries"""
    print(f"\n{BLUE}Test 1: Context Storage{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    # Simulate first query: "Energy for Compressor-1"
    intent = Intent(
        intent=IntentType.ENERGY_QUERY,
        machine="Compressor-1",
        metric="energy",
        confidence=0.95,
        utterance="Energy for Compressor-1"
    )
    
    session.add_turn(
        query="Energy for Compressor-1",
        intent=intent,
        response="Compressor-1 consumed 120 kWh today",
        api_data={'energy_kwh': 120}
    )
    
    # Verify context stored
    assert session.last_machine == "Compressor-1", f"Expected last_machine='Compressor-1', got '{session.last_machine}'"
    assert session.last_metric == "energy", f"Expected last_metric='energy', got '{session.last_metric}'"
    assert session.last_intent == IntentType.ENERGY_QUERY
    assert len(session.history) == 1
    
    print(f"{GREEN}✓ Context stored: machine={session.last_machine}, metric={session.last_metric}{RESET}")
    return True


def test_context_retrieval_machine():
    """Test that machine context is retrieved for follow-up queries"""
    print(f"\n{BLUE}Test 2: Machine Context Retrieval{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    # First query: "Energy for Compressor-1"
    intent1 = Intent(
        intent=IntentType.ENERGY_QUERY,
        machine="Compressor-1",
        metric="energy",
        confidence=0.95,
        utterance="Energy for Compressor-1"
    )
    session.add_turn("Energy for Compressor-1", intent1, "120 kWh", {'energy_kwh': 120})
    
    # Second query: "What about yesterday?" (no machine specified)
    # Handler should retrieve machine from context
    retrieved_machine = session.last_machine
    
    assert retrieved_machine == "Compressor-1", f"Expected 'Compressor-1' from context, got '{retrieved_machine}'"
    
    print(f"{GREEN}✓ Machine retrieved from context: {retrieved_machine}{RESET}")
    return True


def test_context_retrieval_metric():
    """Test that metric context is retrieved for follow-up queries"""
    print(f"\n{BLUE}Test 3: Metric Context Retrieval{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    # First query: "Power for HVAC-Main"
    intent1 = Intent(
        intent=IntentType.POWER_QUERY,
        machine="HVAC-Main",
        metric="power",
        confidence=0.95,
        utterance="Power for HVAC-Main"
    )
    session.add_turn("Power for HVAC-Main", intent1, "8.5 kW", {'power_kw': 8.5})
    
    # Verify metric stored
    assert session.last_metric == "power", f"Expected 'power', got '{session.last_metric}'"
    
    print(f"{GREEN}✓ Metric retrieved from context: {session.last_metric}{RESET}")
    return True


def test_multi_turn_conversation():
    """Test multi-turn conversation flow"""
    print(f"\n{BLUE}Test 4: Multi-Turn Conversation{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    # Turn 1: "Status of Compressor-1"
    intent1 = Intent(
        intent=IntentType.POWER_QUERY,
        machine="Compressor-1",
        confidence=0.95,
        utterance="Status of Compressor-1"
    )
    session.add_turn("Status of Compressor-1", intent1, "Compressor-1 is using 47.3 kW", {'power_kw': 47.3})
    
    # Turn 2: "How about yesterday?" (uses machine from context)
    assert session.last_machine == "Compressor-1"
    
    intent2 = Intent(
        intent=IntentType.ENERGY_QUERY,
        machine="Compressor-1",  # Retrieved from context
        confidence=0.95,
        utterance="How about yesterday?"
    )
    session.add_turn("How about yesterday?", intent2, "Yesterday consumed 1100 kWh", {'energy_kwh': 1100})
    
    # Turn 3: "And the cost?" (uses machine from context)
    assert session.last_machine == "Compressor-1"
    
    intent3 = Intent(
        intent=IntentType.COST_ANALYSIS,
        machine="Compressor-1",  # Retrieved from context
        confidence=0.95,
        utterance="And the cost?"
    )
    session.add_turn("And the cost?", intent3, "Cost was $165", {'cost_usd': 165})
    
    # Verify history
    assert len(session.history) == 3, f"Expected 3 turns, got {len(session.history)}"
    assert session.history[0].query == "Status of Compressor-1"
    assert session.history[1].query == "How about yesterday?"
    assert session.history[2].query == "And the cost?"
    
    print(f"{GREEN}✓ Multi-turn conversation: 3 turns tracked{RESET}")
    print(f"  Turn 1: {session.history[0].query}")
    print(f"  Turn 2: {session.history[1].query}")
    print(f"  Turn 3: {session.history[2].query}")
    return True


def test_session_timeout():
    """Test that sessions expire after timeout"""
    print(f"\n{BLUE}Test 5: Session Timeout{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=0)  # Immediate timeout
    session = manager.get_or_create_session("test_user")
    
    # Add a turn
    intent = Intent(
        intent=IntentType.ENERGY_QUERY,
        machine="Compressor-1",
        confidence=0.95,
        utterance="Energy for Compressor-1"
    )
    session.add_turn("Energy for Compressor-1", intent, "120 kWh", {'energy_kwh': 120})
    
    # Wait and check if expired
    import time
    time.sleep(1)
    
    is_expired = session.is_expired()
    assert is_expired, "Session should be expired after timeout"
    
    print(f"{GREEN}✓ Session timeout works: expired={is_expired}{RESET}")
    return True


def test_context_machine_update():
    """Test that machine context updates with each new query"""
    print(f"\n{BLUE}Test 6: Context Machine Update{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    # Query 1: Compressor-1
    intent1 = Intent(
        intent=IntentType.ENERGY_QUERY,
        machine="Compressor-1",
        confidence=0.95,
        utterance="Energy for Compressor-1"
    )
    session.add_turn("Energy for Compressor-1", intent1, "120 kWh", {'energy_kwh': 120})
    assert session.last_machine == "Compressor-1"
    
    # Query 2: HVAC-Main (should update context)
    intent2 = Intent(
        intent=IntentType.POWER_QUERY,
        machine="HVAC-Main",
        confidence=0.95,
        utterance="Power for HVAC-Main"
    )
    session.add_turn("Power for HVAC-Main", intent2, "8.5 kW", {'power_kw': 8.5})
    assert session.last_machine == "HVAC-Main", f"Expected 'HVAC-Main', got '{session.last_machine}'"
    
    print(f"{GREEN}✓ Machine context updated: Compressor-1 → HVAC-Main{RESET}")
    return True


def test_context_comparison_machines():
    """Test that comparison queries store multiple machines"""
    print(f"\n{BLUE}Test 7: Comparison Machines Context{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    # Comparison query: "Compare Compressor-1 and Boiler-1"
    intent = Intent(
        intent=IntentType.COMPARISON,
        machines=["Compressor-1", "Boiler-1"],
        metric="energy",
        confidence=0.95,
        utterance="Compare Compressor-1 and Boiler-1"
    )
    session.add_turn("Compare Compressor-1 and Boiler-1", intent, 
                     "Compressor-1 used 120 kWh, Boiler-1 used 85 kWh",
                     {'machines': [{'name': 'Compressor-1', 'energy_kwh': 120}, 
                                   {'name': 'Boiler-1', 'energy_kwh': 85}]})
    
    # Verify both machines stored
    assert session.last_machines == ["Compressor-1", "Boiler-1"], \
        f"Expected both machines, got {session.last_machines}"
    
    print(f"{GREEN}✓ Multiple machines stored: {session.last_machines}{RESET}")
    return True


def test_context_summary():
    """Test context summary for debugging"""
    print(f"\n{BLUE}Test 8: Context Summary{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    # Add some turns
    intent1 = Intent(
        intent=IntentType.ENERGY_QUERY,
        machine="Compressor-1",
        metric="energy",
        confidence=0.95,
        utterance="Energy for Compressor-1"
    )
    session.add_turn("Energy for Compressor-1", intent1, "120 kWh", {'energy_kwh': 120})
    
    intent2 = Intent(
        intent=IntentType.POWER_QUERY,
        machine="Compressor-1",
        metric="power",
        confidence=0.95,
        utterance="What's the power?"
    )
    session.add_turn("What's the power?", intent2, "47.3 kW", {'power_kw': 47.3})
    
    # Get summary
    summary = session.get_context_summary()
    
    assert summary['session_id'] == "test_user"
    assert summary['turn_count'] == 2
    assert summary['last_machine'] == "Compressor-1"
    assert summary['last_metric'] == "power"
    assert summary['last_intent'] == IntentType.POWER_QUERY.value
    
    print(f"{GREEN}✓ Context summary generated:{RESET}")
    print(f"  Session ID: {summary['session_id']}")
    print(f"  Turns: {summary['turn_count']}")
    print(f"  Last machine: {summary['last_machine']}")
    print(f"  Last metric: {summary['last_metric']}")
    return True


def test_manager_multiple_sessions():
    """Test that manager handles multiple sessions"""
    print(f"\n{BLUE}Test 9: Multiple Sessions{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    
    # User 1
    session1 = manager.get_or_create_session("user1")
    intent1 = Intent(
        intent=IntentType.ENERGY_QUERY,
        machine="Compressor-1",
        confidence=0.95,
        utterance="Energy for Compressor-1"
    )
    session1.add_turn("Energy for Compressor-1", intent1, "120 kWh", {'energy_kwh': 120})
    
    # User 2
    session2 = manager.get_or_create_session("user2")
    intent2 = Intent(
        intent=IntentType.POWER_QUERY,
        machine="HVAC-Main",
        confidence=0.95,
        utterance="Power for HVAC-Main"
    )
    session2.add_turn("Power for HVAC-Main", intent2, "8.5 kW", {'power_kw': 8.5})
    
    # Verify sessions are separate
    assert session1.last_machine == "Compressor-1"
    assert session2.last_machine == "HVAC-Main"
    assert len(manager.sessions) == 2
    
    print(f"{GREEN}✓ Multiple sessions isolated:{RESET}")
    print(f"  User1: {session1.last_machine}")
    print(f"  User2: {session2.last_machine}")
    return True


def test_history_limit():
    """Test that history is limited to max_history"""
    print(f"\n{BLUE}Test 10: History Limit{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    session.max_history = 5  # Set limit to 5
    
    # Add 10 turns
    for i in range(10):
        intent = Intent(
            intent=IntentType.ENERGY_QUERY,
            machine=f"Machine-{i}",
            confidence=0.95,
            utterance=f"Query {i}"
        )
        session.add_turn(f"Query {i}", intent, f"Response {i}", {})
    
    # Verify only last 5 turns kept
    assert len(session.history) == 5, f"Expected 5 turns, got {len(session.history)}"
    assert session.history[0].query == "Query 5", "Oldest turn should be Query 5"
    assert session.history[-1].query == "Query 9", "Newest turn should be Query 9"
    
    print(f"{GREEN}✓ History limited to {session.max_history} turns{RESET}")
    print(f"  Oldest: {session.history[0].query}")
    print(f"  Newest: {session.history[-1].query}")
    return True


def run_all_tests():
    """Run all Phase 3.1 tests"""
    print(f"\n{YELLOW}{'='*70}{RESET}")
    print(f"{YELLOW}Phase 3.1 - Session Context Management Tests{RESET}")
    print(f"{YELLOW}{'='*70}{RESET}")
    
    tests = [
        ("Context Storage", test_context_storage),
        ("Machine Context Retrieval", test_context_retrieval_machine),
        ("Metric Context Retrieval", test_context_retrieval_metric),
        ("Multi-Turn Conversation", test_multi_turn_conversation),
        ("Session Timeout", test_session_timeout),
        ("Context Machine Update", test_context_machine_update),
        ("Comparison Machines Context", test_context_comparison_machines),
        ("Context Summary", test_context_summary),
        ("Multiple Sessions", test_manager_multiple_sessions),
        ("History Limit", test_history_limit),
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
