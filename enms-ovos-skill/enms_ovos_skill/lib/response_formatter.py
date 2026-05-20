"""
Response Template System
Week 2 Days 11-12: Voice-Optimized Response Generation

Tier 4: Response Formatter
- Jinja2 template engine
- Voice-optimized number formatting  
- 100% data from API (NO LLM generation)
- <1ms latency
"""
from typing import Dict, Any, Optional, List
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
            0.00006132 → "0.00006" (scientific notation for very small)
        """
        if value is None:
            return "0"
        
        rounded = round(float(value), precision)
        
        # Handle very small numbers (< 0.001) with more precision
        if 0 < abs(float(value)) < 0.001:
            # Use 5 decimal places for tiny values like SEC
            return f"{float(value):.5f}"
        
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

            if intent_type == "anomaly_detection":
                data = self.enrich_anomaly_response(data)
            
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

    def enrich_anomaly_response(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add voice- and widget-friendly anomaly summaries for machine-specific anomaly lists."""
        if not isinstance(api_data, dict):
            return api_data

        if api_data.get('is_active') or api_data.get('is_detection'):
            return api_data

        machine_name = api_data.get('machine_name')
        anomalies = api_data.get('anomalies')
        if not machine_name or not isinstance(anomalies, list):
            return api_data

        total_count = api_data.get('total_count')
        if total_count is None:
            total_count = len(anomalies)
            api_data['total_count'] = total_count

        severity_counts: Dict[str, int] = {}
        group_map: Dict[tuple, Dict[str, Any]] = {}
        resolved_count = 0

        for anomaly in anomalies:
            severity = str(anomaly.get('severity') or 'unknown').lower()
            metric_label = self._humanize_metric_name(anomaly.get('metric_name'))
            anomaly_label = self._humanize_anomaly_type(anomaly.get('anomaly_type'))
            group_key = (severity, metric_label, anomaly_label)
            detected_at = self._parse_datetime(anomaly.get('detected_at'))

            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            if anomaly.get('is_resolved'):
                resolved_count += 1

            if group_key not in group_map:
                group_map[group_key] = {
                    'severity': severity,
                    'metric_label': metric_label,
                    'anomaly_label': anomaly_label,
                    'count': 0,
                    'latest_detected_at': detected_at,
                }

            group_map[group_key]['count'] += 1
            latest_detected = group_map[group_key]['latest_detected_at']
            if detected_at and (latest_detected is None or detected_at > latest_detected):
                group_map[group_key]['latest_detected_at'] = detected_at

        grouped_anomalies = sorted(
            group_map.values(),
            key=lambda group: (
                -group['count'],
                group['latest_detected_at'].timestamp() if group['latest_detected_at'] else 0,
            )
        )

        unresolved_count = max(total_count - resolved_count, 0)
        detail_limit = min(2, len(anomalies))
        detail_anomaly_summaries = [
            self._build_anomaly_example_summary(anomaly)
            for anomaly in anomalies[:detail_limit]
        ]

        api_data['response_mode'] = 'machine_anomaly_detail'
        api_data['response_period_label'] = self._anomaly_period_label(api_data)
        api_data['by_severity'] = severity_counts
        api_data['critical'] = severity_counts.get('critical', 0)
        api_data['warnings'] = severity_counts.get('warning', 0)
        api_data['resolved_count'] = resolved_count
        api_data['unresolved_count'] = unresolved_count
        api_data['group_summaries'] = [
            self._build_anomaly_group_summary(group)
            for group in grouped_anomalies
        ]
        api_data['all_same_pattern'] = len(grouped_anomalies) == 1 and total_count > 1
        api_data['primary_group_summary'] = (
            self._build_anomaly_descriptor(grouped_anomalies[0], plural=grouped_anomalies[0]['count'] != 1)
            if grouped_anomalies else None
        )
        api_data['detail_anomaly_summaries'] = detail_anomaly_summaries
        api_data['additional_anomaly_count'] = max(total_count - detail_limit, 0)

        return api_data

    def _anomaly_period_label(self, api_data: Dict[str, Any]) -> str:
        """Return a short voice-friendly period label for anomaly summaries."""
        filters = api_data.get('filters') or {}
        if filters.get('start_time') or filters.get('end_time'):
            return 'in the requested time range'
        return 'in the last 7 days'

    def _humanize_metric_name(self, metric_name: Any) -> str:
        """Convert raw metric keys to voice-friendly metric names."""
        if not metric_name:
            return 'observed metric'

        metric_key = str(metric_name).strip().lower()
        metric_map = {
            'power_kw': 'power',
            'total_energy_kwh': 'energy use',
            'energy_kwh': 'energy use',
            'avg_pressure_bar': 'pressure',
            'pressure_bar': 'pressure',
            'avg_machine_temp_c': 'machine temperature',
            'machine_temp_c': 'machine temperature',
            'avg_outdoor_temp_c': 'outdoor temperature',
            'outdoor_temp_c': 'outdoor temperature',
            'avg_load_factor': 'load factor',
            'load_factor': 'load factor',
            'total_production_count': 'production',
            'production_count': 'production',
        }
        if metric_key in metric_map:
            return metric_map[metric_key]

        return metric_key.replace('_', ' ')

    def _humanize_anomaly_type(self, anomaly_type: Any) -> str:
        """Convert raw anomaly type keys to voice-friendly labels."""
        if not anomaly_type:
            return 'anomaly'
        return str(anomaly_type).strip().lower().replace('_', ' ')

    def _parse_datetime(self, value: Any):
        """Parse ISO datetimes when present."""
        from datetime import datetime

        if isinstance(value, datetime):
            return value
        if not value:
            return None

        try:
            return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        except ValueError:
            return None

    def _format_anomaly_time(self, value: Any) -> Optional[str]:
        """Render anomaly timestamps in a short spoken form."""
        timestamp = self._parse_datetime(value)
        if not timestamp:
            return str(value) if value else None

        month_names = [
            '', 'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        hour = timestamp.hour
        minute = timestamp.minute
        ampm = 'AM' if hour < 12 else 'PM'
        display_hour = hour % 12 or 12

        if minute:
            return f"{month_names[timestamp.month]} {timestamp.day} at {display_hour}:{minute:02d} {ampm}"
        return f"{month_names[timestamp.month]} {timestamp.day} at {display_hour} {ampm}"

    def _build_anomaly_descriptor(self, group: Dict[str, Any], plural: bool = True) -> str:
        """Build a compact human-readable anomaly descriptor."""
        parts: List[str] = []
        severity = group.get('severity')
        metric_label = group.get('metric_label')
        anomaly_label = group.get('anomaly_label')

        if severity and severity != 'unknown':
            parts.append(severity)
        if metric_label and metric_label != 'observed metric':
            parts.append(metric_label)
        if anomaly_label and anomaly_label != 'anomaly':
            parts.append(anomaly_label)

        suffix = 'anomalies' if plural else 'anomaly'
        return ' '.join(parts + [suffix]).strip()

    def _build_anomaly_group_summary(self, group: Dict[str, Any]) -> str:
        """Build a count-oriented summary for an anomaly group."""
        count = group.get('count', 0)
        descriptor = self._build_anomaly_descriptor(group, plural=count != 1)
        return f"{count} {descriptor}".strip()

    def _build_anomaly_example_summary(self, anomaly: Dict[str, Any]) -> str:
        """Build a short detailed spoken summary for one anomaly record."""
        group = {
            'severity': str(anomaly.get('severity') or 'unknown').lower(),
            'metric_label': self._humanize_metric_name(anomaly.get('metric_name')),
            'anomaly_label': self._humanize_anomaly_type(anomaly.get('anomaly_type')),
        }
        descriptor = self._build_anomaly_descriptor(group, plural=False)
        time_text = self._format_anomaly_time(anomaly.get('detected_at'))
        observed_value = self._safe_number_text(anomaly.get('metric_value'), 1)
        expected_value = self._safe_number_text(anomaly.get('expected_value'), 1)
        deviation_text = self._deviation_text(anomaly.get('deviation_percent'))
        resolution_text = 'resolved' if anomaly.get('is_resolved') else 'unresolved'

        headline = descriptor
        if time_text:
            headline = f"{headline} at {time_text}"

        parts = [headline]
        if observed_value and expected_value:
            parts.append(f"observed {observed_value} versus expected {expected_value}")
        if deviation_text:
            parts.append(deviation_text)
        parts.append(resolution_text)

        return ', '.join(parts)

    def _safe_number_text(self, value: Any, precision: int = 1) -> Optional[str]:
        """Format numeric values without raising if they are missing or invalid."""
        try:
            if value is None:
                return None
            return self._format_number(float(value), precision)
        except (TypeError, ValueError):
            return None

    def _deviation_text(self, value: Any) -> Optional[str]:
        """Render deviation percentages in a voice-friendly form."""
        try:
            if value is None:
                return None
            numeric_value = float(value)
        except (TypeError, ValueError):
            return None

        direction = 'above expected' if numeric_value >= 0 else 'below expected'
        formatted = self._format_number(abs(numeric_value), 0)
        return f"{formatted} percent {direction}"
    
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
