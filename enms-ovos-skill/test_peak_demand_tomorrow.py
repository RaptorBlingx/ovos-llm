#!/usr/bin/env python3
"""
Test: "When will peak demand occur tomorrow?" should route to FORECAST intent
"""

import sys
sys.path.insert(0, '/home/swemo/ovos-llm-core/ovos-llm/enms-ovos-skill')

from enms_ovos_skill.lib.intent_parser import HybridParser

# Initialize parser
parser = HybridParser()

# Test query
query = "When will peak demand occur tomorrow?"

# Parse intent
result = parser.parse(query)

print("=" * 60)
print(f"Query: {query}")
print("=" * 60)
print(f"Intent: {result['intent']}")
print(f"Confidence: {result['confidence']}")
print(f"Tier: {result.get('tier', 'N/A')}")
print(f"Machine: {result.get('machine', 'N/A')}")
print("=" * 60)

# Expected result
expected_intent = 'forecast'
if result['intent'] == expected_intent:
    print(f"✅ PASS: Query correctly routed to {expected_intent} intent")
else:
    print(f"❌ FAIL: Expected {expected_intent}, got {result['intent']}")
    sys.exit(1)
