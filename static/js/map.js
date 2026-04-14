/**
 * map.js - Park Smart UK - Enhanced Google Maps Version
 * APIs used:
 *   - Maps JavaScript API (map, markers, info windows)
 *   - Street View API (embedded panorama)
 *   - Directions API (embedded turn-by-turn route)
 *   - Places API (autocomplete search, nearby search)
 *   - Geocoding API (address lookup)
 *   - Distance Matrix API (travel time from current location)
 */

var gmap, selectedZone, infoWindow;
var markers = [], allZones = [], currentFilter = 'all';
var routeRenderer = null, userMarker = null;
var userLat = null, userLng = null;
var streetViewPanorama = null;
var autocomplete = null;
var heatmapLayer = null;
var distanceService = null;
var directionsService = null;
var directionsRenderer = null;
var placesService = null;
var navigationWatchId = null;
var navigationActive = false;
var activeDestination = null;
var activeTravelMode = 'DRIVING';
var lastDirectionsResult = null;
var lastNavigationRerouteAt = 0;
var lastNavigationOrigin = null;
var currentStepIndex = 0;

var TYPE_COLOURS = {
  free: '#27ae60', timed: '#e67e22', pay_display: '#2980b9',
  permit: '#8e44ad', no_waiting: '#e74c3c', disabled: '#16a085', unknown: '#95a5a6'
};
var TYPE_LABELS = {
  free: 'Free Parking', timed: 'Timed Restriction', pay_display: 'Pay & Display',
  permit: 'Permit Only', no_waiting: 'No Waiting', disabled: 'Disabled Bay', unknown: 'Unknown'
};
var TYPE_ICONS = {
  free: '🟢', timed: '🟠', pay_display: '🔵',
  permit: '🟣', no_waiting: '🔴', disabled: '♿', unknown: '⚪'
};

// ── Map initialise ─────────────────────────────────────────────────────────────
function initMap(lat, lng, zoom) {
  lat = lat || 54.5; lng = lng || -3.5; zoom = zoom || 6;

  gmap = new google.maps.Map(document.getElementById('map'), {
    center: { lat: lat, lng: lng },
    zoom: zoom,
    mapTypeId: 'roadmap',
    mapTypeControl: true,
    mapTypeControlOptions: {
      style: google.maps.MapTypeControlStyle.HORIZONTAL_BAR,
      position: google.maps.ControlPosition.TOP_RIGHT,
      mapTypeIds: ['roadmap', 'satellite', 'hybrid', 'terrain']
    },
    streetViewControl: false,
    fullscreenControl: true,
    zoomControl: true,
    gestureHandling: 'greedy',
    styles: [
      { featureType: 'poi.business', stylers: [{ visibility: 'off' }] },
      { featureType: 'transit', elementType: 'labels.icon', stylers: [{ visibility: 'off' }] }
    ]
  });

  infoWindow = new google.maps.InfoWindow({ maxWidth: 320 });
  directionsService = new google.maps.DirectionsService();
  directionsRenderer = new google.maps.DirectionsRenderer({
    map: gmap,
    suppressMarkers: false,
    polylineOptions: { strokeColor: '#2980b9', strokeWeight: 5, strokeOpacity: 0.8 }
  });
  distanceService = new google.maps.DistanceMatrixService();
  placesService = new google.maps.places.PlacesService(gmap);

  // Street View
  streetViewPanorama = new google.maps.StreetViewPanorama(
    document.getElementById('svPanel'), {
      visible: false, addressControl: true, linksControl: true,
      panControl: true, enableCloseButton: false,
      motionTracking: false, motionTrackingControl: false
    }
  );
  gmap.setStreetView(streetViewPanorama);

  // Places Autocomplete on search input
  var input = document.getElementById('searchInput');
  if (input && google.maps.places) {
    autocomplete = new google.maps.places.Autocomplete(input, {
      componentRestrictions: { country: 'gb' },
      fields: ['geometry', 'name', 'formatted_address']
    });
    autocomplete.addListener('place_changed', function() {
      var place = autocomplete.getPlace();
      if (place.geometry) {
        gmap.panTo(place.geometry.location);
        gmap.setZoom(15);
        searchZones();
      }
    });
  }

  // From-address autocomplete in directions
  var fromInput = document.getElementById('fromInput');
  if (fromInput && google.maps.places) {
    var fromAuto = new google.maps.places.Autocomplete(fromInput, {
      componentRestrictions: { country: 'gb' },
      fields: ['geometry', 'formatted_address', 'name']
    });
  }

  gmap.addListener('click', function() {
    infoWindow.close();
    closeDetailPanel();
  });
}

