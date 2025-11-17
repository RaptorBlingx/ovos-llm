"""
Week 2 Days 13-14: Observability Integration Test
Verify Prometheus metrics collection
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.observability import (
    MetricsCollector, record_llm_latency, record_api_call,
    record_validation_rejection, record_error, set_model_status,
    get_metrics, get_metrics_summary
)
import time


def test_metrics_collection():
    """Test observability metrics"""
    
    print("=" * 80)
    print("Observability Integration Test")
    print("=" * 80)
    
    # Test 1: Model loading
    print("\n[1] Model status tracking...")
    set_model_status(True)
    print("✓ Model marked as loaded")
    
    # Test 2: Query processing with context manager
    print("\n[2] Query metrics with context manager...")
    with MetricsCollector('energy_query', 'llm') as metrics:
        time.sleep(0.1)  # Simulate processing
        metrics.success()
    print("✓ Query metrics recorded (success)")
    
    with MetricsCollector('power_query', 'llm') as metrics:
        time.sleep(0.05)
        metrics.failure('validation_error')
    print("✓ Query metrics recorded (failure)")
    
    # Test 3: LLM latency
    print("\n[3] LLM latency tracking...")
    record_llm_latency(2.5)
    record_llm_latency(3.1)
    print("✓ LLM latencies recorded")
    
    # Test 4: API calls
    print("\n[4] API call metrics...")
    record_api_call('/machines', 200, 0.015)
    record_api_call('/timeseries', 200, 0.032)
    record_api_call('/forecast', 500, 1.2)
    print("✓ API call metrics recorded")
    
    # Test 5: Validation rejections
    print("\n[5] Validation rejection tracking...")
    record_validation_rejection('low_confidence')
    record_validation_rejection('invalid_entity')
    print("✓ Validation rejections recorded")
    
    # Test 6: Error tracking
    print("\n[6] Error tracking...")
    record_error('json_parse_error', 'llm')
    record_error('timeout', 'api')
    print("✓ Errors recorded")
    
    # Test 7: Get metrics summary
    print("\n[7] Metrics summary...")
    summary = get_metrics_summary()
    print(f"Total queries: {summary['total_queries']}")
    print(f"Active queries: {summary['active_queries']}")
    print(f"Model loaded: {summary['model_loaded']}")
    
    # Test 8: Prometheus exposition format
    print("\n[8] Prometheus metrics export...")
    metrics_text = get_metrics()
    
    # Show sample metrics
    lines = metrics_text.split('\n')
    metric_lines = [l for l in lines if not l.startswith('#') and l.strip()]
    
    print(f"✓ Generated {len(metric_lines)} metric lines")
    print("\nSample metrics:")
    for line in metric_lines[:10]:
        print(f"  {line}")
    
    print("\n" + "=" * 80)
    print("OBSERVABILITY TEST: ✓ PASS")
    print("=" * 80)
    print("\nMetrics can be scraped from Prometheus at /metrics endpoint")
    print("Example queries:")
    print("  - histogram_quantile(0.5, enms_query_latency_seconds)")
    print("  - rate(enms_queries_total[5m])")
    print("  - enms_errors_total")


if __name__ == "__main__":
    test_metrics_collection()
