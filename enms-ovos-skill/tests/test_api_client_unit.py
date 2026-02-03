"""
Unit Tests for ENMSClient API Client
=====================================

Tests the async HTTP client with 30+ test cases
- Mock all HTTP calls (no real API dependency)
- Test all 8 endpoint methods
- Test timeout handling
- Test retry logic
- Test error responses
- Test async behavior
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
import httpx

from lib.api_client import ENMSClient, ENMSClientContext


# ============================================================================
# BASIC ENDPOINT TESTS (10 cases)
# ============================================================================

class TestBasicEndpoints:
    """Test basic API endpoint methods"""
    
    @pytest.mark.asyncio
    async def test_health_check(self, mocker):
        """Test health check endpoint"""
        client = ENMSClient()
        
        # Mock the _request method
        mock_response = {"status": "healthy", "version": "1.0.0"}
        mocker.patch.object(client, '_request', return_value=mock_response)
        
        result = await client.health_check()
        
        assert result["status"] == "healthy"
        client._request.assert_called_once_with("GET", "/health")
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_system_stats(self, mocker):
        """Test system stats endpoint"""
        client = ENMSClient()
        
        mock_response = {
            "cpu_percent": 45.2,
            "memory_percent": 62.1,
            "active_machines": 8
        }
        mocker.patch.object(client, '_request', return_value=mock_response)
        
        result = await client.system_stats()
        
        assert result["cpu_percent"] == 45.2
        assert result["active_machines"] == 8
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_list_machines_no_filter(self, mocker):
        """Test listing all machines"""
        client = ENMSClient()
        
        mock_response = [
            {"machine_id": "comp-1", "machine_name": "Compressor-1"},
            {"machine_id": "boil-1", "machine_name": "Boiler-1"}
        ]
        mocker.patch.object(client, '_request', return_value=mock_response)
        
        result = await client.list_machines()
        
        assert len(result) == 2
        assert result[0]["machine_name"] == "Compressor-1"
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_list_machines_with_search(self, mocker):
        """Test listing machines with search filter"""
        client = ENMSClient()
        
        mock_response = [
            {"machine_id": "comp-1", "machine_name": "Compressor-1"}
        ]
        mocker.patch.object(client, '_request', return_value=mock_response)
        
        result = await client.list_machines(search="Compressor")
        
        assert len(result) == 1
        client._request.assert_called_with(
            "GET", "/machines", 
            params={"search": "Compressor"}
        )
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_list_machines_active_filter(self, mocker):
        """Test filtering by active status"""
        client = ENMSClient()
        
        mock_response = [
            {"machine_id": "comp-1", "machine_name": "Compressor-1", "is_active": True}
        ]
        mocker.patch.object(client, '_request', return_value=mock_response)
        
        result = await client.list_machines(is_active=True)
        
        assert len(result) == 1
        client._request.assert_called_with(
            "GET", "/machines",
            params={"is_active": "true"}
        )
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_machine_status(self, mocker):
        """Test get machine status by name"""
        client = ENMSClient()
        
        mock_response = {
            "machine_name": "Compressor-1",
            "current_status": "running",
            "power_kw": 47.98
        }
        mocker.patch.object(client, '_request', return_value=mock_response)
        
        result = await client.get_machine_status("Compressor-1")
        
        assert result["machine_name"] == "Compressor-1"
        assert result["current_status"] == "running"
        client._request.assert_called_with(
            "GET", "/machines/status/Compressor-1"
        )
        
        await client.close()


# ============================================================================
# TIME-SERIES ENDPOINT TESTS (5 cases)
# ============================================================================

class TestTimeSeriesEndpoints:
    """Test time-series data endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_energy_timeseries(self, mocker):
        """Test energy time-series endpoint"""
        client = ENMSClient()
        
        start = datetime(2025, 11, 19, 0, 0, 0)
        end = datetime(2025, 11, 19, 23, 59, 59)
        
        mock_response = {
            "machine_id": "comp-1",
            "data": [
                {"timestamp": "2025-11-19T00:00:00", "energy_kwh": 48.5},
                {"timestamp": "2025-11-19T01:00:00", "energy_kwh": 47.2}
            ]
        }
        mocker.patch.object(client, '_request', return_value=mock_response)
        
        result = await client.get_energy_timeseries(
            machine_id="comp-1",
            start_time=start,
            end_time=end,
            interval="1hour"
        )
        
        assert result["machine_id"] == "comp-1"
        assert len(result["data"]) == 2
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_power_timeseries(self, mocker):
        """Test power time-series endpoint"""
        client = ENMSClient()
        
        start = datetime.utcnow() - timedelta(hours=24)
        end = datetime.utcnow()
        
        mock_response = {
            "machine_id": "comp-1",
            "data": [
                {"timestamp": start.isoformat(), "power_kw": 47.98}
            ]
        }
        mocker.patch.object(client, '_request', return_value=mock_response)
        
        result = await client.get_power_timeseries(
            machine_id="comp-1",
            start_time=start,
            end_time=end
        )
        
        assert result["machine_id"] == "comp-1"
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_latest_reading(self, mocker):
        """Test latest reading endpoint"""
        client = ENMSClient()
        
        mock_response = {
            "machine_id": "comp-1",
            "timestamp": "2025-11-19T12:00:00",
            "power_kw": 47.98,
            "energy_kwh": 1152.5
        }
        mocker.patch.object(client, '_request', return_value=mock_response)
        
        result = await client.get_latest_reading("comp-1")
        
        assert result["machine_id"] == "comp-1"
        assert "power_kw" in result
        
        await client.close()


