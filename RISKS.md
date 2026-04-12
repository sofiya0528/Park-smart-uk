# Park Smart UK — Stakeholder Risk Register

This document maps directly to the **Stakeholder Risks** section of the CW1 Concept Proposal and
describes how each risk is identified, mitigated, and tracked within the codebase.

---

## Risk 1 — Technical Difficulty Identifying Various UK Parking Sign Formats

**Proposal reference:** *"Potential risks involve technical difficulties in identifying various UK parking sign formats"*

### Description
UK parking signs vary significantly across local councils. Common variations include:

| Format type | Example | Challenge |
|---|---|---|
| Standard yellow-on-black | "No Waiting Mon–Sat 8am–6:30pm" | Most common; OCR handles well |
| White-on-blue (disabled) | "Disabled Badge Holders Only" | High contrast — good OCR accuracy |
| Permit zone plates | "Permit Holders Only Zone B2" | Zone code parsing regex needed |
| Time-plate stacks | Multiple time plates on one post | Multi-region image detection required |
| Handwritten council notices | Rare; usually laminated A4 sheets | Very low accuracy — flagged for manual review |
| Faded / weathered signs | Any type | Pre-processing pipeline mitigates |

### Mitigation in codebase

**`ocr/sign_reader.py`** implements a 5-step pre-processing pipeline specifically tuned for UK signs:

1. **Resize** — images scaled to minimum 1000px wide (OCR accuracy degrades below ~300 DPI)
2. **Greyscale conversion** — removes colour noise (yellow/white backgrounds)
3. **Denoising** (`fastNlMeansDenoising`) — removes JPEG compression artefacts and environmental noise
4. **Adaptive thresholding** (`ADAPTIVE_THRESH_GAUSSIAN_C`) — handles uneven lighting and shadow across signs
5. **Dilation** — closes gaps in character strokes caused by weathering or fading

**Contour detection** attempts to isolate the rectangular sign region from surrounding poles,
walls, and sky before passing the cropped region to Tesseract.

**Regex parser** covers all major UK restriction formats:
- `NO_WAITING_PATTERN` — "No Waiting" / "No stopping"
- `PERMIT_PATTERN` — "Permit Holders Only Zone [code]"
- `HOUR_RANGE_PATTERN` — "8am – 6:30pm", "08:00 – 18:30"
- `DAY_PATTERN` — "Mon–Sat", "Monday to Friday"
- `LIMITED_WAITING_PATTERN` — "Max stay 2 hours", "30 minutes"
- `DISABLED_PATTERN` — "Disabled Badge Holders", "Blue Badge"
- `FREE_PATTERN` — "Free Parking"

### Known limitations
- Very small signs (< 100px wide in the photo) may not be detected by contour detection
- Multi-plate stacks (e.g. a standard restriction with an added resident permit plate) are read
  as one combined text block — this may produce unexpected parsed output
- Handwritten or printed A4 council notices are outside scope for v1.0

### Testing
See `tests/test_all.py` → `TestParseRestriction` — 10 unit tests covering all major sign formats.

---

## Risk 2 — Time Needed to Map Extensive Urban Regions

**Proposal reference:** *"the time needed to map extensive urban regions"*

### Description
Manually photographing and uploading every parking sign across even a single UK city would
require thousands of submissions. A single London borough (e.g. Westminster) has over 3,000
individual parking bays, each potentially with different restrictions.

### Mitigation in codebase

**Crowdsourced contribution model** (`/upload` route):
- Any user or volunteer can photograph a sign and submit it
- OCR runs automatically — no manual data entry required
- The uploaded photo is stored in `static/images/uploads/` for audit purposes
- The parsed zone is immediately visible on the map

**Seed data** (`data/zones.json`):
- 13 pre-loaded zones across 5 UK cities provide immediate value on first run
- Covers London, Manchester, Birmingham, Edinburgh, Bristol

**Admin manual entry** (`/admin/zone/add`):
- Council staff or administrators can enter zones directly from council data without needing a photo
- Supports bulk population of areas from official regulation documents

**Scalability path** (production):
- Replace `zones.json` with PostgreSQL + PostGIS for millions of zones
- Add batch import API endpoint for council-provided GeoJSON datasets
- Partner with local councils to import official regulation data directly

---

## Risk 3 — Keeping Council Regulation Data Current

**Proposal reference:** *"the resource challenge of keeping council regulation data current"*

### Description
UK parking regulations change regularly — councils update hours, introduce new permit zones,
create temporary restrictions, and revise PCN enforcement zones. Outdated map data could mislead
drivers and undermine trust in the system.

### Mitigation in codebase

**Admin zone management** (`dashboard.html` + `app.py`):
- `/admin/zone/<id>/edit` — edit any zone's restriction type, hours, days, permit code, max stay
- `/admin/zone/<id>/delete` — remove zones that no longer exist
- All edits are timestamped (`updated_at`) and attributed (`updated_by: admin`)

**Audit trail in data store** (`data/parking_data.py`):
- Every zone record stores `submitted_at` (when first added) and optionally `updated_at`
- The `source` field records whether the zone came from OCR upload, manual admin entry, or seed data
- The stored sign image (where available) provides a visual reference for verification

**Crowdsourced updates**:
- Any user can re-upload a new photo of the same sign after regulations change
- The new submission creates a second zone entry; admin can then delete the outdated one

**Production-scale strategy** (recommended):
- Set up a quarterly data review cycle where admin staff verify high-traffic zones
- Integrate with [UK Government Parking API](https://www.gov.uk/guidance/transport-data-services) when available
- Subscribe to local council planning notices RSS feeds for regulation change alerts
- Add a "report outdated data" button to map popups (future feature)

---

## Risk Summary Matrix

| # | Risk | Likelihood | Impact | Status |
|---|---|---|---|---|
| 1 | Difficulty reading varied UK sign formats | Medium | High | Mitigated (OCR pipeline + regex) |
| 2 | Time to map extensive urban areas | High | Medium | Mitigated (crowdsourcing + admin entry) |
| 3 | Keeping council data current | Medium | High | Mitigated (admin CRUD + audit trail) |

---

*Last updated: 2024 — Park Smart UK CW1 Concept Proposal submission*
