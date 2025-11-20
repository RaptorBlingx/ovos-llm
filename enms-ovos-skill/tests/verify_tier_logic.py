#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from lib.intent_parser import HybridParser, RoutingTier

parser = HybridParser()
test_queries = {
    "Ultra-short power": "Boiler-1 power",
    "Ultra-short energy": "Compressor kwh",
    "Status question": "Is Boiler-1 running?",
    "Ranking": "top 3",
    "Factory": "factory overview",
    "Comparison": "Compare Boiler-1 and Compressor-1",
    "Time-based": "Boiler-1 energy yesterday",
    "Complex": "Which machine uses most power?",
}

print("\n🔍 TIER ROUTING\n")
for cat, q in test_queries.items():
    r = parser.parse(q)
    t = r.get('tier', 'unknown')
    print(f"{'⚡' if t==RoutingTier.HEURISTIC else '🟦' if t==RoutingTier.ADAPT else '🧠'} {str(t):12s} | {cat:20s} | {q}")
