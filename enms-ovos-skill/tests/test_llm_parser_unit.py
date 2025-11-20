"""
Unit Tests for Qwen3Parser (LLM Parser)
========================================

Tests the LLM-based intent parsing (30+ cases)
- JSON extraction from LLM output
- Intent parsing
- Entity extraction
- Error handling
- Mock LLM responses (no real LLM calls for speed)
"""
import pytest
import json

from lib.qwen3_parser import Qwen3Parser


class TestJSONExtraction:
    """Test JSON extraction from LLM output"""
    
    def test_extract_clean_json(self, mocker):
        """Test extracting clean JSON object"""
        parser = Qwen3Parser()
        
        llm_output = '''{"intent": "machine_status", "confidence": 0.95, "machine": "Compressor-1"}'''
        
        # Mock the LLM call
        mocker.patch.object(parser, '_call_llm', return_value=llm_output)
        
        result = parser.parse("Is Compressor-1 running?")
        
        assert result is not None
        assert result['intent'] == 'machine_status'
        assert result['confidence'] == 0.95
    
    def test_extract_json_with_markdown(self, mocker):
        """Test extracting JSON from markdown code block"""
        parser = Qwen3Parser()
        
        llm_output = '''
        ```json
        {"intent": "power_query", "confidence": 0.92, "machine": "Boiler-1"}
        ```
        '''
        
        mocker.patch.object(parser, '_call_llm', return_value=llm_output)
        
        result = parser.parse("Boiler-1 power")
        
        assert result is not None
        assert result['intent'] == 'power_query'
    
    def test_extract_json_with_text_before(self, mocker):
        """Test extracting JSON with explanatory text before"""
        parser = Qwen3Parser()
        
        llm_output = '''
        Let me parse this query for you.
        {"intent": "energy_query", "confidence": 0.90, "machine": "HVAC-Main"}
        '''
        
        mocker.patch.object(parser, '_call_llm', return_value=llm_output)
        
        result = parser.parse("HVAC-Main energy")
        
        assert result is not None
        assert result['intent'] == 'energy_query'
    
    def test_extract_json_with_text_after(self, mocker):
        """Test extracting JSON with text after"""
        parser = Qwen3Parser()
        
        llm_output = '''
        {"intent": "ranking", "confidence": 0.95, "limit": 5}
        This query asks for the top 5 machines.
        '''
        
        mocker.patch.object(parser, '_call_llm', return_value=llm_output)
        
        result = parser.parse("top 5")
        
        assert result is not None
        assert result['intent'] == 'ranking'
        assert result['limit'] == 5


