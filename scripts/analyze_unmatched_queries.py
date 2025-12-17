#!/usr/bin/env python3
"""
Analyze unmatched queries and suggest new patterns

Usage:
    python3 scripts/analyze_unmatched_queries.py
    
Reads: /home/ubuntu/ovos-llm/logs/unmatched_queries.log
Outputs: Pattern recommendations for heuristic router
"""
import json
from collections import Counter
from pathlib import Path
import sys

LOG_FILE = Path("/home/ubuntu/ovos-llm/logs/unmatched_queries.log")


def analyze():
    """Analyze unmatched query patterns"""
    if not LOG_FILE.exists():
        print(f"❌ Log file not found: {LOG_FILE}")
        print("   No unmatched queries yet (or logging not enabled)")
        return
    
    queries = []
    try:
        with LOG_FILE.open('r') as f:
            for line in f:
                if line.strip():
                    queries.append(json.loads(line))
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing log file: {e}")
        return
    
    if not queries:
        print("✅ No unmatched queries found!")
        return
    
    # Count common terms
    all_words = []
    for q in queries:
        all_words.extend(q['query'].lower().split())
    
    common_terms = Counter(all_words).most_common(20)
    
    print("📊 Unmatched Query Analysis")
    print(f"{'='*60}")
    print(f"Total unmatched: {len(queries)}")
    print(f"{'='*60}\n")
    
    print("🔤 Most common terms:")
    for term, count in common_terms:
        print(f"  - {term}: {count}x")
    
    print(f"\n📝 Recent unmatched queries (last 10):")
    for q in queries[-10:]:
        timestamp = q.get('timestamp', 'N/A')
        query = q.get('query', 'N/A')
        reason = q.get('reason', 'N/A')
        confidence = q.get('confidence', 0.0)
        print(f"  [{timestamp}] \"{query}\" (reason: {reason}, conf: {confidence})")
    
    print(f"\n💡 Recommendation:")
    print("  Add regex patterns for these common queries to heuristic_router.py")
    print("  Or expand Adapt vocabulary in adapt_parser.py")


if __name__ == "__main__":
    analyze()
