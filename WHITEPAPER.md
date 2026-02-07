# Lab Compare: Diagnostic Lab Test Price Comparison System

## Project White Paper

**Version:** 1.0
**Date:** February 2026
**Repository:** [github.com/musicofthings/lab-compare](https://github.com/musicofthings/lab-compare)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [System Architecture](#3-system-architecture)
4. [Data Sources & Scale](#4-data-sources--scale)
5. [Database Schema](#5-database-schema)
6. [Python Data Pipeline](#6-python-data-pipeline)
7. [Multi-Pass Matching Algorithm](#7-multi-pass-matching-algorithm)
8. [Dashboard Features](#8-dashboard-features)
9. [Deployment & Infrastructure](#9-deployment--infrastructure)
10. [Performance & Scalability](#10-performance--scalability)
11. [Data Quality & Validation](#11-data-quality--validation)
12. [Future Roadmap](#12-future-roadmap)

---

## 1. Executive Summary

Lab Compare is a full-stack system that aggregates, normalizes, and compares diagnostic laboratory test pricing across five major Indian diagnostic chains. The system ingests approximately 190,000 lab test entries from Metropolis, Agilus, Apollo, Neuberg, and TRUSTlab, normalizes them through a multi-pass fuzzy matching algorithm, and creates a unified catalog of ~15,000 canonical tests. These are presented through an interactive dashboard with pricing comparison, heatmap visualization, and availability analysis.

| Metric | Value |
|--------|-------|
| Labs covered | 5 (Metropolis, Agilus, Apollo, Neuberg, TRUSTlab) |
| Raw lab test entries | ~190,000 |
| Canonical (deduplicated) tests | ~15,000 |
| Lab locations | ~100 across 35+ Indian cities |
| Test name aliases | ~70,000 |
| Tests at 3+ labs (popular) | ~2,500 |
| Tests at all 5 labs | ~400 |

---

## 2. Problem Statement

India's diagnostic laboratory market is valued at over $10 billion and growing at 15% annually. Five major chains dominate the organized segment:

- **Metropolis Healthcare** — pan-India, 3,100+ tests
- **Agilus Diagnostics (SRL)** — pan-India, 2,300+ tests
- **Apollo Diagnostics** — 68+ centres, 2,700+ tests
- **Neuberg Diagnostics** — 15+ cities, 2,800+ tests
- **TRUSTlab Diagnostics** — 15 locations, 1,700+ tests

### The Problem

Patients face three critical challenges:

1. **Price opacity**: The same CBC test can cost Rs. 150 at one lab and Rs. 450 at another in the same city, but patients have no way to compare.
2. **Name fragmentation**: Labs use different names for identical tests ("Complete Blood Count" vs "CBC" vs "Hemogram" vs "Blood CP"), making comparison nearly impossible.
3. **Availability blindness**: Patients don't know which labs serve their city, which departments are covered, or what turnaround times to expect.

### The Solution

Lab Compare creates a unified, searchable catalog by:
- Normalizing test names across labs using fuzzy matching
- Mapping lab-specific location codes to canonical cities
- Aggregating pricing, TAT, methodology, and accreditation data
- Presenting side-by-side comparisons through an intuitive dashboard

---

## 3. System Architecture

Lab Compare follows a three-layer architecture:

```
┌─────────────────────────────────────────────────────────────┐
│                    CLOUDFLARE PAGES                          │
│            Next.js 16 Static Dashboard                      │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│   │  Search   │ │ Compare  │ │ Heatmap  │ │ Availability │  │
│   │  + Lab    │ │  + Chart │ │  + Grid  │ │  + Matrix    │  │
│   │  Filter   │ │  + Table │ │  + Color │ │  + Counts    │  │
│   └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │ REST API (supabase-js)
┌──────────────────────▼──────────────────────────────────────┐
│                  SUPABASE (PostgreSQL 15)                    │
│                                                              │
│  canonical_tests (15K)  ◄──── lab_tests (190K) ──── labs    │
│  test_aliases (70K)            │                   (5)      │
│  departments (20)              │                             │
│  cities (80)           lab_locations (100)                   │
│                                                              │
│  pg_trgm indexes │ RLS policies │ test_comparison view      │
└──────────────────────▲──────────────────────────────────────┘
                       │ supabase-py (batch upsert)
┌──────────────────────┴──────────────────────────────────────┐
│                  PYTHON DATA PIPELINE                        │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  CSV Loaders (5 labs)                                  │  │
│  │  Metropolis │ Agilus │ Apollo │ Neuberg │ TRUSTlab     │  │
│  └──────────────────────┬─────────────────────────────────┘  │
│  ┌──────────────────────▼─────────────────────────────────┐  │
│  │  Normalizers                                           │  │
│  │  City │ Department │ TAT                               │  │
│  └──────────────────────┬─────────────────────────────────┘  │
│  ┌──────────────────────▼─────────────────────────────────┐  │
│  │  Multi-Pass Matching Algorithm                         │  │
│  │  Pass 1: Exact Name │ Pass 2: Alias │ Pass 3: Fuzzy   │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Pipeline | Python 3.10+, pandas, rapidfuzz, pydantic | ETL, matching, normalization |
| Database | Supabase (PostgreSQL 15), pg_trgm | Storage, fuzzy search, RLS |
| Frontend | Next.js 16, React 19, Tailwind CSS 4, Recharts | Dashboard UI |
| Deployment | Cloudflare Pages, GitHub | Static hosting, CI/CD |

---

## 4. Data Sources & Scale

### Per-Lab Breakdown

#### Metropolis Healthcare
- **Source**: PDF extracted to CSV
- **Scale**: 3,187 tests (Delhi only)
- **Unique fields**: Price, fasting required (YES/NO), NABL accredited (Y/N), TAT from "Reported On" field, methodology, sample quantity
- **Limitations**: Single city, no department data

#### Agilus Diagnostics (SRL)
- **Source**: CSV directory
- **Scale**: 2,376 tests (Delhi only)
- **Unique fields**: product_type for test/package classification
- **Processing**: Strips "Package in New Delhi" noise from names

#### Apollo Diagnostics
- **Source**: CSV with centre-level rows
- **Scale**: 151,157 rows across 68 centres, 2,786 unique test codes
- **Unique fields**: Centre-level pricing (SL0001, GRL0001, RRL0002, etc.), department_name, methodology, sample type, container info
- **Processing**: Deduplication by test_code; prefers Global Reference Lab (GRL0001) as representative. All 151K rows preserved for location-specific pricing.

#### Neuberg Diagnostics
- **Source**: CSV with pipe-delimited aliases
- **Scale**: 23,102 rows across 15 cities, 2,838 unique tests
- **Unique fields**: `alias_name` field containing ~70,000 pipe-delimited alternate names
- **Critical advantage**: Aliases are the backbone of Pass 2 matching, enabling cross-lab test identification even when names differ completely

#### TRUSTlab Diagnostics
- **Source**: CSV with comma-separated locations
- **Scale**: 1,764 test definitions, expanded to multiple per-city rows
- **Processing**: "Hyderabad, Bangalore, Chennai" in location field is expanded into 3 separate lab_test entries
- **Limitations**: Smaller coverage than other labs; dynamically hidden in dashboard when irrelevant

### Raw Data Volumes

```
Lab          │ Raw Rows   │ Unique Tests │ Centres │ Cities
─────────────┼────────────┼──────────────┼─────────┼────────
Metropolis   │    3,187   │     3,187    │    1    │    1
Agilus       │    2,376   │     2,376    │    1    │    1
Apollo       │  151,157   │     2,786    │   68    │   23
Neuberg      │   23,102   │     2,838    │   15    │   15
TRUSTlab     │    1,764   │     1,764    │   15    │    8
─────────────┼────────────┼──────────────┼─────────┼────────
TOTAL        │  ~184,000  │   ~12,951    │  100    │   35+
```

---

## 5. Database Schema

### Entity-Relationship Overview

```
labs (5 rows)
  └── lab_locations (~100 rows) ── cities (~80 rows)
        └── lab_tests (~190K rows)
              └── canonical_tests (~15K rows)
                    ├── departments (~20 rows)
                    └── test_aliases (~70K rows)
```

### Table Definitions

**`labs`** — Diagnostic lab metadata
- Fields: id, name, slug, website_url, created_at
- 5 records: metropolis, agilus, apollo, neuberg, trustlab

**`cities`** — Canonical Indian cities
- Fields: id, name, state, tier (1=metro, 2=tier-2, 3=tier-3), created_at
- ~80 records covering metros (Delhi, Mumbai, Bangalore) to tier-3 cities (Anantapur, Karimnagar)

**`departments`** — Medical departments
- Fields: id, name, slug, created_at
- ~20 records: Biochemistry, Haematology, Microbiology, Serology, Histopathology, Molecular Biology, Cytogenetics, Immunology, Allergy, Clinical Pathology, Radiology, etc.

**`lab_locations`** — Lab-specific centres mapped to canonical cities
- Fields: id, lab_id, city_id, location_code, location_name, is_active, created_at
- ~100 records (Apollo contributes 68 alone)
- UNIQUE constraint on (lab_id, location_code)

**`canonical_tests`** — Master deduplicated test catalog
- Fields: id, name, slug, department_id, test_type, sample_type, methodology, keywords (TEXT[]), is_popular (BOOLEAN), created_at, updated_at
- ~15,000 records
- `is_popular = TRUE` when test available at 3+ labs
- `keywords` array stores all known variant names for search

**`lab_tests`** — The fact table
- Fields: id, lab_id, canonical_test_id, lab_location_id, source_test_code, source_test_name, source_product_id, price, mrp, discount_pct, test_type, department_raw, methodology, sample_type, sample_volume, sample_container, fasting_required, tat_text, tat_hours, home_collection, nabl_accredited, is_active, source_url, raw_data (JSONB), match_confidence, match_method, created_at, updated_at
- ~190,000 records
- `raw_data` JSONB preserves entire original CSV row for audit

**`test_aliases`** — Alternate test names
- Fields: id, canonical_test_id, alias, source_lab_id
- ~70,000+ records (primarily from Neuberg's pipe-delimited aliases)
- UNIQUE on (canonical_test_id, alias)

### Indexes

```sql
-- Trigram indexes for fuzzy search
CREATE INDEX idx_canonical_tests_name_trgm ON canonical_tests USING gin (name gin_trgm_ops);
CREATE INDEX idx_lab_tests_source_name_trgm ON lab_tests USING gin (source_test_name gin_trgm_ops);
CREATE INDEX idx_test_aliases_alias_trgm ON test_aliases USING gin (alias gin_trgm_ops);

-- GIN index on keyword arrays
CREATE INDEX idx_canonical_tests_keywords ON canonical_tests USING gin (keywords);

-- B-tree indexes for joins and filters
CREATE INDEX idx_lab_tests_canonical ON lab_tests(canonical_test_id) WHERE canonical_test_id IS NOT NULL;
CREATE INDEX idx_lab_tests_lab ON lab_tests(lab_id);
CREATE INDEX idx_lab_tests_location ON lab_tests(lab_location_id);
CREATE INDEX idx_lab_tests_code_lab ON lab_tests(source_test_code, lab_id);
CREATE INDEX idx_test_aliases_canonical ON test_aliases(canonical_test_id);
```

### Views

**`test_comparison`** — Denormalized view for dashboard queries
- Joins: canonical_tests + lab_tests + labs + lab_locations + cities + departments
- Filters: is_active = TRUE
- Used by the Compare page for detailed side-by-side pricing

---

## 6. Python Data Pipeline

### Pipeline Execution Flow

The orchestrator (`scripts/run_pipeline.py`) runs 6 sequential steps:

```
Step 1: Seed Reference Data
  └── Insert labs, cities (35+), departments (20)

Step 2: Load CSVs
  └── 5 loaders → ~184K NormalizedLabTest objects

Step 3: Create Lab Locations
  └── Normalize city codes → ~100 lab_location records

Step 4: Run Test Matching
  └── Deduplicate → ~12K unique tests → 4-pass matching → ~15K canonical tests

Step 5: Upload Canonical Tests & Aliases
  └── Batch insert canonicals + ~70K aliases

Step 6: Upload Lab Tests
  └── Link to canonical_test_id → batch insert ~190K lab_tests
```

### Data Model

Every lab test is normalized to a `NormalizedLabTest` (Pydantic model) with unified fields:

```python
class NormalizedLabTest(BaseModel):
    lab_slug: str                    # "metropolis", "apollo", etc.
    source_test_code: Optional[str]  # Original lab's code
    source_test_name: str            # Original name from CSV
    price: Optional[float]           # Customer-facing price
    mrp: Optional[float]             # Maximum retail price
    test_type: str = "test"          # "test" or "package"
    department_raw: Optional[str]    # Un-normalized department
    methodology: Optional[str]       # HPLC, LC-MS, ELISA, etc.
    sample_type: Optional[str]       # Blood, urine, CSF, etc.
    fasting_required: Optional[bool]
    tat_text: Optional[str]          # "Same Day", "24 hours"
    tat_hours: Optional[int]         # Normalized hours
    home_collection: Optional[bool]
    nabl_accredited: Optional[bool]
    location_code: Optional[str]     # Lab's centre code
    aliases: list[str] = []          # Alternate test names
    raw_data: dict = {}              # Original CSV row (JSONB)
```

### Normalizers

**City Normalizer**: 3-tier mapping system
1. Apollo centre code map (23 codes: "GRL0001" → Hyderabad, "RRL0002" → Bangalore, etc.)
2. TRUSTlab area map ("Begumpet" → Hyderabad, "Miyapur" → Hyderabad, etc.)
3. Neuberg direct city names, Metropolis/Agilus default to "Delhi"

**Department Normalizer**: Handles 30+ raw variations
- "Bio Chemistry" / "Clinical Chemistry" / "Special Chemistry" → Biochemistry
- "HAEMATOLOGY" / "Hematology" / "Coagulation" / "Flow Cytometry" → Haematology
- "EIA - Infectious Section" / "Autoimmune" / "Nephelometry" → Serology

**TAT Normalizer**: Diverse format parsing
- "Same Day" → 12h, "Next Day" → 24h, "After 5 Days" → 120h
- "1 hour" → 1h, "2-3 days" → 48h (lower bound)
- Minute fields → divided by 60

---

## 7. Multi-Pass Matching Algorithm

The matching algorithm is the core innovation of Lab Compare. Given ~12,000 unique tests across 5 labs with different naming conventions, it produces ~15,000 canonical test clusters.

### Text Preprocessing

Before matching, all test names undergo preprocessing:

**Abbreviation Expansion** (83 medical terms):
```
CBC → Complete Blood Count
TSH → Thyroid Stimulating Hormone
HbA1c → Glycated Hemoglobin
LFT → Liver Function Test
KFT → Kidney Function Test
PSA → Prostate Specific Antigen
HBsAg → Hepatitis B Surface Antigen
ESR → Erythrocyte Sedimentation Rate
...
```

**Specimen Suffix Stripping**:
```
", Serum" / ", EDTA Blood" / ", Urine 24 Hrs" / ", Plasma"
", Heparin Blood" / ", Bone Marrow" / ", CSF"
```

**Noise Removal**:
```
"Package in New Delhi" (Agilus-specific)
Asterisks, "(quantitative)", "(qualitative)"
```

**Token Expansion**: Produces sets of 2+ character tokens after abbreviation expansion for Jaccard similarity.

### The Four Passes

#### Pass 1: Exact Normalized Name Match
- **Confidence**: 1.0 (multi-member) / 0.95 (resolved later)
- **Method**: Group all tests by normalized name (lowercase, stripped, cleaned)
- **Result**: Multi-member groups are confirmed clusters; singletons proceed to next pass
- **Example**: "Complete Blood Count" from Metropolis + "complete blood count" from Apollo → same cluster

#### Pass 2: Neuberg Alias Match
- **Confidence**: 0.90
- **Method**: Build alias index from all 70K+ Neuberg aliases. For each unmatched test, check if any alias contains the normalized name or vice versa with ratio > 0.5.
- **Example**: Apollo's "TSH - Ultrasensitive" matches Neuberg's alias "Thyroid Stimulating Hormone (TSH) Ultra Sensitive" via containment
- **Impact**: Resolves ~30% of remaining unmatched tests after Pass 1

#### Pass 3: Fuzzy Scoring
- **Confidence**: 0.65 - 0.89 (based on score)
- **Method**: Combined scoring against existing multi-member clusters:
  ```
  score = 0.35 × trigram_similarity + 0.35 × token_jaccard + 0.30 × partial_ratio
  ```
  - **Trigram similarity**: rapidfuzz `fuzz.ratio()` / 100 — measures character-level similarity
  - **Token Jaccard**: |intersection| / |union| of expanded token sets
  - **Partial ratio**: rapidfuzz `fuzz.partial_ratio()` / 100 — substring matching
- **Threshold**: best_score >= 0.65
- **Example**: "Lipid Profile" scores 0.78 against cluster containing "Lipid Panel Complete" + "Fasting Lipid Profile"

#### Pass 4: Singleton Cluster Creation
- **Confidence**: 1.0
- **Method**: Remaining unmatched tests become standalone canonical entries
- **Purpose**: Ensures every lab test maps to a canonical_test_id

### Matching Outcomes

```
Pass           │ Tests Matched │ Confidence │ Method
───────────────┼───────────────┼────────────┼──────────────────
Exact Name     │    ~5,000     │    1.00    │ exact_name
Alias Match    │    ~2,000     │    0.90    │ alias_match
Fuzzy Score    │    ~1,500     │  0.65-0.89 │ fuzzy_match
Singletons     │    ~3,500     │    1.00    │ singleton
───────────────┼───────────────┼────────────┼──────────────────
TOTAL          │   ~12,000     │            │
Canonical out  │   ~15,000     │            │
```

### Canonical Test Name Selection

For each cluster, the "best" name is chosen:
1. Prefer Neuberg names (most descriptive and standardized)
2. Otherwise, pick the longest name (more descriptive)
3. All variant names stored in `keywords` array for search

---

## 8. Dashboard Features

### Page 1: Search & Lab Quick-Filter (Home)

**URL**: `/`

The landing page presents a search-first interface with lab-specific browsing.

**Lab Quick-Filter Bar**: Four clickable cards (Metropolis, Agilus, Apollo, Neuberg) above the search box. TRUSTlab is excluded due to limited coverage.
- Click a lab → loads that lab's test catalog via `getLabTests()`
- Type a keyword while lab selected → searches within that lab only
- Click again → toggles off, returns to popular tests
- Placeholder text updates: "Search within Apollo..."

**Search Bar**: Text input + City dropdown + Department dropdown + Search button
- Global search: queries `canonical_tests` via ILIKE, fetches `lab_tests` pricing
- Lab-scoped search: filters canonical test names within the selected lab's offerings
- Keyboard: Enter key triggers search

**Results List**: Each result card shows:
- Test name + department badge
- Lab count ("4 labs")
- Price range ("Rs. 150 - Rs. 450")
- Potential savings ("Save up to Rs. 300")
- Click navigates to Compare page

### Page 2: Price Comparison

**URL**: `/compare?id={testId}`

Detailed side-by-side comparison for a single test across all labs.

**Price Summary Cards** (shown when 2+ labs have different prices):
- Green card: Cheapest lab + price
- Red card: Most expensive lab + price
- Blue card: Savings amount + percentage

**Bar Chart**: Horizontal bar chart of average price per lab
- Sorted by price ascending (cheapest first)
- Color-coded by lab brand colors
- Tooltip shows exact formatted price

**Comparison Table**:
| Column | Description |
|--------|-------------|
| Lab | Lab name with color indicator dot |
| City | City where test is offered |
| Price | Customer-facing price in Rs. |
| MRP | Maximum retail price |
| TAT | Turnaround time (hours or text) |
| Home | Home collection available (Yes/No) |
| NABL | NABL accredited (Yes/No) |
| Method | Test methodology (HPLC, ELISA, etc.) |

### Page 3: Price Heatmap

**URL**: `/heatmap`

Visual price comparison across labs for the top 100 tests in a city.

**City Selector**: Dropdown (defaults to Delhi), triggers data reload.

**Color-Coded Grid**:
- Rows: Top 100 tests sorted by price spread (largest differences first)
- Columns: Only labs with data for selected city (dynamic — TRUSTlab hidden when no data)
- Cell colors:
  - 0-25% of range: Green (cheapest)
  - 25-50%: Yellow
  - 50-75%: Orange
  - 75-100%: Red (most expensive)
  - No data: Gray
- Spread column: Shows absolute Rs. difference between cheapest and most expensive

**UX Features**: Sticky test name column on horizontal scroll, hover highlights, test names link to Compare page.

### Page 4: Availability Matrix

**URL**: `/availability`

Department-level test coverage analysis across labs.

**City Selector**: Dropdown (defaults to Delhi).

**Department x Lab Grid**:
- Rows: Medical departments with tests in the city
- Columns: Only labs with data for selected city (dynamic)
- Cells: Count of unique canonical tests per department per lab
- Color gradient based on relative count in row:
  - 80%+ of row max: Green (strong coverage)
  - 50-80%: Blue
  - 20-50%: Yellow
  - <20%: Orange (limited coverage)
  - 0: Gray (no tests)
- Lab totals displayed in column headers

**Department Normalization**: Client-side normalizer handles 30+ raw variations via exact match, substring match, and manual mapping dictionary.

### Floating Navigation Widget

Fixed-position panel on the right edge, vertically centered:
- Home button (navigate to /)
- Back button (browser history back)
- Forward button (browser history forward)
- Scroll Up (smooth scroll to top)
- Scroll Down (smooth scroll to bottom)
- Hidden on mobile (< 640px) for clean responsive design

### Smart TRUSTlab Visibility

TRUSTlab has limited geographic and test coverage compared to the other four labs. Rather than showing empty columns that add visual noise, the dashboard dynamically computes which labs have data for the current context:

- **Heatmap**: `activeLabs` computed from `PriceHeatmapEntry.lab_prices` keys
- **Availability**: `activeLabs` computed from `AvailabilityEntry.lab_slug` values with test_count > 0
- **Compare**: Already data-driven (only shows labs with pricing for that test)
- **Home**: Lab quick-filter excludes TRUSTlab; lab legend shows all 5 as reference

---

## 9. Deployment & Infrastructure

### Supabase Configuration

- **Plan**: Free tier (sufficient for ~300MB database)
- **PostgreSQL version**: 15
- **Extensions**: pg_trgm (enabled via `CREATE EXTENSION IF NOT EXISTS pg_trgm`)
- **RLS**: Enabled with public read policies on all tables
- **API**: REST API via PostgREST, accessed through supabase-js client

**Environment variables**:
```
SUPABASE_URL=https://[project].supabase.co
SUPABASE_ANON_KEY=[public_anon_key]          # Dashboard (read-only)
SUPABASE_SERVICE_ROLE_KEY=[service_role_key]  # Pipeline (admin)
```

### Cloudflare Pages

- **Build**: Next.js static export (`output: "export"` in next.config.ts)
- **Build command**: `cd dashboard && npm install && npm run build`
- **Output directory**: `dashboard/out`
- **Environment**: `NODE_VERSION=18`
- **CDN**: Global Cloudflare edge network
- **CI/CD**: Auto-deploy on push to `main` via GitHub integration

### GitHub Repository

- **URL**: github.com/musicofthings/lab-compare
- **Branch**: main
- **Excluded**: .env files, raw CSVs, PDFs, scraper scripts, iterative SQL fixes
- **Included**: Pipeline code, schema SQL, dashboard source, README, PLAN.md

---

## 10. Performance & Scalability

### Query Optimization Strategy

Supabase's free tier has a ~8 second statement timeout. Complex multi-table joins (e.g., joining 190K lab_tests with 15K canonical_tests, filtering by city, grouping by lab) consistently hit this limit.

**Solution**: Client-side data aggregation pattern:
1. Execute multiple simple, fast REST queries (each under 2 seconds)
2. Aggregate results in the browser
3. Paginate large result sets in 1000-row batches

This pattern is used for:
- **Search**: Query canonical_tests, then lab_tests, then aggregate pricing client-side
- **Heatmap**: Fetch lab_tests for city locations, group and average prices client-side
- **Availability**: Fetch lab_tests with department_raw, normalize and count client-side

### Database Size

```
Table              │ Rows     │ Est. Size
───────────────────┼──────────┼──────────
lab_tests          │ 190,000  │ ~285 MB
test_aliases       │  70,000  │  ~14 MB
canonical_tests    │  15,000  │  ~7.5 MB
lab_locations      │     100  │  ~10 KB
cities             │      80  │   ~5 KB
departments        │      20  │   ~2 KB
labs               │       5  │   ~1 KB
───────────────────┼──────────┼──────────
TOTAL              │ ~275,000 │ ~307 MB
```

Fits within Supabase's free tier (500 MB database limit).

### Matching Algorithm Performance

- Input: ~12,000 unique tests
- Pass 1 (grouping): O(n) — dict lookups, < 1 second
- Pass 2 (alias matching): O(n x m) where m = avg aliases — ~5 seconds
- Pass 3 (fuzzy scoring): O(n x k) where k = multi-member clusters — ~20 seconds
- Total: **< 30 seconds** on modern hardware

### Frontend Performance

- Static export: all pages pre-rendered as HTML, served from Cloudflare CDN
- Zero server-side rendering latency
- Client-side hydration: ~2-3 seconds for search page
- Data queries: 1-3 seconds depending on dataset size and city

---

## 11. Data Quality & Validation

### Match Confidence Tracking

Every `lab_test` record stores its matching confidence and method:

| Confidence | Method | Meaning |
|-----------|--------|---------|
| 1.00 | exact_name | Identical normalized names across labs |
| 0.90 | alias_match | Matched via Neuberg alias or name containment |
| 0.65-0.89 | fuzzy_match | Trigram + Jaccard + partial ratio scoring |
| 1.00 | singleton | No match found; standalone canonical entry |

### Data Completeness Matrix

```
Field              │ Metropolis │ Agilus │ Apollo │ Neuberg │ TRUSTlab
───────────────────┼────────────┼────────┼────────┼─────────┼─────────
Price              │    100%    │  100%  │  100%  │   98%   │   95%
Department         │      0%   │   85%  │  100%  │  100%   │   90%
TAT                │     90%   │   70%  │   95%  │   90%   │   80%
Methodology        │     80%   │   50%  │   90%  │   85%   │   60%
NABL Accredited    │    100%   │    0%  │    0%  │    0%   │    0%
Home Collection    │      0%   │    0%  │   20%  │    0%   │    0%
Fasting Required   │     90%   │    0%  │    0%  │    0%   │    0%
```

### Known Limitations

1. **Department gap**: Metropolis CSV lacks department data entirely, affecting the availability matrix accuracy for Delhi
2. **Name ambiguity**: Some generic tests ("Chemistry Profile") could validly match multiple canonical entries
3. **Pricing staleness**: CSV data is a point-in-time snapshot; prices may change at any time
4. **Geographic bias**: Delhi has the most data (3 labs are Delhi-only); smaller cities have fewer comparison options
5. **Package decomposition**: Lab package prices don't decompose into individual test costs

### Audit Trail

All original CSV data is preserved in the `raw_data` JSONB column of `lab_tests`. This enables:
- Full audit of how prices were extracted
- Re-running normalization with updated logic
- Debugging matching decisions
- Historical pricing analysis

---

## 12. Future Roadmap

### Short-Term Enhancements
- **Real-time pricing**: Integrate lab APIs (where available) for live price updates
- **Price alerts**: Notify users when a test they're tracking drops in price
- **Saved favorites**: User accounts with bookmarked tests and labs
- **Test recommendations**: "Patients who compared X also looked at Y"
- **Direct booking links**: Deep links to each lab's test booking page

### Medium-Term Features
- **Price trend charts**: Historical pricing data showing lab price changes over time
- **Health tracking**: Users log test results for longitudinal health monitoring
- **Mobile app**: React Native companion app for on-the-go comparison
- **Lab partnerships**: Negotiate platform-exclusive discounts
- **Analytics dashboard**: Track popular tests, price trends, seasonal patterns

### Long-Term Vision
- **20+ labs**: Expand to cover Thyrocare, Dr. Lal PathLabs, Redcliffe, iGenetic, and regional chains
- **International expansion**: Southeast Asia, Middle East diagnostic markets
- **Telehealth integration**: Connect with doctor platforms for test recommendations
- **Insurance integration**: Show which tests are covered under specific insurance plans
- **AI-powered matching**: Train ML models on confirmed matches to improve fuzzy matching accuracy
- **Blockchain verification**: Immutable test result storage and verification

---

## Appendix A: Project File Structure

```
D:\Projects\scraper\
├── PLAN.md                                 # Implementation plan
├── README.md                               # Setup & deployment docs
├── WHITEPAPER.md                           # This document
├── requirements.txt                        # Python dependencies
│
├── pipeline/
│   ├── __init__.py
│   ├── config.py                           # Supabase credentials, constants
│   ├── db.py                               # Supabase client wrapper
│   ├── models.py                           # NormalizedLabTest Pydantic model
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── base_loader.py                  # Abstract CSV loader
│   │   ├── metropolis_loader.py            # 3,187 tests
│   │   ├── agilus_loader.py                # 2,376 tests
│   │   ├── apollo_loader.py               # 151K rows → 2,786 unique
│   │   ├── neuberg_loader.py              # 23K rows → 2,838 unique
│   │   ├── trustlab_loader.py             # 1,764 tests
│   │   ├── city_normalizer.py             # Location code → city
│   │   ├── department_normalizer.py       # Raw dept → canonical
│   │   └── tat_normalizer.py              # TAT parsing → hours
│   └── matching/
│       ├── __init__.py
│       ├── preprocessor.py                 # Abbreviations, stripping, tokens
│       └── matcher.py                      # 4-pass matching algorithm
│
├── scripts/
│   ├── schema.sql                          # Full Supabase schema (DDL)
│   ├── run_pipeline.py                     # Pipeline orchestrator
│   ├── setup_supabase.py                   # Schema creation helper
│   ├── fix_linkage.py                      # Post-pipeline linkage fix
│   ├── fix_linkage_sql.sql                 # Bulk SQL linkage
│   └── fix_search_v2.sql                   # Search function + indexes
│
├── dashboard/
│   ├── next.config.ts                      # Static export config
│   ├── package.json                        # Dependencies
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx                  # Root layout + nav + FloatingNav
│   │   │   ├── globals.css                 # Tailwind + dark mode
│   │   │   ├── page.tsx                    # Search + lab quick-filter
│   │   │   ├── compare/page.tsx            # Price comparison + chart
│   │   │   ├── heatmap/page.tsx            # Price heatmap grid
│   │   │   └── availability/page.tsx       # Availability matrix
│   │   ├── components/
│   │   │   └── FloatingNav.tsx             # Fixed floating navigation
│   │   └── lib/
│   │       ├── supabase.ts                 # Client initialization
│   │       ├── queries.ts                  # All Supabase queries
│   │       └── types.ts                    # TypeScript interfaces
│   └── .env.local                          # Supabase public keys
│
└── (excluded from repo)
    ├── .env                                # Supabase service keys
    ├── *.csv                               # Raw lab CSVs
    └── extract_*.py                        # Scraper scripts
```

---

## Appendix B: Key Dependencies

### Python Pipeline
```
supabase>=2.0.0          # Supabase client
python-dotenv>=1.0.0     # Environment variables
pydantic>=2.0.0          # Data validation models
pandas>=2.0.0            # CSV/data manipulation
rapidfuzz>=3.0.0         # Fuzzy string matching
tqdm>=4.65.0             # Progress bars
pdfplumber>=0.11.0       # PDF extraction (Metropolis)
requests>=2.31.0         # HTTP client
beautifulsoup4>=4.12.0   # HTML parsing
```

### Dashboard
```
next: 16.1.6             # React framework
react: 19.2.3            # UI library
@supabase/supabase-js: ^2.95.3  # Database client
recharts: ^3.7.0         # Charts
@tanstack/react-table: ^8.21.3  # Data tables
tailwindcss: ^4           # CSS framework
typescript: ^5            # Type safety
```

---

*Lab Compare is a private project. All rights reserved.*
