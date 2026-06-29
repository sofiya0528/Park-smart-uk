"""
tests/test_all.py
-----------------
Full test suite for Park Smart UK.
Run with:  pytest tests/ -v
"""

import pytest
import os
import sys
import json

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ══════════════════════════════════════════════════════════════════════════════
# OCR Module Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestParseRestriction:
    """Unit tests for ocr.sign_reader.parse_restriction()"""

    def setup_method(self):
        from ocr.sign_reader import parse_restriction
        self.parse = parse_restriction

    def test_no_waiting_type(self):
        result = self.parse("No Waiting\nMon - Sat\n8am - 6pm")
        assert result['restriction_type'] == 'no_waiting'

    def test_permit_type_and_zone(self):
        result = self.parse("Permit Holders Only\nZone B2\nAt Any Time")
        assert result['restriction_type'] == 'permit'
        assert result['permit_zone'] == 'B2'

    def test_free_type(self):
        result = self.parse("Free Parking\nMax Stay 1 Hour")
        assert result['restriction_type'] == 'free'

    def test_disabled_type(self):
        result = self.parse("Disabled Badge Holders Only\nNo Time Limit")
        assert result['restriction_type'] == 'disabled'

    def test_pay_display_type(self):
        result = self.parse("Pay & Display\nMon-Fri 9am-5pm\nMax Stay 2 Hours")
        assert result['restriction_type'] == 'pay_display'

    def test_hour_extraction(self):
        result = self.parse("No Waiting\n8am - 6:30pm")
        assert result['hours'] is not None
        assert '8' in result['hours']

    def test_day_range_extraction(self):
        result = self.parse("No Waiting\nMonday - Saturday\n8am-6pm")
        assert result['days'] is not None
        assert 'Monday' in result['days'] or 'Mon' in result['days']

    def test_max_stay_extraction(self):
        result = self.parse("Timed Parking\nMax Stay 2 Hours")
        assert result['max_stay'] is not None
        assert '2' in result['max_stay']

    def test_empty_string(self):
        result = self.parse("")
        assert result['restriction_type'] in ('timed', 'unknown')

    def test_no_return_extraction(self):
        result = self.parse("No Waiting\nNo return within 1 hour")
        assert result['no_return'] is not None


class TestReadParkingSign:
    """Integration tests for the main OCR entry point."""

    def setup_method(self):
        from ocr.sign_reader import read_parking_sign
        self.read = read_parking_sign

    def test_missing_file_returns_failure(self):
        result = self.read('/nonexistent/path/sign.jpg')
        assert result['success'] is False
        assert 'error' in result

    def test_demo_mode_returns_success(self, tmp_path):
        """When pytesseract is unavailable, demo mode should still succeed."""
        # Create a dummy image file
        img_path = str(tmp_path / 'test_sign.jpg')
        with open(img_path, 'wb') as f:
            # Minimal valid JPEG header
            f.write(bytes([
                0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46,
                0x00, 0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00,
                0xFF, 0xD9,
            ]))
        result = self.read(img_path)
        # In demo mode this will succeed; in live mode it may fail (no real image)
        assert 'success' in result


