"use client";

import type { Indicator } from "@/lib/api";

const CATEGORY_ORDER = ["原油", "天然ガス", "石炭", "海運", "為替", "金利", "国内"];

const COLORS: Record<string, string> = {
  wti_crude:      "#ef4444",
  brent_crude:    "#f97316",
  crude_oil_cif:  "#b45309",
  henry_hub:      "#3b82f6",
  ttf_gas:        "#0ea5e9",
  jkm_lng:        "#38bdf8",
  lng_export:     "#06b6d4",
  gas_storage:    "#8b5cf6",
  coal_australia: "#78716c",
  usd_jpy:        "#eab308",
  eur_jpy:        "#84cc16",
  jpy_neer:       "#a78bfa",
  dollar_index:   "#f59e0b",
  fed_funds_rate: "#6366f1",
  electricity:    "#10b981",
  city_gas:       "#14b8a6",
  gasoline:            "#f43f5e",
  gasoline_wholesale:  "#fb7185",
  kerosene:       "#fb923c",
  jepx_system:    "#22c55e",
  jepx_tokyo:     "#4ade80",
  bdry:           "#0f172a",
  bwet:           "#1e3a5f",
  zim:            "#2563eb",
};

type Props = {
  indicators: Indicator[];
  selected: Set<string>;
  onToggle: (id: string) => void;
};

export default function IndicatorToggle({ indicators, selected, onToggle }: Props) {
  const grouped = CATEGORY_ORDER.reduce<Record<string, Indicator[]>>(
    (acc, cat) => {
      acc[cat] = indicators.filter((i) => i.category === cat);
      return acc;
    },
    {}
  );

  return (
    <div className="flex flex-wrap gap-x-6 gap-y-3">
      {CATEGORY_ORDER.map((cat) => {
        const items = grouped[cat];
        if (!items || items.length === 0) return null;
        return (
          <div key={cat}>
            <p className="text-xs text-gray-400 mb-1">{cat}</p>
            <div className="flex flex-wrap gap-2">
              {items.map((ind) => {
                const active = selected.has(ind.id);
                const color = COLORS[ind.id] ?? "#6b7280";
                return (
                  <button
                    key={ind.id}
                    onClick={() => onToggle(ind.id)}
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-all ${
                      active
                        ? "text-white border-transparent"
                        : "text-gray-500 dark:text-gray-400 border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800"
                    }`}
                    style={active ? { backgroundColor: color, borderColor: color } : {}}
                  >
                    <span
                      className="w-2 h-2 rounded-full shrink-0"
                      style={{ backgroundColor: color }}
                    />
                    {ind.label}
                  </button>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
