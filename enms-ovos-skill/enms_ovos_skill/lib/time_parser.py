"""
Time Range Parser - Convert natural language dates to datetime objects
Supports relative ("yesterday", "last week") and absolute ("October 27, 3 PM") formats
"""
from typing import Optional, Tuple
from datetime import datetime, timedelta, timezone
import re
import structlog

logger = structlog.get_logger(__name__)


class TimeRangeParser:
    """Parse natural language time ranges to datetime objects"""
    
    # Month name to number mapping
    MONTHS = {
        'january': 1, 'jan': 1,
        'february': 2, 'feb': 2,
        'march': 3, 'mar': 3,
        'april': 4, 'apr': 4,
        'may': 5,
        'june': 6, 'jun': 6,
        'july': 7, 'jul': 7,
        'august': 8, 'aug': 8,
        'september': 9, 'sep': 9, 'sept': 9,
        'october': 10, 'oct': 10,
        'november': 11, 'nov': 11,
        'december': 12, 'dec': 12
    }
    
    @staticmethod
    def parse(time_range_str: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Parse time range string to (start_time, end_time)
        
        Supported formats:
        - "today" → (today 00:00, now)
        - "yesterday" → (yesterday 00:00, yesterday 23:59)
        - "last week" → (7 days ago, now)
        - "last 24 hours" → (24h ago, now)
        - "October 27, 3 PM to October 28, 10 AM"
        - "from Monday to Friday"
        
        Args:
            time_range_str: Natural language time range
            
        Returns:
            (start_datetime, end_datetime) or (None, None) if parsing fails
        """
        if not time_range_str:
            return None, None
        
        time_range_str = time_range_str.lower().strip()
        now = datetime.now(timezone.utc)
        
        logger.debug("parsing_time_range", input=time_range_str)
        
        # Relative time ranges
        if time_range_str == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return start, now
        
        elif time_range_str == "yesterday":
            yesterday = now - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start, end
        
        elif time_range_str in ["this week", "current week"]:
            # Start of week (Monday)
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            return start, now
        
        elif time_range_str == "next week":
            # Next Monday to next Sunday
            days_until_next_monday = 7 - now.weekday()
            next_monday = now + timedelta(days=days_until_next_monday)
            next_monday = next_monday.replace(hour=0, minute=0, second=0, microsecond=0)
            next_sunday = next_monday + timedelta(days=6)
            next_sunday = next_sunday.replace(hour=23, minute=59, second=59, microsecond=999999)
            return next_monday, next_sunday
        
        elif time_range_str == "last week":
            # Previous Monday to previous Sunday
            days_since_monday = now.weekday()  # Monday=0, Sunday=6
            last_monday = now - timedelta(days=days_since_monday + 7)
            last_monday = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
            last_sunday = last_monday + timedelta(days=6)
            last_sunday = last_sunday.replace(hour=23, minute=59, second=59, microsecond=999999)
            return last_monday, last_sunday
        
        elif time_range_str == "this month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return start, now
        
        elif time_range_str == "next month":
            # First day of next month to last day of next month
            if now.month == 12:
                first_next_month = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                first_next_month = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Calculate last day of next month
            if first_next_month.month == 12:
                first_month_after_next = first_next_month.replace(year=first_next_month.year + 1, month=1, day=1)
            else:
                first_month_after_next = first_next_month.replace(month=first_next_month.month + 1, day=1)
            last_next_month = first_month_after_next - timedelta(days=1)
            last_next_month = last_next_month.replace(hour=23, minute=59, second=59, microsecond=999999)
            return first_next_month, last_next_month
        
        elif time_range_str == "last month":
            # First day of last month to last day of last month
            first_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_day_last_month = first_this_month - timedelta(days=1)
            first_last_month = last_day_last_month.replace(day=1)
            return first_last_month, last_day_last_month
        
        # "the last hour/day/week" (singular, no number)
        singular_match = re.match(r'(?:in\s+)?(?:the\s+)?(?:last|past)\s+(hour|day|week)', time_range_str)
        if singular_match:
            unit = singular_match.group(1)
            if unit == 'hour':
                start = now - timedelta(hours=1)
            elif unit == 'day':
                start = now - timedelta(days=1)
            elif unit == 'week':
                start = now - timedelta(weeks=1)
            return start, now
        
        # "last N hours/days/weeks" patterns
        match = re.match(r'(?:last|past)\s+(\d+)\s+(hour|day|week)s?', time_range_str)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            
            if unit == 'hour':
                start = now - timedelta(hours=amount)
            elif unit == 'day':
                start = now - timedelta(days=amount)
            elif unit == 'week':
                start = now - timedelta(weeks=amount)
            
            return start, now
        
        # NEW Phase 2.3: Simple date ranges without hours: "from January 1st to January 15th"
        # Supports ordinal suffixes: 1st, 2nd, 3rd, 14th, 15th (voice recognition)
        simple_range_pattern = r'from\s+(\w+)\s+(\d+)(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?\s+to\s+(\w+)\s+(\d+)(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?'
        match = re.match(simple_range_pattern, time_range_str)
        
        if match:
            start_month_name = match.group(1)
            start_day = int(match.group(2))
            start_year_explicit = match.group(3)
            
            end_month_name = match.group(4)
            end_day = int(match.group(5))
            end_year_explicit = match.group(6)
            
            start_month = TimeRangeParser.MONTHS.get(start_month_name)
            end_month = TimeRangeParser.MONTHS.get(end_month_name)
            
            if not start_month or not end_month:
                logger.warning("invalid_month_name", 
                             start_month=start_month_name, 
                             end_month=end_month_name)
                return None, None
            
            # YEAR INFERENCE LOGIC:
            # Default to current year unless explicitly specified
            # This matches user expectation: "January 1st to January 15th" means current year (2026)
            # Only use different year if user explicitly says "december 1st 2025"
            if start_year_explicit:
                start_year = int(start_year_explicit)
            else:
                # Always default to current year
                start_year = now.year
            
            if end_year_explicit:
                end_year = int(end_year_explicit)
            else:
                # Always default to current year
                end_year = now.year
            
            try:
                start_dt = datetime(start_year, start_month, start_day, 0, 0, 0, tzinfo=timezone.utc)
                end_dt = datetime(end_year, end_month, end_day, 23, 59, 59, tzinfo=timezone.utc)
                
                logger.info("parsed_simple_date_range",
                           start=start_dt.isoformat(),
                           end=end_dt.isoformat())
                
                return start_dt, end_dt
                
            except ValueError as e:
                logger.error("invalid_datetime_values", error=str(e))
                return None, None
        
        # NEW Phase 2.3: Between...and pattern: "between January 5th and January 10th"
        # Supports ordinal suffixes: 1st, 2nd, 3rd, 14th, 15th (voice recognition)
        between_pattern = r'between\s+(\w+)\s+(\d+)(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?\s+and\s+(\w+)\s+(\d+)(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?'
        match = re.match(between_pattern, time_range_str)
        
        if match:
            start_month_name = match.group(1)
            start_day = int(match.group(2))
            start_year_explicit = match.group(3)
            
            end_month_name = match.group(4)
            end_day = int(match.group(5))
            end_year_explicit = match.group(6)
            
            start_month = TimeRangeParser.MONTHS.get(start_month_name)
            end_month = TimeRangeParser.MONTHS.get(end_month_name)
            
            if not start_month or not end_month:
                logger.warning("invalid_month_name", 
                             start_month=start_month_name, 
                             end_month=end_month_name)
                return None, None
            
            # YEAR INFERENCE LOGIC:
            # Default to current year unless explicitly specified
            if start_year_explicit:
                start_year = int(start_year_explicit)
            else:
                # Always default to current year
                start_year = now.year
            
            if end_year_explicit:
                end_year = int(end_year_explicit)
            else:
                # Always default to current year
                end_year = now.year
            
            try:
                start_dt = datetime(start_year, start_month, start_day, 0, 0, 0, tzinfo=timezone.utc)
                end_dt = datetime(end_year, end_month, end_day, 23, 59, 59, tzinfo=timezone.utc)
                
                logger.info("parsed_between_date_range",
                           start=start_dt.isoformat(),
                           end=end_dt.isoformat())
                
                return start_dt, end_dt
                
            except ValueError as e:
                logger.error("invalid_datetime_values", error=str(e))
                return None, None
        
        # NEW Phase 2.3: Single date: "on January 15" or "on January 15th"
        single_date_pattern = r'on\s+(\w+)\s+(\d+)(?:st|nd|rd|th)?(?:,?\s+(\d{4}))?'
        match = re.match(single_date_pattern, time_range_str)
        
        if match:
            month_name = match.group(1)
            day = int(match.group(2))
            year_explicit = match.group(3)
            
            month = TimeRangeParser.MONTHS.get(month_name)
            
            if not month:
                logger.warning("invalid_month_name", month=month_name)
                return None, None
            
            # YEAR INFERENCE LOGIC:
            # Default to current year unless explicitly specified
            if year_explicit:
                year = int(year_explicit)
            else:
                # Always default to current year
                year = now.year
            
            try:
                start_dt = datetime(year, month, day, 0, 0, 0, tzinfo=timezone.utc)
                end_dt = datetime(year, month, day, 23, 59, 59, tzinfo=timezone.utc)
                
                logger.info("parsed_single_date",
                           date=start_dt.date().isoformat())
                
                return start_dt, end_dt
                
            except ValueError as e:
                logger.error("invalid_datetime_values", error=str(e))
                return None, None
        
        # EXISTING: Absolute date ranges with hours: "October 27, 3 PM to October 28, 10 AM"
        # Pattern: "Month Day, Hour AM/PM to Month Day, Hour AM/PM"
        absolute_pattern = r'(\w+)\s+(\d+),?\s+(\d+)\s*(am|pm)?\s+to\s+(\w+)\s+(\d+),?\s+(\d+)\s*(am|pm)?'
        match = re.match(absolute_pattern, time_range_str)
        
        if match:
            start_month_name = match.group(1)
            start_day = int(match.group(2))
            start_hour = int(match.group(3))
            start_ampm = match.group(4) or 'am'
            
            end_month_name = match.group(5)
            end_day = int(match.group(6))
            end_hour = int(match.group(7))
            end_ampm = match.group(8) or 'am'
            
            # Convert month names to numbers
            start_month = TimeRangeParser.MONTHS.get(start_month_name)
            end_month = TimeRangeParser.MONTHS.get(end_month_name)
            
            if not start_month or not end_month:
                logger.warning("invalid_month_name", 
                             start_month=start_month_name, 
                             end_month=end_month_name)
                return None, None
            
            # Convert 12-hour to 24-hour
            if start_ampm == 'pm' and start_hour != 12:
                start_hour += 12
            elif start_ampm == 'am' and start_hour == 12:
                start_hour = 0
            
            if end_ampm == 'pm' and end_hour != 12:
                end_hour += 12
            elif end_ampm == 'am' and end_hour == 12:
                end_hour = 0
            
            # Assume current year
            current_year = now.year
            
            try:
                start_dt = datetime(current_year, start_month, start_day, start_hour, 0, 0, tzinfo=timezone.utc)
                end_dt = datetime(current_year, end_month, end_day, end_hour, 0, 0, tzinfo=timezone.utc)
                
                logger.info("parsed_absolute_time_range",
                           start=start_dt.isoformat(),
                           end=end_dt.isoformat())
                
                return start_dt, end_dt
                
            except ValueError as e:
                logger.error("invalid_datetime_values", error=str(e))
                return None, None
        
        # Simpler pattern: "from Monday to Friday"
        # Not implemented yet - would require week calculation
        
        logger.warning("time_range_not_parsed", input=time_range_str)
        return None, None
    
    @staticmethod
    def parse_single_date(date_str: str) -> Optional[datetime]:
        """
        Parse single date string to datetime
        
        Examples:
        - "yesterday" → yesterday 00:00
        - "October 27" → Oct 27 current year 00:00
        
        Args:
            date_str: Natural language date
            
        Returns:
            datetime object or None
        """
        date_str = date_str.lower().strip()
        now = datetime.now(timezone.utc)
        
        if date_str == "today":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        elif date_str == "yesterday":
            yesterday = now - timedelta(days=1)
            return yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # "Month Day" pattern
        match = re.match(r'(\w+)\s+(\d+)', date_str)
        if match:
            month_name = match.group(1)
            day = int(match.group(2))
            
            month = TimeRangeParser.MONTHS.get(month_name)
            if not month:
                return None
            
            try:
                return datetime(now.year, month, day, 0, 0, 0, tzinfo=timezone.utc)
            except ValueError:
                return None
        
        return None
    @staticmethod
    def extract_interval(query: str) -> Optional[str]:
        """
        Extract time interval from query for API calls
        
        Supported patterns:
        - "hourly" / "hour" / "every hour" → "1hour"
        - "15 minute" / "15-minute" / "fifteen minute" → "15min"
        - "5 minute" / "5-minute" / "five minute" → "5min"
        - "1 minute" / "one minute" / "minute" → "1min"
        - "daily" / "day" / "every day" → "1day"
        
        Args:
            query: Natural language query
            
        Returns:
            API interval string (1min, 5min, 15min, 1hour, 1day) or None
        """
        query_lower = query.lower()
        
        # Number word to digit mapping
        number_words = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'eleven': 11, 'twelve': 12, 'fifteen': 15, 'twenty': 20, 'thirty': 30
        }
        
        # Pattern 1: "hourly" or "hour"
        if re.search(r'\b(hourly|per hour|every hour|hour interval)\b', query_lower):
            return "1hour"
        
        # Pattern 2: "15 minute" or "15-minute" or "fifteen minute"
        minute_pattern = r'\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty)[\s-]?minute'
        match = re.search(minute_pattern, query_lower)
        if match:
            minute_str = match.group(1)
            minutes = number_words.get(minute_str, None)
            if minutes is None:
                try:
                    minutes = int(minute_str)
                except ValueError:
                    minutes = None
            
            if minutes:
                # Map to valid API intervals
                if minutes == 1:
                    return "1min"
                elif minutes <= 5:
                    return "5min"
                elif minutes <= 15:
                    return "15min"
                else:
                    # For larger minute values, use hour
                    return "1hour"
        
        # Pattern 3: "daily" or "day"
        if re.search(r'\b(daily|per day|every day|day interval)\b', query_lower):
            return "1day"
        
        # Pattern 4: Just "minute" without number (assume 1min)
        if re.search(r'\bminute\b', query_lower) and not re.search(r'\d+\s*minute', query_lower):
            return "1min"
        
        return None