// ── Custom pin icon ────────────────────────────────────────────────────────────
function makePinIcon(colour) {
  var svg = '<svg xmlns="http://www.w3.org/2000/svg" width="34" height="48" viewBox="0 0 34 48">'
    + '<path d="M17 0C7.6 0 0 7.6 0 17c0 11.7 17 31 17 31S34 28.7 34 17C34 7.6 26.4 0 17 0z" fill="' + colour + '" stroke="white" stroke-width="2.5"/>'
    + '<circle cx="17" cy="17" r="8" fill="white" opacity="0.95"/>'
    + '</svg>';
  return {
    url: 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(svg),
    scaledSize: new google.maps.Size(34, 48),
    anchor: new google.maps.Point(17, 48)
  };
}

// ── Add marker ────────────────────────────────────────────────────────────────
function addZoneMarker(zone) {
  if (!zone.lat || !zone.lng) return;
  var colour = TYPE_COLOURS[zone.restriction_type] || TYPE_COLOURS.unknown;
  var marker = new google.maps.Marker({
    position: { lat: parseFloat(zone.lat), lng: parseFloat(zone.lng) },
    map: gmap,
    icon: makePinIcon(colour),
    title: zone.street || 'Parking Zone',
    animation: google.maps.Animation.DROP
  });
  marker.zoneData = zone;
  marker.addListener('click', function() {
    openDetailPanel(zone, marker);
  });
  markers.push(marker);
}

