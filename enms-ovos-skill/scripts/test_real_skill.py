#!/usr/bin/env python3
"""
REAL Skill Tester - Tests the ACTUAL EnmsSkill class from __init__.py
NO mocks, NO reimplementation, REAL skill behavior only
"""
import sys
from pathlib import Path

# Add parent dir to path so we can import the skill package
skill_dir = Path(__file__).parent.parent
parent_dir = skill_dir.parent
sys.path.insert(0, str(parent_dir))

import os
os.chdir(str(skill_dir))

# Now we can import as a package
# The skill directory is named 'enms-ovos-skill' 
# But Python can't import with hyphens, so we need to use importlib
import importlib.util

spec = importlib.util.spec_from_file_location(
    "enms_skill",
    skill_dir / "__init__.py"
)
enms_module = importlib.util.module_from_spec(spec)

# Manually set up the package structure
sys.modules['enms_skill'] = enms_module
enms_module.__package__ = 'enms_skill'
enms_module.__path__ = [str(skill_dir)]

# Import lib modules first
from lib.intent_parser import HybridParser, RoutingTier
from lib.validator import ENMSValidator
from lib.api_client import ENMSClient
from lib.response_formatter import ResponseFormatter
from lib.conversation_context import ConversationContextManager
from lib.voice_feedback import VoiceFeedbackManager
from lib.models import IntentType, Intent

# Set them in the module
enms_module.lib = type('lib', (), {
    'intent_parser': type('module', (), {'HybridParser': HybridParser, 'RoutingTier': RoutingTier})(),
    'validator': type('module', (), {'ENMSValidator': ENMSValidator})(),
    'api_client': type('module', (), {'ENMSClient': ENMSClient})(),
    'response_formatter': type('module', (), {'ResponseFormatter': ResponseFormatter})(),
    'conversation_context': type('module', (), {'ConversationContextManager': ConversationContextManager})(),
    'voice_feedback': type('module', (), {'VoiceFeedbackManager': VoiceFeedbackManager})(),
    'models': type('module', (), {'IntentType': IntentType, 'Intent': Intent})(),
})()

# Now load the skill
spec.loader.exec_module(enms_module)

EnmsSkill = enms_module.EnmsSkill

from ovos_bus_client.message import Message
import uuid


def test_query(query_text):
    """Test a query using the REAL skill"""
    
    print("=" * 80)
    print(f"🔍 Testing REAL Skill: \"{query_text}\"")
    print("=" * 80)
    
    # Create the REAL skill instance
    print("\n[Loading] Initializing REAL EnmsSkill from __init__.py...")
    skill = EnmsSkill()
    
    # Simulate OVOS message
    message = Message(
        "recognizer_loop:utterance",
        {
            "utterances": [query_text],
            "utterance": query_text,
            "lang": "en-us",
            "session": {
                "session_id": str(uuid.uuid4())
            }
        }
    )
    
    # Call the REAL skill's processing method
    print(f"\n[Processing] Calling skill._process_query()...")
    session_id = message.data.get("session", {}).get("session_id", str(uuid.uuid4()))
    
    result = skill._process_query(
        utterance=query_text,
        session_id=session_id
    )
    
    print(f"\n{'=' * 80}")
    print("FINAL RESPONSE (from REAL skill):")
    print(f"{'=' * 80}")
    print(result['response'])
    print(f"{'=' * 80}\n")
    
    print("Debug Info:")
    print(f"  Success: {result['success']}")
    print(f"  Intent: {result.get('intent')}")
    print(f"  Machine: {result.get('machine')}")
    print(f"  Latency: {result.get('latency_ms')}ms")
    print(f"  Tier: {result.get('tier')}")
    
    return result


if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "Is the energy system online?"
    
    test_query(query)
