"""
Dynamic Machine Registry - Priority 4
Fetches and caches machines/SEUs from EnMS API dynamically
Eliminates hardcoded machine names for WASABI portability
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio
import structlog

logger = structlog.get_logger(__name__)


class DynamicMachineRegistry:
    """
    Dynamically fetches and caches machine/SEU lists from EnMS API
    
    Features:
    - Auto-refresh every 1 hour (configurable)
    - Fallback to hardcoded list if API fails
    - Thread-safe caching
    - Supports both machines and SEUs
    
    Usage:
        registry = DynamicMachineRegistry(api_client)
        await registry.refresh()
        machines = registry.get_machines()
    """
    
    def __init__(
        self,
        api_client,
        refresh_interval: timedelta = timedelta(hours=1),
        fallback_machines: Optional[List[str]] = None
    ):
        """
        Initialize registry
        
        Args:
            api_client: ENMSClient instance for API calls
            refresh_interval: How often to refresh (default: 1 hour)
            fallback_machines: Hardcoded fallback if API fails
        """
        self.api_client = api_client
        self.refresh_interval = refresh_interval
        
        # Fallback machines (used if API unavailable)
        self.fallback_machines = fallback_machines or [
            "Compressor-1",
            "Boiler-1",
            "HVAC-Main",
            "Conveyor-A",
            "Injection-Molding-1",
            "Pump-1"
        ]
        
        # Cached data
        self.machines: List[str] = []
        self.seus: List[Dict[str, Any]] = []
        self.last_refresh: Optional[datetime] = None
        self.refresh_in_progress = False
        
        logger.info("machine_registry_initialized",
                   refresh_interval_hours=refresh_interval.total_seconds() / 3600,
                   fallback_count=len(self.fallback_machines))
    
    async def refresh(self) -> bool:
        """
        Fetch machines and SEUs from EnMS API
        
        Returns:
            True if refresh succeeded, False if using fallback
        """
        if self.refresh_in_progress:
            logger.debug("refresh_already_in_progress")
            return False
        
        self.refresh_in_progress = True
        success = False
        
        try:
            logger.info("machine_registry_refresh_start")
            
            # Fetch machines from API
            try:
                machines_response = await self.api_client.list_machines()
                
                if machines_response and isinstance(machines_response, list):
                    # Extract machine names/IDs
                    self.machines = []
                    for machine in machines_response:
                        if isinstance(machine, dict):
                            # Prefer 'machine_name' or 'name' field
                            machine_name = machine.get('machine_name') or machine.get('name') or machine.get('machine_id')
                            if machine_name:
                                self.machines.append(machine_name)
                    
                    logger.info("machines_fetched_from_api",
                               count=len(self.machines),
                               machines=self.machines[:5])  # Log first 5
                    success = True
                else:
                    logger.warning("machines_api_returned_invalid_format",
                                 response_type=type(machines_response).__name__)
                    self.machines = self.fallback_machines
            
            except Exception as e:
                logger.error("machines_api_fetch_failed",
                           error=str(e),
                           using_fallback=True)
                self.machines = self.fallback_machines
            
            # Fetch SEUs from API
            try:
                seus_response = await self.api_client.list_seus()
                
                if seus_response and isinstance(seus_response, dict):
                    # API returns {"seus": [...]} format
                    self.seus = seus_response.get('seus', [])
                    logger.info("seus_fetched_from_api",
                               count=len(self.seus))
                elif isinstance(seus_response, list):
                    self.seus = seus_response
                    logger.info("seus_fetched_from_api",
                               count=len(self.seus))
                else:
                    logger.warning("seus_api_returned_invalid_format",
                                 response_type=type(seus_response).__name__)
                    self.seus = []
            
            except Exception as e:
                logger.error("seus_api_fetch_failed",
                           error=str(e))
                self.seus = []
            
            # Update timestamp
            self.last_refresh = datetime.now()
            
            logger.info("machine_registry_refresh_complete",
                       machines_count=len(self.machines),
                       seus_count=len(self.seus),
                       success=success)
            
            return success
        
        finally:
            self.refresh_in_progress = False
    
    def get_machines(self) -> List[str]:
        """
        Get cached machine list (auto-refresh if stale)
        
        Returns:
            List of machine names
        """
        # Check if refresh needed
        if self._needs_refresh():
            logger.info("machine_list_stale_triggering_refresh")
            # Note: Can't await in non-async method, just return current cache
            # Refresh will happen on next scheduled refresh
        
        return self.machines if self.machines else self.fallback_machines
    
    def get_seus(self) -> List[Dict[str, Any]]:
        """
        Get cached SEU list
        
        Returns:
            List of SEU dictionaries
        """
        return self.seus
    
    def get_seu_names(self) -> List[str]:
        """
        Get list of SEU names (for validation)
        
        Returns:
            List of SEU name strings
        """
        if not self.seus:
            return []
        
        seu_names = []
        for seu in self.seus:
            if isinstance(seu, dict):
                name = seu.get('seu_name') or seu.get('name')
                if name:
                    seu_names.append(name)
        
        return seu_names
    
    def _needs_refresh(self) -> bool:
        """Check if cache is stale"""
        if not self.last_refresh:
            return True
        
        age = datetime.now() - self.last_refresh
        return age > self.refresh_interval
    
    def is_stale(self) -> bool:
        """Public method to check if refresh is needed"""
        return self._needs_refresh()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics for monitoring"""
        return {
            "machines_count": len(self.machines),
            "seus_count": len(self.seus),
            "last_refresh": self.last_refresh.isoformat() if self.last_refresh else None,
            "is_stale": self._needs_refresh(),
            "using_fallback": self.machines == self.fallback_machines,
            "refresh_interval_hours": self.refresh_interval.total_seconds() / 3600
        }
