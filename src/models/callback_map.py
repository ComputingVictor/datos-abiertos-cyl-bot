"""Callback data mapping for Telegram bot."""

import hashlib
from typing import Dict, Optional


class CallbackMapper:
    """Maps long callback data to short IDs for Telegram buttons."""
    
    def __init__(self):
        self._id_to_data: Dict[str, str] = {}
        self._data_to_id: Dict[str, str] = {}
    
    def _generate_short_id(self, data: str) -> str:
        """Generate a short ID from data."""
        # Use MD5 hash and take first 8 characters
        hash_obj = hashlib.md5(data.encode())
        return hash_obj.hexdigest()[:8]
    
    def get_short_id(self, full_data: str) -> str:
        """Get or create a short ID for full callback data."""
        if full_data in self._data_to_id:
            return self._data_to_id[full_data]
        
        short_id = self._generate_short_id(full_data)
        
        # Handle collisions by adding suffix
        counter = 0
        original_short_id = short_id
        while short_id in self._id_to_data:
            counter += 1
            short_id = f"{original_short_id}{counter}"
        
        self._id_to_data[short_id] = full_data
        self._data_to_id[full_data] = short_id
        
        return short_id
    
    def get_full_data(self, short_id: str) -> Optional[str]:
        """Get full callback data from short ID."""
        return self._id_to_data.get(short_id)


# Global mapper instance
callback_mapper = CallbackMapper()