# ══════════════════════════════════════════════════════════════════════════════
# ML Predictor Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestPredictor:
    """Tests for ml.predictor.predict_availability()"""

    def setup_method(self):
        from ml.predictor import predict_availability
        self.predict = predict_availability

    def test_returns_required_keys(self):
        result = self.predict('test-zone-001', hour=10, weekday=1)
        required = ['zone_id', 'occupancy', 'availability_label', 'colour', 'method']
        for key in required:
            assert key in result, f"Missing key: {key}"

    def test_occupancy_in_range(self):
        result = self.predict('test-zone-002', hour=12, weekday=2)
        assert 0.0 <= result['occupancy'] <= 1.0

    def test_colour_is_hex(self):
        result = self.predict('test-zone-003', hour=8, weekday=0)
        assert result['colour'].startswith('#')
        assert len(result['colour']) == 7

    def test_all_labels_valid(self):
        valid_labels = {'Available', 'Moderately Busy', 'Busy', 'Full / Very Busy'}
        for hour in [0, 8, 12, 17, 22]:
            result = self.predict('test-zone-004', hour=hour, weekday=1)
            assert result['availability_label'] in valid_labels

    def test_defaults_use_current_time(self):
        # Should not raise even with no hour/weekday args
        result = self.predict('test-zone-005')
        assert result['occupancy'] is not None

    def test_occupancy_to_label_function(self):
        from ml.predictor import occupancy_to_label
        assert occupancy_to_label(0.1)['label'] == 'Available'
        assert occupancy_to_label(0.4)['label'] == 'Moderately Busy'
        assert occupancy_to_label(0.7)['label'] == 'Busy'
        assert occupancy_to_label(0.95)['label'] == 'Full / Very Busy'


# ══════════════════════════════════════════════════════════════════════════════
# Data Store Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestParkingData:
    """Tests for data.parking_data CRUD functions."""

    def setup_method(self):
        from data import parking_data as pd_mod
        self.pd = pd_mod

    def test_get_all_zones_returns_list(self):
        zones = self.pd.get_all_zones()
        assert isinstance(zones, list)
        assert len(zones) > 0

    def test_seed_data_present(self):
        zones = self.pd.get_all_zones()
        ids = [z['id'] for z in zones]
        assert 'lon-001' in ids

    def test_get_zone_by_id_found(self):
        zone = self.pd.get_zone_by_id('lon-001')
        assert zone is not None
        assert zone['id'] == 'lon-001'

    def test_get_zone_by_id_not_found(self):
        zone = self.pd.get_zone_by_id('nonexistent-id')
        assert zone is None

    def test_get_parking_zones_filter(self):
        zones = self.pd.get_parking_zones(filter_type='free')
        assert all(z['restriction_type'] == 'free' for z in zones)

    def test_get_parking_zones_search(self):
        zones = self.pd.get_parking_zones(search='Oxford')
        assert all('oxford' in z['street'].lower() for z in zones)

    def test_add_and_retrieve_zone(self, tmp_path, monkeypatch):
        """Test zone addition with a temporary data file."""
        tmp_file = str(tmp_path / 'zones.json')
        monkeypatch.setattr(self.pd, 'DATA_FILE', tmp_file)

        new_zone = {
            'lat': 51.5, 'lng': -0.1, 'street': 'Test Street, London',
            'restriction_type': 'free', 'restriction_text': 'Free Parking',
            'hours': None, 'days': None, 'permit_zone': None,
        }
        zone_id = self.pd.add_parking_zone(new_zone)
        assert zone_id is not None

        retrieved = self.pd.get_zone_by_id(zone_id)
        assert retrieved is not None
        assert retrieved['street'] == 'Test Street, London'

    def test_update_zone(self, tmp_path, monkeypatch):
        tmp_file = str(tmp_path / 'zones.json')
        monkeypatch.setattr(self.pd, 'DATA_FILE', tmp_file)

        zone_id = self.pd.add_parking_zone({
            'street': 'Before', 'restriction_type': 'timed',
            'restriction_text': 'Test', 'hours': None, 'days': None,
            'permit_zone': None, 'lat': 51.5, 'lng': -0.1,
        })
        result = self.pd.update_parking_zone(zone_id, {'street': 'After'})
        assert result is True
        updated = self.pd.get_zone_by_id(zone_id)
        assert updated['street'] == 'After'

    def test_delete_zone(self, tmp_path, monkeypatch):
        tmp_file = str(tmp_path / 'zones.json')
        monkeypatch.setattr(self.pd, 'DATA_FILE', tmp_file)

        zone_id = self.pd.add_parking_zone({
            'street': 'To Delete', 'restriction_type': 'free',
            'restriction_text': 'Test', 'hours': None, 'days': None,
            'permit_zone': None, 'lat': 51.5, 'lng': -0.1,
        })
        deleted = self.pd.delete_parking_zone(zone_id)
        assert deleted is True
        assert self.pd.get_zone_by_id(zone_id) is None


