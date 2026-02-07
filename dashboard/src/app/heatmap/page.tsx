"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import { getPriceHeatmap, getCities } from "@/lib/queries";
import { LAB_COLORS, LAB_NAMES } from "@/lib/types";
import type { PriceHeatmapEntry } from "@/lib/types";

function getPriceColor(
  price: number | null,
  minPrice: number,
  maxPrice: number
): string {
  if (price === null || price === undefined) return "bg-gray-100 dark:bg-gray-800";
  if (maxPrice === minPrice) return "bg-yellow-100 dark:bg-yellow-900";

  const ratio = (price - minPrice) / (maxPrice - minPrice);
  if (ratio < 0.25) return "bg-green-200 dark:bg-green-900 text-green-800 dark:text-green-200";
  if (ratio < 0.5) return "bg-yellow-100 dark:bg-yellow-900 text-yellow-800 dark:text-yellow-200";
  if (ratio < 0.75) return "bg-orange-200 dark:bg-orange-900 text-orange-800 dark:text-orange-200";
  return "bg-red-200 dark:bg-red-900 text-red-800 dark:text-red-200";
}

export default function HeatmapPage() {
  const [city, setCity] = useState("Delhi");
  const [cities, setCities] = useState<string[]>([]);
  const [data, setData] = useState<PriceHeatmapEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCities().then((c) => {
      setCities(c);
      if (c.length > 0 && !c.includes(city)) setCity(c[0]);
    });
  }, []);

  useEffect(() => {
    if (!city) return;
    setLoading(true);
    getPriceHeatmap(city, 100).then((d) => {
      setData(d);
      setLoading(false);
    });
  }, [city]);

  const formatPrice = (p: number | null) => {
    if (p === null || p === undefined) return "-";
    if (p >= 10000) return `${(p / 1000).toFixed(1)}K`;
    return p.toLocaleString("en-IN");
  };

  // Compute which labs actually have data for this city
  const activeLabs = useMemo(() => {
    const labSet = new Set<string>();
    for (const entry of data) {
      for (const slug of Object.keys(entry.lab_prices)) {
        if (entry.lab_prices[slug] !== null) {
          labSet.add(slug);
        }
      }
    }
    const preferredOrder = ["metropolis", "agilus", "apollo", "neuberg", "trustlab"];
    return preferredOrder.filter((slug) => labSet.has(slug));
  }, [data]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Price Heatmap</h1>
          <p className="text-sm text-gray-500 mt-1">
            Compare test prices across labs. Green = cheapest, Red = most expensive.
          </p>
        </div>
        <select
          value={city}
          onChange={(e) => setCity(e.target.value)}
          className="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm"
        >
          {cities.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-500">Loading heatmap data for {city}...</div>
      ) : data.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          No cross-lab pricing data available for {city}.
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                  <th className="px-4 py-3 text-left font-medium text-gray-500 sticky left-0 bg-gray-50 dark:bg-gray-800 min-w-[250px]">
                    Test Name
                  </th>
                  {activeLabs.map((slug) => (
                    <th key={slug} className="px-3 py-3 text-center font-medium min-w-[100px]">
                      <div className="flex items-center justify-center gap-1">
                        <span
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: LAB_COLORS[slug] }}
                        />
                        <span className="text-gray-500">{LAB_NAMES[slug]}</span>
                      </div>
                    </th>
                  ))}
                  <th className="px-3 py-3 text-right font-medium text-gray-500 min-w-[80px]">
                    Spread
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {data.map((row) => {
                  const prices = Object.values(row.lab_prices).filter(
                    (p): p is number => p !== null
                  );
                  const minP = Math.min(...prices);
                  const maxP = Math.max(...prices);

                  return (
                    <tr key={row.canonical_test_id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                      <td className="px-4 py-2 sticky left-0 bg-white dark:bg-gray-900">
                        <Link
                          href={`/compare?id=${row.canonical_test_id}`}
                          className="text-gray-900 dark:text-white hover:text-blue-600 font-medium"
                        >
                          {row.test_name}
                        </Link>
                        <div className="text-xs text-gray-400">{row.lab_count} labs</div>
                      </td>
                      {activeLabs.map((slug) => {
                        const price = row.lab_prices[slug] ?? null;
                        return (
                          <td key={slug} className="px-3 py-2 text-center">
                            <span
                              className={`inline-block px-2 py-1 rounded text-xs font-medium ${getPriceColor(
                                price,
                                minP,
                                maxP
                              )}`}
                            >
                              {formatPrice(price)}
                            </span>
                          </td>
                        );
                      })}
                      <td className="px-3 py-2 text-right text-xs font-medium text-gray-500">
                        Rs. {row.price_spread.toLocaleString("en-IN")}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