// ── Detail panel ──────────────────────────────────────────────────────────────
async function openDetailPanel(zone, marker) {
  stopLiveNavigation();
  selectedZone = zone;
  var colour = TYPE_COLOURS[zone.restriction_type] || TYPE_COLOURS.unknown;
  var label  = TYPE_LABELS[zone.restriction_type]  || 'Unknown';
  var icon   = TYPE_ICONS[zone.restriction_type]   || '⚪';

  document.getElementById('detailPanel').style.display = 'flex';
  document.getElementById('dpTitle').textContent = zone.street || 'Unknown Street';
  document.getElementById('dpBadge').textContent = icon + ' ' + label;
  document.getElementById('dpBadge').style.background  = colour + '22';
  document.getElementById('dpBadge').style.color       = colour;
  document.getElementById('dpBadge').style.borderColor = colour + '44';

  // Restriction details
  var rows = '';
  if (zone.hours)            rows += detailRow('🕐', 'Hours', zone.hours);
  if (zone.days)             rows += detailRow('📅', 'Days', zone.days);
  if (zone.permit_zone)      rows += detailRow('🪪', 'Permit Zone', zone.permit_zone);
  if (zone.max_stay)         rows += detailRow('⏱', 'Max Stay', zone.max_stay);
  if (zone.restriction_text) rows += detailRow('📋', 'Sign Text', zone.restriction_text);
  document.getElementById('dpDetails').innerHTML = rows || '<p style="color:#95a5a6;font-size:13px;">No additional details</p>';

  // Reset panels
  document.getElementById('dpAvail').innerHTML = '<span style="color:#95a5a6;font-size:13px;">⏳ Loading forecast...</span>';
  document.getElementById('directionsResult').style.display = 'none';
  document.getElementById('directionsForm').style.display = 'block';
  document.getElementById('fromInput').value = '';
  document.getElementById('dirDest').textContent = '🏁 To: ' + (zone.street || 'Parking Zone');
  hideSV();

  // Nearby parking (Places API)
  loadNearbyPlaces(zone);

  // Fetch ML prediction
  var pred = await apiFetch('/api/predict/' + encodeURIComponent(zone.id));
  if (pred) {
    document.getElementById('dpAvail').innerHTML =
      '<div style="background:' + pred.colour + '18;border:1px solid ' + pred.colour + '44;border-radius:8px;padding:10px 12px;">'
      + '<div style="font-size:16px;font-weight:700;color:' + pred.colour + ';">' + pred.emoji + ' ' + pred.availability_label + '</div>'
      + '<div style="font-size:12px;color:#7f8c8d;margin-top:4px;">'
      + Math.round(pred.occupancy * 100) + '% estimated occupancy &nbsp;·&nbsp; ' + pred.method + ' model'
      + '</div></div>';
  }

  // If user location known, get Distance Matrix
  if (userLat && userLng) {
    distanceService.getDistanceMatrix({
      origins: [new google.maps.LatLng(userLat, userLng)],
      destinations: [new google.maps.LatLng(parseFloat(zone.lat), parseFloat(zone.lng))],
      travelMode: google.maps.TravelMode.DRIVING,
      unitSystem: google.maps.UnitSystem.METRIC
    }, function(resp, status) {
      if (status === 'OK' && resp.rows[0].elements[0].status === 'OK') {
        var el = resp.rows[0].elements[0];
        var distEl = document.getElementById('dpDistance');
        if (distEl) {
          distEl.innerHTML = '🚗 ' + el.distance.text + ' &nbsp;·&nbsp; 🕐 ' + el.duration.text + ' from your location';
          distEl.style.display = 'block';
        }
      }
    });
  }

  gmap.panTo({ lat: parseFloat(zone.lat), lng: parseFloat(zone.lng) });
}

// ── Nearby places using Google Places API ─────────────────────────────────────
function loadNearbyPlaces(zone) {
  if (!placesService) return;
  var nearbyEl = document.getElementById('dpNearby');
  if (!nearbyEl) return;
  nearbyEl.innerHTML = '<span style="color:#95a5a6;font-size:12px;">Searching nearby...</span>';

  placesService.nearbySearch({
    location: new google.maps.LatLng(parseFloat(zone.lat), parseFloat(zone.lng)),
    radius: 200,
    type: 'parking'
  }, function(results, status) {
    if (status === google.maps.places.PlacesServiceStatus.OK && results.length > 0) {
      var count = results.length;
      nearbyEl.innerHTML = '<span style="font-size:12px;color:#2980b9;">📍 ' + count + ' parking area' + (count !== 1 ? 's' : '') + ' within 200m</span>';
    } else {
      var nearby = allZones.filter(function(z) {
        if (z.id === zone.id) return false;
        var dlat = parseFloat(z.lat) - parseFloat(zone.lat);
        var dlng = parseFloat(z.lng) - parseFloat(zone.lng);
        return Math.sqrt(dlat*dlat + dlng*dlng) < 0.02;
      });
      nearbyEl.innerHTML = '<span style="font-size:12px;color:#7f8c8d;">📍 ' + nearby.length + ' other zone' + (nearby.length !== 1 ? 's' : '') + ' nearby</span>';
    }
  });
}

function detailRow(icon, label, value) {
  return '<div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid #f5f6f8;">'
    + '<span style="font-size:16px;flex-shrink:0;">' + icon + '</span>'
    + '<div><div style="font-size:10px;color:#95a5a6;font-weight:700;text-transform:uppercase;letter-spacing:.05em;">' + label + '</div>'
    + '<div style="font-size:13px;color:#2c3e50;font-weight:500;margin-top:2px;">' + escHtml(value) + '</div></div></div>';
}

