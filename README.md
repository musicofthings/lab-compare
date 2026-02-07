# Lab Compare — Diagnostic Lab Test Price Comparison

Compare diagnostic test prices across **5 major Indian labs** — Metropolis, Agilus, Apollo, Neuberg, and TRUSTlab — with a unified search, price comparison, heatmap, and availability dashboard.

![Next.js](https://img.shields.io/badge/Next.js-16-black) ![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-3ECF8E) ![Python](https://img.shields.io/badge/Python-3.10+-3776AB) ![Cloudflare Pages](https://img.shields.io/badge/Deploy-Cloudflare%20Pages-F38020)

## Overview

| Metric | Value |
|--------|-------|
| Canonical tests | ~15,000 |
| Lab test rows | ~190,000 |
| Lab locations | ~100 across India |
| Labs covered | Metropolis, Agilus, Apollo, Neuberg, TRUSTlab |

The system has three parts:

1. **Python Data Pipeline** — Loads CSVs from 5 labs, normalizes names/cities/departments, uploads to Supabase, and runs a multi-pass fuzzy matching algorithm to create canonical test entries.
2. **Supabase Backend** — PostgreSQL database with `pg_trgm` indexes, RLS policies for public read access, and optimized views.
3. **Next.js Dashboard** — Static site with search, comparison, heatmap, and availability pages. Deploys to Cloudflare Pages.

## Dashboard Pages

| Page | Route | Description |
|------|-------|-------------|
| **Search** | `/` | Fuzzy search tests by name, filter by city. Shows price range and lab count. |
| **Compare** | `/compare?id={testId}` | Side-by-side lab pricing with bar chart, price summary cards, and detail table. |
| **Heatmap** | `/heatmap` | Color-coded price grid (top 50 tests × labs) for a selected city. |
| **Availability** | `/availability` | Department × Lab matrix showing how many tests each lab offers. |

## Tech Stack

- **Pipeline**: Python 3.10+, pandas, rapidfuzz, pydantic, supabase-py
- **Database**: Supabase (PostgreSQL 15) with pg_trgm extension
- **Frontend**: Next.js 16 (App Router), React 19, Tailwind CSS 4, Recharts, TanStack Table
- **Deployment**: Cloudflare Pages (static export)

## Project Structure

```
├── pipeline/                  # Python data pipeline
│   ├── config.py              # Supabase credentials & constants
│   ├── db.py                  # Supabase client wrapper
│   ├── models.py              # Pydantic models
│   ├── ingest/                # Per-lab CSV loaders + normalizers
│   │   ├── metropolis_loader.py
│   │   ├── agilus_loader.py
│   │   ├── apollo_loader.py
│   │   ├── neuberg_loader.py
│   │   ├── trustlab_loader.py
│   │   ├── city_normalizer.py
│   │   ├── department_normalizer.py
│   │   └── tat_normalizer.py
│   └── matching/              # Multi-pass fuzzy matching
│       ├── matcher.py
│       └── preprocessor.py
├── scripts/
│   ├── schema.sql             # Full Supabase schema
│   ├── setup_supabase.py      # Schema creation helper
│   ├── run_pipeline.py        # Full pipeline orchestrator
│   ├── fix_linkage.py         # Link lab_tests → canonical_tests
│   ├── fix_linkage_sql.sql    # Bulk SQL linkage fix
│   └── fix_search_v2.sql      # Optimized search function + indexes
├── dashboard/                 # Next.js frontend
│   ├── src/
│   │   ├── app/               # App Router pages
│   │   │   ├── page.tsx              # Search page
│   │   │   ├── compare/page.tsx      # Price comparison
│   │   │   ├── heatmap/page.tsx      # Price heatmap
│   │   │   └── availability/page.tsx # Availability matrix
│   │   └── lib/
│   │       ├── queries.ts     # Supabase query functions
│   │       ├── supabase.ts    # Supabase client init
│   │       └── types.ts       # TypeScript interfaces
│   ├── next.config.ts         # Static export config
│   └── package.json
├── requirements.txt           # Python dependencies
└── PLAN.md                    # Original implementation plan
```

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- A [Supabase](https://supabase.com) project (free tier works)

### 1. Supabase Database Setup

1. Create a new Supabase project.
2. In the SQL Editor, run `scripts/schema.sql` to create all tables, indexes, views, and RLS policies.
3. Enable the `pg_trgm` extension (the schema script does this automatically).

### 2. Environment Variables

Create a `.env` file in the project root for the Python pipeline:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

Create `dashboard/.env.local` for the Next.js dashboard:

```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### 3. Run the Data Pipeline

```bash
# Install Python dependencies
pip install -r requirements.txt

# Place lab CSV files in the project root:
#   - metropolis.csv
#   - agilus.csv
#   - apollo.csv
#   - neuberg.csv
#   - trustlab.csv

# Run the full pipeline (loads, normalizes, matches)
python scripts/run_pipeline.py
```

The pipeline will:
- Load and normalize CSV data from all 5 labs
- Upload ~190K lab test rows to Supabase
- Run 4-pass fuzzy matching to create ~15K canonical tests
- Link lab tests to their canonical entries

### 4. Post-Pipeline SQL Fixes

After the pipeline completes, run these in the Supabase SQL Editor for optimal linkage:

```sql
-- Run fix_linkage_sql.sql to bulk-link remaining unlinked lab_tests
-- Run fix_search_v2.sql to create optimized search indexes
```

### 5. Run the Dashboard Locally

```bash
cd dashboard
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to see the dashboard.

## Deployment to Cloudflare Pages

The dashboard is configured for static export (`output: "export"` in `next.config.ts`), making it compatible with Cloudflare Pages.

### Option A: Deploy via Cloudflare Dashboard

1. Go to [Cloudflare Pages](https://dash.cloudflare.com/?to=/:account/pages) and click **Create a project**.
2. Connect your GitHub repository (`musicofthings/lab-compare`).
3. Configure the build settings:

   | Setting | Value |
   |---------|-------|
   | **Framework preset** | Next.js (Static HTML Export) |
   | **Build command** | `cd dashboard && npm install && npm run build` |
   | **Build output directory** | `dashboard/out` |
   | **Root directory** | `/` |

4. Add environment variables:

   | Variable | Value |
   |----------|-------|
   | `NEXT_PUBLIC_SUPABASE_URL` | `https://your-project.supabase.co` |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `your-anon-key` |
   | `NODE_VERSION` | `18` |

5. Click **Save and Deploy**.

### Option B: Deploy via Wrangler CLI

```bash
# Install Wrangler
npm install -g wrangler

# Login to Cloudflare
wrangler login

# Build the static site
cd dashboard
npm run build

# Deploy
wrangler pages deploy out --project-name=lab-compare
```

### Custom Domain (Optional)

After deployment, you can add a custom domain:
1. Go to your Pages project → **Custom domains**.
2. Add your domain and follow the DNS instructions.

## Database Schema

```
labs (5 rows)
  └── lab_locations (~100 rows)
        └── lab_tests (~190K rows) → canonical_tests (~15K rows)
                                        └── departments
cities (~80 rows)
```

Key tables:
- **`labs`** — Lab metadata (name, slug, website)
- **`lab_locations`** — Per-lab location/centre entries mapped to canonical cities
- **`canonical_tests`** — Deduplicated master test catalog
- **`lab_tests`** — Individual test entries per lab per location with pricing, TAT, methodology
- **`test_comparison`** — Materialized view joining lab_tests with lab names and cities

## Matching Algorithm

The pipeline uses a 4-pass approach to match tests across labs:

1. **Exact code match** (confidence 1.0) — shared test codes
2. **Alias match** (confidence 0.95) — Neuberg's 70K+ alias entries
3. **Normalized name match** (confidence 0.90) — after preprocessing (lowercase, abbreviation expansion, specimen stripping)
4. **Fuzzy scoring** (confidence 0.60–0.89) — trigram similarity + token Jaccard, scoped by department

## Notes

- **Supabase free tier** has a ~8s statement timeout. Complex joins are handled client-side to avoid timeouts.
- **Apollo** has 151K+ rows (2,786 unique tests across 68 centres) — the largest dataset.
- **Metropolis and Neuberg** may show 0 in the availability matrix if their source CSVs lack department data.
- The dashboard uses client-side data aggregation for search, heatmap, and availability to work within Supabase REST API limits.

## License

Private project — all rights reserved.