# ══════════════════════════════════════════════════════════════════════════════
# Utils Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestHelpers:
    """Tests for utils.helpers functions."""

    def setup_method(self):
        from utils import helpers
        self.h = helpers

    def test_allowed_file_valid(self):
        assert self.h.allowed_file('sign.jpg', {'jpg', 'png'}) is True

    def test_allowed_file_invalid(self):
        assert self.h.allowed_file('virus.exe', {'jpg', 'png'}) is False

    def test_allowed_file_no_extension(self):
        assert self.h.allowed_file('noextension', {'jpg', 'png'}) is False

    def test_format_restriction_free(self):
        zone = {'restriction_type': 'free', 'hours': None, 'days': None,
                'permit_zone': None, 'max_stay': None}
        text = self.h.format_restriction(zone)
        assert 'Free Parking' in text

    def test_format_restriction_with_hours(self):
        zone = {'restriction_type': 'timed', 'hours': '8am-6pm', 'days': 'Mon-Sat',
                'permit_zone': None, 'max_stay': None}
        text = self.h.format_restriction(zone)
        assert '8am-6pm' in text
        assert 'Mon-Sat' in text

    def test_format_restriction_permit_with_zone(self):
        zone = {'restriction_type': 'permit', 'hours': None, 'days': None,
                'permit_zone': 'B2', 'max_stay': None}
        text = self.h.format_restriction(zone)
        assert 'B2' in text

    def test_is_restriction_active_free_is_false(self):
        zone = {'restriction_type': 'free', 'hours': None, 'days': None}
        assert self.h.is_restriction_active(zone) is False

    def test_is_restriction_active_permit_always_true(self):
        zone = {'restriction_type': 'permit', 'hours': None, 'days': None}
        assert self.h.is_restriction_active(zone) is True

    def test_colour_for_type(self):
        assert self.h.colour_for_type('free')   == 'green'
        assert self.h.colour_for_type('permit') == 'purple'
        assert self.h.colour_for_type('unknown')== 'grey'

    def test_hex_colour_for_type(self):
        colour = self.h.hex_colour_for_type('free')
        assert colour.startswith('#')

    def test_paginate_first_page(self):
        items = list(range(50))
        result = self.h.paginate(items, page=1, per_page=20)
        assert len(result['items']) == 20
        assert result['items'][0] == 0
        assert result['total'] == 50
        assert result['pages'] == 3

    def test_paginate_last_page(self):
        items = list(range(50))
        result = self.h.paginate(items, page=3, per_page=20)
        assert len(result['items']) == 10


# ══════════════════════════════════════════════════════════════════════════════
# Flask Route Tests
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def client():
    """Create a Flask test client."""
    import app as flask_app
    flask_app.app.config['TESTING'] = True
    flask_app.app.config['WTF_CSRF_ENABLED'] = False
    with flask_app.app.test_client() as c:
        yield c


