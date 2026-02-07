import { supabase } from "./supabase";
import type {
  TestComparison,
  SearchResult,
  PriceHeatmapEntry,
  AvailabilityEntry,
} from "./types";

export async function searchTests(
  query: string,
  city?: string,
  department?: string,
  limit = 50
): Promise<SearchResult[]> {
  // Step 1: Find matching canonical tests via ILIKE (fast, uses index)
  let ctQuery = supabase
    .from("canonical_tests")
    .select("id, name, test_type, department_id, departments(name)")
    .ilike("name", `%${query}%`)
    .limit(limit);

  if (department) {
    // Filter by department name via join
    ctQuery = ctQuery.eq("departments.name", department);
  }

  const { data: tests, error } = await ctQuery;
  if (error || !tests || tests.length === 0) {
    console.error("Search error:", error);
    return [];
  }

  // Step 2: Get pricing stats for matched tests from lab_tests
  const testIds = tests.map((t) => t.id);

  let ltQuery = supabase
    .from("lab_tests")
    .select("canonical_test_id, lab_id, price, lab_location_id")
    .in("canonical_test_id", testIds)
    .eq("is_active", true)
    .gt("price", 0);

  const { data: labTests } = await ltQuery;

  // If city filter, also fetch lab_locations for that city to filter client-side
  let validLocationIds: Set<number> | null = null;
  if (city) {
    const { data: cityData } = await supabase
      .from("cities")
      .select("id")
      .ilike("name", city)
      .limit(1);
    if (cityData && cityData.length > 0) {
      const { data: locations } = await supabase
        .from("lab_locations")
        .select("id")
        .eq("city_id", cityData[0].id);
      if (locations) {
        validLocationIds = new Set(locations.map((l) => l.id));
      }
    }
  }

  // Aggregate pricing per canonical_test_id
  const priceMap: Record<
    number,
    { labs: Set<number>; prices: number[] }
  > = {};

  for (const lt of labTests || []) {
    // Apply city filter if active
    if (validLocationIds && lt.lab_location_id && !validLocationIds.has(lt.lab_location_id)) {
      continue;
    }
    if (!priceMap[lt.canonical_test_id]) {
      priceMap[lt.canonical_test_id] = { labs: new Set(), prices: [] };
    }
    priceMap[lt.canonical_test_id].labs.add(lt.lab_id);
    if (lt.price > 0) {
      priceMap[lt.canonical_test_id].prices.push(lt.price);
    }
  }

  // Merge and return
  return tests.map((t) => {
    const stats = priceMap[t.id];
    const deptRaw = t.departments as unknown;
    const dept = Array.isArray(deptRaw) ? deptRaw[0] as { name: string } | undefined : deptRaw as { name: string } | null;
    const prices = stats?.prices || [];
    return {
      canonical_test_id: t.id,
      test_name: t.name,
      department: dept?.name || null,
      similarity_score: 0.5,
      lab_count: stats?.labs.size || 0,
      min_price: prices.length ? Math.min(...prices) : null,
      max_price: prices.length ? Math.max(...prices) : null,
      avg_price: prices.length
        ? Math.round(prices.reduce((a, b) => a + b, 0) / prices.length)
        : null,
    };
  })
  // Sort: tests with lab data first, then by lab count desc
  .sort((a, b) => b.lab_count - a.lab_count);
}

export async function getTestComparison(
  testId: number,
  city?: string
): Promise<TestComparison[]> {
  let query = supabase
    .from("test_comparison")
    .select("*")
    .eq("canonical_test_id", testId)
    .order("price", { ascending: true });

  if (city) {
    query = query.eq("city", city);
  }

  const { data, error } = await query;
  if (error) {
    console.error("Comparison error:", error);
    return [];
  }
  return data || [];
}

export async function getTestDetails(testId: number) {
  const { data, error } = await supabase
    .from("canonical_tests")
    .select("*, departments(name)")
    .eq("id", testId)
    .single();

  if (error) {
    console.error("Test details error:", error);
    return null;
  }
  return data;
}

