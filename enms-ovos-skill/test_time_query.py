"""Quick test for time-based energy query"""
import sys
sys.path.insert(0, '.')

from lib.intent_parser import HybridParser
from lib.time_parser import TimeRangeParser

# Test time parsing
print("=" * 60)
print("TIME RANGE PARSING TEST")
print("=" * 60)

test_ranges = [
    "October 27, 3 PM to October 28, 10 AM",
    "yesterday",
    "today",
    "last 24 hours"
]

parser = TimeRangeParser()
for time_str in test_ranges:
    start, end = parser.parse(time_str)
    print(f"\nInput: {time_str}")
    if start and end:
        print(f"  ✓ Start: {start.isoformat()}")
        print(f"  ✓ End:   {end.isoformat()}")
    else:
        print(f"  ✗ Parse failed")

# Test full query parsing
print("\n" + "=" * 60)
print("FULL QUERY PARSING TEST")
print("=" * 60)

hybrid = HybridParser()

query = "Show me the energy consumption of Compressor-1 from October 27, 3 PM to October 28, 10 AM"
print(f"\nQuery: {query}")

result = hybrid.parse(query)

print(f"\n✓ Intent: {result.get('intent')}")
print(f"✓ Tier: {result.get('tier')}")
print(f"✓ Confidence: {result.get('confidence')}")
print(f"✓ Entities:")
for key, val in result.get('entities', {}).items():
    if 'time' in key.lower():
        # Show datetime nicely
        if hasattr(val, 'isoformat'):
            print(f"    {key}: {val.isoformat()}")
        else:
            print(f"    {key}: {val}")
    else:
        print(f"    {key}: {val}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
