#!/usr/bin/env python3
"""
Tests for Voice Feedback Manager
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lib.voice_feedback import (
    VoiceFeedbackManager, FeedbackType, FeedbackMessage
)


def test_acknowledgments():
    """Test acknowledgment message generation"""
    print("\nTest: Acknowledgment Messages")
    
    manager = VoiceFeedbackManager()
    
    # Test different intent types
    intents = ['factory_overview', 'machine_status', 'power_query', 
               'energy_query', 'comparison', 'ranking']
    
    for intent in intents:
        msg = manager.get_acknowledgment(intent)
        assert msg.type == FeedbackType.ACKNOWLEDGMENT
        assert msg.should_speak is True
        assert len(msg.message) > 0
        print(f"  {intent}: {msg.message}")
    
    print("✓ Acknowledgments generated successfully")


def test_progress_indicators():
    """Test progress indicator logic"""
    print("\nTest: Progress Indicators")
    
    manager = VoiceFeedbackManager(enable_progress=True, progress_threshold_ms=500)
    
    # No progress for fast queries
    msg = manager.get_progress_indicator(100, "fetching")
    assert msg is None
    print("  No progress for 100ms: ✓")
    
    # Progress for slow queries
    msg = manager.get_progress_indicator(600, "fetching")
    if msg:
        assert msg.type == FeedbackType.CHECKING
        print(f"  Progress at 600ms: {msg.message}")
    
    # Progress at 2 second intervals
    msg = manager.get_progress_indicator(2500, "thinking")
    if msg:
        print(f"  Progress at 2500ms: {msg.message}")
    
    print("✓ Progress indicators working")


def test_error_messages():
    """Test error message generation"""
    print("\nTest: Error Messages")
    
    manager = VoiceFeedbackManager()
    
    # Test different error types
    errors = {
        'api_timeout': "Sorry, the server is taking too long",
        'unknown_machine': "I don't recognize that machine name",
        'invalid_query': "I didn't quite understand that",
        'no_data': "I couldn't find any data"
    }
    
    for error_type, expected_substring in errors.items():
        msg = manager.get_error_message(error_type)
        assert msg.type == FeedbackType.ERROR
        assert expected_substring in msg.message
        print(f"  {error_type}: {msg.message}")
    
    # Test with context
    msg = manager.get_error_message('unknown_machine', {'machine': 'Compressor-99'})
    assert 'Compressor-99' in msg.message
    print(f"  With context: {msg.message}")
    
    print("✓ Error messages generated correctly")


def test_confirmation_requests():
    """Test confirmation request generation"""
    print("\nTest: Confirmation Requests")
    
    manager = VoiceFeedbackManager()
    
    # Test different actions
    actions = {
        'shutdown': {'machine': 'Boiler-1'},
        'restart': {'machine': 'Compressor-1'},
        'reset': {'machine': 'HVAC-Main'}
    }
    
    for action, details in actions.items():
        msg = manager.get_confirmation_request(action, details)
        assert msg.type == FeedbackType.CONFIRMATION
        assert action in msg.message or details['machine'] in msg.message
        print(f"  {action}: {msg.message}")
    
    print("✓ Confirmation requests working")


def test_help_responses():
    """Test help system responses"""
    print("\nTest: Help Responses")
    
    manager = VoiceFeedbackManager()
    
    # General help
    msg = manager.get_help_response('general')
    assert msg.type == FeedbackType.HELP
    assert "factory" in msg.message.lower()
    print(f"  General help: {len(msg.message)} chars")
    
    # Example queries
    msg = manager.get_help_response('examples')
    assert "things you can ask" in msg.message
    assert len(manager.help_messages['examples']) > 0
    print(f"  Examples: {len(manager.help_messages['examples'])} queries")
    
    print("✓ Help responses working")


def test_stage_feedback():
    """Test processing stage feedback"""
    print("\nTest: Stage Feedback")
    
    manager = VoiceFeedbackManager()
    
    # Test different stages
    stages = {
        'fetching': {'machine': 'Compressor-1'},
        'thinking': None,
        'formatting': {'count': 5},
        'validating': {'machine': 'Boiler-1', 'count': 3}
    }
    
    for stage, details in stages.items():
        msg = manager.get_stage_feedback(stage, details)
        assert msg.type == FeedbackType.CHECKING
        print(f"  {stage}: {msg.message}")
    
    print("✓ Stage feedback working")


def test_speech_formatting():
    """Test message formatting for speech"""
    print("\nTest: Speech Formatting")
    
    manager = VoiceFeedbackManager()
    
    # Test technical term replacements
    tests = [
        ("Using 150 kW", "kilowatts"),
        ("Consumed 500 kWh", "kilowatt hours"),
        ("Using 2 MW", "megawatts"),
        ("API error", "A P I"),
        ("HVAC system", "H VAC")
    ]
    
    for input_msg, expected_substring in tests:
        result = manager.format_for_speech(input_msg)
        assert expected_substring in result, f"Expected '{expected_substring}' in '{result}'"
        print(f"  '{input_msg}' -> '{result}'")
    
    print("✓ Speech formatting working")


def test_acknowledgment_variations():
    """Test cycling through acknowledgment variations"""
    print("\nTest: Acknowledgment Variations")
    
    manager = VoiceFeedbackManager()
    
    intent = 'machine_status'
    variations = []
    
    # Get 5 variations (should cycle)
    for i in range(5):
        msg = manager.get_acknowledgment(intent, variation=i)
        variations.append(msg.message)
        print(f"  Variation {i}: {msg.message}")
    
    # Should have cycled back
    assert variations[0] == variations[3]  # Assuming 3 variations
    
    print("✓ Variations working")


def test_disabled_progress():
    """Test with progress indicators disabled"""
    print("\nTest: Disabled Progress")
    
    manager = VoiceFeedbackManager(enable_progress=False)
    
    # Should not show progress even for slow queries
    msg = manager.get_progress_indicator(5000, "fetching")
    assert msg is None
    
    # Stage feedback should not speak
    msg = manager.get_stage_feedback('fetching')
    assert msg.should_speak is False
    
    print("✓ Progress disabled correctly")


if __name__ == '__main__':
    print("=" * 70)
    print("VOICE FEEDBACK MANAGER TESTS")
    print("=" * 70)
    
    test_acknowledgments()
    test_progress_indicators()
    test_error_messages()
    test_confirmation_requests()
    test_help_responses()
    test_stage_feedback()
    test_speech_formatting()
    test_acknowledgment_variations()
    test_disabled_progress()
    
    print("\n" + "=" * 70)
    print("Test Summary:")
    print("  Passed: 9")
    print("=" * 70)
