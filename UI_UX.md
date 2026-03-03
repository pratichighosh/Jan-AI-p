# 🎨 CAIS — UI/UX Flow Documentation

> **Citizen Application Intelligence System**  
> Complete screen-by-screen design specification with interaction details, backend triggers, and state transitions.

---

## 📐 Design Principles

| Principle | Implementation |
|---|---|
| **Mobile-first** | 90% of target users are on low-end Android phones |
| **Offline-tolerant** | Core flows work with intermittent connectivity |
| **Low-literacy friendly** | Icons + color always accompany text labels |
| **Language-first** | Language selection happens before anything else |
| **Zero jargon** | Every bureaucratic term is replaced or explained inline |

---

## 🗺️ Master Flow Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          COMPLETE USER JOURNEY                               │
└─────────────────────────────────────────────────────────────────────────────┘

  [SPLASH]
     │
     ▼
  [LANGUAGE SELECT] ──────────────────────────────────────────────────┐
     │                                                                  │
     ▼                                                                  │
  [HOME / DASHBOARD]                                              (persisted
     │                                                             preference)
     ├──── "I have a form to fill"  ──────► [FORM UPLOAD FLOW]
     │                                              │
     ├──── "I got rejected"  ──────────────► [REJECTION FLOW]
     │                                              │
     └──── "Check my documents"  ──────────► [DOCUMENT CHECK FLOW]
                                                    │
                                          [PROCESSING SCREEN]
                                                    │
                                          [RESULTS DASHBOARD]
                                                    │
                                    ┌───────────────┼───────────────┐
                                    ▼               ▼               ▼
                             [SCORE DETAIL]  [ACTION ITEMS]  [DEADLINES]
                                    │               │
                                    ▼               ▼
                             [FIELD GUIDE]   [STEP-BY-STEP]
                                                    │
                                          [PROGRESS TRACKER]
                                                    │
                                          [READY TO SUBMIT ✓]