// Helper: get lab_location IDs for a city
async function getLocationIdsForCity(city: string): Promise<number[]> {
  const { data: cityData } = await supabase
    .from("cities")
    .select("id")
    .ilike("name", city)
    .limit(1);
  if (!cityData || cityData.length === 0) return [];

  const { data: locations } = await supabase
    .from("lab_locations")
    .select("id")
    .eq("city_id", cityData[0].id);

  return (locations || []).map((l) => l.id);
}

// Helper: paginated fetch from lab_tests
async function fetchLabTestsForLocations(
  locationIds: number[],
  fields: string
): Promise<Record<string, unknown>[]> {
  let allRows: Record<string, unknown>[] = [];
  let offset = 0;
  const pageSize = 1000;

  while (true) {
    const { data: page } = await supabase
      .from("lab_tests")
      .select(fields)
      .in("lab_location_id", locationIds)
      .eq("is_active", true)
      .not("canonical_test_id", "is", null)
      .range(offset, offset + pageSize - 1);

    if (!page || page.length === 0) break;
    allRows = allRows.concat(page as unknown as Record<string, unknown>[]);
    if (page.length < pageSize) break;
    offset += pageSize;
  }

  return allRows;
}

// Helper: get lab slug map
async function getLabSlugMap(): Promise<Record<number, string>> {
  const { data: labs } = await supabase.from("labs").select("id, slug");
  const map: Record<number, string> = {};
  for (const l of labs || []) map[l.id] = l.slug;
  return map;
}

export async function getPriceHeatmap(
  city: string,
  limit = 100
): Promise<PriceHeatmapEntry[]> {
  const locationIds = await getLocationIdsForCity(city);
  if (locationIds.length === 0) return [];

  const allRows = await fetchLabTestsForLocations(
    locationIds,
    "canonical_test_id, lab_id, price"
  );

  const labSlugMap = await getLabSlugMap();

  // Get canonical test names
  const testIds = [...new Set(allRows.map((r) => r.canonical_test_id as number))];
  const nameMap: Record<number, string> = {};
  for (let i = 0; i < testIds.length; i += 200) {
    const batch = testIds.slice(i, i + 200);
    const { data: names } = await supabase
      .from("canonical_tests")
      .select("id, name")
      .in("id", batch);
    for (const n of names || []) nameMap[n.id] = n.name;
  }

  // Group by canonical_test_id
  const grouped: Record<number, { prices: Record<string, number[]> }> = {};
  for (const row of allRows) {
    const price = row.price as number;
    if (!price || price <= 0) continue;
    const ctId = row.canonical_test_id as number;
    const slug = labSlugMap[row.lab_id as number];
    if (!slug) continue;

    if (!grouped[ctId]) grouped[ctId] = { prices: {} };
    if (!grouped[ctId].prices[slug]) grouped[ctId].prices[slug] = [];
    grouped[ctId].prices[slug].push(price);
  }

  // Convert to heatmap entries, filtering to 2+ labs
  const entries: PriceHeatmapEntry[] = [];
  for (const [testId, g] of Object.entries(grouped)) {
    const labSlugs = Object.keys(g.prices);
    if (labSlugs.length < 2) continue;

    const labPrices: Record<string, number | null> = {};
    let minP = Infinity;
    let maxP = -Infinity;

    for (const slug of labSlugs) {
      const avg =
        g.prices[slug].reduce((a, b) => a + b, 0) / g.prices[slug].length;
      labPrices[slug] = Math.round(avg);
      minP = Math.min(minP, avg);
      maxP = Math.max(maxP, avg);
    }

    entries.push({
      canonical_test_id: Number(testId),
      test_name: nameMap[Number(testId)] || `Test #${testId}`,
      lab_prices: labPrices,
      price_spread: Math.round(maxP - minP),
      lab_count: labSlugs.length,
    });
  }

  entries.sort((a, b) => b.price_spread - a.price_spread);
  return entries.slice(0, limit);
}

