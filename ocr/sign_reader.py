"""
ocr/sign_reader.py
------------------
Uses OpenCV for image pre-processing and Tesseract OCR to extract text
from UK parking sign images. Parses the extracted text into structured
restriction data (type, hours, days, permit zone).
"""

import re
import os
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# Try importing pytesseract; fall back gracefully if not installed
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("[WARN] pytesseract not installed — OCR will use demo mode.")


# ── Constants ──────────────────────────────────────────────────────────────────

UK_DAYS = {
    'mon': 'Monday', 'tue': 'Tuesday', 'wed': 'Wednesday',
    'thu': 'Thursday', 'fri': 'Friday', 'sat': 'Saturday', 'sun': 'Sunday',
    'monday': 'Monday', 'tuesday': 'Tuesday', 'wednesday': 'Wednesday',
    'thursday': 'Thursday', 'friday': 'Friday', 'saturday': 'Saturday', 'sunday': 'Sunday',
}

TIME_PATTERN = re.compile(r'(\d{1,2}(?::\d{2})?)\s*(?:am|pm|AM|PM)?', re.IGNORECASE)
DAY_PATTERN = re.compile(
    r'(Mon(?:day)?|Tue(?:sday)?|Wed(?:nesday)?|Thu(?:rsday)?|Fri(?:day)?|Sat(?:urday)?|Sun(?:day)?)',
    re.IGNORECASE,
)
HOUR_RANGE_PATTERN = re.compile(
    r'(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s*[-–]\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)',
    re.IGNORECASE,
)
PERMIT_PATTERN = re.compile(r'permit\s*(?:holders?\s*)?(?:only\s*)?zone\s*([A-Z0-9]+)|zone\s*([A-Z0-9]+)', re.IGNORECASE)
NO_WAITING_PATTERN = re.compile(r'no\s+waiting', re.IGNORECASE)
NO_RETURN_PATTERN = re.compile(r'no\s+return\s+within\s+(\d+)\s*(?:hour|hr)', re.IGNORECASE)
LIMITED_WAITING_PATTERN = re.compile(r'(\d+)\s*(?:min(?:utes?)?|hour(?:s?)|hr)', re.IGNORECASE)
FREE_PATTERN = re.compile(r'\bfree\b', re.IGNORECASE)
DISABLED_PATTERN = re.compile(r'disabled|blue\s*badge', re.IGNORECASE)


# ── Image Pre-processing ───────────────────────────────────────────────────────