function closeDetailPanel() {
  document.getElementById('detailPanel').style.display = 'none';
  selectedZone = null;
  if (directionsRenderer) directionsRenderer.setDirections({ routes: [] });
  stopLiveNavigation();
  hideSV();
}

// ── EMBEDDED GOOGLE MAPS DIRECTIONS (no redirect) ─────────────────────────────
function getDirections() {
  if (!selectedZone) return;
  var fromVal = document.getElementById('fromInput').value.trim();
  if (!fromVal) { alert('Please enter a starting point or click 📍 to use your location.'); return; }

  var btn = document.getElementById('dirBtn');
  btn.textContent = 'Calculating...'; btn.disabled = true;

  var dest = new google.maps.LatLng(parseFloat(selectedZone.lat), parseFloat(selectedZone.lng));
  var origin;

  if (fromVal.startsWith('📍 My Location') && userLat && userLng) {
    origin = new google.maps.LatLng(userLat, userLng);
    computeRoute(origin, dest, btn, {
      originLabel: 'My Location',
      fromLiveLocation: true,
      keepNavigation: false
    });
  } else {
    var geocoder = new google.maps.Geocoder();
    geocoder.geocode({ address: fromVal, region: 'gb' }, function(results, status) {
      if (status === 'OK' && results[0]) {
        origin = results[0].geometry.location;
        computeRoute(origin, dest, btn, {
          originLabel: results[0].formatted_address || fromVal,
          fromLiveLocation: false,
          keepNavigation: false
        });
      } else {
        alert('Could not find that location. Try a postcode or full street address.');
        btn.textContent = 'Get Directions'; btn.disabled = false;
      }
    });
  }
}

function computeRoute(origin, dest, btn, options) {
  options = options || {};
  var travelMode = options.travelMode || (document.getElementById('travelMode') ? document.getElementById('travelMode').value : 'DRIVING');
  directionsService.route({
    origin: origin,
    destination: dest,
    travelMode: google.maps.TravelMode[travelMode],
    unitSystem: google.maps.UnitSystem.METRIC,
    avoidHighways: false,
    avoidTolls: false
  }, function(result, status) {
    btn.textContent = 'Get Directions'; btn.disabled = false;
    if (status === 'OK') {
      directionsRenderer.setDirections(result);
      lastDirectionsResult = result;
      activeDestination = dest;
      activeTravelMode = travelMode;
      showDirectionsResult(result, travelMode, options.originLabel, options.fromLiveLocation);
      if (navigationActive || options.keepNavigation) {
        updateLiveNavigationUi(result);
      } else {
        hideLiveNavigationCard();
      }
    } else {
      document.getElementById('directionsResult').style.display = 'block';
      document.getElementById('directionsResult').innerHTML =
        '<div style="background:#fdedec;padding:10px;border-radius:8px;color:#e74c3c;font-size:13px;">⚠️ No route found. Try a different start point.</div>';
    }
  });
}

