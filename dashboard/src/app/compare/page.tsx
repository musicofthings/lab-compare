"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { getTestComparison, getTestDetails, getCities } from "@/lib/queries";
import { LAB_COLORS, LAB_NAMES } from "@/lib/types";
import type { TestComparison } from "@/lib/types";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

function CompareContent() {
  const searchParams = useSearchParams();
  const testId = searchParams.get("id") || "";
  const [data, setData] = useState<TestComparison[]>([]);
  const [testInfo, setTestInfo] = useState<{ name: string; test_type: string | null } | null>(null);
  const [selectedCity, setSelectedCity] = useState("");
  const [cities, setCities] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!testId) return;
    getCities().then(setCities);
    getTestDetails(Number(testId)).then((info) => {
      if (info) setTestInfo({ name: info.name, test_type: info.test_type });
    });
  }, [testId]);

  useEffect(() => {
    if (!testId) return;
    setLoading(true);
    getTestComparison(Number(testId), selectedCity || undefined).then((d) => {
      setData(d);
      setLoading(false);
    });
  }, [testId, selectedCity]);

  const formatPrice = (p: number | null) => {
    if (p === null || p === undefined) return "-";
    return `Rs. ${p.toLocaleString("en-IN")}`;
  };

  if (!testId) {
    return (
      <div className="text-center py-12 text-gray-500">
        No test selected. <Link href="/" className="text-blue-600 hover:underline">Go back to search</Link>
      </div>
    );
  }

  // Group by lab for chart (average price per lab)
  const labPrices: Record<string, { prices: number[]; slug: string }> = {};
  for (const row of data) {
    if (row.price && row.price > 0) {
      if (!labPrices[row.lab_slug]) {
        labPrices[row.lab_slug] = { prices: [], slug: row.lab_slug };
      }
      labPrices[row.lab_slug].prices.push(row.price);
    }
  }

  const chartData = Object.entries(labPrices)
    .map(([slug, { prices }]) => ({
      lab: LAB_NAMES[slug] || slug,
      slug,
      price: Math.round(prices.reduce((a, b) => a + b, 0) / prices.length),
    }))
    .sort((a, b) => a.price - b.price);

  // Deduplicate for table: one row per (lab_slug, city)
  const seen = new Set<string>();
  const tableRows = data.filter((r) => {
    const key = `${r.lab_slug}-${r.city || ""}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  const cheapest = chartData.length > 0 ? chartData[0] : null;
  const mostExpensive = chartData.length > 0 ? chartData[chartData.length - 1] : null;

  return (
    <div>
      <Link href="/" className="text-sm text-blue-600 hover:underline mb-4 inline-block">
        &larr; Back to search
      </Link>

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          {testInfo?.name || `Test #${testId}`}
        </h1>
        {testInfo?.test_type && (
          <span className="text-xs px-2 py-0.5 mt-1 inline-block rounded-full bg-gray-100 dark:bg-gray-800 text-gray-500">
            {testInfo.test_type}
          </span>
        )}
      </div>

      {/* City Filter */}
      <div className="mb-6">
        <select
          value={selectedCity}
          onChange={(e) => setSelectedCity(e.target.value)}
          className="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm"
        >
          <option value="">All Cities</option>
          {cities.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading comparison data...</div>
      ) : data.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          No pricing data available for this test.
        </div>
      ) : (
        <>
          {/* Price Summary */}
          {cheapest && mostExpensive && cheapest.slug !== mostExpensive.slug && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
              <div className="bg-green-50 dark:bg-green-950 rounded-lg p-4 border border-green-200 dark:border-green-800">
                <div className="text-xs text-green-600 font-medium">Cheapest</div>
                <div className="text-lg font-bold text-green-700 dark:text-green-400">
                  {formatPrice(cheapest.price)}
                </div>
                <div className="text-sm text-green-600">{cheapest.lab}</div>
              </div>
              <div className="bg-red-50 dark:bg-red-950 rounded-lg p-4 border border-red-200 dark:border-red-800">
                <div className="text-xs text-red-600 font-medium">Most Expensive</div>
                <div className="text-lg font-bold text-red-700 dark:text-red-400">
                  {formatPrice(mostExpensive.price)}
                </div>
                <div className="text-sm text-red-600">{mostExpensive.lab}</div>
              </div>
              <div className="bg-blue-50 dark:bg-blue-950 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
                <div className="text-xs text-blue-600 font-medium">You Could Save</div>
                <div className="text-lg font-bold text-blue-700 dark:text-blue-400">
                  {formatPrice(mostExpensive.price - cheapest.price)}
                </div>
                <div className="text-sm text-blue-600">
                  {Math.round(((mostExpensive.price - cheapest.price) / mostExpensive.price) * 100)}% less
                </div>
              </div>
            </div>
          )}

          {/* Bar Chart */}
          {chartData.length > 1 && (
            <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4 mb-6">
              <h2 className="text-sm font-medium text-gray-500 mb-4">Price by Lab</h2>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={chartData} layout="vertical" margin={{ left: 80 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" tickFormatter={(v) => `Rs.${v}`} />
                  <YAxis type="category" dataKey="lab" width={80} />
                  <Tooltip formatter={(value) => [`Rs. ${Number(value).toLocaleString("en-IN")}`, "Price"]} />
                  <Bar dataKey="price" radius={[0, 4, 4, 0]}>
                    {chartData.map((entry) => (
                      <Cell key={entry.slug} fill={LAB_COLORS[entry.slug] || "#6b7280"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Comparison Table */}
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                    <th className="px-4 py-3 text-left font-medium text-gray-500">Lab</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-500">City</th>
                    <th className="px-4 py-3 text-right font-medium text-gray-500">Price</th>
                    <th className="px-4 py-3 text-right font-medium text-gray-500">MRP</th>
                    <th className="px-4 py-3 text-center font-medium text-gray-500">TAT</th>
                    <th className="px-4 py-3 text-center font-medium text-gray-500">Home</th>
                    <th className="px-4 py-3 text-center font-medium text-gray-500">NABL</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-500">Method</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                  {tableRows.map((row, i) => (
                    <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span
                            className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                            style={{ backgroundColor: LAB_COLORS[row.lab_slug] || "#6b7280" }}
                          />
                          <span className="font-medium text-gray-900 dark:text-white">
                            {LAB_NAMES[row.lab_slug] || row.lab_name}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                        {row.city || "-"}
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-gray-900 dark:text-white">
                        {formatPrice(row.price)}
                      </td>
                      <td className="px-4 py-3 text-right text-gray-500">
                        {formatPrice(row.mrp)}
                      </td>
                      <td className="px-4 py-3 text-center text-gray-500">
                        {row.tat_text || (row.tat_hours ? `${row.tat_hours}h` : "-")}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {row.home_collection === true ? (
                          <span className="text-green-600">Yes</span>
                        ) : row.home_collection === false ? (
                          <span className="text-gray-400">No</span>
                        ) : (
                          <span className="text-gray-300">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {row.nabl_accredited === true ? (
                          <span className="text-green-600">Yes</span>
                        ) : row.nabl_accredited === false ? (
                          <span className="text-gray-400">No</span>
                        ) : (
                          <span className="text-gray-300">-</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-500 max-w-[200px] truncate">
                        {row.methodology || "-"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={<div className="text-center py-12 text-gray-500">Loading...</div>}>
      <CompareContent />
    </Suspense>
  );
}
