"""
Base EnMS Adapter - Abstract interface for any EnMS implementation
Defines the contract that all EnMS adapters must implement
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
import structlog

logger = structlog.get_logger(__name__)


class EnMSAdapter(ABC):
    """
    Abstract base class for EnMS adapters
    
    This defines the standard interface that OVOS skill expects.
    Implement this for your specific EnMS to enable voice control.
    
    WASABI Portability: Any EnMS can be integrated by implementing
    this interface, regardless of underlying API structure.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize adapter with configuration
        
        Args:
            config: Configuration dict from config.yaml
                    Must contain: api_base_url, timeout, etc.
        """
        self.config = config
        self.base_url = config.get('api_base_url', 'http://localhost:8001/api/v1')
        self.timeout = config.get('timeout', 90.0)
        self.factory_name = config.get('factory_name', 'Factory')
        self.terminology = config.get('terminology', {})
        
        logger.info("adapter_initialized", 
                   adapter_type=self.__class__.__name__,
                   base_url=self.base_url)
    
    @abstractmethod
    async def close(self):
        """Cleanup resources (close HTTP connections, etc.)"""
        pass
    
    # ==================== Machine Discovery ====================
    
    @abstractmethod
    async def list_machines(
        self,
        search: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        List all machines with optional filtering
        
        Args:
            search: Filter by machine name (case-insensitive)
            is_active: Filter by active status
            
        Returns:
            List of dicts with at minimum:
            [
                {
                    "machine_id": "uuid-or-name",
                    "machine_name": "Compressor-1",
                    "type": "compressor",
                    "status": "running",
                    "is_active": true
                },
                ...
            ]
        """
        pass
    
    @abstractmethod
    async def get_machine_status(self, machine_name: str) -> Dict[str, Any]:
        """
        Get current status of a machine
        
        Args:
            machine_name: Machine name (case-insensitive)
            
        Returns:
            Dict with at minimum:
            {
                "machine_name": "Compressor-1",
                "status": "running",
                "power_kw": 24.5,
                "energy_kwh_today": 450.2,
                "last_seen": "2025-12-19T10:30:00Z"
            }
        """
        pass
    
    # ==================== Energy Queries ====================
    
    @abstractmethod
    async def get_energy_timeseries(
        self,
        machine_id: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = "1hour"
    ) -> Dict[str, Any]:
        """
        Get energy consumption time-series
        
        Args:
            machine_id: Machine identifier
            start_time: Period start (UTC)
            end_time: Period end (UTC)
            interval: Aggregation interval (1min, 15min, 1hour, 1day)
            
        Returns:
            Dict with at minimum:
            {
                "machine_id": "uuid",
                "machine_name": "Compressor-1",
                "total_kwh": 450.2,
                "avg_power_kw": 18.7,
                "timeseries": [
                    {"timestamp": "2025-12-19T00:00:00Z", "kwh": 18.5, "kw": 18.5},
                    ...
                ]
            }
        """
        pass
    
    @abstractmethod
    async def get_factory_summary(self) -> Dict[str, Any]:
        """
        Get factory-wide energy summary
        
        Returns:
            Dict with at minimum:
            {
                "total_energy_kwh": 19456.8,
                "total_power_kw": 810.3,
                "active_machines": 12,
                "period": "today"
            }
        """
        pass
    
    # ==================== SEU (Significant Energy Use) ====================
    
    @abstractmethod
    async def list_seus(self) -> Dict[str, Any]:
        """
        List all Significant Energy Uses (SEUs)
        
        Returns:
            Dict with at minimum:
            {
                "seus": [
                    {
                        "seu_name": "Compressed Air System",
                        "category": "production",
                        "machines": ["Compressor-1", "Compressor-2"],
                        "total_kwh": 5600.2
                    },
                    ...
                ]
            }
        """
        pass
    
    # ==================== Baseline & Predictions ====================
    
    @abstractmethod
    async def get_baseline_models(self) -> Dict[str, Any]:
        """
        List available baseline models
        
        Returns:
            Dict with at minimum:
            {
                "models": [
                    {
                        "model_id": 186,
                        "machine_name": "Compressor-1",
                        "accuracy": 0.94,
                        "trained_at": "2025-12-15T10:00:00Z"
                    },
                    ...
                ]
            }
        """
        pass
    
    @abstractmethod
    async def predict_baseline(
        self,
        machine_name: str,
        temperature: Optional[float] = None,
        pressure: Optional[float] = None,
        load_percent: Optional[float] = None,
        production_units: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Predict baseline energy consumption
        
        Args:
            machine_name: Machine name
            temperature: Ambient temperature (°C)
            pressure: Operating pressure (bar)
            load_percent: Load percentage (0-100)
            production_units: Production output
            
        Returns:
            Dict with at minimum:
            {
                "machine_name": "Compressor-1",
                "predicted_kwh": 97.74,
                "confidence": 0.95,
                "model_version": 186
            }
        """
        pass
    
    # ==================== Anomalies ====================
    
    @abstractmethod
    async def get_anomalies(
        self,
        machine_name: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get energy anomalies
        
        Args:
            machine_name: Filter by machine (optional)
            severity: Filter by severity (low, medium, high, critical)
            limit: Max results to return
            
        Returns:
            Dict with at minimum:
            {
                "anomalies": [
                    {
                        "machine_name": "Boiler-1",
                        "severity": "high",
                        "deviation_percent": 25.3,
                        "detected_at": "2025-12-19T08:15:00Z",
                        "description": "Energy consumption 25% above baseline"
                    },
                    ...
                ]
            }
        """
        pass
    
    # ==================== Comparisons ====================
    
    @abstractmethod
    async def compare_machines(
        self,
        machine_ids: List[str],
        start_time: datetime,
        end_time: datetime,
        metric: str = "energy"
    ) -> Dict[str, Any]:
        """
        Compare multiple machines
        
        Args:
            machine_ids: List of machine identifiers
            start_time: Period start
            end_time: Period end
            metric: Metric to compare (energy, power, cost)
            
        Returns:
            Dict with at minimum:
            {
                "comparison": [
                    {
                        "machine_name": "Compressor-1",
                        "total_kwh": 450.2,
                        "rank": 1
                    },
                    {
                        "machine_name": "Boiler-1",
                        "total_kwh": 380.5,
                        "rank": 2
                    }
                ]
            }
        """
        pass
    
    # ==================== Helper Methods ====================
    
    def format_energy_value(self, kwh: float) -> str:
        """
        Format energy value according to configured units
        
        Args:
            kwh: Energy in kWh
            
        Returns:
            Formatted string (e.g., "450.2 kWh" or "0.45 MWh")
        """
        unit = self.terminology.get('energy_unit', 'kWh')
        
        if unit == 'MWh' and kwh >= 1000:
            return f"{kwh/1000:.2f} MWh"
        elif unit == 'GJ':
            # 1 kWh = 3.6 MJ = 0.0036 GJ
            return f"{kwh * 0.0036:.2f} GJ"
        else:
            return f"{kwh:.1f} kWh"
    
    def format_power_value(self, kw: float) -> str:
        """Format power value according to configured units"""
        unit = self.terminology.get('power_unit', 'kW')
        
        if unit == 'MW' and kw >= 1000:
            return f"{kw/1000:.2f} MW"
        elif unit == 'HP':
            # 1 kW ≈ 1.341 HP
            return f"{kw * 1.341:.1f} HP"
        else:
            return f"{kw:.1f} kW"
    
    def get_machine_term(self) -> str:
        """Get configured terminology for 'machine'"""
        return self.terminology.get('machine_term', 'machine')
    
    def get_seu_term(self) -> str:
        """Get configured terminology for 'SEU'"""
        return self.terminology.get('seu_term', 'significant energy use')
