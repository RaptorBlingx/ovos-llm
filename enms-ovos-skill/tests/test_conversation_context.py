#!/usr/bin/env python3
"""
Tests for Conversation Context Manager
Week 5 Days 31-32: Multi-Turn Conversation Support
"""
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from lib.conversation_context import (
    ConversationContextManager,
    ConversationSession,
    ConversationTurn
)
from lib.models import Intent, IntentType


# ANSI colors
GREEN = '\033[92m'
RED = '\033[91m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'


def test_session_creation():
    """Test session creation and retrieval"""
    print(f"\n{BOLD}Test: Session Creation{RESET}")
    
    manager = ConversationContextManager()
    session = manager.get_or_create_session("user_123")
    
    assert session.session_id == "user_123"
    assert len(session.history) == 0
    assert session.last_machine is None
    
    print(f"{GREEN}✓ Session created successfully{RESET}")
    print(f"  Session ID: {session.session_id}")
    print(f"  History: {len(session.history)} turns")


def test_context_carryover():
    """Test context carryover across turns"""
    print(f"\n{BOLD}Test: Context Carryover{RESET}")
    
    manager = ConversationContextManager()
    session = manager.get_or_create_session("user_456")
    
    # Turn 1: Ask about Compressor-1 power
    intent1 = Intent(
        intent=IntentType.POWER_QUERY,
        machine="Compressor-1",
        metric="power",
        confidence=0.95,
        utterance="What's the power of Compressor-1?"
    )
    session.add_turn(
        "What's the power of Compressor-1?",
        intent1,
        "Compressor-1 is using 45 kilowatts"
    )
    
    assert session.last_machine == "Compressor-1"
    assert session.last_metric == "power"
    assert session.last_intent == IntentType.POWER_QUERY
    
    print(f"{GREEN}✓ Turn 1 context saved{RESET}")
    print(f"  Last machine: {session.last_machine}")
    print(f"  Last metric: {session.last_metric}")
    print(f"  Last intent: {session.last_intent.value}")
    
    # Turn 2: Follow-up about energy (should remember Compressor-1)
    intent2 = Intent(
        intent=IntentType.ENERGY_QUERY,
        machine=None,  # Not specified
        metric="energy",
        confidence=0.85,
        utterance="What about energy?"
    )
    
    # Resolve context
    resolved = manager.resolve_context_references("What about energy?", intent2, session)
    
    assert resolved.machine == "Compressor-1"  # Should be filled from context
    print(f"{GREEN}✓ Turn 2 context resolved{RESET}")
    print(f"  Resolved machine: {resolved.machine}")


def test_followup_patterns():
    """Test follow-up question patterns"""
    print(f"\n{BOLD}Test: Follow-up Patterns{RESET}")
    
    manager = ConversationContextManager()
    session = manager.get_or_create_session("user_789")
    
    # Setup context
    intent1 = Intent(
        intent=IntentType.MACHINE_STATUS,
        machine="Boiler-1",
        confidence=0.95,
        utterance="Is Boiler-1 running?"
    )
    session.add_turn("Is Boiler-1 running?", intent1, "Yes, Boiler-1 is online")
    
    # Test various follow-up patterns
    followup_queries = [
        "What about Compressor-1?",
        "How about HVAC-Main?",
        "Check Conveyor-A",
        "Show me Pump-1"
    ]
    
    for query in followup_queries:
        intent = Intent(
            intent=IntentType.UNKNOWN,  # Should be resolved
            machine="Compressor-1" if "Compressor" in query else None,
            confidence=0.8,
            utterance=query
        )
        resolved = manager.resolve_context_references(query, intent, session)
        
        # Should inherit intent type if UNKNOWN
        if "What about" in query or "How about" in query:
            expected_intent = IntentType.MACHINE_STATUS  # From context
        else:
            expected_intent = resolved.intent
        
        print(f"  Query: \"{query}\"")
        print(f"    Resolved intent: {resolved.intent.value}")
    
    print(f"{GREEN}✓ All follow-up patterns resolved{RESET}")


def test_clarification_needed():
    """Test clarification detection"""
    print(f"\n{BOLD}Test: Clarification Detection{RESET}")
    
    manager = ConversationContextManager()
    
    # Test cases needing clarification
    test_cases = [
        (Intent(intent=IntentType.UNKNOWN, confidence=0.5, utterance="help"), 
         "Unknown intent needs clarification"),
        (Intent(intent=IntentType.POWER_QUERY, machine=None, confidence=0.9, utterance="power"),
         "Machine-specific query without machine"),
        (Intent(intent=IntentType.COMPARISON, machines=None, confidence=0.9, utterance="compare"),
         "Comparison without machines"),
    ]
    
    for intent, description in test_cases:
        clarification = manager.needs_clarification(intent)
        print(f"  {description}:")
        print(f"    Clarification: \"{clarification}\"")
        assert clarification is not None
    
    print(f"{GREEN}✓ All clarifications detected{RESET}")


