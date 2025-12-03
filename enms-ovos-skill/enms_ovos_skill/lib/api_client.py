"""
EnMS API Client - Async HTTP client for Energy Management System
Tier 3: API Executor with circuit breaker, retries, and connection pooling
"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_exception
)
import structlog

logger = structlog.get_logger(__name__)


def _should_retry_exception(exception: BaseException) -> bool:
    """Only retry on transient errors, not on 4xx client errors."""
    if isinstance(exception, httpx.HTTPStatusError):
        # Don't retry on client errors (4xx) - they won't change
        # Only retry on server errors (5xx) which may be transient
        return exception.response.status_code >= 500
    # Retry on connection/timeout errors
    return isinstance(exception, (httpx.ConnectError, httpx.TimeoutException))


class ENMSClient:
    """
    Async HTTP client for EnMS API with reliability features
    
    Features:
    - Connection pooling
    - Automatic retries with exponential backoff
    - Timeout management
    - Circuit breaker pattern
    - Structured logging
    """
    
    def __init__(
        self,
        base_url: str = "http://10.33.10.109:8001/api/v1",
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        """
        Initialize EnMS API client
        
        Args:
            base_url: EnMS API base URL
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Async HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
        
        logger.info("enms_client_initialized", base_url=self.base_url, timeout=timeout)
    
    async def close(self):
        """Close the HTTP client and cleanup resources"""
        await self.client.aclose()
        logger.info("enms_client_closed")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(_should_retry_exception)
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request with automatic retries
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            params: Query parameters
            json: JSON request body
            
        Returns:
            Response JSON data
            
        Raises:
            httpx.HTTPError: On request failure after retries
        """
        url = f"{self.base_url}{endpoint}"
        
        logger.info("api_request", method=method, endpoint=endpoint, params=params)
        
        try:
            response = await self.client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info("api_response", 
                       endpoint=endpoint, 
                       status_code=response.status_code,
                       response_time_ms=response.elapsed.total_seconds() * 1000)
            
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error("api_http_error",
                        endpoint=endpoint,
                        status_code=e.response.status_code,
                        error=str(e))
            raise
        except httpx.RequestError as e:
            logger.error("api_request_error",
                        endpoint=endpoint,
                        error=str(e))
            raise
    
    # Health & System Endpoints
    
    async def health_check(self) -> Dict[str, Any]:
        """Check EnMS API health status"""
        return await self._request("GET", "/health")
    
    async def system_stats(self) -> Dict[str, Any]:
        """Get real-time system statistics"""
        return await self._request("GET", "/stats/system")
    
    async def factory_summary(self) -> Dict[str, Any]:
        """Get comprehensive factory summary with status, energy, costs, machines, anomalies"""
        return await self._request("GET", "/factory/summary")
    
    async def aggregated_stats(
        self,
        start_time: datetime,
        end_time: datetime,
        machine_ids: str = "all"
    ) -> Dict[str, Any]:
        """
        Get aggregated statistics over time range
        
        Args:
            start_time: Start of time range
            end_time: End of time range
            machine_ids: Comma-separated UUIDs or 'all'
        
        Returns:
            Aggregated stats with totals and per-machine breakdown
        """
        params = {
            "machine_ids": machine_ids,
            "start_time": start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "end_time": end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        }
        return await self._request("GET", "/stats/aggregated", params=params)
    
    # Machine Endpoints
    
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
            List of machine metadata
        """
        params = {}
        if search:
            params["search"] = search
        if is_active is not None:
            params["is_active"] = str(is_active).lower()
        
        return await self._request("GET", "/machines", params=params)
    
    async def get_machine(self, machine_id: str) -> Dict[str, Any]:
        """Get single machine by ID"""
        return await self._request("GET", f"/machines/{machine_id}")
    
    async def get_machine_status(self, machine_name: str) -> Dict[str, Any]:
        """
        Get comprehensive machine status by name (NEW endpoint)
        
        Args:
            machine_name: Machine name (case-insensitive)
            
        Returns:
            Machine status with current stats, anomalies, production
        """
        return await self._request("GET", f"/machines/status/{machine_name}")
    
    # Time-Series Endpoints
    
    async def get_energy_timeseries(
        self,
        machine_id: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = "1hour"
    ) -> Dict[str, Any]:
        """
        Get energy consumption time-series data
        
        Args:
            machine_id: Machine UUID
            start_time: Period start
            end_time: Period end
            interval: Time bucket (1min, 5min, 15min, 1hour, 1day)
            
        Returns:
            Time-series energy data with aggregated values
        """
        params = {
            "machine_id": machine_id,
            "start_time": start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "end_time": end_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "interval": interval
        }
        return await self._request("GET", "/timeseries/energy", params=params)
    
    async def get_power_timeseries(
        self,
        machine_id: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = "1hour"
    ) -> Dict[str, Any]:
        """Get power demand time-series data"""
        params = {
            "machine_id": machine_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "interval": interval
        }
        return await self._request("GET", "/timeseries/power", params=params)
    
    async def get_latest_reading(self, machine_id: str) -> Dict[str, Any]:
        """Get most recent sensor reading for machine"""
        return await self._request("GET", f"/timeseries/latest/{machine_id}")
    
    async def get_multi_machine_energy(
        self,
        machine_ids: List[str],
        start_time: datetime,
        end_time: datetime,
        interval: str = "1hour"
    ) -> Dict[str, Any]:
        """
        Compare energy consumption across multiple machines
        
        Args:
            machine_ids: List of machine UUIDs to compare
            start_time: Period start
            end_time: Period end
            interval: Time bucket (15min, 1hour, 1day)
            
        Returns:
            Multi-machine comparison with aligned timestamps
        """
        params = {
            "machine_ids": ",".join(machine_ids),
            "start_time": start_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "end_time": end_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "interval": interval
        }
        return await self._request("GET", "/timeseries/multi-machine/energy", params=params)
    
    # Factory-Wide Endpoints (NEW - from OVOS endpoints)
    
    async def get_health(self) -> Dict[str, Any]:
        """Check EnMS service health status"""
        return await self._request("GET", "/health")
    
    async def get_factory_summary(self) -> Dict[str, Any]:
        """Get factory-wide energy summary"""
        return await self._request("GET", "/factory/summary")
    
    async def get_top_consumers(
        self,
        metric: str = "energy",
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Get top energy consumers
        
        Args:
            metric: Ranking metric (energy, cost, power, anomalies)
            start_time: Start time (ISO format), defaults to today 00:00
            end_time: End time (ISO format), defaults to now
            limit: Number of machines to return (1-20, default 5)
            
        Returns:
            Ranked list of machines by specified metric
        """
        from datetime import datetime, timezone
        
        # Default to today if not specified
        if not start_time:
            start_time = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        if not end_time:
            end_time = datetime.now(timezone.utc).isoformat()
            
        params = {
            "metric": metric,
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit
        }
        return await self._request("GET", "/analytics/top-consumers", params=params)
    
    # Anomaly Detection Endpoints
    
    async def detect_anomalies(
        self,
        machine_id: str,
        start: datetime,
        end: datetime,
        contamination: float = 0.1
    ) -> Dict[str, Any]:
        """
        Run anomaly detection on machine data
        
        Args:
            machine_id: Machine UUID
            start: Detection period start
            end: Detection period end
            contamination: Expected anomaly rate (0.1 = 10%)
            
        Returns:
            Detected anomalies with confidence scores
        """
        data = {
            "machine_id": machine_id,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "contamination": contamination
        }
        return await self._request("POST", "/anomaly/detect", json=data)
    
    async def get_recent_anomalies(
        self,
        machine_id: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get recent anomalies (last 7 days)"""
        params = {"limit": limit}
        if machine_id:
            params["machine_id"] = machine_id
        if severity:
            params["severity"] = severity
        
        return await self._request("GET", "/anomaly/recent", params=params)
    
    async def get_active_anomalies(self) -> Dict[str, Any]:
        """Get currently unresolved anomalies requiring attention"""
        return await self._request("GET", "/anomaly/active")
    
    async def search_anomalies(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        machine_id: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Search anomalies with date range and filters"""
        params = {"limit": limit}
        if start_time:
            params["start_date"] = start_time.isoformat()
        if end_time:
            params["end_date"] = end_time.isoformat()
        if machine_id:
            params["machine_id"] = machine_id
        if severity:
            params["severity"] = severity
        
        return await self._request("GET", "/anomaly/search", params=params)
    
    # KPI Endpoints
    
    async def get_all_kpis(
        self,
        machine_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Get all KPIs for a machine in a time period
        
        Args:
            machine_id: Machine UUID
            start_time: Period start
            end_time: Period end
            
        Returns:
            All KPIs including SEC, peak demand, load factor, energy cost, carbon intensity
        """
        params = {
            "machine_id": machine_id,
            "start": start_time.isoformat(),
            "end": end_time.isoformat()
        }
        return await self._request("GET", "/kpi/all", params=params)
    
    async def analyze_performance(
        self,
        seu_name: str,
        energy_source: str,
        analysis_date: str
    ) -> Dict[str, Any]:
        """
        Analyze SEU performance for a specific date
        
        Args:
            seu_name: SEU name (e.g., "Compressor-1")
            energy_source: Energy type ("energy" or "electricity")
            analysis_date: Date to analyze (YYYY-MM-DD format)
            
        Returns:
            Performance analysis with actual vs baseline, efficiency score, root cause
        """
        payload = {
            "seu_name": seu_name,
            "energy_source": energy_source,
            "analysis_date": analysis_date
        }
        return await self._request("POST", "/performance/analyze", json=payload)
    
    async def get_performance_health(self) -> Dict[str, Any]:
        """
        Get performance engine health status
        
        Returns:
            Engine status, version, features availability
        """
        return await self._request("GET", "/performance/health")
    
    async def get_performance_opportunities(
        self,
        factory_id: str,
        period: str = "week"
    ) -> Dict[str, Any]:
        """
        Get energy saving opportunities
        
        Args:
            factory_id: Factory UUID
            period: Analysis period ("week", "month", "quarter")
            
        Returns:
            Ranked list of improvement opportunities with potential savings
            Note: API doesn't support SEU filtering - filter client-side if needed
        """
        params = {
            "factory_id": factory_id,
            "period": period
        }
        return await self._request("GET", "/performance/opportunities", params=params)
    
    async def create_action_plan(
        self,
        seu_name: str,
        issue_type: str
    ) -> Dict[str, Any]:
        """
        Create ISO 50001 compliant action plan for energy improvement
        
        Args:
            seu_name: SEU name (e.g., "Compressor-1")
            issue_type: Issue type - one of: excessive_idle, inefficient_scheduling, 
                       baseline_drift, suboptimal_setpoints
            
        Returns:
            Action plan with prioritized steps, expected outcomes, monitoring plan
        """
        params = {
            "seu_name": seu_name,
            "issue_type": issue_type
        }
        return await self._request("POST", "/performance/action-plan", params=params)
    
    # Forecast Endpoint
    
    async def forecast_demand(
        self,
        machine_id: str,
        horizon: str = "short",
        periods: int = 4
    ) -> Dict[str, Any]:
        """
        Forecast energy demand
        
        Args:
            machine_id: Machine UUID
            horizon: "short" (1-24h), "medium" (1-7d), "long" (1-4w)
            periods: Number of future periods
            
        Returns:
            Forecasted power values with confidence intervals
        """
        params = {
            "machine_id": machine_id,
            "horizon": horizon,
            "periods": periods
        }
        return await self._request("GET", "/forecast/demand", params=params)
    
    async def list_baseline_models(
        self,
        seu_name: str,
        energy_source: str = "electricity"
    ) -> Dict[str, Any]:
        """
        List baseline models for a specific machine
        
        Args:
            seu_name: Machine/SEU name
            energy_source: Energy source type
            
        Returns:
            List of baseline models with their metadata
        """
        params = {
            "seu_name": seu_name,
            "energy_source": energy_source
        }
        return await self._request("GET", "/baseline/models", params=params)
    
    async def get_baseline_model_explanation(
        self,
        model_id: str,
        include_explanation: bool = True
    ) -> Dict[str, Any]:
        """
        Get baseline model details with optional explanation
        
        Args:
            model_id: Model UUID
            include_explanation: Include key drivers and accuracy explanation
            
        Returns:
            Model details with explanation (key_drivers, accuracy_explanation, formula_explanation, etc.)
        """
        params = {"include_explanation": str(include_explanation).lower()}
        return await self._request("GET", f"/baseline/model/{model_id}", params=params)
    
    async def list_seus(
        self,
        energy_source: str = None
    ) -> Dict[str, Any]:
        """
        List all significant energy uses (SEUs)
        
        Args:
            energy_source: Optional filter by energy source
            
        Returns:
            List of SEUs with their metadata
        """
        params = {}
        if energy_source:
            params["energy_source"] = energy_source
        return await self._request("GET", "/seus", params=params)
    
    async def get_energy_types(
        self,
        machine_id: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        List energy types consumed by a machine
        
        Args:
            machine_id: Machine UUID
            hours: Time window in hours
            
        Returns:
            List of energy types with statistics
        """
        params = {"hours": hours}
        return await self._request("GET", f"/machines/{machine_id}/energy-types", params=params)
    
    async def get_energy_readings(
        self,
        machine_id: str,
        energy_type: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get energy readings for specific type
        
        Args:
            machine_id: Machine UUID
            energy_type: electricity, natural_gas, steam, compressed_air
            hours: Time window in hours
            
        Returns:
            Energy readings and statistics
        """
        params = {"hours": hours}
        return await self._request("GET", f"/machines/{machine_id}/energy/{energy_type}", params=params)
    
    async def get_energy_summary(
        self,
        machine_id: str,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> Dict[str, Any]:
        """
        Get multi-energy summary for all types
        
        Args:
            machine_id: Machine UUID
            start_time: Period start (defaults to 24 hours ago)
            end_time: Period end (defaults to now)
            
        Returns:
            Summary across all energy types
        """
        # Default to last 24 hours if not specified
        if not end_time:
            end_time = datetime.now(timezone.utc)
        if not start_time:
            start_time = end_time - timedelta(hours=24)
        
        params = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }
        return await self._request("GET", f"/machines/{machine_id}/energy-summary", params=params)
    
    async def predict_baseline(
        self,
        seu_name: str,
        energy_source: str = "electricity",
        features: Dict[str, float] = None,
        include_message: bool = True
    ) -> Dict[str, Any]:
        """
        Predict baseline energy consumption
        
        Args:
            seu_name: Machine/SEU name
            energy_source: Energy source type
            features: Operating condition features
            include_message: Include formatted message
            
        Returns:
            Baseline prediction with predicted_energy_kwh
        """
        payload = {
            "seu_name": seu_name,
            "energy_source": energy_source,
            "features": features or {},
            "include_message": include_message
        }
        return await self._request("POST", "/baseline/predict", json=payload)
    
    async def get_forecast(
        self,
        machine: str = None,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get short-term forecast
        
        Args:
            machine: Machine name (optional). Will be resolved to machine_id.
            hours: Forecast horizon in hours
            
        Returns:
            Forecast data
        """
        params = {}
        if machine:
            # Lookup machine ID by name
            machines = await self.list_machines(search=machine)
            if not machines:
                raise ValueError(f"Machine not found: {machine}")
            params["machine_id"] = machines[0]["id"]
        
        return await self._request("GET", "/forecast/short-term", params=params)
    
    # ISO 50001 Compliance
    
    async def get_enpi_report(
        self,
        factory_id: str,
        period: str
    ) -> Dict[str, Any]:
        """
        Get ISO 50001 EnPI compliance report
        
        Args:
            factory_id: Factory UUID
            period: Report period (quarterly: "2025-Q1", "2025-Q2", etc. or annual: "2025")
            
        Returns:
            EnPI report with overall performance, SEU breakdown, action plans status
        """
        params = {
            "factory_id": factory_id,
            "period": period
        }
        return await self._request("GET", "/iso50001/enpi-report", params=params)
    
    async def list_action_plans(
        self,
        factory_id: str,
        status: Optional[str] = None,
        priority: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List ISO 50001 action plans with optional filtering
        
        Args:
            factory_id: Factory UUID
            status: Filter by status (planned, in_progress, completed, cancelled, on_hold)
            priority: Filter by priority (low, medium, high, critical)
            
        Returns:
            List of action plans with details
        """
        params = {"factory_id": factory_id}
        if status:
            params["status"] = status
        if priority:
            params["priority"] = priority
        return await self._request("GET", "/iso50001/action-plans", params=params)


# Context manager support
class ENMSClientContext:
    """Context manager for ENMSClient"""
    
    def __init__(self, base_url: str = "http://localhost:8001/api/v1", **kwargs):
        self.base_url = base_url
        self.kwargs = kwargs
        self.client: Optional[ENMSClient] = None
    
    async def __aenter__(self) -> ENMSClient:
        self.client = ENMSClient(self.base_url, **self.kwargs)
        return self.client
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.close()