function showDirectionsResult(result, mode, originLabel, fromLiveLocation) {
  var leg = result.routes[0].legs[0];
  document.getElementById('directionsForm').style.display = 'none';
  var modeIcon = { DRIVING: '🚗', WALKING: '🚶', BICYCLING: '🚲', TRANSIT: '🚌' };
  var el = document.getElementById('directionsResult');
  el.style.display = 'block';

  var stepsHtml = leg.steps.map(function(s) {
    var inst = s.instructions.replace(/<[^>]+>/g, '');
    var dist = s.distance ? s.distance.text : '';
    return '<div style="display:flex;gap:8px;padding:6px 0;border-bottom:1px solid #f5f6f8;font-size:12px;">'
      + '<span style="color:#2980b9;flex-shrink:0;">→</span>'
      + '<div><div style="color:#2c3e50;">' + inst + '</div>'
      + (dist ? '<div style="color:#95a5a6;margin-top:1px;">' + dist + '</div>' : '')
      + '</div></div>';
  }).join('');

  el.innerHTML =
    '<div style="display:flex;gap:8px;margin-bottom:10px;">'
    + '<div style="flex:1;background:#eaf4fb;border-radius:8px;padding:10px;text-align:center;">'
    + '<div style="font-size:20px;font-weight:700;color:#2980b9;">' + leg.distance.text + '</div>'
    + '<div style="font-size:11px;color:#7f8c8d;">Distance</div></div>'
    + '<div style="flex:1;background:#eafaf1;border-radius:8px;padding:10px;text-align:center;">'
    + '<div style="font-size:20px;font-weight:700;color:#27ae60;">' + leg.duration.text + '</div>'
    + '<div style="font-size:11px;color:#7f8c8d;">' + (modeIcon[mode] || '🚗') + ' Travel time</div></div>'
    + '</div>'
    + '<div style="font-size:11px;color:#7f8c8d;margin-bottom:8px;">From: ' + escHtml(originLabel || leg.start_address) + '</div>'
    + '<div style="max-height:180px;overflow-y:auto;border:1px solid #f0f2f5;border-radius:8px;padding:6px 10px;">'
    + stepsHtml + '</div>'
    + '<div style="display:flex;gap:6px;margin-top:10px;flex-wrap:wrap;">'
    + (navigationActive
      ? '<button onclick="recenterNavigation()" style="flex:1;min-width:96px;padding:8px;border:1px solid #dbeafe;border-radius:6px;background:#dbeafe;color:#1d4ed8;cursor:pointer;font-size:12px;font-weight:700;">◎ Follow Me</button>'
      : '<button onclick="startLiveNavigation()" style="flex:1;min-width:96px;padding:8px;border:1px solid #dbeafe;border-radius:6px;background:#dbeafe;color:#1d4ed8;cursor:pointer;font-size:12px;font-weight:700;">▶ Start Live</button>')
    + '<button onclick="showDirectionsForm()" style="flex:1;min-width:96px;padding:8px;border:1px solid #dde3ea;border-radius:6px;background:#f8f9fa;cursor:pointer;font-size:12px;">← Change</button>'
    + '<button onclick="clearRoute()" style="flex:1;min-width:96px;padding:8px;border:1px solid #fdedec;border-radius:6px;background:#fdedec;color:#e74c3c;cursor:pointer;font-size:12px;">✕ Clear</button>'
    + '</div>';
}

function showDirectionsForm() {
  document.getElementById('directionsResult').style.display = 'none';
  document.getElementById('directionsForm').style.display = 'block';
}

function clearRoute() {
  if (directionsRenderer) directionsRenderer.setDirections({ routes: [] });
  lastDirectionsResult = null;
  activeDestination = null;
  stopLiveNavigation();
  showDirectionsForm();
}

function useMyLocation() {
  if (!navigator.geolocation) { alert('Geolocation not supported.'); return; }
  var btn = document.getElementById('locBtn');
  btn.textContent = '⏳'; btn.disabled = true;
  navigator.geolocation.getCurrentPosition(function(pos) {
    userLat = pos.coords.latitude; userLng = pos.coords.longitude;
    document.getElementById('fromInput').value = '📍 My Location';
    btn.textContent = '✅'; btn.disabled = false;
    if (userMarker) userMarker.setMap(null);
    userMarker = new google.maps.Marker({
      position: { lat: userLat, lng: userLng }, map: gmap,
      title: 'Your Location',
      icon: { path: google.maps.SymbolPath.CIRCLE, scale: 8, fillColor: '#3498db', fillOpacity: 1, strokeColor: '#fff', strokeWeight: 2 }
    });
  }, function() { btn.textContent = '📍'; btn.disabled = false; alert('Could not get your location.'); });
}