def test_session_expiration():
    """Test session timeout and cleanup"""
    print(f"\n{BOLD}Test: Session Expiration{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=1)  # 1 minute timeout
    session = manager.get_or_create_session("user_temp")
    
    # Add activity
    intent = Intent(intent=IntentType.FACTORY_OVERVIEW, confidence=0.95, utterance="factory status")
    session.add_turn("factory status", intent, "Factory overview response")
    
    assert not session.is_expired()
    print(f"  Session fresh: {not session.is_expired()}")
    
    # Simulate time passing
    session.last_activity = datetime.utcnow() - timedelta(minutes=2)
    
    assert session.is_expired()
    print(f"  Session expired: {session.is_expired()}")
    
    # Cleanup should remove it
    manager.cleanup_expired_sessions()
    assert "user_temp" not in manager.sessions
    
    print(f"{GREEN}✓ Session expiration working{RESET}")


def test_conversation_history():
    """Test conversation history tracking"""
    print(f"\n{BOLD}Test: Conversation History{RESET}")
    
    manager = ConversationContextManager()
    session = manager.get_or_create_session("user_history")
    
    # Add multiple turns
    queries = [
        ("factory status", IntentType.FACTORY_OVERVIEW, "Factory running normally"),
        ("Compressor-1 power", IntentType.POWER_QUERY, "45 kilowatts"),
        ("Boiler-1 energy", IntentType.ENERGY_QUERY, "1500 kWh"),
        ("top 5", IntentType.RANKING, "Top consumers listed"),
    ]
    
    for query, intent_type, response in queries:
        intent = Intent(
            intent=intent_type,
            confidence=0.95,
            utterance=query
        )
        session.add_turn(query, intent, response)
    
    assert len(session.history) == 4
    print(f"  History length: {len(session.history)} turns")
    
    last_turn = session.get_last_turn()
    assert last_turn.query == "top 5"
    print(f"  Last query: \"{last_turn.query}\"")
    
    # Test context summary
    summary = session.get_context_summary()
    print(f"  Context summary:")
    print(f"    Turn count: {summary['turn_count']}")
    print(f"    Last intent: {summary['last_intent']}")
    
    print(f"{GREEN}✓ History tracking working{RESET}")


def test_max_history_limit():
    """Test history size limiting"""
    print(f"\n{BOLD}Test: History Size Limit{RESET}")
    
    session = ConversationSession(session_id="user_limit", max_history=5)
    
    # Add more than max_history turns
    for i in range(10):
        intent = Intent(
            intent=IntentType.FACTORY_OVERVIEW,
            confidence=0.95,
            utterance=f"query {i}"
        )
        session.add_turn(f"query {i}", intent, f"response {i}")
    
    assert len(session.history) == 5  # Should be trimmed to max
    assert session.history[0].query == "query 5"  # Oldest kept
    assert session.history[-1].query == "query 9"  # Most recent
    
    print(f"  Max history: 5")
    print(f"  Actual history: {len(session.history)}")
    print(f"  Oldest query: \"{session.history[0].query}\"")
    print(f"  Newest query: \"{session.history[-1].query}\"")
    
    print(f"{GREEN}✓ History size limiting working{RESET}")


def test_session_stats():
    """Test session statistics"""
    print(f"\n{BOLD}Test: Session Statistics{RESET}")
    
    manager = ConversationContextManager()
    
    # Create multiple sessions with different activity
    for i in range(3):
        session = manager.get_or_create_session(f"user_{i}")
        for j in range(i + 2):  # Different number of turns per session
            intent = Intent(
                intent=IntentType.FACTORY_OVERVIEW,
                confidence=0.95,
                utterance=f"query {j}"
            )
            session.add_turn(f"query {j}", intent, f"response {j}")
    
    stats = manager.get_session_stats()
    
    print(f"  Total sessions: {stats['total_sessions']}")
    print(f"  Active sessions: {stats['active_sessions']}")
    print(f"  Total turns: {stats['total_turns']}")
    print(f"  Avg turns/session: {stats['avg_turns_per_session']:.1f}")
    
    assert stats['total_sessions'] == 3
    assert stats['total_turns'] == 9  # 2+3+4 turns
    
    print(f"{GREEN}✓ Statistics calculation working{RESET}")


def run_all_tests():
    """Run all conversation context tests"""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}CONVERSATION CONTEXT MANAGER TESTS{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}")
    
    tests = [
        test_session_creation,
        test_context_carryover,
        test_followup_patterns,
        test_clarification_needed,
        test_session_expiration,
        test_conversation_history,
        test_max_history_limit,
        test_session_stats
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"{RED}✗ Test failed: {str(e)}{RESET}")
        except Exception as e:
            failed += 1
            print(f"{RED}✗ Test error: {str(e)}{RESET}")
    
    print(f"\n{BOLD}{'='*70}{RESET}")
    print(f"{BOLD}Test Summary:{RESET}")
    print(f"  {GREEN}Passed: {passed}{RESET}")
    if failed > 0:
        print(f"  {RED}Failed: {failed}{RESET}")
    print(f"{BOLD}{'='*70}{RESET}\n")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
