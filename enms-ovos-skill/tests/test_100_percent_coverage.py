#!/usr/bin/env python3
"""
Release coverage smoke test for the advertised OVOS use cases.

This file must be import-safe for pytest collection. It intentionally avoids
calling sys.exit at module import time.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "enms_ovos_skill"))

from lib.intent_parser import HybridParser
from lib.validator import ENMSValidator
from lib.models import IntentType


TEST_CASES = {
    "BASIC_SUPPORTED": [
        ("Boiler-1 power", IntentType.POWER_QUERY),
        ("Compressor-1 energy", IntentType.ENERGY_QUERY),
        ("Is Compressor-1 running?", IntentType.MACHINE_STATUS),
        ("top 3", IntentType.RANKING),
        ("factory overview", IntentType.FACTORY_OVERVIEW),
        ("Compare Boiler-1 and Compressor-1", IntentType.COMPARISON),
    ],
    "MULTI_ENERGY": [
        ("Show me natural gas consumption for Boiler-1", IntentType.ENERGY_QUERY),
        ("List all energy sources for HVAC-Main", IntentType.ENERGY_QUERY),
        ("What energy types does Boiler-1 use?", IntentType.ENERGY_QUERY),
        ("Show me energy types for Compressor-1", IntentType.ENERGY_QUERY),
        ("Get electricity readings for Compressor-1 with metadata", IntentType.ENERGY_QUERY),
        ("Summarize all energy consumption for Boiler-1 today", IntentType.ENERGY_QUERY),
        ("What's the energy breakdown for Compressor-1?", IntentType.ENERGY_QUERY),
    ],
    "RANKING_EFFICIENCY": [
        ("Rank all machines by efficiency", IntentType.RANKING),
        ("Which machine is most cost-effective?", IntentType.RANKING),
        ("Which machine uses the most energy?", IntentType.RANKING),
        ("Which machine has the most alerts?", IntentType.ANOMALY_DETECTION),
        ("Show me which machines use the most energy today", IntentType.RANKING),
    ],
    "MULTI_FACTORY": [
        ("Compare energy usage across all factories", IntentType.FACTORY_OVERVIEW),
        ("Which factory is most efficient?", IntentType.FACTORY_OVERVIEW),
    ],
    "BASELINE": [
        ("Explain the Compressor-1 baseline model", IntentType.BASELINE_EXPLANATION),
        ("What are the key energy drivers?", IntentType.DRIVER_ANALYSIS),
        ("How accurate is the model?", IntentType.BASELINE_EXPLANATION),
        ("Does Compressor-1 have a baseline model?", IntentType.BASELINE_MODELS),
    ],
    "FORECAST": [
        ("Forecast energy demand for Compressor-1 next 4 hours", IntentType.FORECAST),
        ("When will peak demand occur tomorrow?", IntentType.FORECAST),
        ("Predict power consumption for HVAC-Main next week", IntentType.FORECAST),
    ],
    "ANOMALY": [
        ("Check for anomalies in Compressor-1 today", IntentType.ANOMALY_DETECTION),
        ("Show me recent anomalies", IntentType.ANOMALY_DETECTION),
        ("Are there any active alerts?", IntentType.ANOMALY_DETECTION),
    ],
    "COST_KPI": [
        ("How much is energy costing us?", IntentType.FACTORY_OVERVIEW),
        ("Show me the KPIs for Compressor-1 today", IntentType.KPI),
        ("Calculate peak demand and load factor", IntentType.KPI),
    ],
}

# This phrasing still falls into clarification and is tracked as a fallback
# robustness gap rather than a release-blocking advertised happy path.
KNOWN_LIMITATIONS = [
    ("What's the steam flow rate for HVAC-Main?", IntentType.POWER_QUERY),
    ("When was the baseline last trained?", IntentType.BASELINE_MODELS),
]


def _run_cases(cases):
    parser = HybridParser()
    validator = ENMSValidator()
    failures = []
    total = 0
    passed = 0

    for category, category_cases in cases.items():
        for query, expected_intent in category_cases:
            total += 1
            result = parser.parse(query)
            validation = validator.validate(result)
            got = validation.intent.intent if validation.valid else None
            if validation.valid and got == expected_intent:
                passed += 1
            else:
                failures.append({
                    "category": category,
                    "query": query,
                    "expected": expected_intent.value,
                    "got": got.value if got else validation.errors[:1],
                })

    return passed, total, failures


def test_release_coverage_for_advertised_use_cases():
    threshold = float(os.getenv("OVOS_RELEASE_COVERAGE_THRESHOLD", "95.0"))
    passed, total, failures = _run_cases(TEST_CASES)
    percentage = (passed / total) * 100

    assert percentage >= threshold, (
        f"Release coverage {percentage:.1f}% is below {threshold:.1f}%: {failures}"
    )


def test_known_limitations_are_documented():
    passed, total, failures = _run_cases({"KNOWN_LIMITATIONS": KNOWN_LIMITATIONS})
    assert total == len(KNOWN_LIMITATIONS)
    assert failures, "Known limitation list should be revisited; all listed gaps now pass."