function startLiveNavigation() {
  if (!selectedZone) {
    showToast('Choose a parking zone first.', 'error');
    return;
  }
  if (!navigator.geolocation) {
    showToast('Geolocation is not supported in this browser.', 'error');
    return;
  }

  navigationActive = true;
  activeDestination = new google.maps.LatLng(parseFloat(selectedZone.lat), parseFloat(selectedZone.lng));
  showLiveNavigationCard('Starting', 'Getting your live position...', 'Route will switch to live guidance once GPS locks on.');

  if (navigationWatchId !== null) navigator.geolocation.clearWatch(navigationWatchId);
  navigationWatchId = navigator.geolocation.watchPosition(function(pos) {
    var movedEnough = !lastNavigationOrigin || distanceMeters(lastNavigationOrigin, pos.coords) > 20;
    userLat = pos.coords.latitude;
    userLng = pos.coords.longitude;
    updateUserMarker(userLat, userLng);

    if (gmap) {
      gmap.panTo({ lat: userLat, lng: userLng });
    }

    var now = Date.now();
    if (!movedEnough && now - lastNavigationRerouteAt < 8000 && lastDirectionsResult) {
      updateLiveNavigationUi(lastDirectionsResult);
      return;
    }

    lastNavigationOrigin = { latitude: userLat, longitude: userLng };
    lastNavigationRerouteAt = now;

    computeRoute(
      new google.maps.LatLng(userLat, userLng),
      activeDestination,
      {
        textContent: 'Live',
        disabled: true
      },
      {
        originLabel: 'My live location',
        fromLiveLocation: true,
        keepNavigation: true,
        travelMode: activeTravelMode
      }
    );
  }, function() {
    showLiveNavigationCard('GPS Error', 'Unable to track your location.', 'Allow location access in the browser to use live navigation.');
    stopLiveNavigation(false);
  }, {
    enableHighAccuracy: true,
    maximumAge: 3000,
    timeout: 10000
  });
}

function stopLiveNavigation(resetCard) {
  if (navigationWatchId !== null) {
    navigator.geolocation.clearWatch(navigationWatchId);
    navigationWatchId = null;
  }
  navigationActive = false;
  lastNavigationOrigin = null;
  lastNavigationRerouteAt = 0;
  currentStepIndex = 0;
  if (resetCard !== false) hideLiveNavigationCard();
}

function recenterNavigation() {
  if (userLat && userLng && gmap) {
    gmap.panTo({ lat: userLat, lng: userLng });
    gmap.setZoom(Math.max(gmap.getZoom(), 16));
  }
}

function updateLiveNavigationUi(result) {
  var leg = result.routes[0] && result.routes[0].legs[0];
  if (!leg) return;
  var step = getCurrentStep(leg);
  var remainingDistance = leg.distance ? leg.distance.text : 'Unknown distance';
  var remainingDuration = leg.duration ? leg.duration.text : 'Unknown time';
  var instruction = step ? stripHtml(step.instructions) : 'Continue on the current route';
  var meta = remainingDistance + ' remaining · ' + remainingDuration + ' ETA';
  var stepDistance = step && step.distance ? step.distance.text : '';
  if (stepDistance) meta += ' · next in ' + stepDistance;
  showLiveNavigationCard('Live', instruction, meta);
}

function getCurrentStep(leg) {
  if (!leg.steps || !leg.steps.length || userLat === null || userLng === null) return leg.steps && leg.steps[0];
  var userPoint = { latitude: userLat, longitude: userLng };
  for (var i = currentStepIndex; i < leg.steps.length; i++) {
    var endLoc = leg.steps[i].end_location;
    var stepEnd = { latitude: endLoc.lat(), longitude: endLoc.lng() };
    if (distanceMeters(userPoint, stepEnd) > 35) {
      currentStepIndex = i;
      return leg.steps[i];
    }
  }
  currentStepIndex = leg.steps.length - 1;
  return leg.steps[currentStepIndex];
}

function showLiveNavigationCard(status, instruction, meta) {
  var card = document.getElementById('liveNavCard');
  if (!card) return;
  card.style.display = 'block';
  document.getElementById('liveNavStatus').textContent = status;
  document.getElementById('liveNavInstruction').textContent = instruction;
  document.getElementById('liveNavMeta').textContent = meta;
}

