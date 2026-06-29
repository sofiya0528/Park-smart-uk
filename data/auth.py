"""
data/auth.py
------------
Lightweight JSON-backed user database and authentication helper.
"""

import os
import json
from typing import Optional, List, Tuple
from werkzeug.security import generate_password_hash, check_password_hash
from data.parking_data import get_zone_by_id

USERS_FILE = os.path.join(os.path.dirname(__file__), 'users.json')

def _load_users() -> list:
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []

def _save_users(users: list) -> None:
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

def register_user(username: str, password: str) -> Tuple[bool, str]:
    """Register a new user with hashed password."""
    if not username or not password:
        return False, "Username and password are required."
    
    username_clean = username.strip()
    if len(username_clean) < 3:
        return False, "Username must be at least 3 characters long."
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."

    users = _load_users()
    for user in users:
        if user['username'].lower() == username_clean.lower():
            return False, "Username already exists."

    new_user = {
        'username': username_clean,
        'password_hash': generate_password_hash(password),
        'saved_locations': []
    }
    users.append(new_user)
    _save_users(users)
    return True, "User registered successfully."

def authenticate_user(username: str, password: str) -> Tuple[bool, str]:
    """Authenticate a user's credentials."""
    if not username or not password:
        return False, "Username and password are required."
    
    users = _load_users()
    for user in users:
        if user['username'].lower() == username.strip().lower():
            if check_password_hash(user['password_hash'], password):
                return True, user['username']
            break
    return False, "Invalid username or password."

def toggle_saved_location(username: str, zone_id: str) -> Tuple[bool, bool, str]:
    """
    Toggle a zone in the user's location book.
    Returns (success, is_saved, message)
    """
    users = _load_users()
    for user in users:
        if user['username'].lower() == username.strip().lower():
            saved = user.get('saved_locations', [])
            if zone_id in saved:
                saved.remove(zone_id)
                user['saved_locations'] = saved
                _save_users(users)
                return True, False, "Location removed from Location Book."
            else:
                # Optional validation: ensure zone exists
                zone = get_zone_by_id(zone_id)
                if not zone:
                    return False, False, "Parking zone not found."
                saved.append(zone_id)
                user['saved_locations'] = saved
                _save_users(users)
                return True, True, "Location saved to Location Book."
    return False, False, "User not found."

def is_location_saved(username: str, zone_id: str) -> bool:
    """Check if a location is saved by user."""
    users = _load_users()
    for user in users:
        if user['username'].lower() == username.strip().lower():
            return zone_id in user.get('saved_locations', [])
    return False

def get_saved_locations(username: str) -> List[dict]:
    """Get all saved zones details for the user."""
    users = _load_users()
    zone_ids = []
    for user in users:
        if user['username'].lower() == username.strip().lower():
            zone_ids = user.get('saved_locations', [])
            break
    
    saved_zones = []
    for zid in zone_ids:
        zone = get_zone_by_id(zid)
        if zone:
            saved_zones.append(zone)
    return saved_zones
