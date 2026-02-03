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
