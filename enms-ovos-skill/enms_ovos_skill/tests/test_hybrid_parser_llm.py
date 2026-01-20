"""
Integration tests for HybridParser with LLM tier

Tests the complete 3-tier intent routing system:
- Tier 1: Heuristic patterns
- Tier 2: Adapt vocabulary
- Tier 3: LLM fallback (Qwen3-1.7B)
"""

import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Mock dependencies
sys.modules['structlog'] = MagicMock()

sys.path.insert(0, str(Path(__file__).parent.parent / 'lib'))

from intent_parser import HybridParser, RoutingTier, IntentType


class TestHybridParserLLMIntegration:
    """Test LLM tier integration in HybridParser"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.parser = HybridParser()
    
    def test_parser_initialization(self):
        """Test parser initializes with LLM tier disabled"""
        assert self.parser.llm is None
        assert 'llm' in self.parser.stats
        assert self.parser.stats['llm'] == 0
    
    def test_stats_dict_has_llm_key(self):
        """Test that stats dict includes 'llm' key (bugfix verification)"""
        # This was a pre-existing bug where stats['llm'] was referenced
        # at line 1197 but never initialized
        assert 'llm' in self.parser.stats
        assert self.parser.stats['llm'] == 0
    
    def test_init_llm_method_exists(self):
        """Test that init_llm method exists"""
        assert hasattr(self.parser, 'init_llm')
        assert callable(self.parser.init_llm)


class TestTierRouting:
    """Test query routing across tiers"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.parser = HybridParser()
    
    def test_tier1_heuristic_match(self):
        """Test that heuristic tier catches simple queries"""
        result = self.parser.parse("power of Compressor-1")
        
        assert result is not None
        assert result.get('tier') == RoutingTier.HEURISTIC
        assert result.get('intent') in ['power_query', 'energy_query']
        assert self.parser.stats['heuristic'] == 1
        assert self.parser.stats['llm'] == 0
    
    def test_tier1_energy_query(self):
        """Test heuristic tier for energy queries"""
        result = self.parser.parse("energy consumption of Boiler-1")
        
        assert result is not None
        assert result.get('tier') == RoutingTier.HEURISTIC
        assert result.get('intent') == 'energy_query'
        assert self.parser.stats['heuristic'] == 1
    
    def test_tier1_factory_overview(self):
        """Test heuristic tier for factory overview"""
        result = self.parser.parse("factory overview")
        
        assert result is not None
        assert result.get('tier') == RoutingTier.HEURISTIC
        assert result.get('intent') == 'factory_overview'


class TestLLMTierFallback:
    """Test LLM tier as fallback when Tier 1+2 fail"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.parser = HybridParser()
    
    @patch('intent_parser.Qwen3Parser')
    def test_llm_tier_not_called_when_disabled(self, mock_qwen):
        """Test that LLM tier is not called when not initialized"""
        result = self.parser.parse("complex unmatched query")
        
        # Should fall through to clarification_needed
        assert result.get('intent') == 'clarification_needed'
        assert self.parser.stats['llm'] == 0
        mock_qwen.assert_not_called()
    
    @patch('intent_parser.Qwen3Parser')
    def test_llm_tier_called_when_enabled(self, mock_qwen):
        """Test that LLM tier is called when initialized and Tier 1+2 fail"""
        # Mock LLM parser
        mock_llm_instance = MagicMock()
        mock_llm_instance.model = MagicMock()  # Model is loaded
        mock_llm_instance.parse.return_value = {
            'intent': 'ranking',
            'machine': None,
            'confidence': 0.85,
            'tier': 'llm'
        }
        
        # Initialize LLM (mock)
        self.parser.llm = mock_llm_instance
        
        # Query that should miss Tier 1+2
        result = self.parser.parse("give me a breakdown of where power is going")
        
        # Verify LLM was called
        assert mock_llm_instance.parse.called
        assert result.get('intent') == 'ranking'
        assert self.parser.stats['llm'] == 1
    
    @patch('intent_parser.Qwen3Parser')
    def test_llm_tier_confidence_threshold(self, mock_qwen):
        """Test that LLM results below confidence threshold are rejected"""
        mock_llm_instance = MagicMock()
        mock_llm_instance.model = MagicMock()
        mock_llm_instance.parse.return_value = {
            'intent': 'unclear_intent',
            'machine': None,
            'confidence': 0.4,  # Below 0.7 threshold
            'tier': 'llm'
        }
        
        self.parser.llm = mock_llm_instance
        
        result = self.parser.parse("ambiguous query")
        
        # Should fall through to clarification_needed
        assert result.get('intent') == 'clarification_needed'
        assert self.parser.stats['llm'] == 0  # Not counted as success


class TestRoutingLatency:
    """Test routing latency tracking"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.parser = HybridParser()
    
    def test_heuristic_latency_fast(self):
        """Test that heuristic tier is very fast (<10ms)"""
        start = time.time()
        result = self.parser.parse("power of Compressor-1")
        latency_ms = (time.time() - start) * 1000
        
        assert result.get('tier') == RoutingTier.HEURISTIC
        assert latency_ms < 10, f"Heuristic tier too slow: {latency_ms:.2f}ms"
    
    @patch('intent_parser.Qwen3Parser')
    def test_llm_latency_slower(self, mock_qwen):
        """Test that LLM tier is slower but bounded"""
        mock_llm_instance = MagicMock()
        mock_llm_instance.model = MagicMock()
        
        # Simulate LLM inference delay (100ms)
        def slow_parse(*args, **kwargs):
            time.sleep(0.1)
            return {
                'intent': 'ranking',
                'confidence': 0.85,
                'tier': 'llm'
            }
        
        mock_llm_instance.parse.side_effect = slow_parse
        self.parser.llm = mock_llm_instance
        
        start = time.time()
        result = self.parser.parse("complex query")
        latency_ms = (time.time() - start) * 1000
        
        # Should be >100ms (LLM time) but <200ms (no cascading delays)
        assert latency_ms > 90
        assert latency_ms < 200


