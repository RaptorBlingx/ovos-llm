"""
Pytest Configuration and Shared Fixtures
=========================================

Provides reusable fixtures for all test modules
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.api_client import ENMSClient
from lib.validator import ENMSValidator
from lib.intent_parser import HybridParser, HeuristicRouter
from lib.response_formatter import ResponseFormatter
from lib.qwen3_parser import Qwen3Parser
from lib.adapt_parser import AdaptParser
from lib.models import Intent, IntentType, TimeRange


# ============================================================================
# EVENT LOOP FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for the test session"""
    return asyncio.get_event_loop_policy()


@pytest.fixture
def event_loop(event_loop_policy):
    """Create an event loop for each test"""
    loop = event_loop_policy.new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# API CLIENT FIXTURES
# ============================================================================

@pytest.fixture
async def api_client():
    """
    Real API client (for integration tests)
    
    Connects to actual EnMS API at http://10.33.10.109:8001/api/v1
    """
    client = ENMSClient(base_url="http://10.33.10.109:8001/api/v1")
    yield client
    await client.close()


@pytest.fixture
def mock_api_client(mocker):
    """
    Mocked API client (for unit tests)
    
    Returns a mock with common responses pre-configured
    """
    mock = mocker.AsyncMock(spec=ENMSClient)
    
    # Mock common responses
    mock.health_check.return_value = {"status": "healthy"}
    mock.system_stats.return_value = {"cpu": 45.2, "memory": 62.1}
    mock.list_machines.return_value = [
        {"machine_id": "comp-1", "machine_name": "Compressor-1", "is_active": True},
        {"machine_id": "boil-1", "machine_name": "Boiler-1", "is_active": True},
    ]
    mock.get_machine_status.return_value = {
        "machine_name": "Compressor-1",
        "current_status": "running",
        "power_kw": 47.98,
        "energy_kwh_today": 1152.5
    }
    
    return mock


# ============================================================================
# VALIDATOR FIXTURES
# ============================================================================

@pytest.fixture
def validator():
    """ENMSValidator instance with default settings"""
    return ENMSValidator(
        machine_whitelist=[
            "Compressor-1", "Boiler-1", "HVAC-Main", "Conveyor-A",
            "Injection-Molding-1", "Compressor-EU-1", "HVAC-EU-North", "Pump-1"
        ],
        confidence_threshold=0.85,
        enable_fuzzy_matching=True
    )


@pytest.fixture
def strict_validator():
    """Validator with no fuzzy matching (exact match only)"""
    return ENMSValidator(
        confidence_threshold=0.95,
        enable_fuzzy_matching=False
    )


# ============================================================================
# PARSER FIXTURES
# ============================================================================

@pytest.fixture
def hybrid_parser():
    """HybridParser instance"""
    return HybridParser()


@pytest.fixture
def heuristic_router():
    """HeuristicRouter instance"""
    return HeuristicRouter()


@pytest.fixture
def adapt_parser():
    """AdaptParser instance"""
    return AdaptParser()


@pytest.fixture
def llm_parser():
    """Qwen3Parser instance (slow - use sparingly)"""
    return Qwen3Parser()


# ============================================================================
# RESPONSE FORMATTER FIXTURES
# ============================================================================

@pytest.fixture
def response_formatter():
    """ResponseFormatter instance"""
    return ResponseFormatter()


# ============================================================================
# SAMPLE DATA FIXTURES
# ============================================================================

@pytest.fixture
def sample_machines():
    """List of valid machine names"""
    return [
        "Compressor-1",
        "Boiler-1",
        "HVAC-Main",
        "Conveyor-A",
        "Injection-Molding-1",
        "Compressor-EU-1",
        "HVAC-EU-North",
        "Pump-1"
    ]


@pytest.fixture
def sample_llm_output():
    """Sample LLM JSON output"""
    return {
        "intent": "machine_status",
        "confidence": 0.95,
        "utterance": "Is Compressor-1 running?",
        "machine": "Compressor-1",
        "entities": {}
    }


@pytest.fixture
def sample_api_response():
    """Sample API response data"""
    return {
        "machine_name": "Compressor-1",
        "current_status": "running",
        "power_kw": 47.98,
        "energy_kwh_today": 1152.5,
        "efficiency_percent": 87.3,
        "uptime_hours": 23.5
    }


@pytest.fixture
def sample_time_range():
    """Sample TimeRange object"""
    now = datetime.utcnow()
    return TimeRange(
        start=now - timedelta(hours=24),
        end=now,
        relative="last_24h"
    )


# ============================================================================
# QUERY FIXTURES
# ============================================================================

@pytest.fixture
def sample_queries():
    """
    Comprehensive list of test queries covering all intent types
    
    Returns dict: {intent_type: [list of queries]}
    """
    return {
        "machine_status": [
            "Is Compressor-1 running?",
            "Boiler-1 status",
            "Check HVAC-Main",
            "Is Conveyor-A online?",
            "What's the status of Pump-1?"
        ],
        "power_query": [
            "Compressor-1 power",
            "What's the power of Boiler-1?",
            "HVAC-Main watts",
            "How many kilowatts is Conveyor-A using?"
        ],
        "energy_query": [
            "Compressor-1 energy",
            "Boiler-1 kwh",
            "How much energy did HVAC-Main use?",
            "Energy consumption of Conveyor-A"
        ],
        "cost_analysis": [
            "How much does Compressor-1 cost?",
            "Boiler-1 expenses",
            "What's the cost of running HVAC-Main?"
        ],
        "ranking": [
            "top 3",
            "top 5 machines",
            "show me top 5",
            "what are the top 3 consumers?",
            "highest 5"
        ],
        "factory_overview": [
            "factory overview",
            "factory status",
            "total kwh",
            "total consumption",
            "facility overview"
        ],
        "comparison": [
            "compare Compressor-1 and Boiler-1",
            "Compressor-1 vs Boiler-1",
            "difference between HVAC-Main and HVAC-EU-North"
        ],
        "forecast": [
            "forecast Compressor-1",
            "predict Boiler-1 demand",
            "what will HVAC-Main use tomorrow?"
        ],
        "anomaly_detection": [
            "anomalies in Compressor-1",
            "detect issues in Boiler-1",
            "any problems with HVAC-Main?"
        ]
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def assert_valid_intent(result, expected_intent_type=None, min_confidence=0.85):
    """
    Helper to assert intent validation result
    
    Args:
        result: ValidationResult object
        expected_intent_type: Expected IntentType (optional)
        min_confidence: Minimum confidence score
    """
    assert result.valid, f"Validation failed: {result.errors}"
    assert result.intent is not None
    assert result.intent.confidence >= min_confidence
    
    if expected_intent_type:
        assert result.intent.intent == expected_intent_type


def assert_intent_dict(intent_dict, expected_intent, min_confidence=0.85):
    """
    Helper to assert raw intent dictionary
    
    Args:
        intent_dict: Raw intent dict from parser
        expected_intent: Expected intent string/enum
        min_confidence: Minimum confidence score
    """
    assert "intent" in intent_dict
    assert "confidence" in intent_dict
    assert intent_dict["confidence"] >= min_confidence
    
    if expected_intent:
        actual_intent = intent_dict["intent"]
        if isinstance(expected_intent, IntentType):
            expected_intent = expected_intent.value
        assert actual_intent == expected_intent or str(actual_intent) == str(expected_intent)
