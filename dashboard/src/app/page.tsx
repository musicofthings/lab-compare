"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { searchTests, getCities, getDepartments, getPopularTests } from "@/lib/queries";
import { LAB_COLORS, LAB_NAMES } from "@/lib/types";
import type { SearchResult } from "@/lib/types";

export default function Home() {
  const [query, setQuery] = useState("");
  const [city, setCity] = useState("");
  const [department, setDepartment] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [cities, setCities] = useState<string[]>([]);
  const [departments, setDepartments] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  useEffect(() => {
    getCities().then(setCities);
    getDepartments().then(setDepartments);
    // Load popular tests initially
    getPopularTests().then((data) => {
      if (data.length > 0) setResults(data);
    });
  }, []);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSearched(true);
    const data = await searchTests(query, city || undefined, department || undefined);
    setResults(data);
    setLoading(false);
  }, [query, city, department]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch();
  };

  const formatPrice = (p: number | null) => {
    if (p === null || p === undefined) return "-";
    return `Rs. ${p.toLocaleString("en-IN")}`;
  };

  return (
    <div>
      {/* Hero Section */}
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Compare Diagnostic Test Prices
        </h1>
        <p className="text-gray-500 dark:text-gray-400">
          Search across Metropolis, Agilus, Apollo, Neuberg, and TRUSTlab
        </p>
      </div>

      {/* Search Bar */}
      <div className="bg-white dark:bg-gray-900 rounded-xl shadow-sm border border-gray-200 dark:border-gray-800 p-4 mb-6">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <input
              type="text"
              placeholder="Search tests... (e.g., CBC, Thyroid Profile, HbA1c)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              className="w-full px-4 py-2.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            />
          </div>
          <select
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className="px-3 py-2.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm"
          >
            <option value="">All Cities</option>
            {cities.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
          <select
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            className="px-3 py-2.5 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm"
          >
            <option value="">All Departments</option>
            {departments.map((d) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
          <button
            onClick={handleSearch}
            disabled={loading}
            className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium text-sm disabled:opacity-50"
          >
            {loading ? "Searching..." : "Search"}
          </button>
        </div>
      </div>

      {/* Results */}
      <div className="space-y-2">
        {!searched && results.length > 0 && (
          <h2 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-3">
            Popular Tests (available at 3+ labs)
          </h2>
        )}
        {searched && results.length === 0 && !loading && (
          <div className="text-center py-12 text-gray-500">
            No tests found for &quot;{query}&quot;. Try a different search term.
          </div>
        )}
        {results.map((r) => (
          <Link
            key={r.canonical_test_id}
            href={`/compare?id=${r.canonical_test_id}`}
            className="block bg-white dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-800 p-4 hover:border-blue-300 dark:hover:border-blue-700 transition-colors"
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <h3 className="font-medium text-gray-900 dark:text-white">
                  {r.test_name}
                </h3>
                <div className="flex items-center gap-3 mt-1">
                  {r.department && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400">
                      {r.department}
                    </span>
                  )}
                  <span className="text-xs text-gray-500">
                    {r.lab_count} lab{r.lab_count !== 1 ? "s" : ""}
                  </span>
                </div>
              </div>
              <div className="text-right">
                {r.min_price !== null && r.max_price !== null ? (
                  <div>
                    <div className="text-sm font-semibold text-gray-900 dark:text-white">
                      {formatPrice(r.min_price)}
                      {r.min_price !== r.max_price && (
                        <span className="text-gray-400"> - {formatPrice(r.max_price)}</span>
                      )}
                    </div>
                    {r.min_price !== r.max_price && (
                      <div className="text-xs text-green-600">
                        Save up to {formatPrice(r.max_price! - r.min_price!)}
                      </div>
                    )}
                  </div>
                ) : (
                  <span className="text-sm text-gray-400">Price N/A</span>
                )}
              </div>
            </div>
          </Link>
        ))}
      </div>

      {/* Lab Legend */}
      <div className="mt-8 flex flex-wrap justify-center gap-4">
        {Object.entries(LAB_NAMES).map(([slug, name]) => (
          <div key={slug} className="flex items-center gap-1.5">
            <span
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: LAB_COLORS[slug] }}
            />
            <span className="text-xs text-gray-500">{name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
