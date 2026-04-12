"""
ml/predictor.py - Lightweight parking availability predictor.
Uses scikit-learn GBR (fast) or heuristic fallback.
TensorFlow intentionally skipped at startup for fast load time.
"""

import os
import random
from datetime import datetime

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

# Lazy-loaded - only imported when first prediction is made
_sklearn_model = None
_model_loaded = False

ZONE_TYPE_MAP = {
    'free': 0, 'timed': 1, 'pay_display': 1,
    'permit': 2, 'no_waiting': 3, 'disabled': 0, 'unknown': 1,
}

def _load_model():
    """Load sklearn model once, on first prediction request."""
    global _sklearn_model, _model_loaded
    if _model_loaded:
        return
    _model_loaded = True
    model_path = os.path.join(MODEL_DIR, 'gbr_parking.joblib')
    try:
        import joblib
        if os.path.exists(model_path):
            _sklearn_model = joblib.load(model_path)
            return
        # Train a quick demo model
        from sklearn.ensemble import GradientBoostingRegressor
        import numpy as np
        rng = np.random.default_rng(42)
        n = 3000
        hours   = rng.integers(0, 24, n)
        weekdays= rng.integers(0, 7, n)
        zones   = rng.integers(0, 4, n)
        occ     = (0.3*np.sin(np.pi*hours/12) + 0.2*(weekdays<5) + rng.normal(0,0.1,n)).clip(0,1)
        X = np.column_stack([hours, weekdays, zones])
        _sklearn_model = GradientBoostingRegressor(n_estimators=50, max_depth=3, random_state=42)
        _sklearn_model.fit(X, occ)
        joblib.dump(_sklearn_model, model_path)
    except Exception:
        _sklearn_model = None

def _heuristic(hour, weekday, zone_type):
    base = 0.3
    if 8 <= hour <= 9 or 17 <= hour <= 18: base += 0.4
    elif 10 <= hour <= 16: base += 0.2
    elif hour < 7 or hour > 21: base -= 0.2
    if weekday < 5: base += 0.1
    if zone_type == 'permit': base -= 0.1
    return min(max(base + random.gauss(0, 0.04), 0.0), 1.0)

def occupancy_to_label(occ):
    if occ < 0.3:  return {'label': 'Available',        'colour': '#2ecc71', 'emoji': '🟢'}
    if occ < 0.6:  return {'label': 'Moderately Busy',  'colour': '#f39c12', 'emoji': '🟡'}
    if occ < 0.85: return {'label': 'Busy',             'colour': '#e67e22', 'emoji': '🟠'}
    return             {'label': 'Full / Very Busy',     'colour': '#e74c3c', 'emoji': '🔴'}

def _get_zone_type(zone_id):
    try:
        from data.parking_data import get_zone_by_id
        z = get_zone_by_id(zone_id)
        return z.get('restriction_type', 'unknown') if z else 'unknown'
    except Exception:
        return 'unknown'

def predict_availability(zone_id, hour=None, weekday=None):
    if hour    is None: hour    = datetime.now().hour
    if weekday is None: weekday = datetime.now().weekday()

    zone_type     = _get_zone_type(zone_id)
    zone_type_enc = ZONE_TYPE_MAP.get(zone_type, 1)
    occupancy     = None
    method        = 'heuristic'

    # Try sklearn (lazy load)
    _load_model()
    if _sklearn_model is not None:
        try:
            import numpy as np
            X = np.array([[hour, weekday, zone_type_enc]])
            occupancy = float(_sklearn_model.predict(X)[0])
            method = 'gbr'
        except Exception:
            occupancy = None

    if occupancy is None:
        occupancy = _heuristic(hour, weekday, zone_type)

    occupancy  = min(max(occupancy, 0.0), 1.0)
    label_info = occupancy_to_label(occupancy)

    return {
        'zone_id':            zone_id,
        'hour':               hour,
        'weekday':            weekday,
        'occupancy':          round(occupancy, 3),
        'availability_label': label_info['label'],
        'colour':             label_info['colour'],
        'emoji':              label_info['emoji'],
        'confidence':         'medium' if method == 'gbr' else 'low',
        'method':             method,
    }