```

---

## 🖥️ Screen-by-Screen Specification

---

### SCREEN 1 — Splash Screen

**Duration:** 2.5 seconds  
**Purpose:** Brand impression + app initialization

```
┌─────────────────────────┐
│                         │
│                         │
│          🇮🇳             │
│                         │
│    CAIS                 │
│    नागरिक सहायक         │
│                         │
│  ████████░░░░░░░  62%   │
│  Loading your language  │
│                         │
│                         │
└─────────────────────────┘
```

**What happens technically:**
- App checks `localStorage` for saved language preference
- Preloads language pack for detected/saved language
- Checks network status → sets offline mode flag if needed
- Calls `/api/health` to verify backend availability
- Progress bar fills as each resource loads

**Transitions:**
- If language previously saved → skip to **Home**
- If first visit → go to **Language Select**
- If backend unreachable → show offline banner but continue

---

### SCREEN 2 — Language Selection

**Purpose:** First and most critical interaction — sets the entire session language  
**Trigger:** First launch OR user taps "Change Language" from any screen

```
┌─────────────────────────┐
│  🇮🇳 Choose Your Language │
│  अपनी भाषा चुनें        │
│  உங்கள் மொழியை தேர்ந்   │
│─────────────────────────│
│                         │
│  🔍 Search / खोजें       │
│  ┌───────────────────┐  │
│  │                   │  │
│  └───────────────────┘  │
│                         │
│  ┌────────┐  ┌────────┐ │
│  │  हिंदी  │  │ বাংলা  │ │
│  │ Hindi  │  │Bengali │ │
│  └────────┘  └────────┘ │
│  ┌────────┐  ┌────────┐ │
│  │தமிழ்   │  │తెలుగు  │ │
│  │ Tamil  │  │Telugu  │ │
│  └────────┘  └────────┘ │
│  ┌────────┐  ┌────────┐ │
│  │ ਪੰਜਾਬੀ  │  │मराठी  │ │
│  │Punjabi │  │Marathi │ │
│  └────────┘  └────────┘ │
│                         │
│  [+ Show all 22 →]      │
│                         │
└─────────────────────────┘
```

**What happens technically:**
- Tap any language card → immediately re-renders ALL UI text in that language
- Language code (e.g., `hi`, `ta`, `bn`) saved to `localStorage` + user session
- `POST /session/language { userId, languageCode }` updates server-side preference
- All subsequent API calls include `Accept-Language: hi` header
- Bhashini translation target language set for entire session

**Interaction details:**
- Search box filters languages in real-time (no API call — local filter)
- Selected card shows checkmark + green border with animation
- "Confirm" button appears after selection (300ms delay to prevent accidental taps)
- Language name shown in both that language AND English (for discoverability)

---

### SCREEN 3 — Home Dashboard

**Purpose:** Central navigation hub + quick status overview  
**Returns to:** After every flow completion

```
┌─────────────────────────┐
│ नमस्ते, Ramesh 👋        │
│ ─────────────────────── │
│                         │
│  What do you need help  │
│  with today?            │
│  आज आपको क्या चाहिए?   │
│                         │
│  ┌─────────────────────┐│
│  │  📄  I have a form  ││
│  │  फॉर्म भरना है       ││
│  │                →    ││
│  └─────────────────────┘│
│                         │
│  ┌─────────────────────┐│
│  │  ❌  I was rejected ││
│  │  आवेदन रद्द हुआ     ││
│  │                →    ││
│  └─────────────────────┘│
│                         │
│  ┌─────────────────────┐│
│  │  📁  Check my docs  ││
│  │  दस्तावेज़ जाँचें    ││
│  │                →    ││
│  └─────────────────────┘│
│                         │
│  ──── Recent ──────     │
│  📊 PM-KISAN  62% ████░ │
│  Last updated: Today    │
│                    [→]  │
└─────────────────────────┘
```

**What happens technically:**
- `GET /progress/{userId}/all` → fetches all in-progress applications
- Recent applications render with last known readiness score
- Score bar color: red (<70), yellow (70–89), green (≥90)
- Offline mode: shows cached progress data with "Last synced" timestamp

**Interaction details:**
- Each "recent" card is tappable → goes directly to Results Dashboard for that document
- Three main CTAs are large tap targets (minimum 48px height)
- Icons + text in user's language — never icon alone

---

### SCREEN 4 — Document Upload (Form / Rejection Notice / Documents)

**Purpose:** Capture the government document  
**Variants:** Same screen, different header text per flow type

```
┌─────────────────────────┐
│ ← Upload Your Form      │
│   अपना फॉर्म अपलोड करें │
│─────────────────────────│
│                         │
│  📸 Take a Photo        │
│  ┌─────────────────────┐│
│  │                     ││
│  │   [ Camera Icon ]   ││
│  │                     ││
│  │  Tap to open camera ││
│  │  कैमरा खोलने के लिए ││
│  │  टैप करें           ││
│  │                     ││
│  └─────────────────────┘│
│                         │
│  ── OR ──               │
│                         │
│  📁  Choose from Gallery │
│  🗂️  Upload PDF          │
│                         │
│  ─── Tips ──────────    │
│  ✅ Keep document flat  │
│  ✅ Good lighting       │
│  ✅ All 4 corners visible│
│  ❌ No blur / shadow    │
│                         │
│  [Accepted: JPG PNG PDF]│
│  [Max size: 10 MB]      │
│                         │
└─────────────────────────┘
```

**What happens technically:**
- Camera tap → opens native device camera with `capture="environment"` hint (rear camera)
- File chosen → immediate client-side validation:
  - MIME type check (not just extension)
  - File size check (≤ 10MB)
  - Basic image dimensions check (minimum 400×400px)
- If PDF → show page count preview ("3 pages detected")
- `POST /upload` with `multipart/form-data`

**Pre-upload client validation errors shown inline:**

```
┌─────────────────────────┐
│  ⚠️ File too large       │
│  आपकी फ़ाइल 10MB से     │
│  ज़्यादा है (12.3 MB)   │
│                         │
│  How to fix:            │
│  → Take photo at lower  │
│    camera resolution    │
│  → Use PDF compression  │
│                         │
│  [Try Again]            │
└─────────────────────────┘
```

---

### SCREEN 5 — Processing / Loading Screen ⭐ *[Major Step]*

**Purpose:** Keep user informed during the 8–15 second AI pipeline  
**Critical UX moment:** Users must not abandon thinking "it's broken"

```
┌─────────────────────────┐
│                         │
│  Analyzing your         │
│  document...            │
│  आपका दस्तावेज़         │
│  जाँचा जा रहा है...     │
│                         │
│  ┌─────────────────────┐│
│  │ ✅ Image received   ││
│  │ ✅ Enhancing image  ││
│  │ ⏳ Reading text...  ││  ← animated spinner
│  │ ░░ Translating      ││  ← greyed out (not yet)
│  │ ░░ Checking scheme  ││
│  │ ░░ Calculating score││
│  └─────────────────────┘│
│                         │
│  ████████░░░░░░  52%    │
│                         │
│  Did you know?          │
│  PM-KISAN requires land │
│  records to be updated  │
│  in the last 2 years.   │
│  ──────────────────     │
│  (rotates every 4s)     │
│                         │
└─────────────────────────┘
```

**What happens technically — step by step:**

**Step 1: Image received** (0.0s)
- Server confirms upload → WebSocket connection opens
- Server sends `{ stage: "received", progress: 10 }`

**Step 2: Enhancing image** (0.5s)
- OpenCV pipeline runs: deskew → denoise (bilateralFilter) → CLAHE contrast
- If multi-page PDF: PyMuPDF splits pages, each page queued
- Server sends `{ stage: "preprocessing", progress: 20 }`

**Step 3: Reading text (OCR)** (1–5s depending on document complexity)
- OpenBharatOCR runs first
- If confidence < 0.7 on any block → PaddleOCR/Parichay runs as fallback
- Text blocks extracted with bounding boxes + per-block confidence
- Language detected per block (handles multilingual docs)
- Server sends `{ stage: "ocr", progress: 40, confidence: 0.87 }`

**Step 4: Translating** (2–4s)
- Bhashini API called with extracted text
- Plain-language simplification applied
- Redis cache checked first (saves ~1.5s on common phrases)
- On Bhashini failure: retry 1 (1s) → retry 2 (2s) → retry 3 (4s) → error
- Server sends `{ stage: "translating", progress: 60 }`

**Step 5: Checking scheme** (0.5s)
- Indic-BERT classifies document type
- Fuzzy match on scheme names + form number regex
- Scheme Knowledge Base queried for validation rules
- Server sends `{ stage: "analyzing", progress: 75 }`

**Step 6: Calculating score** (0.5s)
- Readiness formula applied
- Action items generated and prioritized
- Deadlines extracted, classified, sorted
- Server sends `{ stage: "complete", progress: 100, documentId: "..." }`

**WebSocket disconnect → fallback:**
If WebSocket drops (poor network), UI polls `GET /status/{documentId}` every 3 seconds.

**Error state during processing:**

```
┌─────────────────────────┐
│  ⚠️ Could not read text  │
│                         │
│  The image was too dark │
│  to read clearly.       │
│  तस्वीर बहुत अंधेरी है │
│                         │
│  Please try:            │
│  → Take photo near      │
│    a window / light     │
│  → Increase brightness  │
│    on your phone screen │
│                         │
│  [📸 Retake Photo]      │
│  [📁 Upload Different]  │
└─────────────────────────┘
```

---

### SCREEN 6 — Results Dashboard ⭐ *[Major Step]*

**Purpose:** Primary value delivery — the "aha moment" of the app  
**This is the most important screen in the entire product**

```
┌─────────────────────────┐
│ ← PM-KISAN Application  │
│   Results               │
│─────────────────────────│
│                         │
│    ┌───────────────┐    │
│    │      62       │    │
│    │    ██████░░░░ │    │
│    │  HIGH RISK ⚠️  │    │
│    │ उच्च जोखिम    │    │
│    └───────────────┘    │
│                         │
│  Your application is    │
│  likely to be REJECTED  │
│  unless you fix 3       │
│  critical issues.       │
│                         │
│─── CRITICAL (must fix) ─│
│  ❌ Land records missing │
│  ❌ Bank account not     │
│     linked to Aadhaar   │
│                         │
│── RECOMMENDED ──────────│
│  ⚠️ Mobile number not    │
│     updated             │
│                         │
│── DEADLINES ────────────│
│  🔴 Application window  │
│     closes in 12 days   │
│                         │
│  [Fix Issues →]         │
│  [Download Report]      │
│                         │
└─────────────────────────┘
```

**Score ring animation:**
- On load: ring animates from 0 → 62 over 1.2 seconds
- Color fills progressively: red for <70
- Number counts up with the animation
- Pulse animation on score when it lands (draws eye)

**What happens technically:**
- `GET /analysis/{documentId}` returns full DecisionOutput
- Score, risk level, action items, deadlines all rendered from single API response
- Translated content already in user's preferred language (from Bhashini in pipeline)
- Action items sorted by priority (1 = must fix first)
- "Fix Issues" button deep-links to Action Items screen at item #1

**Score thresholds UI:**

| Score | Color | Label | Icon |
|---|---|---|---|
| 0–49 | 🔴 Red | Very High Risk | ⛔ |
| 50–69 | 🟠 Orange | High Risk | ⚠️ |
| 70–84 | 🟡 Yellow | Medium Risk | ℹ️ |
| 85–94 | 🟢 Light Green | Low Risk | ✅ |
| 95–100 | 💚 Green | Ready to Submit | 🎉 |

---

### SCREEN 7 — Action Items Detail ⭐ *[Major Step]*

**Purpose:** Turn rejection analysis into a practical to-do list  
**The core utility that replaces the middleman**

```
┌─────────────────────────┐
│ ← Fix Issues (3 left)   │
│─────────────────────────│
│                         │
│ ── CRITICAL ─── 2 items │
│                         │
│  ┌─────────────────────┐│
│  │ ❌ 1. Land Records  ││
│  │                     ││
│  │  You need to upload ││
│  │  proof that you own ││
│  │  or cultivate land. ││
│  │                     ││
│  │  ⏱️ Takes: 2-3 days  ││
│  │                     ││
│  │  [See Steps →]      ││
│  └─────────────────────┘│
│                         │
│  ┌─────────────────────┐│
│  │ ❌ 2. Aadhaar-Bank  ││
│  │    Link             ││
│  │                     ││
│  │  Your bank account  ││
│  │  must be linked to  ││
│  │  your Aadhaar card. ││
│  │                     ││
│  │  ⏱️ Takes: 15 mins   ││
│  │  [See Steps →]      ││
│  └─────────────────────┘│
│                         │
│ ── RECOMMENDED ─ 1 item │
│  ┌─────────────────────┐│
│  │ ⚠️ 3. Mobile number  ││
│  │  [See Steps →]      ││
│  └─────────────────────┘│
│                         │
└─────────────────────────┘
```

**Tapping "See Steps →" expands inline:**

```
┌─────────────────────────┐
│ ❌ 1. Land Records      │
│    [Collapse ▲]         │
│─────────────────────────│
│                         │
│  Step 1 of 4            │
│  ────────────           │
│  Go to your Tehsildar   │
│  office (तहसीलदार       │
│  कार्यालय)               │
│                         │
│  📍 Your nearest office:│
│  Rampur Tehsil, 2.3 km  │
│  Open: Mon-Sat 10am-5pm │
│                         │
│  Step 2 of 4            │
│  ────────────           │
│  Ask for Khatauni/      │
│  Khasra copy            │
│  (खतौनी / खसरा प्रति)  │
│                         │
│  Step 3 of 4            │
│  ────────────           │
│  Get it stamped and     │
│  signed by the officer  │
│                         │
│  Step 4 of 4            │
│  ────────────           │
│  Take a clear photo of  │
│  all pages and upload   │
│  here ↓                 │
│                         │
│  [📸 Upload Document]   │
│                         │
│  ✅ Mark as Done        │
│                         │
└─────────────────────────┘
```

**What happens technically when "Mark as Done" is tapped:**

1. `POST /progress/{userId}/{documentId}/complete/{actionId}`
2. Server recalculates readiness score
3. Response: `{ newScore: 74, riskLevel: "MEDIUM", ... }`
4. Score ring on Results Dashboard updates (visible if navigating back)
5. Action item animates out with green checkmark ✅
6. If all critical items done → celebration animation + "Ready to Submit" prompt appears
7. Score delta shown: `+12 points ↑`

---

### SCREEN 8 — Rejection Notice Flow ⭐ *[Major Step]*

**Purpose:** Specific flow for users who received a rejection letter

**Step 1: Upload rejection notice** (same upload screen, different header)

**Step 2: Processing** (same pipeline, but Document Analysis Engine focuses on rejection reason extraction using Sarvam 2B LLM)

**Step 3: Rejection Analysis Results**

```
┌─────────────────────────┐
│ ← Why Was I Rejected?   │
│   आवेदन क्यों रद्द हुआ │
│─────────────────────────│
│                         │
│  We found 3 reasons     │
│  for your rejection.    │
│                         │
│  All reasons explained  │
│  below with fix steps.  │
│                         │
│─── Reason 1 ────────────│
│  📄 Original (Hindi):   │
│  "आवेदक के दस्तावेज़ में │
│  भूमि रिकॉर्ड का        │
│  सत्यापन नहीं हुआ"      │
│                         │
│  ✏️ In simple words:    │
│  Your land ownership    │
│  papers could not be    │
│  verified.              │
│                         │
│  🔧 How to fix:         │
│  [See 4 Steps →]        │
│                         │
│─── Reason 2 ────────────│
│  📄 Original:           │
│  "बैंक खाता आधार से     │
│  असंबद्ध"               │
│                         │
│  ✏️ In simple words:    │
│  Bank account not       │
│  linked to Aadhaar.     │
│                         │
│  🔧 How to fix:         │
│  [See 3 Steps →]        │
│                         │
│─── Reason 3 ────────────│
│  ...                    │
│                         │
│  [Fix All Issues →]     │
│                         │
└─────────────────────────┘
```

**What happens technically:**
- `analyzeDocument()` detects `documentType: REJECTION_NOTICE`
- Sarvam 2B LLM extracts all rejection reasons semantically (not just keyword match)
- Each reason is translated to user's language by Bhashini API
- `generateDecision()` maps each rejection reason → Action_Item(s)
- Related Action_Items grouped (e.g., two reasons about documents → combined into one document upload task)
- Action_Items prioritized by: severity → estimated time → complexity

**Grouping logic example:**
```
Rejection Reason 1: "land records unverified"     ─┐
Rejection Reason 3: "land measurement mismatch"   ─┴─► ACTION: "Fix Land Records" (combined)