export async function getAvailabilityMatrix(
  city: string
): Promise<AvailabilityEntry[]> {
  const locationIds = await getLocationIdsForCity(city);
  if (locationIds.length === 0) return [];

  // Fetch lab_tests with department_raw (since canonical_tests.department_id is not populated)
  const allRows = await fetchLabTestsForLocations(
    locationIds,
    "canonical_test_id, lab_id, department_raw"
  );

  const labSlugMap = await getLabSlugMap();

  // Build department normalizer from the departments table
  const { data: depts } = await supabase.from("departments").select("name");
  const canonicalDeptNames = (depts || []).map((d) => d.name);

  // Map raw department names to canonical ones
  // Handles: "Bio chemistry" -> "Biochemistry", "HAEMATOLOGY" -> "Haematology",
  // "Biochemistry." -> "Biochemistry", "Clinical chemistry" -> "Biochemistry", etc.
  function normalizeDept(raw: string): string | null {
    if (!raw) return null;
    // Strip trailing dots, extra spaces, lowercase for comparison
    const cleaned = raw.trim().replace(/\.+$/, "").replace(/\s+/g, " ");
    const lower = cleaned.toLowerCase().replace(/\s/g, "");

    // Try exact match first (case-insensitive, ignore spaces)
    for (const cd of canonicalDeptNames) {
      if (cd.toLowerCase().replace(/\s/g, "") === lower) return cd;
    }

    // Try substring/contains match (e.g., "Bio chemistry" contains "biochemistry")
    for (const cd of canonicalDeptNames) {
      const cdLower = cd.toLowerCase().replace(/\s/g, "");
      if (lower.includes(cdLower) || cdLower.includes(lower)) return cd;
    }

    // Common manual mappings
    const manualMap: Record<string, string> = {
      "clinicalchemistry": "Biochemistry",
      "specialchemistry": "Biochemistry",
      "proteinchemistry": "Biochemistry",
      "serologyimmunology": "Serology",
      "immunology": "Serology",
      "eiainfectioussection": "Serology",
      "eiaautoimmunesection": "Serology",
      "eiainfectious": "Serology",
      "eiaautoimmune": "Serology",
      "autoimmune": "Serology",
      "automuineifa": "Serology",
      "nephelometry": "Serology",
      "molecularbiology": "Molecular Biology",
      "genomicsandmoleculardiagnostics": "Molecular Biology",
      "advancedmoleculardiagnosticsr": "Molecular Biology",
      "coagulation": "Haematology",
      "flowcytometry": "Haematology",
      "coehistopath": "Histopathology",
      "immunohistochemistry": "Histopathology",
      "hplc": "Biochemistry",
      "metals": "Biochemistry",
      "torch": "Serology",
      "tumormarker": "Serology",
      "maternalmarker": "Biochemistry",
      "mycology": "Microbiology",
      "radiology": "Radiology",
    };

    const noSpace = cleaned.toLowerCase().replace(/[\s\-\/\.]/g, "");
    if (manualMap[noSpace]) return manualMap[noSpace];

    // Filter out noise entries that aren't real departments
    const noise = new Set([
      "localsendout", "internationalsendout", "outsource",
      "marketing", "corporate", "package", "other",
      "superreligarelaboratoriesltd", "homecollection",
    ]);
    if (noise.has(noSpace)) return null;

    // Fallback: title case
    return cleaned.charAt(0).toUpperCase() + cleaned.slice(1).toLowerCase();
  }

  // Count unique tests per department per lab
  const counts: Record<string, Record<string, Set<number>>> = {};
  for (const row of allRows) {
    const ctId = row.canonical_test_id as number;
    const rawDept = row.department_raw as string;
    if (!rawDept) continue;
    const dept = normalizeDept(rawDept);
    if (!dept) continue;
    const slug = labSlugMap[row.lab_id as number];
    if (!slug) continue;

    if (!counts[dept]) counts[dept] = {};
    if (!counts[dept][slug]) counts[dept][slug] = new Set();
    counts[dept][slug].add(ctId);
  }

  const entries: AvailabilityEntry[] = [];
  for (const [dept, labs] of Object.entries(counts)) {
    for (const [slug, tests] of Object.entries(labs)) {
      entries.push({
        department: dept,
        lab_slug: slug,
        test_count: tests.size,
      });
    }
  }

  return entries;
}

export async function getCities(): Promise<string[]> {
  const { data, error } = await supabase
    .from("cities")
    .select("name")
    .order("name");

  if (error) return [];
  return (data || []).map((c) => c.name);
}

