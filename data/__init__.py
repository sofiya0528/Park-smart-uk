"""Data package — parking zone store."""
from .parking_data import (
    get_all_zones, get_zone_by_id, get_parking_zones,
    add_parking_zone, update_parking_zone, delete_parking_zone,
)

__all__ = [
    'get_all_zones', 'get_zone_by_id', 'get_parking_zones',
    'add_parking_zone', 'update_parking_zone', 'delete_parking_zone',
]
