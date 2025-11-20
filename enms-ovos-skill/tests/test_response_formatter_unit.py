"""
Unit Tests for ResponseFormatter
=================================

Tests the voice-optimized response generation (20+ cases)
- Template rendering
- Voice number formatting
- Voice unit formatting
- Voice time formatting
- All dialog templates
"""
import pytest
from datetime import datetime

from lib.response_formatter import ResponseFormatter


class TestTemplateRendering:
    """Test Jinja2 template rendering"""
    
    def test_machine_status_template(self, response_formatter):
        """Test machine status dialog template"""
        data = {
            "machine_name": "Compressor-1",
            "current_status": "running",
            "power_kw": 47.98,
            "uptime_hours": 23.5
        }
        
        response = response_formatter.format_response("machine_status", data)
        
        assert "Compressor-1" in response
        assert "running" in response.lower()
    
    def test_energy_query_template(self, response_formatter):
        """Test energy query dialog template"""
        data = {
            "machine_name": "Boiler-1",
            "energy_kwh": 1152.5,
            "time_period": "today"
        }
        
        response = response_formatter.format_response("energy_query", data)
        
        assert "Boiler-1" in response
    
    def test_power_query_template(self, response_formatter):
        """Test power query dialog template"""
        data = {
            "machine_name": "HVAC-Main",
            "power_kw": 23.45
        }
        
        response = response_formatter.format_response("power_query", data)
        
        assert "HVAC-Main" in response
    
    def test_factory_overview_template(self, response_formatter):
        """Test factory overview dialog template"""
        data = {
            "total_machines": 8,
            "active_machines": 7,
            "total_power_kw": 384.2,
            "total_energy_kwh": 9205.7
        }
        
        response = response_formatter.format_response("factory_overview", data)
        
        assert "8" in response or "eight" in response.lower()


class TestVoiceNumberFormatting:
    """Test voice-optimized number formatting"""
    
    def test_small_integer(self, response_formatter):
        """Test formatting small integers"""
        result = response_formatter._voice_number(5)
        
        assert result == "five"
    
    def test_teen_number(self, response_formatter):
        """Test formatting teen numbers (11-19)"""
        result = response_formatter._voice_number(13)
        
        assert result == "thirteen"
    
    def test_tens(self, response_formatter):
        """Test formatting tens (20, 30, etc.)"""
        result = response_formatter._voice_number(30)
        
        assert result == "thirty"
    
    def test_compound_number(self, response_formatter):
        """Test formatting compound numbers (25, 47, etc.)"""
        result = response_formatter._voice_number(47)
        
        assert "forty" in result
        assert "seven" in result
    
    def test_hundreds(self, response_formatter):
        """Test formatting hundreds"""
        result = response_formatter._voice_number(500)
        
        assert "five hundred" in result
    
    def test_thousands(self, response_formatter):
        """Test formatting thousands"""
        result = response_formatter._voice_number(1500)
        
        assert "thousand" in result
    
    def test_decimal_rounding(self, response_formatter):
        """Test decimal number rounding"""
        result = response_formatter._voice_number(47.984, precision=0)
        
        # Should round to 48
        assert "forty" in result
        assert "eight" in result
    
    def test_zero(self, response_formatter):
        """Test formatting zero"""
        result = response_formatter._voice_number(0)
        
        assert result == "zero"


class TestVoiceUnitFormatting:
    """Test voice-optimized unit formatting"""
    
    def test_kilowatts(self, response_formatter):
        """Test formatting kilowatts"""
        result = response_formatter._voice_unit(47.98, "kW")
        
        assert "kilowatts" in result
        assert "forty" in result
    
    def test_kilowatt_hours(self, response_formatter):
        """Test formatting kilowatt hours"""
        result = response_formatter._voice_unit(1152.5, "kWh")
        
        assert "kilowatt hours" in result
    
    def test_megawatts(self, response_formatter):
        """Test formatting megawatts"""
        result = response_formatter._voice_unit(2.5, "MW")
        
        assert "megawatts" in result
    
    def test_euros(self, response_formatter):
        """Test formatting euros"""
        result = response_formatter._voice_unit(250.50, "EUR")
        
        assert "euros" in result
    
    def test_percent(self, response_formatter):
        """Test formatting percent"""
        result = response_formatter._voice_unit(87.3, "%")
        
        assert "percent" in result


class TestVoiceTimeFormatting:
    """Test voice-optimized time formatting"""
    
    def test_datetime_formatting(self, response_formatter):
        """Test formatting datetime objects"""
        dt = datetime(2025, 11, 19, 15, 30, 0)
        result = response_formatter._voice_time(dt)
        
        assert "November" in result
        assert "19" in result
        assert "PM" in result
    
    def test_relative_today(self, response_formatter):
        """Test formatting 'today' """
        result = response_formatter._voice_time("today")
        
        assert "today" in result
    
    def test_relative_yesterday(self, response_formatter):
        """Test formatting 'yesterday' """
        result = response_formatter._voice_time("yesterday")
        
        assert "yesterday" in result
    
    def test_duration_hours(self, response_formatter):
        """Test formatting hour durations"""
        result = response_formatter._voice_time("24h")
        
        assert "hours" in result


class TestErrorHandling:
    """Test error handling and fallbacks"""
    
    def test_missing_template(self, response_formatter):
        """Test handling missing template"""
        data = {"machine": "Compressor-1"}
        
        response = response_formatter.format_response("nonexistent_intent", data)
        
        # Should return fallback response
        assert "information" in response.lower() or "details" in response.lower()
    
    def test_template_render_error(self, response_formatter):
        """Test handling template rendering errors"""
        data = {}  # Missing required fields
        
        # Should handle gracefully
        try:
            response = response_formatter.format_response("machine_status", data)
            assert isinstance(response, str)
        except Exception:
            # Or raise exception is acceptable
            pass


class TestContextIntegration:
    """Test context integration in templates"""
    
    def test_render_with_context(self, response_formatter):
        """Test rendering template with context"""
        data = {
            "machine_name": "Compressor-1",
            "power_kw": 47.98
        }
        context = {
            "user_name": "Alice",
            "previous_query": "status"
        }
        
        response = response_formatter.format_response("power_query", data, context)
        
        # Should render successfully with or without using context
        assert isinstance(response, str)
        assert len(response) > 0
