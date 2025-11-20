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
        
        elif time_range_str == "last week":
            # 7 days ago to now
            start = now - timedelta(days=7)
            return start, now
        
        elif time_range_str == "this month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return start, now
        
        elif time_range_str == "last month":
            # First day of last month to last day of last month
            first_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            last_day_last_month = first_this_month - timedelta(days=1)
            first_last_month = last_day_last_month.replace(day=1)
            return first_last_month, last_day_last_month
        
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
        
        # Absolute date ranges: "October 27, 3 PM to October 28, 10 AM"
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
