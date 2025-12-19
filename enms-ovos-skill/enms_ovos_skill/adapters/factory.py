"""
Adapter Factory - Dynamically load EnMS adapters based on configuration
Enables WASABI portability by selecting the right adapter at runtime
"""
from typing import Dict, Any
from .base import EnMSAdapter
from .humanergy import HumanergyAdapter
import structlog

logger = structlog.get_logger(__name__)


class AdapterFactory:
    """
    Factory for creating EnMS adapters
    
    Supports multiple EnMS implementations:
    - humanergy: Humanergy's EnMS (default, reference implementation)
    - generic: Generic EnMS with standard REST API
    - custom: Custom adapter (user-provided module)
    
    Usage:
        config = load_config('config.yaml')
        adapter = AdapterFactory.create(config)
        machines = await adapter.list_machines()
    """
    
    # Registry of available adapters
    _adapters = {
        'humanergy': HumanergyAdapter,
        # Future adapters can be registered here:
        # 'siemens': SiemensAdapter,
        # 'schneider': SchneiderAdapter,
        # 'generic': GenericEnMSAdapter,
    }
    
    @classmethod
    def create(cls, config: Dict[str, Any]) -> EnMSAdapter:
        """
        Create an EnMS adapter based on configuration
        
        Args:
            config: Configuration dict with 'adapter_type' key
                    Example:
                    {
                        'adapter_type': 'humanergy',
                        'api_base_url': 'http://localhost:8001/api/v1',
                        'timeout': 90.0,
                        ...
                    }
        
        Returns:
            Concrete adapter instance implementing EnMSAdapter
        
        Raises:
            ValueError: If adapter_type is unknown or missing
        """
        adapter_type = config.get('adapter_type', 'humanergy')
        
        if adapter_type not in cls._adapters:
            available = ', '.join(cls._adapters.keys())
            raise ValueError(
                f"Unknown adapter type: '{adapter_type}'. "
                f"Available adapters: {available}"
            )
        
        adapter_class = cls._adapters[adapter_type]
        
        logger.info("adapter_factory_creating",
                   adapter_type=adapter_type,
                   adapter_class=adapter_class.__name__)
        
        return adapter_class(config)
    
    @classmethod
    def register(cls, name: str, adapter_class: type):
        """
        Register a custom adapter
        
        Allows users to add their own EnMS adapters at runtime.
        
        Args:
            name: Adapter name (used in config.yaml)
            adapter_class: Class implementing EnMSAdapter
        
        Example:
            from enms_ovos_skill.adapters import AdapterFactory
            from my_company.enms_adapter import MyEnMSAdapter
            
            AdapterFactory.register('mycompany', MyEnMSAdapter)
        """
        if not issubclass(adapter_class, EnMSAdapter):
            raise TypeError(
                f"Adapter class must inherit from EnMSAdapter, "
                f"got {adapter_class.__name__}"
            )
        
        cls._adapters[name] = adapter_class
        logger.info("adapter_registered",
                   name=name,
                   adapter_class=adapter_class.__name__)
    
    @classmethod
    def list_adapters(cls) -> list:
        """
        List all available adapter types
        
        Returns:
            List of adapter names (e.g., ['humanergy', 'generic', 'custom'])
        """
        return list(cls._adapters.keys())
    
    @classmethod
    def get_adapter_info(cls, adapter_type: str) -> Dict[str, str]:
        """
        Get information about a specific adapter
        
        Args:
            adapter_type: Adapter name
        
        Returns:
            Dict with adapter metadata
        """
        if adapter_type not in cls._adapters:
            return {"error": f"Unknown adapter: {adapter_type}"}
        
        adapter_class = cls._adapters[adapter_type]
        
        return {
            "name": adapter_type,
            "class": adapter_class.__name__,
            "module": adapter_class.__module__,
            "doc": adapter_class.__doc__ or "No documentation available"
        }