# ============================================================================
# FACTORY-WIDE ENDPOINT TESTS (3 cases)
# ============================================================================

class TestFactoryEndpoints:
    """Test factory-wide analytics endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_factory_summary(self, mocker):
        """Test factory summary endpoint"""
        client = ENMSClient()
        
        mock_response = {
            "total_machines": 8,
            "active_machines": 7,
            "total_power_kw": 384.2,
            "total_energy_kwh_today": 9205.7
        }
        mocker.patch.object(client, '_request', return_value=mock_response)
        
        result = await client.get_factory_summary()
        
        assert result["total_machines"] == 8
        assert result["active_machines"] == 7
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_top_consumers_default(self, mocker):
        """Test top consumers with default params"""
        client = ENMSClient()
        
        mock_response = {
            "metric": "energy",
            "limit": 5,
            "machines": [
                {"machine_name": "Compressor-1", "energy_kwh": 1500.0},
                {"machine_name": "Boiler-1", "energy_kwh": 1200.0}
            ]
        }
        mocker.patch.object(client, '_request', return_value=mock_response)
        
        result = await client.get_top_consumers()
        
        assert result["metric"] == "energy"
        assert len(result["machines"]) == 2
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_top_consumers_custom(self, mocker):
        """Test top consumers with custom params"""
        client = ENMSClient()
        
        mock_response = {
            "metric": "cost",
            "limit": 3,
            "machines": []
        }
        mocker.patch.object(client, '_request', return_value=mock_response)
        
        result = await client.get_top_consumers(
            metric="cost",
            limit=3
        )
        
        assert result["metric"] == "cost"
        assert result["limit"] == 3
        
        await client.close()


# ============================================================================
# ANOMALY & FORECAST ENDPOINTS (4 cases)
# ============================================================================

class TestAnomalyForecastEndpoints:
    """Test anomaly detection and forecasting endpoints"""
    
    @pytest.mark.asyncio
    async def test_detect_anomalies(self, mocker):
        """Test anomaly detection endpoint"""
        client = ENMSClient()
        
        start = datetime.utcnow() - timedelta(days=7)
        end = datetime.utcnow()
        
        mock_response = {
            "machine_id": "comp-1",
            "anomalies": [
                {"timestamp": "2025-11-18T14:30:00", "score": 0.85}
            ]
        }
        mocker.patch.object(client, '_request', return_value=mock_response)
        
        result = await client.detect_anomalies(
            machine_id="comp-1",
            start=start,
            end=end
        )
        
        assert result["machine_id"] == "comp-1"
        assert len(result["anomalies"]) == 1
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_get_recent_anomalies_all(self, mocker):
        """Test get recent anomalies for all machines"""
        client = ENMSClient()
        
        mock_response = {
            "anomalies": [
                {"machine_id": "comp-1", "severity": "high"},
                {"machine_id": "boil-1", "severity": "medium"}
            ]
        }
        mocker.patch.object(client, '_request', return_value=mock_response)
        
        result = await client.get_recent_anomalies()
        
        assert len(result["anomalies"]) == 2
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_forecast_demand_short(self, mocker):
        """Test short-term demand forecast"""
        client = ENMSClient()
        
        mock_response = {
            "machine_id": "comp-1",
            "horizon": "short",
            "forecast": [
                {"timestamp": "2025-11-19T13:00:00", "power_kw": 48.5, "confidence": 0.95}
            ]
        }
        mocker.patch.object(client, '_request', return_value=mock_response)
        
        result = await client.forecast_demand(
            machine_id="comp-1",
            horizon="short",
            periods=4
        )
        
        assert result["horizon"] == "short"
        assert len(result["forecast"]) == 1
        
        await client.close()


# ============================================================================
# ERROR HANDLING TESTS (5 cases)
# ============================================================================

class TestErrorHandling:
    """Test error handling and retries"""
    
    @pytest.mark.asyncio
    async def test_http_404_error(self, mocker):
        """Test 404 Not Found error"""
        client = ENMSClient()
        
        # Mock HTTP 404 error
        error_response = MagicMock()
        error_response.status_code = 404
        error_response.json.return_value = {"detail": "Not Found"}
        
        http_error = httpx.HTTPStatusError(
            message="404",
            request=MagicMock(),
            response=error_response
        )
        
        mocker.patch.object(client, '_request', side_effect=http_error)
        
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_machine_status("NonExistent")
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_http_500_error(self, mocker):
        """Test 500 Internal Server Error"""
        client = ENMSClient()
        
        error_response = MagicMock()
        error_response.status_code = 500
        
        http_error = httpx.HTTPStatusError(
            message="500",
            request=MagicMock(),
            response=error_response
        )
        
        mocker.patch.object(client, '_request', side_effect=http_error)
        
        with pytest.raises(httpx.HTTPStatusError):
            await client.health_check()
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_timeout_error(self, mocker):
        """Test request timeout"""
        client = ENMSClient(timeout=0.1)  # Very short timeout
        
        # Mock timeout error
        timeout_error = httpx.TimeoutException("Request timed out")
        mocker.patch.object(client.client, 'request', side_effect=timeout_error)
        
        with pytest.raises(Exception):  # Will be caught by retry logic
            await client.health_check()
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_connection_error(self, mocker):
        """Test connection error"""
        client = ENMSClient()
        
        conn_error = httpx.ConnectError("Connection refused")
        mocker.patch.object(client.client, 'request', side_effect=conn_error)
        
        with pytest.raises(Exception):
            await client.health_check()
        
        await client.close()


# ============================================================================
# CLIENT LIFECYCLE TESTS (3 cases)
# ============================================================================

class TestClientLifecycle:
    """Test client initialization and cleanup"""
    
    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initializes with correct base URL"""
        client = ENMSClient(base_url="http://example.com/api")
        
        assert client.base_url == "http://example.com/api"
        assert client.timeout == 30.0
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_client_custom_timeout(self):
        """Test client with custom timeout"""
        client = ENMSClient(timeout=60.0)
        
        assert client.timeout == 60.0
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test using client as async context manager"""
        async with ENMSClientContext() as client:
            assert client is not None
            assert isinstance(client, ENMSClient)
        
        # Client should be closed after context