class TestIntentParsing:
    """Test parsing different intent types"""
    
    def test_parse_machine_status(self, mocker):
        """Test parsing machine status intent"""
        parser = Qwen3Parser()
        
        llm_output = json.dumps({
            "intent": "machine_status",
            "confidence": 0.95,
            "machine": "Compressor-1",
            "entities": {}
        })
        
        mocker.patch.object(parser, '_call_llm', return_value=llm_output)
        
        result = parser.parse("Is Compressor-1 running?")
        
        assert result['intent'] == 'machine_status'
        assert result['machine'] == 'Compressor-1'
    
    def test_parse_power_query(self, mocker):
        """Test parsing power query intent"""
        parser = Qwen3Parser()
        
        llm_output = json.dumps({
            "intent": "power_query",
            "confidence": 0.92,
            "machine": "Boiler-1",
            "metric": "power"
        })
        
        mocker.patch.object(parser, '_call_llm', return_value=llm_output)
        
        result = parser.parse("What's the power of Boiler-1?")
        
        assert result['intent'] == 'power_query'
        assert result['metric'] == 'power'
    
    def test_parse_energy_query_with_time(self, mocker):
        """Test parsing energy query with time range"""
        parser = Qwen3Parser()
        
        llm_output = json.dumps({
            "intent": "energy_query",
            "confidence": 0.90,
            "machine": "Compressor-1",
            "entities": {
                "time_range": "yesterday"
            }
        })
        
        mocker.patch.object(parser, '_call_llm', return_value=llm_output)
        
        result = parser.parse("How much energy did Compressor-1 use yesterday?")
        
        assert result['intent'] == 'energy_query'
        assert result['entities']['time_range'] == 'yesterday'
    
    def test_parse_ranking_query(self, mocker):
        """Test parsing ranking query"""
        parser = Qwen3Parser()
        
        llm_output = json.dumps({
            "intent": "ranking",
            "confidence": 0.95,
            "limit": 3,
            "metric": "energy"
        })
        
        mocker.patch.object(parser, '_call_llm', return_value=llm_output)
        
        result = parser.parse("Show me the top 3 energy consumers")
        
        assert result['intent'] == 'ranking'
        assert result['limit'] == 3
    
    def test_parse_factory_overview(self, mocker):
        """Test parsing factory overview intent"""
        parser = Qwen3Parser()
        
        llm_output = json.dumps({
            "intent": "factory_overview",
            "confidence": 0.96
        })
        
        mocker.patch.object(parser, '_call_llm', return_value=llm_output)
        
        result = parser.parse("Give me a factory overview")
        
        assert result['intent'] == 'factory_overview'
    
    def test_parse_comparison(self, mocker):
        """Test parsing comparison intent"""
        parser = Qwen3Parser()
        
        llm_output = json.dumps({
            "intent": "comparison",
            "confidence": 0.93,
            "machines": ["Compressor-1", "Boiler-1"]
        })
        
        mocker.patch.object(parser, '_call_llm', return_value=llm_output)
        
        result = parser.parse("Compare Compressor-1 and Boiler-1")
        
        assert result['intent'] == 'comparison'
        assert len(result['machines']) == 2


class TestEntityExtraction:
    """Test entity extraction from LLM output"""
    
    def test_extract_machine_entity(self, mocker):
        """Test extracting machine entity"""
        parser = Qwen3Parser()
        
        llm_output = json.dumps({
            "intent": "machine_status",
            "confidence": 0.95,
            "entities": {
                "machine": "Compressor-1"
            }
        })
        
        mocker.patch.object(parser, '_call_llm', return_value=llm_output)
        
        result = parser.parse("Check Compressor-1")
        
        assert 'entities' in result
        assert result['entities']['machine'] == 'Compressor-1'
    
    def test_extract_time_range_entity(self, mocker):
        """Test extracting time range entity"""
        parser = Qwen3Parser()
        
        llm_output = json.dumps({
            "intent": "energy_query",
            "confidence": 0.90,
            "machine": "Boiler-1",
            "entities": {
                "time_range": "last week"
            }
        })
        
        mocker.patch.object(parser, '_call_llm', return_value=llm_output)
        
        result = parser.parse("Boiler-1 energy last week")
        
        assert result['entities']['time_range'] == 'last week'
    
    def test_extract_limit_entity(self, mocker):
        """Test extracting limit entity for ranking"""
        parser = Qwen3Parser()
        
        llm_output = json.dumps({
            "intent": "ranking",
            "confidence": 0.95,
            "entities": {
                "limit": 5
            }
        })
        
        mocker.patch.object(parser, '_call_llm', return_value=llm_output)
        
        result = parser.parse("top 5 machines")
        
        assert result['entities']['limit'] == 5


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    def test_invalid_json(self, mocker):
        """Test handling invalid JSON from LLM"""
        parser = Qwen3Parser()
        
        llm_output = '''{"intent": "machine_status", "confidence": 0.95 INVALID'''
        
        mocker.patch.object(parser, '_call_llm', return_value=llm_output)
        
        # Should handle gracefully
        with pytest.raises(Exception):
            parser.parse("Some query")
    
    def test_empty_llm_response(self, mocker):
        """Test handling empty LLM response"""
        parser = Qwen3Parser()
        
        mocker.patch.object(parser, '_call_llm', return_value='')
        
        with pytest.raises(Exception):
            parser.parse("Some query")
    
    def test_llm_timeout(self, mocker):
        """Test handling LLM timeout"""
        parser = Qwen3Parser()
        
        # Mock a timeout exception
        mocker.patch.object(parser, '_call_llm', side_effect=TimeoutError("LLM timeout"))
        
        with pytest.raises(TimeoutError):
            parser.parse("Some query")
    
    def test_llm_error(self, mocker):
        """Test handling LLM error"""
        parser = Qwen3Parser()
        
        mocker.patch.object(parser, '_call_llm', side_effect=Exception("LLM error"))
        
        with pytest.raises(Exception):
            parser.parse("Some query")