Rejection Reason 2: "bank account not linked"      ────► ACTION: "Link Aadhaar to Bank"
```

---

### SCREEN 9 — Form Field Guidance

**Purpose:** Inline help for confusing form fields  
**Trigger:** User taps ❓ next to any field name in action items

```
┌─────────────────────────┐
│ ← Field Help            │
│   खेत नंबर (Khasra No.) │
│─────────────────────────│
│                         │
│  What is this?          │
│  यह क्या है?            │
│                         │
│  This is the unique     │
│  number of your land    │
│  plot as recorded in    │
│  government land maps.  │
│                         │
│  Where to find it:      │
│  → On your Khatauni     │
│    (land record) paper  │
│  → Usually 3-8 digits   │
│  → Example: 425, 1203   │
│                         │
│  ⚠️ Common Mistakes:    │
│  → Don't confuse with   │
│    Khata number         │
│  → Don't leave blank    │
│    if you have multiple │
│    plots — list all     │
│                         │
│  Accepted Documents:    │
│  ✅ Khatauni            │
│  ✅ Jamabandi           │
│  ✅ Fard (Punjab)       │
│  ✅ Pahani (Karnataka)  │
│                         │
│  [Got it ✓]             │
│                         │
└─────────────────────────┘
```

**What happens technically:**
- `GET /guidance/{schemeId}/{fieldId}?language=hi`
- Response pulls from Scheme Knowledge Base:
  - `helpText` (plain language explanation)
  - `validationPattern` (for format example generation)
  - `commonMistakes[]`
  - `acceptedDocuments[]`
- All text already in user's language (translated via Bhashini at Scheme KB load time)
- Cached in Redis — near-instant response (<100ms for cached fields)

---

### SCREEN 10 — Document Validation Screen

**Purpose:** Check if a specific supporting document will be accepted  
**Trigger:** User uploads a supporting doc from action item, or from "Check my docs" flow

```
┌─────────────────────────┐
│ Checking your document  │
│─────────────────────────│
│                         │
│  📄 Aadhaar Card        │
│                         │
│  ✅ File format: OK     │
│     (JPG, 2.1 MB)       │
│                         │
│  ✅ Image quality: Good │
│     (Clear, readable)   │
│                         │
│  ✅ All 4 sides visible │
│                         │
│  ✅ Name visible        │
│                         │
│  ⚠️ Expiry check:       │
│     No expiry on        │
│     Aadhaar — OK        │
│                         │
│  ─────────────────────  │
│                         │
│  ✅ This document looks │
│     good to submit!     │
│                         │
│  [Use this document ✓]  │
│  [Retake / Replace]     │
│                         │
└─────────────────────────┘
```

**Failed validation state:**

```
┌─────────────────────────┐
│  ❌ Document has issues  │
│─────────────────────────│
│  ✅ Format: OK           │
│  ❌ Quality: Too blurry  │
│  ❌ Expiry: EXPIRED      │
│     Expired: Jan 2023   │
│─────────────────────────│
│  How to fix:            │
│                         │
│  For blur:              │
│  → Hold phone steady    │
│  → Use both hands       │
│  → Tap screen to focus  │
│                         │
│  For expiry:            │
│  → This ID is expired   │
│  → Get a valid ID first │
│  → Visit nearest CSC or │
│    government office    │
│                         │
│  [📸 Retake Photo]      │
└─────────────────────────┘
```

**What happens technically:**
- Client-side: basic format + size validation before any API call
- Server-side `POST /validate`:
  - File format validation (magic number check)
  - Size ≤ 10MB
  - OpenCV image quality assessment (Laplacian variance for blur detection)
  - Tesseract OCR run on detected text regions
  - Date regex applied → if expiry date found, compared to `Date.now()`
  - Returns `{ passed: bool, checks: [...], errors: [...], suggestions: [...] }`

---

### SCREEN 11 — Progress Tracker

**Purpose:** Persistent overview of all in-progress applications

```
┌─────────────────────────┐
│ ← My Applications       │
│   मेरे आवेदन            │
│─────────────────────────│
│                         │
│  PM-KISAN               │
│  ████████░░░  74%       │
│  🟡 Medium Risk         │
│  2 actions remaining    │
│  [Continue →]           │
│                         │
│  Ayushman Bharat        │
│  ██░░░░░░░░░  23%       │
│  🔴 High Risk           │
│  5 actions remaining    │
│  [Continue →]           │
│                         │
│  Ration Card            │
│  ████████████ 100%      │
│  🟢 Ready to Submit!    │
│  [View →]               │
│                         │
│  [+ Start New →]        │
│                         │
└─────────────────────────┘
```

---

### SCREEN 12 — Ready to Submit 🎉

**Purpose:** Celebration + final confirmation before user goes to submit  
**Trigger:** All critical Action_Items marked complete + score ≥ 90

```
┌─────────────────────────┐
│                         │
│         🎉              │
│                         │
│   You're Ready!         │
│   आप तैयार हैं!          │
│                         │
│        100              │
│   ████████████ 100%     │
│   🟢 Ready to Submit    │
│                         │
│  All issues fixed.      │
│  Your application is    │
│  complete and should    │
│  be accepted.           │
│                         │
│  ── Summary ──          │
│  ✅ Land records        │
│  ✅ Aadhaar-Bank linked │
│  ✅ Mobile updated      │
│                         │
│  ── Next Step ──        │
│  Take this to your      │
│  nearest CSC center or  │
│  submit online at:      │
│  pmkisan.gov.in         │
│                         │
│  [📥 Download Checklist]│
│  [📍 Find CSC Center]   │
│  [🔗 Go to Portal]      │
│                         │
└─────────────────────────┘
```

**What happens technically:**
- Confetti animation triggered (CSS keyframe, no library needed)
- `GET /analysis/{documentId}` refreshed → confirms score = 100
- Checklist PDF generated via `GET /export/{documentId}?format=pdf`
- "Find CSC Center" → opens maps with `geo:` URI or Google Maps with scheme office query
- "Go to Portal" → opens scheme's official URL in system browser

---

## 🔄 State Transition Diagram

```
                    ┌──────────────┐
                    │   UPLOADED   │
                    └──────┬───────┘
                           │ Upload successful
                           ▼
                    ┌──────────────┐
                    │ OCR_PROCESS  │
                    │    -ING      │
                    └──────┬───────┘
                           │ OCR complete (confidence ≥ 0.7)
                     ┌─────┴─────┐
                     │           │
              confidence     confidence
               ≥ 0.7           < 0.7
                     │           │
                     ▼           ▼
                 Continue    ┌──────────────┐
                             │  OCR_RETRY   │
                             │  (enhanced)  │
                             └──────┬───────┘
                                    │ Still < 0.7
                                    ▼
                             ┌──────────────┐
                             │    FAILED    │ → Show error to user
                             └──────────────┘
                           │
                           ▼ (OCR success)
                    ┌──────────────┐
                    │ TRANSLATING  │
                    └──────┬───────┘
                           │
                     ┌─────┴──────┐
                     │            │
                 Bhashini      Bhashini
                 success        fails
                     │            │
                     ▼            ▼
                 Continue    Retry (×3)
                                  │
                               After 3
                               failures
                                  │
                                  ▼
                           ┌──────────────┐
                           │    ERROR     │ → Show retry option
                           └──────────────┘
                           │
                           ▼ (Translation success)
                    ┌──────────────┐
                    │  ANALYZING   │
                    └──────┬───────┘
                           │ Scheme matched
                           ▼
                    ┌──────────────┐
                    │  COMPLETED   │ → Show Results Dashboard
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
          Score<70     Score 70-89   Score≥90
         HIGH RISK     MED RISK      LOW RISK
              │            │            │
              └────────────┴─────────── ┘
                           │
                           ▼
                  User completes Action_Items
                           │
                           ▼ (score updates each time)
                    ┌──────────────┐
                    │   SCORE=100  │ → READY TO SUBMIT
                    └──────────────┘
