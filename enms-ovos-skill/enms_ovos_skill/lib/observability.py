"""
Observability Module
Week 2 Days 13-14: Prometheus Metrics + Structured Logging

Provides:
- Request latency histograms (P50, P90, P99)
- Error counters by type
- Tier routing distribution
- Query success/failure rates
- API call metrics
"""
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from prometheus_client import CONTENT_TYPE_LATEST
import time
from typing import Optional, Dict, Any
import structlog

logger = structlog.get_logger(__name__)

# Create custom registry to avoid conflicts
REGISTRY = CollectorRegistry()

# Metrics definitions

# Latency histogram - measures end-to-end query processing time
query_latency = Histogram(
    'enms_query_latency_seconds',
    'End-to-end query processing latency',
    ['intent_type', 'tier'],  # Labels for grouping
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0],  # Bucket boundaries
    registry=REGISTRY
)

# LLM inference latency (subset of total)
llm_latency = Histogram(
    'enms_llm_latency_seconds',
    'LLM inference time',
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0],
    registry=REGISTRY
)

# API call latency
api_latency = Histogram(
    'enms_api_latency_seconds',
    'EnMS API call time',
    ['endpoint', 'status_code'],
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0],
    registry=REGISTRY
)

# Query counters
queries_total = Counter(
    'enms_queries_total',
    'Total queries processed',
    ['intent_type', 'tier', 'status'],  # status: success/failure
    registry=REGISTRY
)

# Error counter
errors_total = Counter(
    'enms_errors_total',
    'Total errors by type',
    ['error_type', 'component'],  # component: llm/validator/api/formatter
    registry=REGISTRY
)

# Tier routing distribution
tier_routing = Counter(
    'enms_tier_routing_total',
    'Query routing by tier',
    ['tier'],  # tier: adapt/heuristic/llm
    registry=REGISTRY
)

# Validation metrics
validation_rejections = Counter(
    'enms_validation_rejections_total',
    'Queries rejected by validator',
    ['rejection_reason'],  # reason: low_confidence/invalid_entity/schema_error
    registry=REGISTRY
)

# Active queries gauge
active_queries = Gauge(
    'enms_active_queries',
    'Currently processing queries',
    registry=REGISTRY
)

# Model loading status
model_loaded = Gauge(
    'enms_model_loaded',
    'LLM model loaded status (1=loaded, 0=not loaded)',
    registry=REGISTRY
)


class MetricsCollector:
    """
    Centralized metrics collection with context management
    
    Usage:
        with MetricsCollector('energy_query', 'llm') as metrics:
            result = process_query()
            if result.valid:
                metrics.success()
            else:
                metrics.failure('validation_error')
    """
    
    def __init__(self, intent_type: str, tier: str):
        self.intent_type = intent_type
        self.tier = tier
        self.start_time = None
        self.status = 'unknown'
        
    def __enter__(self):
        self.start_time = time.time()
        active_queries.inc()
        tier_routing.labels(tier=self.tier).inc()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        latency = time.time() - self.start_time
        active_queries.dec()
        
        # Record latency
        query_latency.labels(
            intent_type=self.intent_type,
            tier=self.tier
        ).observe(latency)
        
        # Record outcome
        if exc_type is None and self.status == 'success':
            queries_total.labels(
                intent_type=self.intent_type,
                tier=self.tier,
                status='success'
            ).inc()
        else:
            queries_total.labels(
                intent_type=self.intent_type,
                tier=self.tier,
                status='failure'
            ).inc()
            
            # Log error
            if exc_type:
                logger.error("query_processing_error",
                           intent=self.intent_type,
                           tier=self.tier,
                           error=str(exc_val),
                           latency_sec=latency)
        
        # Suppress exception propagation (already logged)
        return False
    
    def success(self):
        """Mark query as successful"""
        self.status = 'success'
    
    def failure(self, reason: str):
        """Mark query as failed"""
        self.status = 'failure'
        logger.warning("query_failed",
                      intent=self.intent_type,
                      tier=self.tier,
                      reason=reason)


def record_llm_latency(latency_seconds: float):
    """Record LLM inference time"""
    llm_latency.observe(latency_seconds)
    logger.debug("llm_latency_recorded", latency_sec=latency_seconds)


def record_api_call(endpoint: str, status_code: int, latency_seconds: float):
    """Record API call metrics"""
    api_latency.labels(
        endpoint=endpoint,
        status_code=str(status_code)
    ).observe(latency_seconds)
    
    logger.debug("api_call_recorded",
                endpoint=endpoint,
                status=status_code,
                latency_sec=latency_seconds)


def record_validation_rejection(reason: str):
    """Record validation rejection"""
    validation_rejections.labels(rejection_reason=reason).inc()
    logger.warning("validation_rejected", reason=reason)


def record_error(error_type: str, component: str):
    """Record error occurrence"""
    errors_total.labels(error_type=error_type, component=component).inc()
    logger.error("error_recorded", error_type=error_type, component=component)


def set_model_status(loaded: bool):
    """Update model loading status"""
    model_loaded.set(1 if loaded else 0)
    logger.info("model_status_updated", loaded=loaded)


def get_metrics() -> str:
    """
    Get Prometheus metrics in exposition format
    
    Returns:
        Metrics text for Prometheus scraping
    """
    return generate_latest(REGISTRY).decode('utf-8')


def get_metrics_summary() -> Dict[str, Any]:
    """
    Get human-readable metrics summary
    
    Returns:
        Dict with key metrics
    """
    # Simplified summary - real implementation would parse metrics properly
    return {
        "total_queries": "see /metrics endpoint",
        "active_queries": int(active_queries._value.get()),
        "model_loaded": bool(model_loaded._value.get()),
        "metrics_endpoint": "/metrics"
    }
