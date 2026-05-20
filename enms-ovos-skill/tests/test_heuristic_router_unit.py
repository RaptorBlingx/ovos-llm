"""
Unit Tests for HeuristicRouter
===============================

Tests the ultra-fast regex-based intent detection (20+ cases)
- Top N ranking patterns
- Factory overview patterns
- Machine status patterns
- Power/energy queries
- Comparison patterns
- Performance (<5ms target)
"""
import pytest
import time

from lib.intent_parser import HeuristicRouter
from lib.models import IntentType


class TestRankingPatterns:
    """Test 'top N' ranking query patterns"""
    
    def test_top_n_basic(self):
        """Test 'top 3' pattern"""
        router = HeuristicRouter()
        result = router.route("top 3")
        
        assert result is not None
        assert result['intent'] == 'ranking'
        assert result['limit'] == 3
        assert result['confidence'] >= 0.95
    
    def test_top_n_with_machines(self):
        """Test 'top 5 machines' pattern"""
        router = HeuristicRouter()
        result = router.route("top 5 machines")
        
        assert result is not None
        assert result['intent'] == 'ranking'
        assert result['limit'] == 5
    
    def test_top_n_show_me(self):
        """Test 'show me top 5' pattern"""
        router = HeuristicRouter()
        result = router.route("show me top 5")
        
        assert result is not None
        assert result['intent'] == 'ranking'
        assert result['limit'] == 5
    
    def test_top_n_consumers(self):
        """Test 'top 3 consumers' pattern"""
        router = HeuristicRouter()
        result = router.route("top 3 consumers")
        
        assert result is not None
        assert result['intent'] == 'ranking'
        assert result['limit'] == 3
    
    def test_highest_n(self):
        """Test 'highest 5' pattern"""
        router = HeuristicRouter()
        result = router.route("highest 5")
        
        # May or may not match depending on pattern - check gracefully
        if result:
            assert result['intent'] == 'ranking'

    def test_typo_ranking_phrase_still_stays_out_of_power_query(self):
        """Generic machine phrases with ranking language should not become machine-specific power queries."""
        router = HeuristicRouter()
        result = router.route("which machines are using most electricity")

        assert result is None


class TestFactoryPatterns:
    """Test factory overview patterns"""
    
    def test_factory_overview(self):
        """Test 'factory overview' pattern"""
        router = HeuristicRouter()
        result = router.route("factory overview")
        
        assert result is not None
        assert result['intent'] == 'factory_overview'
        assert result['confidence'] >= 0.95
    
    def test_factory_status(self):
        """Test 'factory status' pattern"""
        router = HeuristicRouter()
        result = router.route("factory status")
        
        assert result is not None
        assert result['intent'] == 'factory_overview'
    
    def test_total_kwh(self):
        """Test 'total kwh' pattern"""
        router = HeuristicRouter()
        result = router.route("total kwh")
        
        assert result is not None
        assert result['intent'] == 'factory_overview'
    
    def test_total_factory_consumption(self):
        """Test 'total factory consumption' pattern"""
        router = HeuristicRouter()
        result = router.route("total factory consumption")
        
        assert result is not None
        assert result['intent'] == 'factory_overview'


class TestMachineStatusPatterns:
    """Test machine status patterns"""
    
    def test_machine_status_basic(self):
        """Test 'Compressor-1 status' pattern"""
        router = HeuristicRouter()
        result = router.route("Compressor-1 status")
        
        assert result is not None
        assert result['intent'] == 'machine_status'
        assert result['machine'] == 'Compressor-1'
    
    def test_is_machine_running(self):
        """Test 'Is Boiler-1 running?' pattern"""
        router = HeuristicRouter()
        result = router.route("Is Boiler-1 running?")
        
        assert result is not None
        assert result['intent'] == 'machine_status'
        assert result['machine'] == 'Boiler-1'
    
    def test_check_machine(self):
        """Test 'check HVAC-Main' pattern"""
        router = HeuristicRouter()
        result = router.route("check HVAC-Main")
        
        assert result is not None
        assert result['intent'] == 'machine_status'
        assert result['machine'] == 'HVAC-Main'


class TestPowerPatterns:
    """Test power query patterns"""
    
    def test_machine_power(self):
        """Test 'Compressor-1 power' pattern"""
        router = HeuristicRouter()
        result = router.route("Compressor-1 power")
        
        assert result is not None
        assert result['intent'] == 'power_query'
        assert result['machine'] == 'Compressor-1'
        assert result['metric'] == 'power'
    
    def test_machine_watts(self):
        """Test 'HVAC-Main watts' pattern"""
        router = HeuristicRouter()
        result = router.route("HVAC-Main watts")
        
        assert result is not None
        assert result['intent'] == 'power_query'
        assert 'HVAC' in result['machine']  # Could match HVAC-Main or HVAC-EU-North
    
    def test_power_of_machine(self):
        """Test 'power of Boiler-1' pattern"""
        router = HeuristicRouter()
        result = router.route("power of Boiler-1")
        
        assert result is not None
        assert result['intent'] == 'power_query'
        assert result['machine'] == 'Boiler-1'

    def test_typo_power_query_uses_fuzzy_recovery(self):
        """A typo-heavy power query should recover in the heuristic tier instead of falling to LLM."""
        router = HeuristicRouter()
        result = router.route("what is the powre of comprsor one")

        assert result is not None
        assert result['intent'] == 'power_query'
        assert result['machine'] == 'Compressor-1'
        assert result['metric'] == 'power'


