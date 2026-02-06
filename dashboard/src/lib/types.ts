export interface Lab {
  id: number;
  name: string;
  slug: string;
  website_url: string | null;
}

export interface TestComparison {
  canonical_test_id: number;
  test_name: string;
  test_type: string | null;
  department: string | null;
  city: string | null;
  lab_name: string;
  lab_slug: string;
  price: number | null;
  mrp: number | null;
  discount_pct: number | null;
  tat_hours: number | null;
  tat_text: string | null;
  home_collection: boolean | null;
  nabl_accredited: boolean | null;
  match_confidence: number | null;
  methodology: string | null;
  sample_type: string | null;
}

export interface SearchResult {
  canonical_test_id: number;
  test_name: string;
  department: string | null;
  similarity_score: number;
  lab_count: number;
  min_price: number | null;
  max_price: number | null;
  avg_price: number | null;
}

export interface CanonicalTest {
  id: number;
  name: string;
  slug: string;
  department_id: number | null;
  test_type: string | null;
  keywords: string[] | null;
  is_popular: boolean;
}

export interface PriceHeatmapEntry {
  canonical_test_id: number;
  test_name: string;
  lab_prices: Record<string, number | null>;
  price_spread: number;
  lab_count: number;
}

export interface AvailabilityEntry {
  department: string;
  lab_slug: string;
  test_count: number;
}

export const LAB_COLORS: Record<string, string> = {
  metropolis: "#2563eb",
  agilus: "#16a34a",
  apollo: "#dc2626",
  neuberg: "#9333ea",
  trustlab: "#ea580c",
};

export const LAB_NAMES: Record<string, string> = {
  metropolis: "Metropolis",
  agilus: "Agilus",
  apollo: "Apollo",
  neuberg: "Neuberg",
  trustlab: "TRUSTlab",
};