function hideLiveNavigationCard() {
  var card = document.getElementById('liveNavCard');
  if (card) card.style.display = 'none';
}

function updateUserMarker(lat, lng) {
  if (userMarker) userMarker.setMap(null);
  userMarker = new google.maps.Marker({
    position: { lat: lat, lng: lng },
    map: gmap,
    title: 'Your Location',
    icon: {
      path: google.maps.SymbolPath.CIRCLE,
      scale: 9,
      fillColor: '#3498db',
      fillOpacity: 1,
      strokeColor: '#fff',
      strokeWeight: 2.5
    }
  });
}

// ── Google Street View (embedded, no redirect) ────────────────────────────────
function showStreetView() {
  if (!selectedZone) return;
  var svBtn = document.getElementById('svToggleBtn');
  var panel = document.getElementById('svPanel');
  if (panel.style.display === 'none' || !panel.style.display) {
    panel.style.display = 'block';
    streetViewPanorama.setPosition({ lat: parseFloat(selectedZone.lat), lng: parseFloat(selectedZone.lng) });
    streetViewPanorama.setVisible(true);
    svBtn.textContent = '✕ Close Street View';
  } else {
    hideSV();
  }
}

function hideSV() {
  var panel = document.getElementById('svPanel');
  if (panel) panel.style.display = 'none';
  if (streetViewPanorama) streetViewPanorama.setVisible(false);
  var btn = document.getElementById('svToggleBtn');
  if (btn) btn.textContent = '📷 Street View';
}

// ── Heatmap (Visualization API) ───────────────────────────────────────────────
function toggleHeatmap() {
  var btn = document.getElementById('heatmapBtn');
  if (heatmapLayer) {
    heatmapLayer.setMap(null); heatmapLayer = null;
    btn.style.background = '#fff'; btn.style.color = '#2c3e50';
    return;
  }
  var points = allZones.map(function(z) {
    return { location: new google.maps.LatLng(parseFloat(z.lat), parseFloat(z.lng)), weight: 1 };
  });
  heatmapLayer = new google.maps.visualization.HeatmapLayer({
    data: points, map: gmap,
    radius: 40, opacity: 0.7,
    gradient: ['rgba(0,255,0,0)', 'rgba(0,255,0,1)', 'rgba(255,255,0,1)', 'rgba(255,0,0,1)']
  });
  btn.style.background = '#e74c3c'; btn.style.color = '#fff';
}

// ── Load / filter / search ────────────────────────────────────────────────────
async function loadZones(filterType) {
  filterType = filterType || 'all'; currentFilter = filterType;
  markers.forEach(function(m) { m.setMap(null); }); markers = [];
  var zones = await apiFetch('/api/zones?type=' + encodeURIComponent(filterType));
  if (!zones) return;
  allZones = zones;
  zones.forEach(function(z) { addZoneMarker(z); });
  var countEl = document.getElementById('zoneCount');
  if (countEl) countEl.textContent = zones.length + ' zone' + (zones.length !== 1 ? 's' : '') + ' shown';
  updateAnalytics(zones);
  if (heatmapLayer) { heatmapLayer.setMap(null); heatmapLayer = null; toggleHeatmap(); }
}

function filterZones(type, btn) {
  document.querySelectorAll('.filter-btn').forEach(function(b) { b.classList.remove('active'); });
  if (btn) btn.classList.add('active');
  closeDetailPanel();
  loadZones(type);
}

async function searchZones() {
  var q = (document.getElementById('searchInput') ? document.getElementById('searchInput').value : '').trim();
  if (!q) { loadZones(currentFilter); return; }
  var data = await apiFetch('/api/search?q=' + encodeURIComponent(q) + '&type=' + encodeURIComponent(currentFilter));
  if (!data) return;
  markers.forEach(function(m) { m.setMap(null); }); markers = [];
  allZones = data.results;
  data.results.forEach(function(z) { addZoneMarker(z); });
  var countEl = document.getElementById('zoneCount');
  if (countEl) countEl.textContent = data.count + ' result' + (data.count !== 1 ? 's' : '') + ' for "' + q + '"';
  updateAnalytics(data.results);
  if (data.results.length > 0) {
    gmap.panTo({ lat: parseFloat(data.results[0].lat), lng: parseFloat(data.results[0].lng) });
    gmap.setZoom(14);
  }
}