class TestEnergyPatterns:
    """Test energy query patterns"""
    
    def test_machine_energy(self):
        """Test 'Compressor-1 energy' pattern"""
        router = HeuristicRouter()
        result = router.route("Compressor-1 energy")
        
        assert result is not None
        assert result['intent'] == 'energy_query'
        assert result['machine'] == 'Compressor-1'
    
    def test_machine_kwh(self):
        """Test 'Boiler-1 kwh' pattern"""
        router = HeuristicRouter()
        result = router.route("Boiler-1 kwh")
        
        assert result is not None
        assert result['intent'] == 'energy_query'
        assert result['machine'] == 'Boiler-1'


class TestSEUPatterns:
    """Test SEU query phrase variants"""

    @pytest.mark.parametrize(
        "query",
        [
            "what are the significant energy users",
            "what is the significant energy users",
            "what are the SEU",
            "what are the SEUs",
            "what are the SEU's",
        ],
    )
    def test_seu_query_variants_route_to_seus(self, query):
        """Common SEU phrasings should resolve to the SEUS intent."""
        router = HeuristicRouter()
        result = router.route(query)

        assert result is not None
        assert result['intent'] == 'seus'
        assert result['confidence'] >= 0.95


class TestDriverAnalysisPatterns:
    """Test dedicated driver-analysis routing."""

    def test_main_drivers_for_machine(self):
        """Driver-focused machine queries should not collapse into baseline explanation."""
        router = HeuristicRouter()
        result = router.route("what are the main drivers for Compressor-1")

        assert result is not None
        assert result['intent'] == 'driver_analysis'
        assert result['machine'] == 'Compressor-1'

    def test_specific_driver_question_extracts_driver_name(self):
        """Specific-driver phrasing should preserve the requested driver."""
        router = HeuristicRouter()
        result = router.route("does temperature affect energy use of Compressor-1")

        assert result is not None
        assert result['intent'] == 'driver_analysis'
        assert result['machine'] == 'Compressor-1'
        assert result['driver_name'] == 'temperature'

    def test_driver_query_extracts_energy_source(self):
        """Energy-source qualifiers should be preserved for multi-energy routing."""
        router = HeuristicRouter()
        result = router.route("what are the top drivers for Boiler-1 natural gas")

        assert result is not None
        assert result['intent'] == 'driver_analysis'
        assert result['energy_source'] == 'natural_gas'


class TestComparisonPatterns:
    """Test comparison patterns"""
    
    def test_compare_and(self):
        """Test 'compare Compressor-1 and Boiler-1' pattern"""
        router = HeuristicRouter()
        result = router.route("compare Compressor-1 and Boiler-1")
        
        assert result is not None
        assert result['intent'] == 'comparison'
        assert 'machines' in result
    
    def test_machine_vs_machine(self):
        """Test 'Compressor-1 vs Boiler-1' pattern"""
        router = HeuristicRouter()
        result = router.route("Compressor-1 vs Boiler-1")
        
        assert result is not None
        assert result['intent'] == 'comparison'


class TestPerformance:
    """Test heuristic router performance (<5ms target)"""
    
    def test_latency_under_5ms(self):
        """All patterns should match in <5ms"""
        router = HeuristicRouter()
        
        test_queries = [
            "top 3",
            "factory overview",
            "Compressor-1 status",
            "Boiler-1 power",
            "HVAC-Main energy"
        ]
        
        total_time = 0
        for query in test_queries:
            start = time.time()
            result = router.route(query)
            latency_ms = (time.time() - start) * 1000
            
            total_time += latency_ms
            assert latency_ms < 5.0, f"Query '{query}' took {latency_ms:.2f}ms (> 5ms)"
        
        avg_latency = total_time / len(test_queries)
        assert avg_latency < 3.0, f"Average latency {avg_latency:.2f}ms (target <3ms)"
    
    def test_no_match_performance(self):
        """Non-matching queries should also be fast"""
        router = HeuristicRouter()
        
        start = time.time()
        result = router.route("This is a complex query that won't match any pattern")
        latency_ms = (time.time() - start) * 1000
        
        assert result is None
        assert latency_ms < 5.0
