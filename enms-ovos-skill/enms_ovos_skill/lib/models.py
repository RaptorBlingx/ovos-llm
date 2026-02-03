"""
Pydantic data models for EnMS OVOS Skill
Type-safe schemas for intent parsing, validation, and API responses
"""
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class IntentType(str, Enum):
    """Supported intent types"""
    ENERGY_QUERY = "energy_query"
    POWER_QUERY = "power_query"
    MACHINE_STATUS = "machine_status"
    FACTORY_OVERVIEW = "factory_overview"
    COMPARISON = "comparison"
    RANKING = "ranking"
    ANOMALY_DETECTION = "anomaly_detection"
    COST_ANALYSIS = "cost_analysis"
    FORECAST = "forecast"
    BASELINE = "baseline"
    BASELINE_MODELS = "baseline_models"
    BASELINE_EXPLANATION = "baseline_explanation"
    SEUS = "seus"  # Significant Energy Uses
    KPI = "kpi"
    PERFORMANCE = "performance"
    PRODUCTION = "production"
    REPORT = "report"  # PDF report generation
    HELP = "help"
    HEALTH = "health"  # System health check
    UNKNOWN = "unknown"


class TimeRange(BaseModel):
    """Time range for queries"""
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    duration: Optional[str] = None  # e.g., "24h", "1d", "1w"
    relative: Optional[str] = None  # e.g., "today", "yesterday", "last week"


class Intent(BaseModel):
    """
    Parsed intent from user utterance
    Output from LLM parser, input to validator
    """
    intent: IntentType
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Entities
    machine: Optional[str] = None
    machines: Optional[List[str]] = None
    metric: Optional[str] = None  # energy, power, cost, efficiency, etc.
    time_range: Optional[TimeRange] = None
    aggregation: Optional[str] = None  # sum, avg, max, min
    limit: Optional[int] = None  # for top N queries
    
    # NEW: Multi-energy support
    energy_source: Optional[str] = None  # electricity, natural_gas, steam, compressed_air
    energy_sources: Optional[List[str]] = None  # for multi-source queries
    
    # NEW: Multi-factory support
    factory: Optional[str] = None
    factories: Optional[List[str]] = None
    
    # NEW: Ranking criteria
    ranking_metric: Optional[str] = None  # efficiency, cost, energy, alerts
    
    # NEW: Metadata requests
    include_metadata: bool = False
    include_breakdown: bool = False
    
    # NEW: Extra parameters for special intents (report, etc.)
    params: Optional[Dict[str, Any]] = None
    
    # Raw utterance
    utterance: str
    
    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Ensure confidence is between 0 and 1"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0 and 1")
        return v


class ValidationResult(BaseModel):
    """Result of intent validation"""
    valid: bool
    intent: Optional[Intent] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)  # "Did you mean...?"


class MachineInfo(BaseModel):
    """Machine metadata from EnMS API"""
    id: str
    name: str
    type: str
    rated_power_kw: float
    is_active: bool
    factory_name: Optional[str] = None
    factory_location: Optional[str] = None


class EnergyReading(BaseModel):
    """Energy consumption data point"""
    timestamp: datetime
    value: float
    unit: str = "kWh"


class APIResponse(BaseModel):
    """Generic EnMS API response wrapper"""
    success: bool = True
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SkillResponse(BaseModel):
    """Response from skill to OVOS"""
    text: str  # TTS output
    data: Optional[Dict[str, Any]] = None  # Additional context
    card: Optional[Dict[str, Any]] = None  # Visual display data


# Model configuration
class Config:
    """Pydantic model configuration"""
    arbitrary_types_allowed = True
    json_encoders = {
        datetime: lambda v: v.isoformat()
    }
