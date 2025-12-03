#!/usr/bin/env python3
"""
Test: "What energy types does Boiler-1 use?" should handle 404 gracefully
"""

import sys
sys.path.insert(0, 'D:\\ovos-llm-core\\ovos-llm\\enms-ovos-skill')

from enms_ovos_skill.lib.intent_parser import HybridParser

# Initialize parser
parser = HybridParser()

# Test query
query = "What energy types does Boiler-1 use?"

# Parse intent
result = parser.parse(query)

print("=" * 60)
print(f"Query: {query}")
print("=" * 60)
print(f"Intent: {result['intent']}")
print(f"Confidence: {result['confidence']}")
print(f"Tier: {result.get('tier', 'N/A')}")
print(f"Machine: {result.get('machine', 'N/A')}")
print(f"Metric: {result.get('metric', 'N/A')}")
print("=" * 60)

# Expected result
expected_intent = 'energy_query'
if result['intent'] == expected_intent and result.get('machine') == 'Boiler-1':
    print(f"✅ PASS: Query correctly routed to {expected_intent} with machine Boiler-1")
else:
    print(f"❌ FAIL: Expected {expected_intent}, got {result['intent']}")
    sys.exit(1)
