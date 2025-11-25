"""
Response Template System
Week 2 Days 11-12: Voice-Optimized Response Generation

Tier 4: Response Formatter
- Jinja2 template engine
- Voice-optimized number formatting  
- 100% data from API (NO LLM generation)
- <1ms latency
"""
from typing import Dict, Any, Optional
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, Template
import structlog

logger = structlog.get_logger(__name__)


class ResponseFormatter:
    """
    Voice-optimized response generator using Jinja2 templates
    
    Key principles:
    1. NEVER use LLM to generate final response
    2. ALL data comes from validated API responses
    3. Templates are voice-optimized (numbers, units, timing)
    4. Fast (<1ms) and deterministic
    """
    
    def __init__(self, template_dir: Optional[Path] = None):
        """
        Initialize response formatter
        
        Args:
            template_dir: Path to Jinja2 templates (default: locale/en-us/dialog/)
        """
        if template_dir is None:
            template_dir = Path(__file__).parent.parent / "locale" / "en-us" / "dialog"
        
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=False,  # We control the output
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Register custom filters for voice optimization
        self.env.filters['voice_number'] = self._voice_number
        self.env.filters['voice_unit'] = self._voice_unit
        self.env.filters['voice_time'] = self._voice_time
        self.env.filters['num'] = self._format_number  # Numeric format (better UX)
        
        logger.info("response_formatter_initialized", template_dir=str(template_dir))
    
    def _format_number(self, value: float, precision: int = 1) -> str:
        """
        Format number as digits with proper formatting (better UX than words)
        
        Args:
            value: Numeric value
            precision: Decimal places (default 1)
            
        Returns:
            Formatted number string with thousands separators
            
        Examples:
            47.984 → "48.0"
            1234.5 → "1,234.5"
            0.5 → "0.5"
            1000000 → "1,000,000"
        """
        if value is None:
            return "0"
        
        rounded = round(float(value), precision)
        
        # For integers or .0, show without decimals
        if rounded == int(rounded):
            return f"{int(rounded):,}"
        
        # Format with precision and thousands separator
        return f"{rounded:,.{precision}f}"
    
    def format_response(self, intent_type: str, api_data: Dict[str, Any], 
                       context: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate voice-optimized response from API data
        
        Args:
            intent_type: Intent name (e.g., "energy_query")
            api_data: Validated data from API
            context: Optional conversation context
            
        Returns:
            Voice-optimized response string
            
        Example:
            >>> formatter.format_response(
            ...     "energy_query",
            ...     {"machine": "Compressor-1", "power_kw": 47.984}
            ... )
            "Compressor-1 is currently using forty-eight kilowatts"
        """
        template_name = f"{intent_type}.dialog"
        
        try:
            template = self.env.get_template(template_name)
            
            # Merge API data with context
            data = {**(context or {}), **api_data}
            
            # Render template
            response = template.render(**data)
            
            logger.info("response_generated", 
                       intent=intent_type,
                       template=template_name,
                       length=len(response))
            
            return response.strip()
            
        except Exception as e:
            logger.error("template_error", 
                        intent=intent_type,
                        template=template_name,
                        error=str(e))
            
            # Fallback to generic response
            return self._generic_response(api_data)
    
    def _voice_number(self, value: float, precision: int = 1) -> str:
        """
        Convert number to voice-friendly pronunciation
        
        Args:
            value: Numeric value
            precision: Decimal places
            
        Returns:
            Voice-optimized string
            
        Examples:
            47.984 → "forty-eight"
            1234.5 → "one thousand two hundred thirty-four point five"
            0.5 → "point five"
        """
        # Round to precision
        rounded = round(value, precision)
        
        # For integers, use simple rounding
        if rounded == int(rounded):
            return self._number_to_words(int(rounded))
        
        # For decimals, handle carefully
        if abs(rounded) < 1:
            # "point five" for 0.5
            decimal_part = str(rounded).split('.')[1]
            return f"point {self._number_to_words(int(decimal_part))}"
        
        # For larger decimals, simplify
        # 47.984 → "forty-eight" (round to nearest)
        return self._number_to_words(round(rounded))
    
    def _number_to_words(self, n: int) -> str:
        """
        Convert integer to English words (simplified)
        
        For production, use inflect or num2words library
        This is a basic implementation for common cases
        """
        if n == 0:
            return "zero"
        
        # Handle thousands
        if n >= 1000:
            thousands = n // 1000
            remainder = n % 1000
            if remainder == 0:
                return f"{self._number_to_words(thousands)} thousand"
            return f"{self._number_to_words(thousands)} thousand {self._number_to_words(remainder)}"
        
        # Handle hundreds
        if n >= 100:
            hundreds = n // 100
            remainder = n % 100
            if remainder == 0:
                return f"{self._number_to_words(hundreds)} hundred"
            return f"{self._number_to_words(hundreds)} hundred {self._number_to_words(remainder)}"
        
        # Handle teens and tens
        teens = ["", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
                 "sixteen", "seventeen", "eighteen", "nineteen"]
        tens = ["", "ten", "twenty", "thirty", "forty", "fifty",
                "sixty", "seventy", "eighty", "ninety"]
        ones = ["", "one", "two", "three", "four", "five",
                "six", "seven", "eight", "nine"]
        
        if 11 <= n <= 19:
            return teens[n - 10]
        elif n >= 20:
            ten = n // 10
            one = n % 10
            if one == 0:
                return tens[ten]
            return f"{tens[ten]}-{ones[one]}"
        else:
            return ones[n]
    
    def _voice_unit(self, value: float, unit: str) -> str:
        """
        Format number with unit for voice
        
        Args:
            value: Numeric value
            unit: Unit string (kW, kWh, EUR, etc.)
            
        Returns:
            Voice-optimized "value unit" string
            
        Examples:
            (47.984, "kW") → "forty-eight kilowatts"
            (1500, "kWh") → "one thousand five hundred kilowatt hours"
        """
        # Convert unit abbreviations to full words
        unit_map = {
            "kW": "kilowatts",
            "kWh": "kilowatt hours",
            "MW": "megawatts",
            "MWh": "megawatt hours",
            "EUR": "euros",
            "USD": "dollars",
            "%": "percent"
        }
        
        unit_word = unit_map.get(unit, unit.lower())
        number_word = self._voice_number(value)
        
        return f"{number_word} {unit_word}"
    
    def _voice_time(self, time_value) -> str:
        """
        Convert time to voice-friendly format
        
        Args:
            time_value: datetime object, ISO 8601 string, or relative time string
            
        Returns:
            Voice-optimized time string
            
        Examples:
            datetime(2025, 10, 27, 15, 0) → "October 27 at 3 PM"
            "today" → "today"
            "24h" → "in the last twenty-four hours"
        """
        from datetime import datetime
        
        # Handle datetime objects
        if isinstance(time_value, datetime):
            # Format as "Month Day at Hour AM/PM"
            hour = time_value.hour
            ampm = "AM" if hour < 12 else "PM"
            display_hour = hour if hour <= 12 else hour - 12
            if display_hour == 0:
                display_hour = 12
            
            month_names = ["", "January", "February", "March", "April", "May", "June",
                          "July", "August", "September", "October", "November", "December"]
            return f"{month_names[time_value.month]} {time_value.day} at {display_hour} {ampm}"
        
        # Handle string values
        time_str = str(time_value)
        
        # Simplified - full implementation would parse ISO 8601
        if time_str in ["today", "yesterday", "last_week"]:
            return time_str.replace("_", " ")
        
        if time_str.endswith("h"):
            hours = int(time_str[:-1])
            return f"in the last {self._voice_number(hours)} hours"
        
        if time_str.endswith("d"):
            days = int(time_str[:-1])
            return f"in the last {self._voice_number(days)} days"
        
        return time_str
    
    def _generic_response(self, data: Dict[str, Any]) -> str:
        """
        Fallback response when template fails
        
        Args:
            data: API response data
            
        Returns:
            Generic but informative response
        """
        return "I found the information you requested. Please check the screen for details."


# Convenience function for quick responses
def format_response(intent: str, data: Dict[str, Any], 
                   context: Optional[Dict[str, Any]] = None) -> str:
    """
    Quick response formatting without instantiating class
    
    Args:
        intent: Intent type
        data: API data
        context: Optional context
        
    Returns:
        Formatted response
    """
    formatter = ResponseFormatter()
    return formatter.format_response(intent, data, context)
