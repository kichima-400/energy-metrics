"use client";

import type { SummaryItem } from "@/lib/api";

const CATEGORY_ORDER = ["原油", "天然ガス", "石炭", "為替", "金利", "国内"];

function DiffBadge({ value }: { value: number | null }) {
  if (value === null) return <span className="text-gray-400">—</span>;
  const positive = value > 0;
  const color = positive ? "text-red-500" : value < 0 ? "text-blue-500" : "text-gray-400";
  return (
    <span className={`${color} text-sm font-mono`}>
      {positive ? "+" : ""}{value.toFixed(2)}
    </span>
  );
}

export default function SummaryPanel({ items }: { items: SummaryItem[] }) {
  const grouped = CATEGORY_ORDER.reduce<Record<string, SummaryItem[]>>(
    (acc, cat) => {
      acc[cat] = items.filter((i) => i.category === cat);
      return acc;
    },
    {}
  );

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {CATEGORY_ORDER.map((cat) => {
        const catItems = grouped[cat];
        if (!catItems || catItems.length === 0) return null;
        return (
          <div key={cat} className="bg-white dark:bg-gray-800 rounded-xl shadow p-4">
            <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
              {cat}
            </h3>
            <div className="space-y-2">
              {catItems.map((item) => (
                <div key={item.id} className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">
                      {item.label}
                    </p>
                    <p className="text-xs text-gray-400">{item.latest_date}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-sm font-mono font-semibold text-gray-900 dark:text-white">
                      {item.latest_value.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                      <span className="text-xs font-normal text-gray-400 ml-1">{item.unit}</span>
                    </p>
                    <div className="flex gap-2 justify-end text-xs text-gray-400">
                      <span>前: <DiffBadge value={item.diff_prev} /></span>
                      <span>月: <DiffBadge value={item.diff_month} /></span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
