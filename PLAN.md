# Diagnostic Lab Test Comparison System - Implementation Plan

## Summary
Build a Supabase-powered relational database and Next.js dashboard that normalizes data from 5 diagnostic labs (Metropolis, Agilus, Apollo, Neuberg, TRUSTlab), matches equivalent tests across labs using keyword similarity, and displays lab-to-lab pricing/availability differences.

## Current State (Completed)
- Metropolis PDF extracted to CSV: 3,187 tests
- Agilus CSV: 2,376 tests
- Apollo CSV: 151,157 rows (2,786 unique tests across 68 centres)
- Neuberg CSV: 23,102 rows (2,838 unique tests across 15 cities)
- TRUSTlab CSV: 1,764 tests

---

## Phase 1: Project Setup & Supabase Schema

### Step 1.1: Create project structure
```
D:\Projects\scraper\
├── pipeline/
│   ├── __init__.py
│   ├── config.py              # Supabase URL, key, constants
│   ├── db.py                  # Supabase client wrapper
│   ├── models.py              # Pydantic models for normalized data
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── base_loader.py     # Abstract CSV loader
│   │   ├── metropolis_loader.py
│   │   ├── agilus_loader.py
│   │   ├── apollo_loader.py
│   │   ├── neuberg_loader.py
│   │   ├── trustlab_loader.py
│   │   ├── city_normalizer.py
│   │   ├── department_normalizer.py
│   │   └── tat_normalizer.py
│   └── matching/
│       ├── __init__.py
│       ├── preprocessor.py    # Text cleaning, abbreviation expansion
│       ├── matcher.py         # Multi-pass matching algorithm
│       └── cluster_builder.py # Canonical test creation
├── dashboard/                  # Next.js app
├── scripts/
│   ├── run_pipeline.py        # Full orchestrator
│   ├── setup_supabase.py      # Schema creation
│   └── seed_reference_data.py
├── requirements.txt
└── .env
```

### Step 1.2: Supabase Database Schema
Tables to create:
- **labs** - 5 diagnostic lab records
- **cities** - ~80 canonical cities
- **departments** - ~20 canonical departments
- **lab_locations** - Maps lab-specific location codes to canonical cities (~100 records)
- **canonical_tests** - Master test catalog (~3,000-4,000 tests) with pg_trgm indexes
- **lab_tests** - Per-lab, per-location test entries (~190,000 rows) - the fact table
- **test_aliases** - All known aliases for matching (~70,000 entries from Neuberg alone)
- **match_candidates** - Working table for uncertain matches needing review

Key features:
- `pg_trgm` extension for fuzzy name matching
- `search_tests()` PostgreSQL function for dashboard search
- `test_comparison` view for cross-lab queries
- RLS policies for public read access

---

## Phase 2: Python Data Pipeline

### Step 2.1: Per-lab CSV loaders with normalization

Each loader reads its lab's CSV and produces `NormalizedLabTest` objects with unified fields:
- **Metropolis**: Price -> mrp, parse fasting (YES/NO), NABL (Y/N), TAT from "Reported On"
- **Agilus**: Strip "Package in New delhi" from names, product_type -> test/package
- **Apollo**: Deduplicate 151K rows to 2,786 unique test_codes for matching, keep all rows for pricing
- **Neuberg**: Parse `alias_name` (pipe-delimited) into aliases list - critical for matching
- **TRUSTlab**: Expand comma-separated `location` field into per-city rows, use mrp for comparison

### Step 2.2: Normalizers
- **City normalizer**: Map Apollo centre codes (SL101, GRL0001), Neuberg city names, TRUSTlab locations (Begumpet -> Hyderabad) to canonical cities
- **Department normalizer**: Map "Bio Chemistry" -> "Biochemistry", "HAEMATOLOGY" -> "Haematology", etc.
- **TAT normalizer**: Parse "Same Day" -> 12h, "After 5 Days" -> 120h, tat_minutes -> hours

### Step 2.3: Upload to Supabase
- Batch upsert in chunks of 500 rows
- Store full original row in `raw_data` JSONB for reference
- Idempotent via UNIQUE constraints

---

## Phase 3: Test Matching Algorithm

Multi-pass strategy (highest to lowest confidence):

1. **Pass 1 - Exact Code Match** (confidence 1.0): Check for shared test codes across labs
2. **Pass 2 - Neuberg Alias Match** (confidence 0.95): Match against Neuberg's 70K+ alias entries
3. **Pass 3 - Normalized Name Match** (confidence 0.90): After preprocessing (lowercase, strip specimens, expand abbreviations)
4. **Pass 4 - Fuzzy Scoring** (confidence 0.60-0.89): Combined trigram similarity + token Jaccard + abbreviation-expanded overlap, scoped by department
5. **Pass 5 - Cluster Remainders**: Agglomerative clustering among unmatched tests within same department

**Preprocessing includes:**
- Medical abbreviation expansion (CBC -> Complete Blood Count, TSH -> Thyroid Stimulating Hormone, etc.)
- Specimen suffix stripping (", Serum", ", EDTA Blood", ", Urine 24 Hrs")
- Noise removal ("Package in New Delhi", asterisks)

**Expected outcome:** ~3,000-4,000 canonical tests covering the union of all labs

---

## Phase 4: Dashboard (Next.js)

### Key Views:
1. **Search & Compare** - Fuzzy search bar with city/department filters, results show test name + # labs + price range
2. **Single Test Comparison** (`/compare/[testId]`) - Table: Lab | City | Price | TAT | Home Collection | NABL + price bar chart
3. **Price Heatmap** (`/heatmap`) - Color-coded grid of top tests x labs for a selected city (green=cheap, red=expensive)
4. **Availability Matrix** (`/availability`) - Department x Lab grid showing test counts, with drill-down

### Tech Stack:
- Next.js 14 (App Router)
- @supabase/supabase-js for queries
- Tailwind CSS + shadcn/ui components
- Recharts for charts
- Tanstack Table for data grids

---

## Execution Order
1. Install dependencies (supabase, pydantic, rapidfuzz, etc.)
2. Create .env with Supabase credentials
3. Run schema SQL in Supabase
4. Build pipeline loaders + normalizers
5. Ingest all 5 CSVs into lab_tests
6. Run matching algorithm to create canonical_tests
7. Scaffold Next.js dashboard
8. Build search, comparison, heatmap, and availability views
