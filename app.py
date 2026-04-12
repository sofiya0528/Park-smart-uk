"""
Park Smart UK - Main Flask Application
Fast startup: heavy imports (ML, OCR) loaded lazily on first use.
"""

import os
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from datetime import datetime
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

# ── App Setup ──────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config['SECRET_KEY']          = os.environ.get('SECRET_KEY', 'parksmart-uk-2024')
app.config['GOOGLE_MAPS_API_KEY'] = os.environ.get('GOOGLE_MAPS_API_KEY', '')
app.config['UPLOAD_FOLDER']       = os.path.join('static', 'images', 'uploads')
app.config['MAX_CONTENT_LENGTH']  = 16 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS']  = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# ── Lazy module loader (avoids slow imports at startup) ────────────────────────
_ocr_reader       = None
_predict_fn       = None
_parking_data_mod = None

def get_ocr():
    global _ocr_reader
    if _ocr_reader is None:
        from ocr.sign_reader import read_parking_sign
        _ocr_reader = read_parking_sign
    return _ocr_reader

def get_predictor():
    global _predict_fn
    if _predict_fn is None:
        from ml.predictor import predict_availability
        _predict_fn = predict_availability
    return _predict_fn

def get_data():
    global _parking_data_mod
    if _parking_data_mod is None:
        import data.parking_data as pd_mod
        _parking_data_mod = pd_mod
    return _parking_data_mod

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# ── Simple in-memory cache ─────────────────────────────────────────────────────
import time
_cache = {}
def cache_get(key):
    item = _cache.get(key)
    if item and time.time() - item['t'] < 30:  # 30 second TTL
        return item['v']
    return None
def cache_set(key, val):
    _cache[key] = {'v': val, 't': time.time()}

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    zones    = get_data().get_all_zones()
    gmaps_key = app.config.get('GOOGLE_MAPS_API_KEY', '')
    return render_template('index.html', zones=zones,
                           current_time=datetime.now(), gmaps_key=gmaps_key)


