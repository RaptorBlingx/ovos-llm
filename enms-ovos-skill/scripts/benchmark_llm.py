#!/usr/bin/env python3
"""
Performance Benchmarking Script for LLM Integration

Measures:
- Model load time (cold start)
- Average inference time (non-thinking mode)
- Average inference time (thinking mode)
- Memory usage with model loaded
- Tier distribution across test queries

Usage:
    python scripts/benchmark_llm.py [--model-path PATH] [--iterations N]
"""

import argparse
import time
import json
import psutil
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from enms_ovos_skill.lib.llm_parser import Qwen3Parser
from enms_ovos_skill.lib.intent_parser import HybridParser, RoutingTier


# Test queries for each routing tier
TEST_QUERIES = {
    "heuristic": [
        "power of Compressor-1",
        "energy Boiler-2",
        "consumption Pump-3",
        "status Compressor-1",
        "is Boiler-2 online",
    ],
    "adapt": [
        "energy consumption of Compressor-1 last hour",
        "show power usage for Boiler-2 yesterday",
        "what's the efficiency of Pump-3 this week",
        "compare energy for all compressors today",
        "total power consumption last 24 hours",
    ],
    "llm": [
        "which machines are using most electricity?",
        "give me a breakdown of power consumption",
        "what equipment is wasting energy?",
        "rank machines by efficiency",
        "show me the biggest power consumers",
        "which devices need optimization?",
        "where is most energy going?",
        "breakdown energy usage by machine type",
    ],
}


