"""
Feature Extractor for Baseline Prediction Queries
================================================

Extracts numerical features from natural language utterances:
- Temperature (°C/°F)
- Pressure (bar/psi)
- Load factor (%)
- Production count (units)
"""

import re
from typing import Dict, Optional, Any
import structlog

logger = structlog.get_logger(__name__)


class FeatureExtractor:
    """Extract numerical features from utterances for baseline predictions"""
    
    # Temperature patterns
    TEMP_PATTERNS = [
        r'(\d+(?:\.\d+)?)\s*(?:degrees?|°)\s*(?:celsius|c)?',  # "30 degrees", "30°C", "30 degrees celsius"
        r'(\d+(?:\.\d+)?)\s*(?:degrees?|°)\s*(?:fahrenheit|f)',  # "86 degrees fahrenheit", "86°F"
        r'at\s+(\d+(?:\.\d+)?)\s+celsius\b',  # "at 25 celsius"
        r'(\d+(?:\.\d+)?)\s+celsius\b',  # "25 celsius"
        r'(\d+(?:\.\d+)?)\s+fahrenheit\b',  # "86 fahrenheit"
        r'at\s+(\d+(?:\.\d+)?)\s+(?:degrees?|°)',  # "at 30 degrees"
        r'temp\w*\s+(?:of\s+)?(\d+(?:\.\d+)?)',  # "temperature 30", "temp of 30", "temp 25"
        r'with\s+temp\w*\s+(\d+(?:\.\d+)?)',  # "with temp 25"
    ]
    
    # Pressure patterns
    PRESSURE_PATTERNS = [
        r'(\d+(?:\.\d+)?)\s*bar',  # "8 bar", "7.5bar"
        r'(\d+(?:\.\d+)?)\s*psi',  # "115 psi"
        r'at\s+(\d+(?:\.\d+)?)\s+bar',  # "at 8 bar"
        r'pressure\s+(?:of\s+)?(\d+(?:\.\d+)?)',  # "pressure of 8"
    ]
    
    # Load factor patterns
    LOAD_PATTERNS = [
        r'(\d+(?:\.\d+)?)\s*%\s*load',  # "85% load", "85 % load"
        r'load\s+(?:factor\s+)?(?:of\s+)?(\d+(?:\.\d+)?)\s*%',  # "load of 85%", "load factor 85%"
        r'at\s+(\d+(?:\.\d+)?)\s*%',  # "at 85%"
        r'at\s+(\d+(?:\.\d+)?)\s*percent\s+load',  # "at 90 percent load"
        r'(\d+(?:\.\d+)?)\s*percent\s+load',  # "90 percent load"
    ]
    
    # Production count patterns
    PRODUCTION_PATTERNS = [
        r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:units?|pieces?|items?)',  # "5000 units", "5,000 units"
        r'for\s+(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:units?|pieces?)',  # "for 5000 units"
        r'production\s+(?:of\s+)?(\d+(?:,\d{3})*)',  # "production of 5000"
        r'(\d+)\s+million\s+units?',  # "5 million units"
        r'and\s+(\d+)\s+million',  # "and 5 million"
    ]
    
    @staticmethod
    def extract_temperature(utterance: str) -> Optional[float]:
        """
        Extract temperature from utterance
        
        Args:
            utterance: Natural language query
            
        Returns:
            Temperature in Celsius, or None if not found
        """
        utterance_lower = utterance.lower()
        
        for pattern in FeatureExtractor.TEMP_PATTERNS:
            match = re.search(pattern, utterance_lower)
            if match:
                temp_value = float(match.group(1))
                
                # Check if Fahrenheit and convert
                if 'fahrenheit' in match.group(0) or '°f' in match.group(0):
                    temp_value = (temp_value - 32) * 5/9  # F to C
                    logger.info("temperature_extracted", value=temp_value, unit="C", converted_from="F")
                else:
                    logger.info("temperature_extracted", value=temp_value, unit="C")
                
                return temp_value
        
        return None
    
    @staticmethod
    def extract_pressure(utterance: str) -> Optional[float]:
        """
        Extract pressure from utterance
        
        Args:
            utterance: Natural language query
            
        Returns:
            Pressure in bar, or None if not found
        """
        utterance_lower = utterance.lower()
        
        for pattern in FeatureExtractor.PRESSURE_PATTERNS:
            match = re.search(pattern, utterance_lower)
            if match:
                pressure_value = float(match.group(1))
                
                # Check if PSI and convert
                if 'psi' in match.group(0):
                    pressure_value = pressure_value * 0.0689476  # PSI to bar
                    logger.info("pressure_extracted", value=pressure_value, unit="bar", converted_from="psi")
                else:
                    logger.info("pressure_extracted", value=pressure_value, unit="bar")
                
                return pressure_value
        
        return None
    
    @staticmethod
    def extract_load_factor(utterance: str) -> Optional[float]:
        """
        Extract load factor from utterance
        
        Args:
            utterance: Natural language query
            
        Returns:
            Load factor as decimal (0.0-1.0), or None if not found
        """
        utterance_lower = utterance.lower()
        
        for pattern in FeatureExtractor.LOAD_PATTERNS:
            match = re.search(pattern, utterance_lower)
            if match:
                load_value = float(match.group(1))
                
                # Convert percentage to decimal
                if load_value > 1.0:
                    load_value = load_value / 100.0
                
                logger.info("load_factor_extracted", value=load_value)
                return load_value
        
        return None
    
    @staticmethod
    def extract_production_count(utterance: str) -> Optional[int]:
        """
        Extract production count from utterance
        
        Args:
            utterance: Natural language query
            
        Returns:
            Production count as integer, or None if not found
        """
        utterance_lower = utterance.lower()
        
        for pattern in FeatureExtractor.PRODUCTION_PATTERNS:
            match = re.search(pattern, utterance_lower)
            if match:
                # Remove commas and convert to int
                count_str = match.group(1).replace(',', '')
                count_value = int(float(count_str))
                
                # Check if "million" was in the pattern and multiply
                if 'million' in match.group(0):
                    count_value = count_value * 1000000
                
                logger.info("production_count_extracted", value=count_value)
                return count_value
        
        return None
    
    @staticmethod
    def extract_all_features(utterance: str, defaults: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract all features from utterance, using defaults for missing values
        
        Args:
            utterance: Natural language query
            defaults: Default values for features not found in utterance
            
        Returns:
            Dictionary with all features (extracted or default)
        """
        if defaults is None:
            defaults = {
                "total_production_count": 5000000,
                "avg_outdoor_temp_c": 22.0,
                "avg_pressure_bar": 7.0,
                "avg_load_factor": 0.85
            }
        
        features = defaults.copy()
        
        # Extract each feature
        temp = FeatureExtractor.extract_temperature(utterance)
        if temp is not None:
            features["avg_outdoor_temp_c"] = temp
            features["avg_temperature_c"] = temp  # API also accepts this name
        
        pressure = FeatureExtractor.extract_pressure(utterance)
        if pressure is not None:
            features["avg_pressure_bar"] = pressure
        
        load = FeatureExtractor.extract_load_factor(utterance)
        if load is not None:
            features["avg_load_factor"] = load
        
        production = FeatureExtractor.extract_production_count(utterance)
        if production is not None:
            features["total_production_count"] = production
        
        logger.info("features_extracted", features=features, utterance=utterance)
        return features
