"""
data/parking_data.py
--------------------
Lightweight JSON-backed data store for parking zones.
In production this would connect to a PostgreSQL/PostGIS database.
Seeded with realistic UK parking zones for demonstration purposes.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Optional

DATA_FILE = os.path.join(os.path.dirname(__file__), 'zones.json')


# ── Seed data ──────────────────────────────────────────────────────────────────

SEED_ZONES = [
    # ── London ────────────────────────────────────────────────────────────────
    {
        'id': 'lon-001', 'lat': 51.5074, 'lng': -0.1278,
        'street': 'Oxford Street, London',
        'restriction_type': 'timed',
        'restriction_text': 'No Waiting Mon-Sat 8am-6:30pm',
        'hours': '8am - 6:30pm', 'days': 'Monday - Saturday',
        'permit_zone': None, 'max_stay': None,
        'submitted_at': '2024-01-15T09:00:00',
    },
    {
        'id': 'lon-002', 'lat': 51.5100, 'lng': -0.1340,
        'street': 'Marylebone High Street, London',
        'restriction_type': 'pay_display',
        'restriction_text': 'Pay & Display Mon-Sat 8am-8pm Max Stay 2 Hours',
        'hours': '8am - 8pm', 'days': 'Monday - Saturday',
        'permit_zone': None, 'max_stay': '2 Hours',
        'submitted_at': '2024-01-16T10:00:00',
    },
    {
        'id': 'lon-003', 'lat': 51.5155, 'lng': -0.0922,
        'street': 'Barbican, London',
        'restriction_type': 'permit',
        'restriction_text': 'Permit Holders Only Zone B2',
        'hours': None, 'days': None,
        'permit_zone': 'B2', 'max_stay': None,
        'submitted_at': '2024-01-17T11:00:00',
    },
    {
        'id': 'lon-004', 'lat': 51.5030, 'lng': -0.1195,
        'street': 'Waterloo Road, London',
        'restriction_type': 'disabled',
        'restriction_text': 'Disabled Badge Holders Only No Time Limit',
        'hours': None, 'days': None,
        'permit_zone': None, 'max_stay': None,
        'submitted_at': '2024-01-18T08:00:00',
    },
    {
        'id': 'lon-005', 'lat': 51.4994, 'lng': -0.1245,
        'street': 'Lambeth Bridge Road, London',
        'restriction_type': 'free',
        'restriction_text': 'Free Parking After 6:30pm and Sunday',
        'hours': '6:30pm onwards', 'days': 'Sunday & evenings',
        'permit_zone': None, 'max_stay': None,
        'submitted_at': '2024-01-19T07:30:00',
    },
    # ── Manchester ────────────────────────────────────────────────────────────
    {
        'id': 'man-001', 'lat': 53.4808, 'lng': -2.2426,
        'street': 'Deansgate, Manchester',
        'restriction_type': 'timed',
        'restriction_text': 'No Waiting Mon-Sat 8am-6pm',
        'hours': '8am - 6pm', 'days': 'Monday - Saturday',
        'permit_zone': None, 'max_stay': None,
        'submitted_at': '2024-02-01T09:00:00',
    },
    {
        'id': 'man-002', 'lat': 53.4790, 'lng': -2.2400,
        'street': 'St Peter\'s Square, Manchester',
        'restriction_type': 'pay_display',
        'restriction_text': 'Pay & Display 7 Days 8am-8pm Max Stay 3 Hours',
        'hours': '8am - 8pm', 'days': 'Every Day',
        'permit_zone': None, 'max_stay': '3 Hours',
        'submitted_at': '2024-02-02T10:30:00',
    },
    {
        'id': 'man-003', 'lat': 53.4850, 'lng': -2.2330,
        'street': 'Northern Quarter, Manchester',
        'restriction_type': 'permit',
        'restriction_text': 'Permit Holders Only Zone M1 Mon-Fri',
        'hours': None, 'days': 'Monday - Friday',
        'permit_zone': 'M1', 'max_stay': None,
        'submitted_at': '2024-02-03T11:00:00',
    },
    # ── Birmingham ────────────────────────────────────────────────────────────
    {
        'id': 'bir-001', 'lat': 52.4862, 'lng': -1.8904,
        'street': 'Broad Street, Birmingham',
        'restriction_type': 'timed',
        'restriction_text': 'No Waiting Mon-Sat 8am-7pm',
        'hours': '8am - 7pm', 'days': 'Monday - Saturday',
        'permit_zone': None, 'max_stay': None,
        'submitted_at': '2024-02-10T09:00:00',
    },
    {
        'id': 'bir-002', 'lat': 52.4800, 'lng': -1.8950,
        'street': 'Five Ways, Birmingham',
        'restriction_type': 'free',
        'restriction_text': 'Free Parking Sundays and Bank Holidays',
        'hours': 'All day', 'days': 'Sunday & Bank Holidays',
        'permit_zone': None, 'max_stay': None,
        'submitted_at': '2024-02-11T10:00:00',
    },
    # ── Edinburgh ─────────────────────────────────────────────────────────────
    {
        'id': 'edi-001', 'lat': 55.9533, 'lng': -3.1883,
        'street': 'Princes Street, Edinburgh',
        'restriction_type': 'timed',
        'restriction_text': 'No Waiting Mon-Sat 8am-6:30pm',
        'hours': '8am - 6:30pm', 'days': 'Monday - Saturday',
        'permit_zone': None, 'max_stay': None,
        'submitted_at': '2024-03-01T09:00:00',
    },
    {
        'id': 'edi-002', 'lat': 55.9570, 'lng': -3.1950,
        'street': 'New Town, Edinburgh',
        'restriction_type': 'permit',
        'restriction_text': 'Permit Holders Only Zone E3',
        'hours': None, 'days': None,
        'permit_zone': 'E3', 'max_stay': None,
        'submitted_at': '2024-03-02T11:00:00',
    },
    # ── Bristol ───────────────────────────────────────────────────────────────
    {
        'id': 'brs-001', 'lat': 51.4545, 'lng': -2.5879,
        'street': 'Clifton Village, Bristol',
        'restriction_type': 'pay_display',
        'restriction_text': 'Pay & Display Mon-Sun 9am-6pm Max Stay 1 Hour',
        'hours': '9am - 6pm', 'days': 'Every Day',
        'permit_zone': None, 'max_stay': '1 Hour',
        'submitted_at': '2024-03-10T09:00:00',
    },
]


# ── Persistence ────────────────────────────────────────────────────────────────

def _load_zones() -> list:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    # First run: write seed data
    _save_zones(SEED_ZONES)
    return list(SEED_ZONES)


def _save_zones(zones: list) -> None:
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(zones, f, indent=2, ensure_ascii=False)


# ── Public API ─────────────────────────────────────────────────────────────────

def get_all_zones() -> list:
    return _load_zones()


def get_zone_by_id(zone_id: str) -> Optional[dict]:
    return next((z for z in _load_zones() if z['id'] == zone_id), None)


def get_parking_zones(filter_type: str = 'all', search: str = '') -> list:
    zones = _load_zones()
    if filter_type != 'all':
        zones = [z for z in zones if z['restriction_type'] == filter_type]
    if search:
        search_lower = search.lower()
        zones = [z for z in zones if search_lower in z.get('street', '').lower()]
    return zones


def add_parking_zone(zone_data: dict) -> str:
    zones = _load_zones()
    zone_id = zone_data.get('id') or f"user-{uuid.uuid4().hex[:8]}"
    zone_data['id'] = zone_id
    zone_data.setdefault('submitted_at', datetime.now().isoformat())
    zones.append(zone_data)
    _save_zones(zones)
    return zone_id


def update_parking_zone(zone_id: str, updates: dict) -> bool:
    zones = _load_zones()
    for i, zone in enumerate(zones):
        if zone['id'] == zone_id:
            zones[i].update(updates)
            _save_zones(zones)
            return True
    return False


def delete_parking_zone(zone_id: str) -> bool:
    zones = _load_zones()
    original_count = len(zones)
    zones = [z for z in zones if z['id'] != zone_id]
    if len(zones) < original_count:
        _save_zones(zones)
        return True
    return False
