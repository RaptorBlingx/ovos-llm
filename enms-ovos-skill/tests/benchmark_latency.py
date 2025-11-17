"""
Latency Benchmark for Hybrid Parser
====================================

Measures P50/P90/P99 latency across all tiers
Tests representative query distribution
"""

import sys
import time
import statistics
from pathlib import Path
from typing import List, Tuple, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.intent_parser import HybridParser


# Representative query set (based on test-questions.md distribution)
BENCHMARK_QUERIES = [
    # Heuristic tier (expected 70-80%)
    ("top 3", "heuristic"),
    ("top 5 machines", "heuristic"),
    ("factory overview", "heuristic"),
    ("factory status", "heuristic"),
    ("total kwh", "heuristic"),
    ("Boiler-1 power", "heuristic"),
    ("Compressor-1 kwh", "heuristic"),
    ("HVAC-EU-North status", "heuristic"),
    ("Conveyor-A energy", "heuristic"),
    ("compare Boiler-1 and Compressor-1", "heuristic"),
    ("Compressor-1 vs Boiler-1", "heuristic"),
    ("Is Boiler-1 running?", "heuristic"),
    ("check HVAC-Main", "heuristic"),
    ("power of Turbine-1", "heuristic"),
    ("Injection-Molding-1 consumption", "heuristic"),
    
    # Adapt tier (expected 10-15%)
    ("What is the energy of Compressor-1?", "adapt"),
    ("Is HVAC running?", "adapt"),
    ("Show me Boiler power", "adapt"),
    
    # LLM tier (expected 10-15%)
    ("How much energy did Boiler-1 use yesterday?", "llm"),
    ("What's the consumption in the last 24 hours?", "llm"),
    ("What about that machine?", "llm"),
]


def benchmark_latency(parser: HybridParser, rounds: int = 3) -> Dict:
    """
    Benchmark latency across multiple rounds
    
    Args:
        parser: Initialized HybridParser
        rounds: Number of benchmark rounds
        
    Returns:
        Dict with latency statistics
    """
    print(f"\n🔬 LATENCY BENCHMARK ({rounds} rounds × {len(BENCHMARK_QUERIES)} queries)")
    print("="*80)
    
    tier_latencies = {
        'heuristic': [],
        'adapt': [],
        'llm': []
    }
    
    all_latencies = []
    tier_counts = {'heuristic': 0, 'adapt': 0, 'llm': 0}
    
    for round_num in range(1, rounds + 1):
        print(f"\n📊 Round {round_num}/{rounds}")
        print("-"*80)
        
        for query, expected_tier in BENCHMARK_QUERIES:
            start_time = time.time()
            result = parser.parse(query)
            latency_ms = (time.time() - start_time) * 1000
            
            actual_tier = result['tier']
            tier_latencies[actual_tier].append(latency_ms)
            all_latencies.append(latency_ms)
            tier_counts[actual_tier] += 1
            
            # Show progress (only first round)
            if round_num == 1:
                tier_icon = "🟢" if actual_tier == "heuristic" else "🟡" if actual_tier == "adapt" else "🔵"
                print(f"  {tier_icon} {actual_tier:10s} | {latency_ms:6.1f}ms | {query[:50]}")
    
    # Calculate statistics
    def calc_percentiles(data: List[float]) -> Dict:
        """Calculate P50/P90/P99 percentiles"""
        if not data:
            return {'p50': 0, 'p90': 0, 'p99': 0, 'mean': 0, 'min': 0, 'max': 0}
        
        sorted_data = sorted(data)
        return {
            'p50': statistics.median(sorted_data),
            'p90': sorted_data[int(len(sorted_data) * 0.9)],
            'p99': sorted_data[int(len(sorted_data) * 0.99)] if len(sorted_data) > 10 else sorted_data[-1],
            'mean': statistics.mean(sorted_data),
            'min': min(sorted_data),
            'max': max(sorted_data),
        }
    
    # Overall statistics
    overall_stats = calc_percentiles(all_latencies)
    
    # Per-tier statistics
    tier_stats = {
        tier: calc_percentiles(latencies)
        for tier, latencies in tier_latencies.items()
        if latencies
    }
    
    # Print results
    print("\n" + "="*80)
    print("📈 LATENCY STATISTICS")
    print("="*80)
    
    print(f"\n🎯 Overall ({len(all_latencies)} queries):")
    print(f"   P50: {overall_stats['p50']:.2f}ms")
    print(f"   P90: {overall_stats['p90']:.2f}ms")
    print(f"   P99: {overall_stats['p99']:.2f}ms")
    print(f"   Mean: {overall_stats['mean']:.2f}ms")
    print(f"   Min: {overall_stats['min']:.2f}ms")
    print(f"   Max: {overall_stats['max']:.2f}ms")
    
    # Per-tier breakdown
    for tier, stats in tier_stats.items():
        tier_icon = "🟢" if tier == "heuristic" else "🟡" if tier == "adapt" else "🔵"
        print(f"\n{tier_icon} {tier.upper()} ({len(tier_latencies[tier])} queries):")
        print(f"   P50: {stats['p50']:.2f}ms")
        print(f"   P90: {stats['p90']:.2f}ms")
        print(f"   P99: {stats['p99']:.2f}ms")
        print(f"   Mean: {stats['mean']:.2f}ms")
    
    # Routing distribution
    total_queries = sum(tier_counts.values())
    print(f"\n📊 ROUTING DISTRIBUTION ({total_queries} total):")
    for tier, count in tier_counts.items():
        pct = (count / total_queries) * 100
        tier_icon = "🟢" if tier == "heuristic" else "🟡" if tier == "adapt" else "🔵"
        target = "70-80%" if tier == "heuristic" else "10-15%" if tier == "adapt" else "10-15%"
        status = "✅" if (tier == "heuristic" and 70 <= pct <= 80) or \
                       (tier != "heuristic" and 5 <= pct <= 20) else "⚠️"
        print(f"   {status} {tier_icon} {tier.capitalize()}: {count} ({pct:.1f}%) - target {target}")
    
    # Target check
    print("\n🎯 TARGET VALIDATION:")
    p50_target = overall_stats['p50'] < 200
    heuristic_pct = (tier_counts['heuristic'] / total_queries) * 100
    distribution_target = 70 <= heuristic_pct <= 80
    
    print(f"   {'✅' if p50_target else '❌'} P50 < 200ms: {overall_stats['p50']:.2f}ms")
    print(f"   {'✅' if distribution_target else '⚠️'} Heuristic 70-80%: {heuristic_pct:.1f}%")
    
    if p50_target and distribution_target:
        print("\n🎉 ALL TARGETS MET!")
    else:
        print("\n⚠️ Some targets not met - optimization needed")
    
    return {
        'overall': overall_stats,
        'tiers': tier_stats,
        'distribution': tier_counts
    }


def main():
    """Run latency benchmark"""
    print("\n🚀 HYBRID PARSER LATENCY BENCHMARK")
    print("="*80)
    print("Goal: Measure P50/P90/P99 latency with 3-tier routing")
    print("Target: P50 < 200ms, 70-80% heuristic coverage")
    
    # Initialize parser (this loads LLM model)
    print("\n⏳ Initializing parser (loading LLM model)...")
    start_init = time.time()
    parser = HybridParser()
    init_time = time.time() - start_init
    print(f"✅ Parser initialized in {init_time:.2f}s")
    
    # Run benchmark
    results = benchmark_latency(parser, rounds=1)  # Use 1 round to avoid long LLM wait
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