def get_memory_usage() -> float:
    """Get current process memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024


def benchmark_model_load(model_path: str) -> Dict[str, float]:
    """Benchmark model loading time."""
    print("\n📊 Benchmarking model load time...")
    
    mem_before = get_memory_usage()
    start_time = time.time()
    
    parser = Qwen3Parser(model_path)
    parser.load_model()
    
    load_time = time.time() - start_time
    mem_after = get_memory_usage()
    mem_increase = mem_after - mem_before
    
    print(f"   ✓ Model loaded in {load_time:.2f}s")
    print(f"   ✓ Memory increase: {mem_increase:.1f} MB (total: {mem_after:.1f} MB)")
    
    return {
        "load_time_sec": load_time,
        "memory_before_mb": mem_before,
        "memory_after_mb": mem_after,
        "memory_increase_mb": mem_increase,
    }


def benchmark_inference(
    parser: HybridParser,
    query: str,
    thinking_mode: bool = False,
    label: str = ""
) -> Tuple[Dict, float]:
    """Benchmark a single inference."""
    start_time = time.time()
    result = parser.parse(query, thinking_mode=thinking_mode)
    latency = (time.time() - start_time) * 1000  # Convert to ms
    
    if label:
        tier = result.get("tier", "unknown")
        print(f"   {label}: {latency:.0f}ms (tier: {tier})")
    
    return result, latency


def benchmark_tier_routing(
    model_path: str,
    iterations: int = 3
) -> Dict[str, List[float]]:
    """Benchmark routing across different tiers."""
    print(f"\n📊 Benchmarking tier routing ({iterations} iterations per query)...")
    
    parser = HybridParser()
    parser.init_llm(model_path)
    
    # Ensure LLM is ready
    if not parser.llm or not hasattr(parser.llm, 'model') or parser.llm.model is None:
        print("   ⚠️  LLM not loaded, tier 3 tests will be skipped")
    
    results = {
        "heuristic": [],
        "adapt": [],
        "llm": [],
    }
    
    tier_counts = {
        RoutingTier.HEURISTIC: 0,
        RoutingTier.ADAPT: 0,
        RoutingTier.LLM: 0,
    }
    
    # Test each tier
    for tier_name, queries in TEST_QUERIES.items():
        print(f"\n   Testing {tier_name.upper()} tier:")
        
        for query in queries[:3]:  # Limit to 3 queries per tier for speed
            latencies = []
            
            for i in range(iterations):
                result, latency = benchmark_inference(
                    parser, query,
                    label=f"   [{i+1}/{iterations}] {query[:40]}..."
                )
                latencies.append(latency)
                
                # Track which tier was actually used
                actual_tier = result.get("tier")
                if actual_tier:
                    tier_counts[actual_tier] = tier_counts.get(actual_tier, 0) + 1
            
            avg_latency = sum(latencies) / len(latencies)
            results[tier_name].append(avg_latency)
            print(f"      → Avg: {avg_latency:.0f}ms")
    
    # Calculate tier distribution
    total = sum(tier_counts.values())
    tier_distribution = {
        tier.name: (count / total * 100) if total > 0 else 0
        for tier, count in tier_counts.items()
    }
    
    print("\n   Tier Distribution:")
    for tier_name, percentage in tier_distribution.items():
        print(f"      {tier_name}: {percentage:.1f}%")
    
    return results, tier_distribution


def benchmark_thinking_mode(model_path: str, iterations: int = 2) -> Dict[str, List[float]]:
    """Benchmark thinking vs non-thinking mode."""
    print(f"\n📊 Benchmarking thinking mode ({iterations} iterations)...")
    
    parser = HybridParser()
    parser.init_llm(model_path)
    
    if not parser.llm or not hasattr(parser.llm, 'model') or parser.llm.model is None:
        print("   ⚠️  LLM not loaded, skipping thinking mode benchmark")
        return {"non_thinking": [], "thinking": []}
    
    # Test query that requires LLM
    test_query = "which machines are using most electricity?"
    
    results = {
        "non_thinking": [],
        "thinking": [],
    }
    
    # Test non-thinking mode
    print("\n   Non-thinking mode:")
    for i in range(iterations):
        _, latency = benchmark_inference(
            parser, test_query,
            thinking_mode=False,
            label=f"   [{i+1}/{iterations}] {test_query}"
        )
        results["non_thinking"].append(latency)
    
    # Test thinking mode
    print("\n   Thinking mode:")
    for i in range(iterations):
        _, latency = benchmark_inference(
            parser, test_query,
            thinking_mode=True,
            label=f"   [{i+1}/{iterations}] {test_query}"
        )
        results["thinking"].append(latency)
    
    return results


def calculate_statistics(latencies: List[float]) -> Dict[str, float]:
    """Calculate min, max, avg, median from latency list."""
    if not latencies:
        return {"min": 0, "max": 0, "avg": 0, "median": 0}
    
    sorted_latencies = sorted(latencies)
    n = len(sorted_latencies)
    
    return {
        "min": sorted_latencies[0],
        "max": sorted_latencies[-1],
        "avg": sum(sorted_latencies) / n,
        "median": sorted_latencies[n // 2] if n % 2 == 1 else (
            sorted_latencies[n // 2 - 1] + sorted_latencies[n // 2]
        ) / 2,
    }


def print_summary(results: Dict):
    """Print benchmark summary report."""
    print("\n" + "=" * 70)
    print("📊 BENCHMARK SUMMARY REPORT")
    print("=" * 70)
    
    # Model load
    load_results = results.get("model_load", {})
    print(f"\n🚀 Model Load:")
    print(f"   Time: {load_results.get('load_time_sec', 0):.2f}s")
    print(f"   Memory: {load_results.get('memory_increase_mb', 0):.1f} MB")
    print(f"   Target: <60s ✅" if load_results.get('load_time_sec', 999) < 60 else "   Target: <60s ❌")
    
    # Tier routing
    tier_results = results.get("tier_routing", {})
    print(f"\n⚡ Tier Routing:")
    
    for tier_name, latencies in tier_results.items():
        if not latencies:
            continue
        stats = calculate_statistics(latencies)
        print(f"\n   {tier_name.upper()}:")
        print(f"      Avg: {stats['avg']:.0f}ms")
        print(f"      Min: {stats['min']:.0f}ms")
        print(f"      Max: {stats['max']:.0f}ms")
        
        # Check targets
        if tier_name == "heuristic" and stats['avg'] > 10:
            print(f"      Target: <10ms ❌")
        elif tier_name == "adapt" and stats['avg'] > 20:
            print(f"      Target: <20ms ❌")
        elif tier_name == "llm" and (stats['avg'] < 3000 or stats['avg'] > 5000):
            print(f"      Target: 3000-5000ms ⚠️")
        else:
            print(f"      Target: ✅")
    
    # Tier distribution
    tier_dist = results.get("tier_distribution", {})
    if tier_dist:
        print(f"\n   Distribution:")
        for tier, pct in tier_dist.items():
            print(f"      {tier}: {pct:.1f}%")
    
    # Thinking mode
    thinking_results = results.get("thinking_mode", {})
    if thinking_results.get("non_thinking"):
        print(f"\n🧠 Thinking Mode:")
        
        non_thinking_stats = calculate_statistics(thinking_results["non_thinking"])
        thinking_stats = calculate_statistics(thinking_results["thinking"])
        
        print(f"   Non-thinking: {non_thinking_stats['avg']:.0f}ms (target: 3-5s)")
        print(f"   Thinking:     {thinking_stats['avg']:.0f}ms (target: 10-30s)")
        
        if thinking_stats['avg'] > non_thinking_stats['avg']:
            improvement = (thinking_stats['avg'] - non_thinking_stats['avg']) / non_thinking_stats['avg'] * 100
            print(f"   Overhead:     +{improvement:.0f}%")
    
    # Memory
    final_mem = results.get("model_load", {}).get("memory_after_mb", 0)
    print(f"\n💾 Memory Usage:")
    print(f"   Total: {final_mem:.1f} MB")
    print(f"   Target: <3000 MB ✅" if final_mem < 3000 else f"   Target: <3000 MB ❌")
    
    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Benchmark LLM integration performance")
    parser.add_argument(
        "--model-path",
        default="./models/Qwen3.5-2B-Q4_K_M.gguf",
        help="Path to GGUF model file (default: ./models/Qwen3.5-2B-Q4_K_M.gguf)"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Number of iterations per test (default: 3)"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file for results (optional)"
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🧪 LLM PERFORMANCE BENCHMARK")
    print("=" * 70)
    print(f"Model: {args.model_path}")
    print(f"Iterations: {args.iterations}")
    print(f"Memory before: {get_memory_usage():.1f} MB")
    
    # Check model file exists
    if not os.path.exists(args.model_path):
        print(f"\n❌ Error: Model file not found: {args.model_path}")
        print("   Expected location for Docker: /opt/ovos/skills/enms-ovos-skill/models/Qwen3.5-2B-Q4_K_M.gguf")
        print("   Expected location for dev: ./models/Qwen3.5-2B-Q4_K_M.gguf")
        return 1
    
    results = {}
    
    try:
        # Benchmark model load
        results["model_load"] = benchmark_model_load(args.model_path)
        
        # Benchmark tier routing
        tier_results, tier_dist = benchmark_tier_routing(args.model_path, args.iterations)
        results["tier_routing"] = tier_results
        results["tier_distribution"] = tier_dist
        
        # Benchmark thinking mode
        results["thinking_mode"] = benchmark_thinking_mode(args.model_path, iterations=2)
        
        # Print summary
        print_summary(results)
        
        # Save to file if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n✅ Results saved to {args.output}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
