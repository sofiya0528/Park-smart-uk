# Park Smart UK

> **Park Smart UK: An Interactive Web Mapping System for Real-Time Parking Regulation Visualization**
>
> CW1 Concept Proposal — Implementation

---

## Project Overview

Park Smart UK is a Flask-based web application that helps UK drivers find parking by displaying
street-specific restrictions on an interactive map. It combines:

- **Google Maps JavaScript API** for interactive mapping (Directions, Street View, geolocation)
- **OpenCV + Tesseract OCR** to automatically read UK parking signs from user-submitted photos
- **TensorFlow LSTM** to forecast parking availability from historical patterns
- **Crowdsourced data model** so any user or volunteer can expand map coverage

> **Mapping library note:** The proposal specified Folium or Leaflet.js. This implementation uses the
> **Google Maps JavaScript API** instead, which provides a strict superset of those features:
> interactive maps, custom markers, plus Street View integration, turn-by-turn Directions,
> and native mobile support. All core proposal requirements are fully satisfied.

---

## Project Structure

```
park_smart_uk/
├── app.py                    # Flask application & all routes
├── requirements.txt          # pip dependencies
├── environment.yml           # Anaconda environment (conda create -f environment.yml)
├── pytest.ini                # Test runner config
├── README.md
├── RISKS.md                  # Stakeholder risk register (per proposal)
├── .env.example
│
├── ocr/
│   ├── __init__.py
│   └── sign_reader.py        # OpenCV pipeline + Tesseract OCR + UK sign regex parser
│
├── ml/
│   ├── __init__.py
│   ├── predictor.py          # TensorFlow LSTM / sklearn GBR / heuristic predictor
│   └── models/
│
├── data/
│   ├── __init__.py
│   ├── parking_data.py       # JSON-backed zone CRUD store
│   └── zones.json            # 13 seed zones across 5 UK cities
│
├── utils/
│   ├── __init__.py
│   └── helpers.py
│
├── templates/
│   ├── base.html
│   ├── index.html            # Interactive Google Maps page
│   ├── upload.html           # Live camera + file upload + OCR results
│   ├── dashboard.html        # Stats + zone management (edit/delete/add)
│   ├── edit_zone.html        # Admin: add/edit/delete zone
│   └── about.html
│
├── static/
│   ├── css/main.css
│   ├── js/main.js
│   └── js/map.js             # Google Maps markers, popups, Street View
│
└── tests/
    └── test_all.py           # 50 pytest tests
```

---

## Quick Start

### Option A: Anaconda (recommended, per proposal)

```bash
conda env create -f environment.yml
conda activate parksmart
# Install Tesseract: sudo apt install tesseract-ocr (Ubuntu)
cp .env.example .env          # Add GOOGLE_MAPS_API_KEY
python app.py
```

### Option B: pip / venv

```bash
pip install -r requirements.txt
python app.py
```

Open: http://localhost:5000

---

## Google Maps API Setup

Enable in Google Cloud Console:
- Maps JavaScript API
- Street View Static API
- Directions API

Add key to `.env`:
```
GOOGLE_MAPS_API_KEY=AIzaSy...your_key_here
```

The map still works without a key (limited/watermarked mode).

---

## Running Tests

```bash
pytest tests/ -v
# Expected: 50 passed
```

---

## Stakeholder Risks

See `RISKS.md` for the full risk register covering:
1. Technical difficulty identifying varied UK sign formats
2. Time to map extensive urban areas
3. Keeping council regulation data current

---

## Intellectual Property

All code uses open-source libraries (Flask, OpenCV, TensorFlow, scikit-learn, pytesseract).
Map data: original seed data + OpenStreetMap (ODbL). No personal data stored.