def preprocess_image(image_path: str) -> np.ndarray:
    """
    Apply a standard pipeline to improve OCR accuracy on parking signs:
    1. Convert to grayscale
    2. Resize if small
    3. Denoise
    4. Adaptive threshold (handles uneven lighting / yellow signs)
    5. Dilate to connect character strokes
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot open image: {image_path}")

    # Resize: OCR works best on images ~300 DPI (roughly 1000px wide minimum)
    h, w = img.shape[:2]
    if w < 1000:
        scale = 1000 / w
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

    # Greyscale
    grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Denoise
    denoised = cv2.fastNlMeansDenoising(grey, h=10, templateWindowSize=7, searchWindowSize=21)

    # Adaptive threshold — works well on yellow/white UK signs
    thresh = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=10,
    )

    # Dilate slightly to close gaps in letters
    kernel = np.ones((1, 1), np.uint8)
    processed = cv2.dilate(thresh, kernel, iterations=1)

    return processed


def detect_sign_region(image_path: str) -> np.ndarray:
    """
    Attempt to isolate the rectangular sign region from the photo using
    contour detection. Falls back to the full pre-processed image if no
    clear rectangle is found.
    """
    img = cv2.imread(image_path)
    if img is None:
        return preprocess_image(image_path)

    grey = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(grey, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    for cnt in contours[:5]:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4:  # Rectangular sign found
            x, y, w, h = cv2.boundingRect(approx)
            if w > 100 and h > 50:  # Minimum size filter
                cropped = img[y:y + h, x:x + w]
                grey_crop = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
                return cv2.adaptiveThreshold(
                    grey_crop, 255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY, 31, 10,
                )

    return preprocess_image(image_path)


# ── Text Extraction ────────────────────────────────────────────────────────────

def extract_text(image_path: str) -> str:
    """Run Tesseract OCR on a pre-processed image. Returns raw text."""
    if not TESSERACT_AVAILABLE:
        # Demo mode — return plausible sample text for development
        return _demo_text(image_path)

    processed = detect_sign_region(image_path)
    config = r'--oem 3 --psm 6 -l eng'
    text = pytesseract.image_to_string(processed, config=config)
    return text.strip()


def _demo_text(image_path: str) -> str:
    """Return deterministic demo OCR text based on filename hash."""
    seed = sum(ord(c) for c in os.path.basename(image_path)) % 5
    samples = [
        "No waiting\nMon - Sat\n8 am - 6 pm",
        "Permit Holders Only\nZone B2\nAt Any Time",
        "Pay & Display\nMon-Fri 9am-5pm\nMax Stay 2 Hours",
        "Disabled Badge Holders\nOnly\nNo Time Limit",
        "Free Parking\nMax Stay 1 Hour\nReturn after 1 Hour",
    ]
    return samples[seed]


# ── Text Parsing ───────────────────────────────────────────────────────────────

def parse_restriction(raw_text: str) -> dict:
    """
    Parse raw OCR text into a structured restriction dictionary.
    Returns: restriction_type, restriction_text, hours, days, permit_zone
    """
    text_lower = raw_text.lower()
    result = {
        'restriction_type': 'unknown',
        'restriction_text': raw_text.strip(),
        'hours': None,
        'days': None,
        'permit_zone': None,
        'max_stay': None,
        'no_return': None,
    }

    # ── Determine restriction type ─────────────────────────────────────────────
    if DISABLED_PATTERN.search(raw_text):
        result['restriction_type'] = 'disabled'

    elif PERMIT_PATTERN.search(raw_text):
        result['restriction_type'] = 'permit'
        m = PERMIT_PATTERN.search(raw_text)
        if m:
            result['permit_zone'] = (m.group(1) or m.group(2)).upper()

    elif FREE_PATTERN.search(raw_text) and 'pay' not in text_lower:
        result['restriction_type'] = 'free'

    elif NO_WAITING_PATTERN.search(raw_text):
        result['restriction_type'] = 'no_waiting'

    elif 'pay' in text_lower or 'display' in text_lower:
        result['restriction_type'] = 'pay_display'

    elif LIMITED_WAITING_PATTERN.search(raw_text):
        result['restriction_type'] = 'timed'

    else:
        result['restriction_type'] = 'timed'

    # ── Extract hour range ─────────────────────────────────────────────────────
    hour_match = HOUR_RANGE_PATTERN.search(raw_text)
    if hour_match:
        result['hours'] = f"{hour_match.group(1).strip()} - {hour_match.group(2).strip()}"

    # ── Extract days ───────────────────────────────────────────────────────────
    days_found = DAY_PATTERN.findall(raw_text)
    if days_found:
        if len(days_found) >= 2:
            result['days'] = f"{days_found[0]} - {days_found[-1]}"
        else:
            result['days'] = days_found[0]

    # ── Max stay ───────────────────────────────────────────────────────────────
    stay_match = LIMITED_WAITING_PATTERN.search(raw_text)
    if stay_match:
        result['max_stay'] = stay_match.group(0).strip()

    # ── No return period ───────────────────────────────────────────────────────
    no_return_match = NO_RETURN_PATTERN.search(raw_text)
    if no_return_match:
        result['no_return'] = f"No return within {no_return_match.group(1)} hours"

    return result


# ── Public API ─────────────────────────────────────────────────────────────────

def read_parking_sign(image_path: str) -> dict:
    """
    Main entry point. Accepts a path to a parking sign image and returns
    a structured result dict with success flag and parsed restriction data.
    """
    try:
        raw_text = extract_text(image_path)
        if not raw_text:
            return {'success': False, 'raw_text': '', 'error': 'No text extracted from image'}

        parsed = parse_restriction(raw_text)
        return {
            'success': True,
            'raw_text': raw_text,
            **parsed,
        }
    except FileNotFoundError as e:
        return {'success': False, 'error': str(e), 'raw_text': ''}
    except Exception as e:
        return {'success': False, 'error': f'Unexpected error: {e}', 'raw_text': ''}