class TestComplexQueries:
    """Test parsing complex multi-entity queries"""
    
    def test_complex_temporal_query(self, mocker):
        """Test complex query with time range"""
        parser = Qwen3Parser()
        
        llm_output = json.dumps({
            "intent": "energy_query",
            "confidence": 0.88,
            "machine": "Compressor-1",
            "entities": {
                "time_range": "from October 27 to October 28",
                "metric": "energy"
            }
        })
        
        mocker.patch.object(parser, '_call_llm', return_value=llm_output)
        
        result = parser.parse("How much energy did Compressor-1 use from October 27 to October 28?")
        
        assert result['intent'] == 'energy_query'
        assert 'time_range' in result['entities']
    
    def test_complex_comparison_query(self, mocker):
        """Test complex comparison with multiple attributes"""
        parser = Qwen3Parser()
        
        llm_output = json.dumps({
            "intent": "comparison",
            "confidence": 0.90,
            "machines": ["Compressor-1", "Compressor-EU-1"],
            "metric": "energy",
            "entities": {
                "time_range": "last week"
            }
        })
        
        mocker.patch.object(parser, '_call_llm', return_value=llm_output)
        
        result = parser.parse("Compare energy of Compressor-1 and Compressor-EU-1 last week")
        
        assert result['intent'] == 'comparison'
        assert len(result['machines']) == 2
    
    def test_ambiguous_query(self, mocker):
        """Test handling ambiguous query"""
        parser = Qwen3Parser()
        
        llm_output = json.dumps({
            "intent": "unknown",
            "confidence": 0.45
        })
        
        mocker.patch.object(parser, '_call_llm', return_value=llm_output)
        
        result = parser.parse("What about that thing?")
        
        assert result['intent'] == 'unknown'
        assert result['confidence'] < 0.85  # Below validator threshold


class TestBraceCountingJSONExtraction:
    """Test the brace-counting JSON extraction method"""
    
    def test_nested_json_extraction(self, mocker):
        """Test extracting nested JSON with brace counting"""
        parser = Qwen3Parser()
        
        llm_output = '''
        Here's the result:
        {
            "intent": "energy_query",
            "confidence": 0.90,
            "entities": {
                "machine": "Compressor-1",
                "time_range": "yesterday"
            }
        }
        Additional text here.
        '''
        
        mocker.patch.object(parser, '_call_llm', return_value=llm_output)
        
        result = parser.parse("Some query")
        
        assert result is not None
        assert result['intent'] == 'energy_query'
        assert 'entities' in result
    
    def test_multiple_json_objects(self, mocker):
        """Test extracting first JSON when multiple present"""
        parser = Qwen3Parser()
        
        llm_output = '''
        {"intent": "machine_status", "confidence": 0.95}
        {"intent": "power_query", "confidence": 0.90}
        '''
        
        mocker.patch.object(parser, '_call_llm', return_value=llm_output)
        
        result = parser.parse("Some query")
        
        # Should extract the first valid JSON
        assert result is not None
        assert result['intent'] == 'machine_status'