```

---

## 📱 Responsive Breakpoints

| Breakpoint | Layout | Primary Users |
|---|---|---|
| 320–480px | Single column, large tap targets (48px min) | Low-end Android phones |
| 481–768px | Single column with side panels | Mid-range phones |
| 769–1024px | Two-column (nav + content) | Tablets, CSC computers |
| 1025px+ | Three-column dashboard | Desktop at CSC centers |

---

## ♿ Accessibility Requirements

- All interactive elements: minimum 44×44px tap target
- Color never used as the sole indicator (always icon + color + text)
- Screen reader labels on all icons in user's language
- Font size minimum 16px body, 14px secondary
- Contrast ratio minimum 4.5:1 (WCAG AA)
- Loading states announced to screen readers

---

## 🌐 Offline Behavior

| Feature | Online | Offline |
|---|---|---|
| View saved progress | ✅ | ✅ (cached) |
| Upload new document | ✅ | ❌ (queued) |
| View previous results | ✅ | ✅ (cached) |
| Get field guidance | ✅ | ✅ (cached) |
| Mark action complete | ✅ | ✅ (sync on reconnect) |
| Export PDF | ✅ | ✅ (if previously generated) |

Offline actions are queued in `IndexedDB` and synced when connectivity returns. Banner shown: *"You're offline — changes will sync when connected"*

---

## 🎨 Design Tokens

```css
/* Colors */
--color-primary:      #138808;  /* India green */
--color-accent:       #FF9933;  /* Saffron */
--color-danger:       #D32F2F;  /* High risk red */
--color-warning:      #F57C00;  /* Medium risk orange */
--color-success:      #2E7D32;  /* Low risk green */
--color-surface:      #FFFFFF;
--color-surface-alt:  #F5F5F5;
--color-text:         #212121;
--color-text-muted:   #757575;

