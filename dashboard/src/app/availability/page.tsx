"use client";

import { useState, useEffect } from "react";
import { getAvailabilityMatrix, getCities } from "@/lib/queries";
import { LAB_COLORS, LAB_NAMES } from "@/lib/types";
import type { AvailabilityEntry } from "@/lib/types";

const LAB_SLUGS = ["metropolis", "agilus", "apollo", "neuberg", "trustlab"];

export default function AvailabilityPage() {
  const [city, setCity] = useState("Delhi");
  const [cities, setCities] = useState<string[]>([]);
  const [data, setData] = useState<AvailabilityEntry[]>([]);
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
    getAvailabilityMatrix(city).then((d) => {
      setData(d);
      setLoading(false);
    });
  }, [city]);

  // Build matrix: department -> { lab_slug -> test_count }
  const matrix: Record<string, Record<string, number>> = {};
  for (const row of data) {
    if (!matrix[row.department]) matrix[row.department] = {};
    matrix[row.department][row.lab_slug] = row.test_count;
  }

  const departments = Object.keys(matrix).sort();

  // Lab totals
  const labTotals: Record<string, number> = {};
  for (const slug of LAB_SLUGS) {
    labTotals[slug] = departments.reduce(
      (sum, dept) => sum + (matrix[dept]?.[slug] || 0),
      0
    );
  }

  const getCellColor = (count: number, maxInRow: number) => {
    if (count === 0) return "bg-gray-50 dark:bg-gray-800 text-gray-300 dark:text-gray-600";
    const ratio = count / maxInRow;
    if (ratio >= 0.8) return "bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300";
    if (ratio >= 0.5) return "bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300";
    if (ratio >= 0.2) return "bg-yellow-100 dark:bg-yellow-900 text-yellow-700 dark:text-yellow-300";
    return "bg-orange-100 dark:bg-orange-900 text-orange-700 dark:text-orange-300";
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Test Availability Matrix
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Number of tests available per department per lab in a city.
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
        <div className="text-center py-12 text-gray-500">Loading availability data for {city}...</div>
      ) : departments.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          No availability data for {city}.
        </div>
      ) : (
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                  <th className="px-4 py-3 text-left font-medium text-gray-500 sticky left-0 bg-gray-50 dark:bg-gray-800 min-w-[180px]">
                    Department
                  </th>
                  {LAB_SLUGS.map((slug) => (
                    <th key={slug} className="px-3 py-3 text-center font-medium min-w-[100px]">
                      <div className="flex flex-col items-center gap-1">
                        <div className="flex items-center gap-1">
                          <span
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: LAB_COLORS[slug] }}
                          />
                          <span className="text-gray-500">{LAB_NAMES[slug]}</span>
                        </div>
                        <span className="text-xs text-gray-400">{labTotals[slug]} total</span>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                {departments.map((dept) => {
                  const row = matrix[dept];
                  const values = LAB_SLUGS.map((s) => row[s] || 0);
                  const maxInRow = Math.max(...values, 1);

                  return (
                    <tr key={dept} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                      <td className="px-4 py-2.5 font-medium text-gray-900 dark:text-white sticky left-0 bg-white dark:bg-gray-900">
                        {dept}
                      </td>
                      {LAB_SLUGS.map((slug) => {
                        const count = row[slug] || 0;
                        return (
                          <td key={slug} className="px-3 py-2.5 text-center">
                            <span
                              className={`inline-block px-3 py-1 rounded text-xs font-medium ${getCellColor(
                                count,
                                maxInRow
                              )}`}
                            >
                              {count || "-"}
                            </span>
                          </td>
                        );
                      })}
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