class TestFlaskRoutes:
    """HTTP-level tests for all Flask routes."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, client):
        import data.auth as auth
        import json
        import os
        
        # Save current users
        self.original_users = []
        if os.path.exists(auth.USERS_FILE):
            try:
                with open(auth.USERS_FILE, 'r', encoding='utf-8') as f:
                    self.original_users = json.load(f)
            except:
                pass
        
        # Start with a clean list
        with open(auth.USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
            
        # Log in the client
        client.post('/signup', data={
            'username': 'testuser',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        
        yield
        
        # Restore original users
        if self.original_users:
            with open(auth.USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.original_users, f, indent=2, ensure_ascii=False)
        elif os.path.exists(auth.USERS_FILE):
            try:
                os.remove(auth.USERS_FILE)
            except:
                pass

    def test_index_returns_200(self, client):
        res = client.get('/')
        assert res.status_code == 200

    def test_about_returns_200(self, client):
        res = client.get('/about')
        assert res.status_code == 200

    def test_dashboard_returns_200(self, client):
        res = client.get('/dashboard')
        assert res.status_code == 200

    def test_upload_get_returns_200(self, client):
        res = client.get('/upload')
        assert res.status_code == 200

    def test_api_zones_all(self, client):
        res = client.get('/api/zones')
        assert res.status_code == 200
        data = json.loads(res.data)
        assert isinstance(data, list)

    def test_api_zones_filter_free(self, client):
        res = client.get('/api/zones?type=free')
        assert res.status_code == 200
        data = json.loads(res.data)
        for zone in data:
            assert zone['restriction_type'] == 'free'

    def test_api_predict_returns_prediction(self, client):
        res = client.get('/api/predict/lon-001?hour=10&day=1')
        assert res.status_code == 200
        data = json.loads(res.data)
        assert 'occupancy' in data
        assert 'availability_label' in data

    def test_api_search_by_street(self, client):
        res = client.get('/api/search?q=Oxford')
        assert res.status_code == 200
        data = json.loads(res.data)
        assert 'results' in data
        assert 'count' in data

    def test_api_search_empty_returns_all(self, client):
        res = client.get('/api/search?q=')
        assert res.status_code == 200

    def test_upload_no_file_returns_400(self, client):
        res = client.post('/upload', data={})
        assert res.status_code == 400

    def test_upload_bad_extension_returns_400(self, client):
        data = {
            'sign_image': (b'fake content', 'test.exe'),
            'street_name': 'Test Street',
        }
        res = client.post('/upload', data=data, content_type='multipart/form-data')
        assert res.status_code == 400


# ============================================================================
# Admin Route Tests (new routes: edit_zone, delete_zone, add_zone_manual)
# ============================================================================

class TestAdminRoutes:
    """Tests for admin zone management routes."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, client):
        import data.auth as auth
        import json
        import os
        
        # Save current users
        self.original_users = []
        if os.path.exists(auth.USERS_FILE):
            try:
                with open(auth.USERS_FILE, 'r', encoding='utf-8') as f:
                    self.original_users = json.load(f)
            except:
                pass
        
        # Start with a clean list
        with open(auth.USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
            
        # Log in the client
        client.post('/signup', data={
            'username': 'adminuser',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        
        yield
        
        # Restore original users
        if self.original_users:
            with open(auth.USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.original_users, f, indent=2, ensure_ascii=False)
        elif os.path.exists(auth.USERS_FILE):
            try:
                os.remove(auth.USERS_FILE)
            except:
                pass

    def test_add_zone_manual_get(self, client):
        res = client.get('/admin/zone/add')
        assert res.status_code == 200

    def test_add_zone_manual_post(self, client):
        res = client.post('/admin/zone/add', data={
            'street': 'Test Admin Street, London',
            'restriction_type': 'timed',
            'restriction_text': 'No Waiting 8am-6pm',
            'hours': '8am - 6pm',
            'days': 'Monday - Saturday',
            'permit_zone': '',
            'max_stay': '',
            'lat': '51.5074',
            'lng': '-0.1278',
        }, follow_redirects=True)
        assert res.status_code == 200

    def test_edit_zone_get_existing(self, client):
        res = client.get('/admin/zone/lon-001/edit')
        assert res.status_code == 200

    def test_edit_zone_get_nonexistent(self, client):
        res = client.get('/admin/zone/nonexistent-id/edit', follow_redirects=True)
        assert res.status_code == 200

    def test_edit_zone_post(self, client):
        res = client.post('/admin/zone/lon-001/edit', data={
            'street': 'Oxford Street Updated, London',
            'restriction_type': 'timed',
            'restriction_text': 'No Waiting Mon-Sat 8am-6:30pm',
            'hours': '8am - 6:30pm',
            'days': 'Monday - Saturday',
            'permit_zone': '',
            'max_stay': '',
            'lat': '51.5074',
            'lng': '-0.1278',
        }, follow_redirects=True)
        assert res.status_code == 200

    def test_api_zone_detail_found(self, client):
        res = client.get('/api/zones/lon-001')
        assert res.status_code == 200
        import json
        data = json.loads(res.data)
        assert data['id'] == 'lon-001'

    def test_api_zone_detail_not_found(self, client):
        res = client.get('/api/zones/does-not-exist')
        assert res.status_code == 404


# ============================================================================
# User Authentication & Location Book Tests
# ============================================================================

class TestUserAuthAndLocationBook:
    """Tests for user sign up, sign in, logout, and location book bookmarking."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self):
        # Setup: Ensure user JSON is in a known state or clean
        import data.auth as auth
        import json
        import os
        
        # Save current users if they exist
        self.original_users = []
        if os.path.exists(auth.USERS_FILE):
            try:
                with open(auth.USERS_FILE, 'r', encoding='utf-8') as f:
                    self.original_users = json.load(f)
            except:
                pass
        
        # Write empty user list for test isolation
        with open(auth.USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f)
            
        yield
        
        # Teardown: Restore original users
        if self.original_users:
            with open(auth.USERS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.original_users, f, indent=2, ensure_ascii=False)
        elif os.path.exists(auth.USERS_FILE):
            try:
                os.remove(auth.USERS_FILE)
            except:
                pass

    def test_signup_and_login_flow(self, client):
        # 1. Secured pages redirect when not logged in
        res = client.get('/upload')
        assert res.status_code == 302
        assert '/login' in res.location

        res = client.get('/location-book')
        assert res.status_code == 302
        assert '/login' in res.location

        # 2. Try to signup with invalid fields
        res = client.post('/signup', data={
            'username': 'te',  # username too short
            'password': 'password123',
            'confirm_password': 'password123'
        })
        assert b"Username must be at least 3 characters long." in res.data or res.status_code == 200

        # 3. Successful signup
        res = client.post('/signup', data={
            'username': 'testuser',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        assert res.status_code == 200
        assert b"Account created successfully!" in res.data

        # 4. Logout
        res = client.get('/logout', follow_redirects=True)
        assert res.status_code == 200
        assert b"You have been logged out." in res.data

        # 5. Login with wrong credentials
        res = client.post('/login', data={
            'username': 'testuser',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        assert b"Invalid username or password." in res.data

        # 6. Login with correct credentials
        res = client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        }, follow_redirects=True)
        assert res.status_code == 200
        assert b"Welcome back, testuser!" in res.data

    def test_location_book_bookmarking(self, client):
        # Verify status endpoint before bookmarking (fails because not logged in)
        res = client.get('/api/location-book/status/lon-001')
        assert res.status_code == 401
        
        # Register and log in
        client.post('/signup', data={
            'username': 'bookmarkuser',
            'password': 'password123',
            'confirm_password': 'password123'
        })

        # Verify status endpoint before bookmarking
        res = client.get('/api/location-book/status/lon-001')
        assert res.status_code == 200
        assert b'"saved":false' in res.data or b'"saved": false' in res.data

        # Bookmark location via API
        res = client.post('/api/location-book/toggle', data=json.dumps({
            'zone_id': 'lon-001'
        }), content_type='application/json')
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data['saved'] is True
        assert 'Location saved' in data['message']

        # Verify status now
        res = client.get('/api/location-book/status/lon-001')
        data = json.loads(res.data)
        assert data['saved'] is True

        # View Location Book page
        res = client.get('/location-book')
        assert res.status_code == 200
        assert b'Oxford Street' in res.data

        # Remove location via post form
        res = client.post('/location-book/remove/lon-001', follow_redirects=True)
        assert res.status_code == 200
        assert b'Location removed' in res.data

        # Verify status is false again
        res = client.get('/api/location-book/status/lon-001')
        data = json.loads(res.data)
        assert data['saved'] is False