class TestStatsTracking:
    """Test statistics tracking across tiers"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.parser = HybridParser()
    
    def test_stats_increments_correctly(self):
        """Test that stats dict increments for each tier"""
        # Tier 1 query
        self.parser.parse("power of Compressor-1")
        assert self.parser.stats['heuristic'] == 1
        assert self.parser.stats['total'] == 1
        
        # Another Tier 1 query
        self.parser.parse("energy consumption")
        assert self.parser.stats['heuristic'] == 2
        assert self.parser.stats['total'] == 2
        
        # Clarification query
        self.parser.parse("xyzabc nonsense")
        assert self.parser.stats['clarification'] == 1
        assert self.parser.stats['total'] == 3
    
    def test_get_stats_distribution(self):
        """Test get_stats() returns distribution percentages"""
        # Run mix of queries
        self.parser.parse("power of Compressor-1")
        self.parser.parse("energy consumption")
        self.parser.parse("factory overview")
        self.parser.parse("nonsense query")
        
        stats = self.parser.get_stats()
        
        assert 'distribution' in stats
        assert 'heuristic' in stats['distribution']
        assert 'llm' in stats['distribution']
        
        # Should show percentage strings
        heuristic_pct = stats['distribution']['heuristic']
        assert isinstance(heuristic_pct, str)
        assert '%' in heuristic_pct


@pytest.mark.skipif(
    not Path("/models/Qwen3-1.7B-Q4_K_M.gguf").exists(),
    reason="Model file not available - run in Docker container"
)
class TestLLMTierWithRealModel:
    """Integration tests with actual Qwen3 model (requires Docker)"""
    
    def setup_method(self):
        """Setup parser with real LLM"""
        self.parser = HybridParser()
        try:
            self.parser.init_llm("/models/Qwen3-1.7B-Q4_K_M.gguf")
        except Exception as e:
            pytest.skip(f"Model loading failed: {e}")
    
    def test_llm_handles_natural_language_query(self):
        """Test LLM can parse natural language that Tier 1+2 miss"""
        result = self.parser.parse("which machines are wasting electricity")
        
        assert result is not None
        assert result.get('tier') == RoutingTier.LLM
        assert result.get('intent') in ['ranking', 'energy_query']
        assert result.get('confidence', 0) >= 0.7
    
    def test_llm_reasoning_mode(self):
        """Test LLM thinking mode for complex queries"""
        # Enable thinking mode
        if self.parser.llm:
            self.parser.llm.thinking_enabled = True
        
        result = self.parser.parse("if I reduce compressor runtime by 2 hours how much would I save")
        
        assert result is not None
        # May route to LLM or clarification depending on complexity
        assert result.get('tier') in [RoutingTier.LLM, RoutingTier.HEURISTIC]
    
    def test_llm_inference_latency(self):
        """Test that LLM inference completes within timeout"""
        start = time.time()
        result = self.parser.parse("give me a breakdown of power consumption")
        latency_ms = (time.time() - start) * 1000
        
        # Should complete within 10 seconds (5s timeout + 5s buffer)
        assert latency_ms < 10000
        
        # If LLM was used, should be >100ms
        if result.get('tier') == RoutingTier.LLM:
            assert latency_ms > 100


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
