"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import type { ChartData } from "@/lib/api";

const COLORS: Record<string, string> = {
  wti_crude:      "#ef4444",
  brent_crude:    "#f97316",
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
  data: ChartData;
  normalize: boolean;
};

function calcTicks(rows: Record<string, string | number | null>[], seriesIds: string[]): number[] {
  let min = Infinity, max = -Infinity;
  rows.forEach((row) => {
    seriesIds.forEach((id) => {
      const v = row[id];
      if (typeof v === "number") {
        if (v < min) min = v;
        if (v > max) max = v;
      }
    });
  });
  if (!isFinite(min) || !isFinite(max)) return [];

  const range = max - min;
  const rawStep = range / 5;
  const magnitude = Math.pow(10, Math.floor(Math.log10(rawStep)));
  const step = Math.ceil(rawStep / magnitude) * magnitude;
  const start = Math.floor(min / step) * step;
  const ticks: number[] = [];
  for (let v = start; v <= max + step * 0.1; v += step) {
    ticks.push(Math.round(v * 100) / 100);
  }
  return ticks;
}

export default function Chart({ data, normalize }: Props) {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const check = () => setIsMobile(window.innerWidth < 768);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, []);

  if (!data.dates.length) {
    return (
      <div className="flex items-center justify-center h-96 text-gray-400">
        指標を選択してください
      </div>
    );
  }

  // Recharts 用にデータを変換（日付×全指標のオブジェクト配列）
  const baseValues: Record<string, number | null> = {};
  if (normalize) {
    // 正規化モード: 最初の有効値を100とする
    data.series.forEach((s) => {
      const first = s.values.find((v) => v !== null) ?? null;
      baseValues[s.id] = first;
    });
  }

  const chartRows = data.dates.map((date, i) => {
    const row: Record<string, string | number | null> = { date };
    data.series.forEach((s) => {
      const raw = s.values[i];
      if (normalize && baseValues[s.id] && raw !== null) {
        row[s.id] = Math.round((raw / baseValues[s.id]!) * 10000) / 100;
      } else {
        row[s.id] = raw;
      }
    });
    return row;
  });

  // Y軸目盛りを動的計算
  const seriesIds = data.series.map((s) => s.id);
  const yTicks = calcTicks(chartRows, seriesIds);

  // X軸ラベルを間引く（多すぎると見づらい）
  const tickInterval = Math.max(1, Math.floor(data.dates.length / 12));

  return (
    <ResponsiveContainer width="100%" height={420}>
      <LineChart data={chartRows} margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 11, fill: "#9ca3af" }}
          interval={tickInterval}
          tickLine={false}
        />
        <YAxis
          yAxisId="main"
          ticks={yTicks}
          tick={{ fontSize: 11, fill: "#9ca3af" }}
          tickLine={false}
          axisLine={false}
          label={
            normalize
              ? { value: "指数 (初日=100)", angle: -90, position: "insideLeft", fontSize: 10, fill: "#9ca3af" }
              : undefined
          }
        />
        {!isMobile && (
          <Tooltip
            contentStyle={{
              fontSize: 12,
              borderRadius: 8,
              border: "1px solid #e5e7eb",
              boxShadow: "0 4px 6px -1px rgba(0,0,0,0.1)",
            }}
            formatter={(value, name) => {
              const series = data.series.find((s) => s.id === name);
              const unit = normalize ? "（指数）" : series?.unit ?? "";
              const num = typeof value === "number" ? value.toFixed(2) : value;
              return [`${num} ${unit}`, series?.label ?? String(name)];
            }}
            labelFormatter={(label) => `📅 ${label}`}
          />
        )}
        <Legend
          formatter={(value) => {
            const s = data.series.find((s) => s.id === value);
            return <span style={{ fontSize: 12 }}>{s?.label ?? value}</span>;
          }}
        />
        {yTicks.map((v) => (
          <ReferenceLine
            key={v}
            yAxisId="main"
            y={v}
            stroke="#e5e7eb"
            strokeWidth={1}
          />
        ))}
        {data.series.map((s) => (
          <Line
            key={s.id}
            yAxisId="main"
            type="monotone"
            dataKey={s.id}
            stroke={COLORS[s.id] ?? "#6b7280"}
            strokeWidth={1.5}
            dot={false}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