export async function getDepartments(): Promise<string[]> {
  const { data, error } = await supabase
    .from("departments")
    .select("name")
    .order("name");

  if (error) return [];
  return (data || []).map((d) => d.name);
}

export async function getLabTests(
  labSlug: string,
  city?: string,
  limit = 50
): Promise<SearchResult[]> {
  // Step 1: Get the lab ID from slug
  const { data: labData } = await supabase
    .from("labs")
    .select("id")
    .eq("slug", labSlug)
    .limit(1);

  if (!labData || labData.length === 0) return [];
  const labId = labData[0].id;

  // Step 2: Get lab_tests for this lab (with optional city filter)
  let ltQuery = supabase
    .from("lab_tests")
    .select("canonical_test_id, price, lab_location_id")
    .eq("lab_id", labId)
    .eq("is_active", true)
    .gt("price", 0)
    .not("canonical_test_id", "is", null)
    .limit(1000);

  if (city) {
    const locationIds = await getLocationIdsForCity(city);
    if (locationIds.length > 0) {
      ltQuery = ltQuery.in("lab_location_id", locationIds);
    } else {
      return [];
    }
  }

  const { data: labTests } = await ltQuery;
  if (!labTests || labTests.length === 0) return [];

  // Step 3: Group by canonical_test_id
  const testPriceMap: Record<number, number[]> = {};
  for (const lt of labTests) {
    const ctId = lt.canonical_test_id as number;
    if (!testPriceMap[ctId]) testPriceMap[ctId] = [];
    if (lt.price > 0) testPriceMap[ctId].push(lt.price);
  }

  const testIds = Object.keys(testPriceMap).map(Number);

  // Step 4: Batch-fetch canonical test names
  const nameMap: Record<number, { name: string; department: string | null }> = {};
  for (let i = 0; i < testIds.length; i += 200) {
    const batch = testIds.slice(i, i + 200);
    const { data: tests } = await supabase
      .from("canonical_tests")
      .select("id, name, departments(name)")
      .in("id", batch);
    for (const t of tests || []) {
      const deptRaw = t.departments as unknown;
      const dept = Array.isArray(deptRaw)
        ? (deptRaw[0] as { name: string } | undefined)
        : (deptRaw as { name: string } | null);
      nameMap[t.id] = { name: t.name, department: dept?.name || null };
    }
  }

  // Step 5: Build SearchResult[] sorted by name
  const results: SearchResult[] = testIds
    .filter((id) => nameMap[id])
    .map((id) => {
      const prices = testPriceMap[id];
      return {
        canonical_test_id: id,
        test_name: nameMap[id].name,
        department: nameMap[id].department,
        similarity_score: 1.0,
        lab_count: 1,
        min_price: prices.length ? Math.min(...prices) : null,
        max_price: prices.length ? Math.max(...prices) : null,
        avg_price: prices.length
          ? Math.round(prices.reduce((a, b) => a + b, 0) / prices.length)
          : null,
      };
    })
    .sort((a, b) => (a.test_name || "").localeCompare(b.test_name || ""));

  return results.slice(0, limit);
}

export async function getPopularTests(): Promise<SearchResult[]> {
  const { data, error } = await supabase
    .from("canonical_tests")
    .select(
      `
      id,
      name,
      test_type,
      is_popular,
      lab_tests(lab_id, price)
    `
    )
    .eq("is_popular", true)
    .limit(50);

  if (error || !data) return [];

  return data.map((t) => {
    const prices = (t.lab_tests || [])
      .map((lt: { price: number | null }) => lt.price)
      .filter((p: number | null): p is number => p !== null && p > 0);
    const labIds = new Set(
      (t.lab_tests || []).map((lt: { lab_id: number }) => lt.lab_id)
    );

    return {
      canonical_test_id: t.id,
      test_name: t.name,
      department: null,
      similarity_score: 1.0,
      lab_count: labIds.size,
      min_price: prices.length ? Math.min(...prices) : null,
      max_price: prices.length ? Math.max(...prices) : null,
      avg_price: prices.length
        ? Math.round(prices.reduce((a: number, b: number) => a + b, 0) / prices.length)
        : null,
    };
  });
}
