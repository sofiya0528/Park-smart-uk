"""
utils/helpers.py
----------------
General-purpose helpers shared across the Park Smart UK application.
"""

import os
import re
from datetime import datetime, time


def allowed_file(filename: str, allowed_extensions: set) -> bool:
    """Return True if filename has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions


def format_restriction(zone: dict) -> str:
    """
    Build a single human-readable restriction string from zone fields.
    Example: "No Waiting — Mon-Sat 8am-6pm"
    """
    label_map = {
        'free': 'Free Parking',
        'timed': 'Timed Restriction',
        'pay_display': 'Pay & Display',
        'permit': 'Permit Holders Only',
        'no_waiting': 'No Waiting',
        'disabled': 'Disabled Badge Holders',
        'unknown': 'Restriction',
    }
    restriction_type = zone.get('restriction_type', 'unknown')
    label = label_map.get(restriction_type, 'Restriction')

    parts = [label]
    if zone.get('permit_zone'):
        parts.append(f"Zone {zone['permit_zone']}")
    if zone.get('days'):
        parts.append(zone['days'])
    if zone.get('hours'):
        parts.append(zone['hours'])
    if zone.get('max_stay'):
        parts.append(f"Max {zone['max_stay']}")

    return ' — '.join(parts)


def is_restriction_active(zone: dict, dt: datetime = None) -> bool:
    """
    Return True if a restriction is currently in force based on time and day.
    Falls back to True (assume restricted) if times cannot be parsed.
    """
    if dt is None:
        dt = datetime.now()

    restriction_type = zone.get('restriction_type', 'unknown')

    # Always-on restrictions
    if restriction_type in ('permit', 'disabled'):
        return True
    if restriction_type == 'free':
        return False

    # Parse hours
    hours_str = zone.get('hours', '')
    if not hours_str:
        return True  # No time info — assume active

    try:
        start, end = _parse_time_range(hours_str)
        if start and end:
            current = dt.time()
            if start <= end:
                time_active = start <= current <= end
            else:  # Overnight range (e.g. 8pm - 6am)
                time_active = current >= start or current <= end
        else:
            return True
    except Exception:
        return True

    # Parse days
    days_str = zone.get('days', '')
    if days_str:
        day_active = _is_day_active(days_str, dt.weekday())
    else:
        day_active = True  # No day info — assume every day

    return time_active and day_active


def _parse_time_range(hours_str: str):
    """Parse '8am - 6:30pm' into (time, time) or (None, None)."""
    pattern = re.compile(
        r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?'
        r'\s*[-–]\s*'
        r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?',
        re.IGNORECASE,
    )
    m = pattern.search(hours_str)
    if not m:
        return None, None

    def to_time(h, mins, period):
        h = int(h)
        mins = int(mins) if mins else 0
        if period:
            period = period.lower()
            if period == 'pm' and h != 12:
                h += 12
            elif period == 'am' and h == 12:
                h = 0
        return time(h, mins)

    start = to_time(m.group(1), m.group(2), m.group(3))
    end = to_time(m.group(4), m.group(5), m.group(6))
    return start, end


DAY_RANGES = {
    'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
    'friday': 4, 'saturday': 5, 'sunday': 6,
    'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3,
    'fri': 4, 'sat': 5, 'sun': 6,
}


def _is_day_active(days_str: str, weekday: int) -> bool:
    """Return True if the current weekday falls within the restriction's day range."""
    days_lower = days_str.lower()

    if 'every day' in days_lower or '7 days' in days_lower:
        return True

    # Look for day range like "Monday - Saturday"
    range_match = re.search(
        r'(mon(?:day)?|tue(?:sday)?|wed(?:nesday)?|thu(?:rsday)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?)'
        r'\s*[-–]\s*'
        r'(mon(?:day)?|tue(?:sday)?|wed(?:nesday)?|thu(?:rsday)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?)',
        days_lower,
    )
    if range_match:
        start_day = DAY_RANGES.get(range_match.group(1)[:3])
        end_day = DAY_RANGES.get(range_match.group(2)[:3])
        if start_day is not None and end_day is not None:
            if start_day <= end_day:
                return start_day <= weekday <= end_day
            else:
                return weekday >= start_day or weekday <= end_day

    # Check individual day mentions
    for day_name, day_num in DAY_RANGES.items():
        if len(day_name) >= 3 and day_name in days_lower:
            if day_num == weekday:
                return True

    return True  # Default: assume active


def colour_for_type(restriction_type: str) -> str:
    """Return the Leaflet marker colour for a restriction type."""
    return {
        'free': 'green',
        'timed': 'orange',
        'pay_display': 'blue',
        'permit': 'purple',
        'no_waiting': 'red',
        'disabled': 'cadetblue',
        'unknown': 'grey',
    }.get(restriction_type, 'grey')


def hex_colour_for_type(restriction_type: str) -> str:
    """Return a hex colour for a restriction type (used in charts)."""
    return {
        'free': '#2ecc71',
        'timed': '#f39c12',
        'pay_display': '#3498db',
        'permit': '#9b59b6',
        'no_waiting': '#e74c3c',
        'disabled': '#1abc9c',
        'unknown': '#95a5a6',
    }.get(restriction_type, '#95a5a6')


def paginate(items: list, page: int, per_page: int = 20) -> dict:
    """Simple in-memory pagination helper."""
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    return {
        'items': items[start:end],
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page,
    }
