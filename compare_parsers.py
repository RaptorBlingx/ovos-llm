import time
import sys
import logging
from enms_ovos_skill.lib.llm_parser import Qwen3Parser

# Configure logging to see what's happening
logging.basicConfig(level=logging.INFO)

def run_test(model_path):
    print(f"Testing model: {model_path}")
    machines = ['Compressor-1', 'Boiler-1', 'Boiler-2']
    intents = ['power_query', 'energy_query', 'machine_status', 'factory_overview', 'ranking']
    utterance = "what is the powre of comprsor one"
    
    try:
        parser = Qwen3Parser(model_path=model_path)
        
        start_load = time.time()
        parser.load_model()
        load_time = time.time() - start_load
        
        start_parse = time.time()
        result = parser.parse(utterance, machines, intents)
        parse_time = time.time() - start_parse
        
        print(f"  Load Time: {load_time:.4f}s")
        print(f"  Parse Time: {parse_time:.4f}s")
        print(f"  Result: {result}")
    except Exception as e:
        print(f"  Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 compare_parsers.py <model_path>")
        sys.exit(1)
    run_test(sys.argv[1])
