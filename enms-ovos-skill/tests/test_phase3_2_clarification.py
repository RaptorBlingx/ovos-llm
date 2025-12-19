"""
Test Suite for Phase 3.2 - Clarification Prompts

Tests that clarification prompts are properly generated and handled:
- Ambiguous machine name detection
- Clarification prompt generation (2 options, 3 options, 4+ options)
- Clarification response parsing (direct name, number, ordinal, reference)
- Multi-turn clarification flows
- Integration with session context

Run with:
    python3 tests/test_phase3_2_clarification.py
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from enms_ovos_skill.lib.conversation_context import ConversationContextManager, ConversationSession
from enms_ovos_skill.lib.models import Intent, IntentType
from datetime import datetime

# ANSI color codes for pretty output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def test_ambiguous_machine_2_options():
    """Test clarification prompt for 2 ambiguous machines"""
    print(f"\n{BLUE}Test 1: Ambiguous Machine (2 options){RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    # Intent with ambiguous machine (matches 2 machines)
    intent = Intent(
        intent=IntentType.ENERGY_QUERY,
        machine="compressor",  # Ambiguous!
        confidence=0.95,
        utterance="Energy for compressor"
    )
    
    ambiguous_machines = ["Compressor-1", "Compressor-EU-1"]
    
    # Check clarification needed
    clarification = manager.needs_clarification(intent, ambiguous_machines)
    
    assert clarification is not None, "Clarification should be needed for ambiguous machine"
    assert clarification['type'] == 'machine_ambiguous'
    assert clarification['options'] == ambiguous_machines
    assert "Compressor-1" in clarification['message']
    assert "Compressor-EU-1" in clarification['message']
    
    print(f"{GREEN}✓ Clarification message: {clarification['message']}{RESET}")
    return True


def test_ambiguous_machine_3_options():
    """Test clarification prompt for 3 ambiguous machines"""
    print(f"\n{BLUE}Test 2: Ambiguous Machine (3 options){RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    
    intent = Intent(
        intent=IntentType.POWER_QUERY,
        machine="boiler",
        confidence=0.95,
        utterance="Power for boiler"
    )
    
    ambiguous_machines = ["Boiler-1", "Boiler-2", "Boiler-3"]
    
    clarification = manager.needs_clarification(intent, ambiguous_machines)
    
    assert clarification is not None
    assert clarification['type'] == 'machine_ambiguous'
    assert len(clarification['options']) == 3
    assert all(m in clarification['message'] for m in ambiguous_machines)
    
    print(f"{GREEN}✓ Clarification message: {clarification['message']}{RESET}")
    return True


def test_ambiguous_machine_4plus_options():
    """Test clarification prompt for 4+ ambiguous machines (numbered list)"""
    print(f"\n{BLUE}Test 3: Ambiguous Machine (4+ options - numbered list){RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    
    intent = Intent(
        intent=IntentType.POWER_QUERY,
        machine="machine",
        confidence=0.95,
        utterance="Power for machine"
    )
    
    ambiguous_machines = ["Machine-1", "Machine-2", "Machine-3", "Machine-4", "Machine-5"]
    
    clarification = manager.needs_clarification(intent, ambiguous_machines)
    
    assert clarification is not None
    assert clarification['type'] == 'machine_ambiguous'
    assert len(clarification['options']) == 5
    # Should use numbered format for 4+ options
    assert "1." in clarification['message'] or "Which machine" in clarification['message']
    
    print(f"{GREEN}✓ Clarification message (numbered):{RESET}")
    print(f"  {clarification['message']}")
    return True


def test_parse_clarification_direct_name():
    """Test parsing direct machine name as clarification response"""
    print(f"\n{BLUE}Test 4: Parse Clarification - Direct Name{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    
    options = ["Compressor-1", "Compressor-EU-1"]
    
    # Test direct machine name
    result = manager._parse_clarification_response("Compressor-1", options)
    assert result == "Compressor-1", f"Expected 'Compressor-1', got '{result}'"
    
    # Test case-insensitive
    result = manager._parse_clarification_response("compressor-1", options)
    assert result == "Compressor-1", f"Expected 'Compressor-1', got '{result}'"
    
    print(f"{GREEN}✓ Direct name parsed: 'Compressor-1'{RESET}")
    return True


def test_parse_clarification_number():
    """Test parsing number as clarification response"""
    print(f"\n{BLUE}Test 5: Parse Clarification - Number{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    
    options = ["Compressor-1", "Compressor-EU-1", "Boiler-1"]
    
    # Test "1", "2", "3"
    assert manager._parse_clarification_response("1", options) == "Compressor-1"
    assert manager._parse_clarification_response("2", options) == "Compressor-EU-1"
    assert manager._parse_clarification_response("3", options) == "Boiler-1"
    
    # Test "number 2"
    assert manager._parse_clarification_response("number 2", options) == "Compressor-EU-1"
    
    # Test "option 1"
    assert manager._parse_clarification_response("option 1", options) == "Compressor-1"
    
    print(f"{GREEN}✓ Number responses parsed correctly{RESET}")
    return True


def test_parse_clarification_ordinal():
    """Test parsing ordinal as clarification response"""
    print(f"\n{BLUE}Test 6: Parse Clarification - Ordinal{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    
    options = ["HVAC-Main", "HVAC-EU-North", "Boiler-1"]
    
    # Test "first", "second", "third"
    assert manager._parse_clarification_response("first", options) == "HVAC-Main"
    assert manager._parse_clarification_response("second", options) == "HVAC-EU-North"
    assert manager._parse_clarification_response("third", options) == "Boiler-1"
    
    # Test "the first one"
    assert manager._parse_clarification_response("the first one", options) == "HVAC-Main"
    
    # Test "the second"
    assert manager._parse_clarification_response("the second", options) == "HVAC-EU-North"
    
    # Test "second one"
    assert manager._parse_clarification_response("second one", options) == "HVAC-EU-North"
    
    print(f"{GREEN}✓ Ordinal responses parsed correctly{RESET}")
    return True


def test_parse_clarification_the_number():
    """Test parsing 'the 1st', 'the 2nd' patterns"""
    print(f"\n{BLUE}Test 7: Parse Clarification - 'The' + Number{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    
    options = ["Compressor-1", "Compressor-EU-1"]
    
    # Test "the 1"
    assert manager._parse_clarification_response("the 1", options) == "Compressor-1"
    
    # Test "the 1st"
    assert manager._parse_clarification_response("the 1st", options) == "Compressor-1"
    
    # Test "the 2nd"
    assert manager._parse_clarification_response("the 2nd", options) == "Compressor-EU-1"
    
    # Test "the 1st one"
    assert manager._parse_clarification_response("the 1st one", options) == "Compressor-1"
    
    print(f"{GREEN}✓ 'The' + number patterns parsed correctly{RESET}")
    return True


def test_parse_clarification_invalid():
    """Test handling of invalid clarification responses"""
    print(f"\n{BLUE}Test 8: Parse Clarification - Invalid Responses{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    
    options = ["Compressor-1", "Compressor-EU-1"]
    
    # Test invalid number (out of range)
    assert manager._parse_clarification_response("5", options) is None
    
    # Test unrelated text
    assert manager._parse_clarification_response("what?", options) is None
    
    # Test machine not in options
    assert manager._parse_clarification_response("Boiler-1", options) is None
    
    print(f"{GREEN}✓ Invalid responses handled correctly (return None){RESET}")
    return True


def test_multi_turn_clarification_flow():
    """Test complete multi-turn clarification flow"""
    print(f"\n{BLUE}Test 9: Multi-Turn Clarification Flow{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    # Turn 1: Ambiguous query
    intent1 = Intent(
        intent=IntentType.ENERGY_QUERY,
        machine="compressor",
        confidence=0.95,
        utterance="Energy for compressor"
    )
    
    ambiguous_machines = ["Compressor-1", "Compressor-EU-1"]
    
    # Check clarification needed
    clarification = manager.needs_clarification(intent1, ambiguous_machines)
    assert clarification is not None
    
    # Store pending clarification
    session.pending_clarification = {
        'intent': intent1.intent,
        'metric': intent1.metric,
        'options': ambiguous_machines,
        'timestamp': datetime.utcnow().timestamp()
    }
    
    # Turn 2: User responds with "first"
    clarification_response = "first"
    
    # Parse response
    resolved_machine = manager._parse_clarification_response(
        clarification_response,
        session.pending_clarification['options']
    )
    
    assert resolved_machine == "Compressor-1", f"Expected 'Compressor-1', got '{resolved_machine}'"
    
    # Resolve intent
    intent2 = Intent(
        intent=IntentType.ENERGY_QUERY,  # Restored from pending
        machine=resolved_machine,
        confidence=0.99,  # High confidence after clarification
        utterance=clarification_response
    )
    
    # Clear pending clarification
    session.pending_clarification = None
    
    print(f"{GREEN}✓ Multi-turn clarification flow complete:{RESET}")
    print(f"  Turn 1: Ambiguous 'compressor' → Clarification asked")
    print(f"  Turn 2: User said 'first' → Resolved to 'Compressor-1'")
    return True


def test_clarification_with_context():
    """Test clarification interacting with session context"""
    print(f"\n{BLUE}Test 10: Clarification with Session Context{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    # Store context from previous query
    intent_prev = Intent(
        intent=IntentType.POWER_QUERY,
        machine="HVAC-Main",
        confidence=0.95,
        utterance="Power for HVAC-Main"
    )
    session.add_turn("Power for HVAC-Main", intent_prev, "8.5 kW", {'power_kw': 8.5})
    
    # New query: ambiguous
    intent_new = Intent(
        intent=IntentType.ENERGY_QUERY,
        machine="compressor",
        confidence=0.95,
        utterance="What about compressor?"
    )
    
    ambiguous_machines = ["Compressor-1", "Compressor-EU-1"]
    
    # Check clarification needed (should override context)
    clarification = manager.needs_clarification(intent_new, ambiguous_machines)
    
    assert clarification is not None, "Clarification should be needed despite context"
    assert clarification['type'] == 'machine_ambiguous'
    
    # Store pending clarification
    session.pending_clarification = {
        'intent': intent_new.intent,
        'options': ambiguous_machines,
        'timestamp': datetime.utcnow().timestamp()
    }
    
    # User responds
    resolved = manager._parse_clarification_response("Compressor-1", ambiguous_machines)
    assert resolved == "Compressor-1"
    
    print(f"{GREEN}✓ Clarification overrides context when needed{RESET}")
    print(f"  Previous context: HVAC-Main")
    print(f"  Ambiguous query: 'compressor'")
    print(f"  Clarification requested and resolved to: Compressor-1")
    return True


def test_no_clarification_for_exact_match():
    """Test that exact matches don't trigger clarification"""
    print(f"\n{BLUE}Test 11: No Clarification for Exact Match{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    
    # Intent with exact machine name
    intent = Intent(
        intent=IntentType.ENERGY_QUERY,
        machine="Compressor-1",  # Exact match
        confidence=0.95,
        utterance="Energy for Compressor-1"
    )
    
    # No ambiguous machines (already resolved by validator)
    clarification = manager.needs_clarification(intent, ambiguous_machines=None)
    
    assert clarification is None, "Exact match should not need clarification"
    
    print(f"{GREEN}✓ Exact match bypasses clarification{RESET}")
    return True


def test_clarification_missing_machine():
    """Test clarification when machine is completely missing"""
    print(f"\n{BLUE}Test 12: Clarification for Missing Machine{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    
    # Intent with no machine specified
    intent = Intent(
        intent=IntentType.MACHINE_STATUS,  # Requires machine
        machine=None,
        confidence=0.95,
        utterance="What's the status?"
    )
    
    clarification = manager.needs_clarification(intent, ambiguous_machines=None)
    
    assert clarification is not None
    assert clarification['type'] == 'machine_missing'
    assert "which machine" in clarification['message'].lower()
    
    print(f"{GREEN}✓ Missing machine clarification: {clarification['message']}{RESET}")
    return True


def test_generate_clarification_response():
    """Test full clarification response generation"""
    print(f"\n{BLUE}Test 13: Generate Clarification Response{RESET}")
    
    manager = ConversationContextManager(session_timeout_minutes=30)
    session = manager.get_or_create_session("test_user")
    
    # Intent with ambiguous machine
    intent = Intent(
        intent=IntentType.ENERGY_QUERY,
        machine="compressor",
        confidence=0.95,
        utterance="Energy for compressor"
    )
    
    ambiguous_machines = ["Compressor-1", "Compressor-EU-1"]
    
    # Generate clarification response
    response = manager.generate_clarification_response(
        intent, session, 
        validation_suggestions=None, 
        ambiguous_machines=ambiguous_machines
    )
    
    assert "Compressor-1" in response
    assert "Compressor-EU-1" in response
    assert response.startswith("Did you mean")
    
    print(f"{GREEN}✓ Clarification response: {response}{RESET}")
    return True


def run_all_tests():
    """Run all Phase 3.2 tests"""
    print(f"\n{YELLOW}{'='*70}{RESET}")
    print(f"{YELLOW}Phase 3.2 - Clarification Prompts Tests{RESET}")
    print(f"{YELLOW}{'='*70}{RESET}")
    
    tests = [
        ("Ambiguous Machine (2 options)", test_ambiguous_machine_2_options),
        ("Ambiguous Machine (3 options)", test_ambiguous_machine_3_options),
        ("Ambiguous Machine (4+ options)", test_ambiguous_machine_4plus_options),
        ("Parse Clarification - Direct Name", test_parse_clarification_direct_name),
        ("Parse Clarification - Number", test_parse_clarification_number),
        ("Parse Clarification - Ordinal", test_parse_clarification_ordinal),
        ("Parse Clarification - 'The' + Number", test_parse_clarification_the_number),
        ("Parse Clarification - Invalid", test_parse_clarification_invalid),
        ("Multi-Turn Clarification Flow", test_multi_turn_clarification_flow),
        ("Clarification with Context", test_clarification_with_context),
        ("No Clarification for Exact Match", test_no_clarification_for_exact_match),
        ("Clarification for Missing Machine", test_clarification_missing_machine),
        ("Generate Clarification Response", test_generate_clarification_response),
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
