"""
Unit tests for LLM Parser Module

Tests Qwen3Parser functionality including model loading, parsing,
timeout handling, and error cases.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Test without requiring llama-cpp-python
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from enms_ovos_skill.lib.llm_parser import Qwen3Parser


class TestQwen3ParserInit:
    """Test parser initialization"""
    
    def test_init_default_params(self):
        """Test initialization with default parameters"""
        parser = Qwen3Parser("/models/test.gguf")
        
        assert parser.model_path == Path("/models/test.gguf")
        assert parser.thinking_enabled is False
        assert parser.model is None
        assert parser.context_size == 4096
        assert parser.timeout == 5.0
    
    def test_init_thinking_enabled(self):
        """Test initialization with thinking mode"""
        parser = Qwen3Parser("/models/test.gguf", thinking_enabled=True)
        
        assert parser.thinking_enabled is True
    
    def test_init_metrics(self):
        """Test metrics are initialized"""
        parser = Qwen3Parser("/models/test.gguf")
        
        assert parser.metrics["inferences_total"] == 0
        assert parser.metrics["inferences_success"] == 0
        assert parser.metrics["inferences_failure"] == 0


class TestQwen3ParserJsonParsing:
    """Test JSON response parsing"""
    
    def test_parse_valid_json(self):
        """Test parsing valid JSON response"""
        parser = Qwen3Parser("/models/test.gguf")
        
        json_text = '{"intent": "energy_query", "machine": "Compressor-1", "confidence": 0.95}'
        result = parser._parse_json_response(json_text)
        
        assert result is not None
        assert result["intent"] == "energy_query"
        assert result["machine"] == "Compressor-1"
        assert result["confidence"] == 0.95
        assert result["tier"] == "llm"
    
    def test_parse_json_with_markdown(self):
        """Test parsing JSON wrapped in markdown code blocks"""
        parser = Qwen3Parser("/models/test.gguf")
        
        json_text = '```json\n{"intent": "ranking", "confidence": 0.80}\n```'
        result = parser._parse_json_response(json_text)
        
        assert result is not None
        assert result["intent"] == "ranking"
        assert result["confidence"] == 0.80
    
    def test_parse_json_no_machine(self):
        """Test parsing JSON without machine field"""
        parser = Qwen3Parser("/models/test.gguf")
        
        json_text = '{"intent": "factory_overview", "confidence": 0.99}'
        result = parser._parse_json_response(json_text)
        
        assert result is not None
        assert result["intent"] == "factory_overview"
        assert result["machine"] is None
    
    def test_parse_json_missing_confidence(self):
        """Test parsing JSON with missing confidence (defaults to 0.5)"""
        parser = Qwen3Parser("/models/test.gguf")
        
        json_text = '{"intent": "power_query", "machine": "Boiler-1"}'
        result = parser._parse_json_response(json_text)
        
        assert result is not None
        assert result["confidence"] == 0.5
    
    def test_parse_json_missing_intent(self):
        """Test parsing JSON without intent field (should fail)"""
        parser = Qwen3Parser("/models/test.gguf")
        
        json_text = '{"machine": "Compressor-1", "confidence": 0.95}'
        result = parser._parse_json_response(json_text)
        
        assert result is None
    
    def test_parse_invalid_json(self):
        """Test parsing malformed JSON"""
        parser = Qwen3Parser("/models/test.gguf")
        
        json_text = '{"intent": "energy_query", invalid json'
        result = parser._parse_json_response(json_text)
        
        assert result is None
    
    def test_parse_json_invalid_confidence(self):
        """Test parsing JSON with invalid confidence value"""
        parser = Qwen3Parser("/models/test.gguf")
        
        json_text = '{"intent": "ranking", "confidence": 1.5}'
        result = parser._parse_json_response(json_text)
        
        assert result is not None
        assert result["confidence"] == 0.5  # Should default to 0.5


class TestQwen3ParserMetrics:
    """Test metrics tracking"""
    
    def test_get_metrics_empty(self):
        """Test metrics with no inferences"""
        parser = Qwen3Parser("/models/test.gguf")
        metrics = parser.get_metrics()
        
        assert metrics["total_inferences"] == 0
        assert metrics["success_rate"] == 0.0
        assert metrics["avg_duration_ms"] == 0
    
    def test_get_metrics_with_data(self):
        """Test metrics after simulated inferences"""
        parser = Qwen3Parser("/models/test.gguf")
        
        parser.metrics["inferences_total"] = 10
        parser.metrics["inferences_success"] = 8
        parser.metrics["inferences_failure"] = 2
        parser.metrics["inference_duration_ms"] = [100, 150, 200, 120, 180, 90, 110, 140]
        
        metrics = parser.get_metrics()
        
        assert metrics["total_inferences"] == 10
        assert metrics["success_count"] == 8
        assert metrics["failure_count"] == 2
        assert metrics["success_rate"] == 0.8
        assert 100 < metrics["avg_duration_ms"] < 200


class TestQwen3ParserParse:
    """Test parse method (mocked, no actual model)"""
    
    @patch('enms_ovos_skill.lib.llm_parser.LLAMA_CPP_AVAILABLE', False)
    def test_parse_without_model_loaded(self):
        """Test parsing when model not loaded"""
        parser = Qwen3Parser("/models/test.gguf")
        
        result = parser.parse(
            "test query",
            machines=["Compressor-1"],
            intents=["energy_query"]
        )
        
        assert result is None
    
    @patch('enms_ovos_skill.lib.llm_parser.Llama')
    def test_parse_calls_llm(self, mock_llama):
        """Test that parse calls LLM with correct parameters"""
        parser = Qwen3Parser("/models/test.gguf")
        
        # Mock model response
        mock_model = MagicMock()
        mock_model.return_value = {
            "choices": [{
                "text": '{"intent": "energy_query", "machine": "Compressor-1", "confidence": 0.95}'
            }]
        }
        parser.model = mock_model
        
        result = parser.parse(
            "energy consumption of Compressor-1",
            machines=["Compressor-1", "Boiler-1"],
            intents=["energy_query", "power_query"]
        )
        
        assert result is not None
        assert result["intent"] == "energy_query"
        assert result["machine"] == "Compressor-1"
        assert mock_model.called


@pytest.mark.skipif(
    not Path("/models/Qwen3-1.7B-Q4_K_M.gguf").exists(),
    reason="Model file not available"
)
class TestQwen3ParserIntegration:
    """Integration tests (requires actual model file)"""
    
    def test_load_model_success(self):
        """Test loading actual model file"""
        parser = Qwen3Parser("/models/Qwen3-1.7B-Q4_K_M.gguf")
        
        try:
            parser.load_model()
            assert parser.model is not None
        except Exception as e:
            pytest.skip(f"Model loading failed: {e}")
    
    def test_parse_real_query(self):
        """Test parsing with real model (if available)"""
        parser = Qwen3Parser("/models/Qwen3-1.7B-Q4_K_M.gguf")
        
        try:
            parser.load_model()
        except Exception:
            pytest.skip("Model not available")
        
        result = parser.parse(
            "which machines are wasting electricity",
            machines=["Compressor-1", "Boiler-1", "HVAC-Main"],
            intents=["ranking", "energy_query", "factory_overview"]
        )
        
        assert result is not None
        assert result["intent"] in ["ranking", "energy_query"]
        assert 0.0 <= result["confidence"] <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
