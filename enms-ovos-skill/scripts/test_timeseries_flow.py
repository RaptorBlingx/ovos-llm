"""Test the exact flow causing the issue."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.intent_parser import HybridParser
from lib.validator import ENMSValidator
from lib.time_parser import TimeRangeParser

query = "Show me the energy consumption of Compressor-1 from October 27, 3 PM to October 28, 10 AM"

print("=" * 80)
print("DEBUGGING TIME-SERIES FLOW")
print("=" * 80)
print(f"\nQuery: {query}\n")

# Step 1: Parse
print("STEP 1: HybridParser.parse()")
print("-" * 80)
parser = HybridParser()
result = parser.parse(query)
print(f"Tier: {result.get('tier')}")
print(f"Intent: {result.get('intent')} (type: {type(result.get('intent'))})")
print(f"Confidence: {result.get('confidence')}")
print(f"Entities: {result.get('entities')}")
print(f"\nFull result keys: {list(result.keys())}")

# Step 2: Validate
print("\n\nSTEP 2: ENMSValidator.validate()")
print("-" * 80)
validator = ENMSValidator()
validator.update_machine_whitelist(['Compressor-1', 'Boiler-1', 'HVAC-Main'])

try:
    validation = validator.validate(result)
    print(f"Valid: {validation.valid}")
    
    if validation.valid:
        intent = validation.intent
        print(f"Intent type: {intent.intent} (type: {type(intent.intent)})")
        print(f"Machine: {intent.machine}")
        print(f"Entities: {intent.entities if hasattr(intent, 'entities') else 'N/A'}")
    else:
        print(f"Validation errors: {validation.errors}")
        print(f"Validation warnings: {validation.warnings}")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

# Step 3: Parse time from result
print("\n\nSTEP 3: TimeRangeParser.parse()")
print("-" * 80)
entities = result.get('entities', {})
if 'time_range' in entities:
    time_range_str = entities['time_range']
    print(f"Time range string: {time_range_str}")
    
    time_parser = TimeRangeParser()
    start, end = time_parser.parse(time_range_str)
    print(f"Start: {start}")
    print(f"End: {end}")
else:
    print("No time_range found in entities")

print("\n" + "=" * 80)
print("DONE")
print("=" * 80)