@app.route('/upload', methods=['GET', 'POST'])
def upload_sign():
    if request.method == 'GET':
        return render_template('upload.html')

    if 'sign_image' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file   = request.files['sign_image']
    lat    = request.form.get('latitude',    type=float)
    lng    = request.form.get('longitude',   type=float)
    street = request.form.get('street_name', 'Unknown Street')

    if not file.filename:
        return jsonify({'error': 'No file selected'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(file.filename)}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    ocr_result = get_ocr()(filepath)
    if ocr_result['success']:
        zone_data = {
            'lat': lat or 51.5074, 'lng': lng or -0.1278,
            'street': street,
            'restriction_type': ocr_result['restriction_type'],
            'restriction_text': ocr_result['restriction_text'],
            'hours': ocr_result['hours'], 'days': ocr_result['days'],
            'permit_zone': ocr_result.get('permit_zone'),
            'max_stay': ocr_result.get('max_stay'),
            'image_path': filepath,
            'submitted_at': datetime.now().isoformat(),
        }
        zone_id = get_data().add_parking_zone(zone_data)
        return jsonify({'success': True, 'message': 'Sign processed!',
                        'zone_id': zone_id, 'ocr_result': ocr_result})

    return jsonify({'success': False,
                    'message': 'Could not read sign. Please ensure it is clear and well-lit.',
                    'raw_text': ocr_result.get('raw_text', '')})


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/dashboard')
def dashboard():
    zones = get_data().get_all_zones()
    stats = {
        'total':    len(zones),
        'free':     sum(1 for z in zones if z['restriction_type'] == 'free'),
        'timed':    sum(1 for z in zones if z['restriction_type'] == 'timed'),
        'permit':   sum(1 for z in zones if z['restriction_type'] == 'permit'),
        'disabled': sum(1 for z in zones if z['restriction_type'] == 'disabled'),
        'pay':      sum(1 for z in zones if z['restriction_type'] == 'pay_display'),
    }
    return render_template('dashboard.html', stats=stats, zones=zones)


@app.route('/admin/zone/<zone_id>/edit', methods=['GET', 'POST'])
def edit_zone(zone_id):
    pd = get_data()
    zone = pd.get_zone_by_id(zone_id)
    if not zone:
        flash('Zone not found.', 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        updates = {
            'street':           request.form.get('street', zone['street']),
            'restriction_type': request.form.get('restriction_type', zone['restriction_type']),
            'restriction_text': request.form.get('restriction_text', ''),
            'hours':            request.form.get('hours') or None,
            'days':             request.form.get('days') or None,
            'permit_zone':      request.form.get('permit_zone') or None,
            'max_stay':         request.form.get('max_stay') or None,
            'lat':              float(request.form.get('lat', zone['lat'])),
            'lng':              float(request.form.get('lng', zone['lng'])),
            'updated_at':       datetime.now().isoformat(),
        }
        pd.update_parking_zone(zone_id, updates)
        flash(f'Zone updated successfully.', 'success')
        return redirect(url_for('dashboard'))
    restriction_types = ['free', 'timed', 'pay_display', 'permit', 'no_waiting', 'disabled']
    return render_template('edit_zone.html', zone=zone, restriction_types=restriction_types)


@app.route('/admin/zone/<zone_id>/delete', methods=['POST'])
def delete_zone(zone_id):
    pd = get_data()
    zone = pd.get_zone_by_id(zone_id)
    if zone:
        pd.delete_parking_zone(zone_id)
        flash(f'Zone deleted.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/admin/zone/add', methods=['GET', 'POST'])
def add_zone_manual():
    if request.method == 'POST':
        zone_data = {
            'street':           request.form.get('street', 'Unknown Street'),
            'restriction_type': request.form.get('restriction_type', 'timed'),
            'restriction_text': request.form.get('restriction_text', ''),
            'hours':            request.form.get('hours') or None,
            'days':             request.form.get('days') or None,
            'permit_zone':      request.form.get('permit_zone') or None,
            'max_stay':         request.form.get('max_stay') or None,
            'lat':              float(request.form.get('lat', 51.5074)),
            'lng':              float(request.form.get('lng', -0.1278)),
            'submitted_at':     datetime.now().isoformat(),
            'source':           'manual_admin',
        }
        zone_id = get_data().add_parking_zone(zone_data)
        flash(f'Zone added (ID: {zone_id}).', 'success')
        return redirect(url_for('dashboard'))
    restriction_types = ['free', 'timed', 'pay_display', 'permit', 'no_waiting', 'disabled']
    return render_template('edit_zone.html', zone=None, restriction_types=restriction_types)


# ── REST API ───────────────────────────────────────────────────────────────────

@app.route('/api/zones')
def api_zones():
    filter_type = request.args.get('type', 'all')
    cache_key = 'zones_' + filter_type
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)
    zones = get_data().get_parking_zones(filter_type=filter_type)
    cache_set(cache_key, zones)
    return jsonify(zones)


@app.route('/api/predict/<zone_id>')
def api_predict(zone_id):
    hour    = request.args.get('hour', datetime.now().hour,    type=int)
    weekday = request.args.get('day',  datetime.now().weekday(), type=int)
    return jsonify(get_predictor()(zone_id, hour, weekday))


@app.route('/api/search')
def api_search():
    query       = request.args.get('q', '')
    filter_type = request.args.get('type', 'all')
    zones = get_data().get_parking_zones(filter_type=filter_type, search=query)
    return jsonify({'results': zones, 'count': len(zones)})


@app.route('/api/zones/<zone_id>')
def api_zone_detail(zone_id):
    zone = get_data().get_zone_by_id(zone_id)
    if not zone:
        return jsonify({'error': 'Zone not found'}), 404
    return jsonify(zone)


# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001,
            use_reloader=True, threaded=True)
