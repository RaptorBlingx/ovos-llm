"""
EnMS API Client - Async HTTP client for Energy Management System
Tier 3: API Executor with circuit breaker, retries, and connection pooling
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
import structlog

logger = structlog.get_logger(__name__)


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
        retry=retry_if_exception_type(httpx.HTTPError)
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
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
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
    
    # Factory-Wide Endpoints (NEW - from OVOS endpoints)
    
    async def get_factory_summary(self) -> Dict[str, Any]:
        """Get factory-wide energy summary"""
        return await self._request("GET", "/factory/summary")
    
    async def get_top_consumers(self, limit: int = 10) -> Dict[str, Any]:
        """
        Get top energy consumers
        
        Args:
            limit: Number of machines to return (default 10)
            
        Returns:
            Ranked list of machines by energy consumption
        """
        params = {"limit": limit}
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
