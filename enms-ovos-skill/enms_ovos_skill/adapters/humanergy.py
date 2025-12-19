"""
Humanergy EnMS Adapter - Concrete implementation for Humanergy's EnMS
Wraps the existing ENMSClient and implements the EnMSAdapter interface
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base import EnMSAdapter
from ..lib.api_client import ENMSClient
import structlog

logger = structlog.get_logger(__name__)


class HumanergyAdapter(EnMSAdapter):
    """
    Adapter for Humanergy's EnMS implementation
    
    This is the reference implementation that wraps the existing ENMSClient.
    Other EnMS implementations should follow this pattern.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Humanergy adapter
        
        Args:
            config: Configuration dict with Humanergy-specific settings
        """
        super().__init__(config)
        
        # Initialize Humanergy ENMSClient with config
        self.client = ENMSClient(
            base_url=self.base_url,
            timeout=self.timeout,
            max_retries=config.get('max_retries', 3)
        )
        
        logger.info("humanergy_adapter_initialized", base_url=self.base_url)
    
    async def close(self):
        """Close HTTP client"""
        await self.client.close()
    
    # ==================== Machine Discovery ====================
    
    async def list_machines(
        self,
        search: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """List all machines - delegates to ENMSClient"""
        machines = await self.client.list_machines(search=search, is_active=is_active)
        
        # Normalize response format
        normalized = []
        for m in machines:
            normalized.append({
                "machine_id": m.get("id"),
                "machine_name": m.get("machine_name") or m.get("name"),
                "type": m.get("type"),
                "status": m.get("status"),
                "is_active": m.get("is_active", True)
            })
        
        return normalized
    
    async def get_machine_status(self, machine_name: str) -> Dict[str, Any]:
        """Get machine status by name"""
        response = await self.client.get_machine_status(machine_name)
        
        # Extract relevant fields
        return {
            "machine_name": response.get("machine_name"),
            "status": response.get("status"),
            "power_kw": response.get("current_power_kw"),
            "energy_kwh_today": response.get("energy_today_kwh"),
            "last_seen": response.get("last_reading_time"),
            "raw_response": response  # Include full response for debugging
        }
    
    # ==================== Energy Queries ====================
    
    async def get_energy_timeseries(
        self,
        machine_id: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = "1hour"
    ) -> Dict[str, Any]:
        """Get energy time-series data"""
        response = await self.client.get_energy_timeseries(
            machine_id=machine_id,
            start_time=start_time,
            end_time=end_time,
            interval=interval
        )
        
        # Normalize response
        return {
            "machine_id": machine_id,
            "machine_name": response.get("machine_name"),
            "total_kwh": response.get("total_energy_kwh"),
            "avg_power_kw": response.get("avg_power_kw"),
            "timeseries": response.get("data", []),
            "raw_response": response
        }
    
    async def get_factory_summary(self) -> Dict[str, Any]:
        """Get factory-wide energy summary"""
        response = await self.client.get_factory_summary()
        
        # Extract key metrics
        return {
            "total_energy_kwh": response.get("total_energy_kwh"),
            "total_power_kw": response.get("total_power_kw"),
            "active_machines": response.get("active_machines"),
            "period": response.get("period", "current"),
            "raw_response": response
        }
    
    # ==================== SEU (Significant Energy Use) ====================
    
    async def list_seus(self) -> Dict[str, Any]:
        """List all SEUs"""
        response = await self.client.list_seus()
        
        # Normalize SEU list
        seus = response.get("seus", [])
        normalized_seus = []
        
        for seu in seus:
            normalized_seus.append({
                "seu_name": seu.get("seu_name"),
                "category": seu.get("category"),
                "machines": seu.get("machines", []),
                "total_kwh": seu.get("total_energy_kwh")
            })
        
        return {
            "seus": normalized_seus,
            "count": len(normalized_seus),
            "raw_response": response
        }
    
    # ==================== Baseline & Predictions ====================
    
    async def get_baseline_models(self) -> Dict[str, Any]:
        """List baseline models"""
        # Humanergy doesn't have a direct "list all models" endpoint
        # So we return a placeholder - this would need enhancement
        logger.warning("get_baseline_models_not_fully_implemented",
                      message="Returning placeholder - enhance with actual Humanergy API")
        
        return {
            "models": [],
            "message": "Use list_baseline_models(seu_name) for specific machine"
        }
    
    async def predict_baseline(
        self,
        machine_name: str,
        temperature: Optional[float] = None,
        pressure: Optional[float] = None,
        load_percent: Optional[float] = None,
        production_units: Optional[float] = None
    ) -> Dict[str, Any]:
        """Predict baseline energy consumption"""
        # Build features dict
        features = {}
        if temperature is not None:
            features["temperature"] = temperature
        if pressure is not None:
            features["pressure"] = pressure
        if load_percent is not None:
            features["load_percent"] = load_percent
        if production_units is not None:
            features["production_units"] = production_units
        
        response = await self.client.predict_baseline(
            seu_name=machine_name,
            energy_source="electricity",
            features=features,
            include_message=True
        )
        
        # Normalize response
        return {
            "machine_name": machine_name,
            "predicted_kwh": response.get("predicted_energy_kwh"),
            "confidence": response.get("confidence", 0.95),
            "model_version": response.get("model_version"),
            "message": response.get("message"),
            "raw_response": response
        }
    
    # ==================== Anomalies ====================
    
    async def get_anomalies(
        self,
        machine_name: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Get energy anomalies"""
        # Humanergy uses machine_id, not machine_name
        # If machine_name provided, need to look up ID first
        machine_id = None
        if machine_name:
            machines = await self.list_machines(search=machine_name)
            if machines:
                machine_id = machines[0]["machine_id"]
        
        response = await self.client.get_recent_anomalies(
            machine_id=machine_id,
            severity=severity,
            limit=limit
        )
        
        # Normalize anomalies
        anomalies_list = response.get("anomalies", [])
        normalized = []
        
        for a in anomalies_list:
            normalized.append({
                "machine_name": a.get("machine_name"),
                "severity": a.get("severity"),
                "deviation_percent": a.get("deviation_percent"),
                "detected_at": a.get("detected_at"),
                "description": a.get("description")
            })
        
        return {
            "anomalies": normalized,
            "count": len(normalized),
            "raw_response": response
        }
    
    # ==================== Comparisons ====================
    
    async def compare_machines(
        self,
        machine_ids: List[str],
        start_time: datetime,
        end_time: datetime,
        metric: str = "energy"
    ) -> Dict[str, Any]:
        """Compare multiple machines"""
        # Humanergy has multi-machine endpoint
        response = await self.client.get_multi_machine_energy(
            machine_ids=machine_ids,
            start_time=start_time,
            end_time=end_time,
            interval="1hour"
        )
        
        # Build comparison ranking
        comparison = []
        machines_data = response.get("machines", {})
        
        for idx, (machine_id, data) in enumerate(machines_data.items(), 1):
            comparison.append({
                "machine_id": machine_id,
                "machine_name": data.get("machine_name"),
                "total_kwh": data.get("total_kwh"),
                "rank": idx
            })
        
        # Sort by total_kwh descending
        comparison.sort(key=lambda x: x.get("total_kwh", 0), reverse=True)
        
        # Update ranks after sorting
        for idx, item in enumerate(comparison, 1):
            item["rank"] = idx
        
        return {
            "comparison": comparison,
            "metric": metric,
            "period": {"start": start_time.isoformat(), "end": end_time.isoformat()},
            "raw_response": response
        }
    
    # ==================== Humanergy-Specific Extensions ====================
    
    async def get_top_consumers(
        self,
        metric: str = "energy",
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """Get top energy consumers (Humanergy-specific endpoint)"""
        return await self.client.get_top_consumers(
            metric=metric,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
    
    async def get_performance_opportunities(
        self,
        factory_id: str,
        period: str = "week"
    ) -> Dict[str, Any]:
        """Get energy saving opportunities (Humanergy-specific)"""
        return await self.client.get_performance_opportunities(
            factory_id=factory_id,
            period=period
        )
    
    async def create_action_plan(
        self,
        seu_name: str,
        issue_type: str
    ) -> Dict[str, Any]:
        """Create ISO 50001 action plan (Humanergy-specific)"""
        return await self.client.create_action_plan(
            seu_name=seu_name,
            issue_type=issue_type
        )
    
    async def generate_report(
        self,
        report_type: str = "monthly_enpi",
        year: int = None,
        month: int = None,
        factory_id: Optional[str] = None,
        download_dir: Optional[str] = None,
        return_base64: bool = True
    ) -> Dict[str, Any]:
        """Generate PDF report (Humanergy-specific)"""
        return await self.client.generate_report(
            report_type=report_type,
            year=year,
            month=month,
            factory_id=factory_id,
            download_dir=download_dir,
            return_base64=return_base64
        )