function updateAnalytics(zones) {
  var counts = { free:0, timed:0, pay_display:0, permit:0, disabled:0 };
  zones.forEach(function(z) { if (counts[z.restriction_type] !== undefined) counts[z.restriction_type]++; });
  var total = zones.length || 1;
  var bars = [
    { type:'free', label:'Free', colour:'#27ae60' },
    { type:'timed', label:'Timed', colour:'#e67e22' },
    { type:'pay_display', label:'Pay & Display', colour:'#2980b9' },
    { type:'permit', label:'Permit Only', colour:'#8e44ad' },
    { type:'disabled', label:'Disabled', colour:'#16a085' }
  ];
  var html = '';
  bars.forEach(function(b) {
    var pct = Math.round((counts[b.type] / total) * 100);
    html += '<div style="margin-bottom:9px;">'
      + '<div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px;">'
      + '<span style="color:#555;font-weight:500;">' + b.label + '</span>'
      + '<span style="color:' + b.colour + ';font-weight:700;">' + counts[b.type] + '</span></div>'
      + '<div style="height:6px;background:#f0f2f5;border-radius:3px;">'
      + '<div style="height:6px;background:' + b.colour + ';border-radius:3px;width:' + pct + '%;transition:width .6s;"></div>'
      + '</div></div>';
  });
  var el = document.getElementById('analyticsBars'); if (el) el.innerHTML = html;
  var t = document.getElementById('analyticsTotal'); if (t) t.textContent = zones.length;
  var f = document.getElementById('analyticsFree'); if (f) f.textContent = counts.free;
  var d = document.getElementById('analyticsDisabled'); if (d) d.textContent = counts.disabled;
}

function locateMe() {
  if (!navigator.geolocation) { showToast('Geolocation not supported.', 'error'); return; }
  showToast('Finding your location...', 'info');
  navigator.geolocation.getCurrentPosition(function(pos) {
    userLat = pos.coords.latitude; userLng = pos.coords.longitude;
    gmap.panTo({ lat: userLat, lng: userLng }); gmap.setZoom(15);
    updateUserMarker(userLat, userLng);
    showToast('Location found!', 'success');
  }, function() { showToast('Could not get location.', 'error'); });
}

document.addEventListener('DOMContentLoaded', function() {
  var inp = document.getElementById('searchInput');
  if (inp) inp.addEventListener('keypress', function(e) { if (e.key === 'Enter') searchZones(); });
  var params = new URLSearchParams(window.location.search);
  var highlightId = params.get('highlight');
  if (highlightId) {
    loadZones('all').then(function() {
      var m = markers.find(function(mk) { return mk.zoneData && mk.zoneData.id === highlightId; });
      if (m) { gmap.panTo(m.getPosition()); gmap.setZoom(17); google.maps.event.trigger(m, 'click'); }
    });
  }
});

function escHtml(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function stripHtml(s) {
  return String(s || '').replace(/<[^>]+>/g, '').trim();
}

function distanceMeters(a, b) {
  var toRad = function(v) { return v * Math.PI / 180; };
  var lat1 = a.latitude, lng1 = a.longitude;
  var lat2 = b.latitude, lng2 = b.longitude;
  var dLat = toRad(lat2 - lat1);
  var dLng = toRad(lng2 - lng1);
  var sinLat = Math.sin(dLat / 2);
  var sinLng = Math.sin(dLng / 2);
  var aa = sinLat * sinLat
    + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * sinLng * sinLng;
  return 6371000 * 2 * Math.atan2(Math.sqrt(aa), Math.sqrt(1 - aa));
}