/* Typography */
--font-display:  'Noto Sans', system-ui;  /* Supports all Indian scripts */
--font-body:     'Noto Sans', system-ui;
--font-mono:     'Noto Sans Mono', monospace;

/* Spacing (8px base grid) */
--space-xs:   4px;
--space-sm:   8px;
--space-md:   16px;
--space-lg:   24px;
--space-xl:   32px;
--space-xxl:  48px;

/* Score ring sizes */
--score-ring-size:  120px;
--score-font-size:  36px;
```

**Note on fonts:** Noto Sans is mandatory — it's the only free font family with complete coverage of all 22 Indian scripts in a single family. No other font should be used for multilingual content.

---

## 🧩 Component Library

| Component | Used In | Key Behavior |
|---|---|---|
| `<ScoreRing>` | Results Dashboard | Animated 0→score on mount, color by threshold |
| `<ActionCard>` | Action Items | Expandable, inline step list, upload trigger |
| `<LanguagePicker>` | Language Select, Settings | Grid of script cards, search filter |
| `<ProcessingSteps>` | Loading Screen | Real-time WebSocket stage updates |
| `<DocumentUpload>` | All upload screens | Camera + gallery + PDF, client validation |
| `<DeadlineChip>` | Results, Deadlines | Color by urgency, days-remaining countdown |
| `<ProgressBar>` | Progress Tracker | Animated fill, color by score |
| `<FieldHelp>` | Form Guidance | Bottom sheet, Bhashini-translated content |
| `<ValidationResult>` | Doc Validation | Check/cross list with inline fix suggestions |

---

*This document covers the complete UI/UX specification for CAIS v1.0. Every screen maps to a backend API call, a correctness property, and a user story from the PRD.*