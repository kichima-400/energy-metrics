"use client";

import { useEffect, useState, useCallback } from "react";
import Chart from "@/components/Chart";
import SummaryPanel from "@/components/SummaryPanel";
import IndicatorToggle from "@/components/IndicatorToggle";
import {
  fetchIndicators,
  fetchChart,
  fetchSummary,
  type Indicator,
  type ChartData,
  type SummaryItem,
} from "@/lib/api";

const PERIODS = [
  { label: "1ヶ月", days: 30 },
  { label: "3ヶ月", days: 90 },
  { label: "6ヶ月", days: 180 },
  { label: "1年",   days: 365 },
  { label: "5年",   days: 365 * 5 },
  { label: "10年",  days: 365 * 10 },
  { label: "全期間", days: 365 * 15 },
] as const;

const DEFAULT_INDICATORS = [
  "wti_crude",
  "brent_crude",
  "ttf_gas",
  "coal_australia",
  "gas_storage",
  "usd_jpy",
  "bwet",
];

function toDateStr(daysAgo: number): string {
  const d = new Date();
  d.setDate(d.getDate() - daysAgo);
  return d.toISOString().slice(0, 10);
}

export default function Home() {
  const [indicators, setIndicators] = useState<Indicator[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set(DEFAULT_INDICATORS));
  const [periodDays, setPeriodDays] = useState(365);
  const [normalize, setNormalize] = useState(true);
  const [chartData, setChartData] = useState<ChartData>({ dates: [], series: [] });
  const [summary, setSummary] = useState<SummaryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 指標一覧・サマリーを初回取得
  useEffect(() => {
    fetchIndicators()
      .then(setIndicators)
      .catch(() =>
        setError("APIに接続できません。バックエンドが起動しているか確認してください。")
      );
    fetchSummary().then(setSummary).catch(() => {});
  }, []);

  // チャートデータを取得
  const loadChart = useCallback(async () => {
    if (selected.size === 0) {
      setChartData({ dates: [], series: [] });
      return;
    }
    setLoading(true);
    try {
      const end = toDateStr(0);
      const start = toDateStr(periodDays);
      const data = await fetchChart(Array.from(selected), start, end);
      setChartData(data);
    } catch {
      setError("チャートデータの取得に失敗しました");
    } finally {
      setLoading(false);
    }
  }, [selected, periodDays]);

  useEffect(() => {
    loadChart();
  }, [loadChart]);

  function toggleIndicator(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      {/* ヘッダー */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <h1 className="text-xl font-bold tracking-tight">
          ⚡ エネルギー価格相関ダッシュボード
        </h1>
        <p className="text-xs text-gray-400 mt-0.5">
          原油・LNG・石炭・為替と国内エネルギー価格の相関を可視化
        </p>
      </header>

      <main className="max-w-screen-2xl mx-auto px-4 py-6 space-y-6">
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3 text-sm text-red-700 dark:text-red-300">
            ⚠️ {error}
          </div>
        )}

        {/* サマリーパネル */}
        <section>
          <h2 className="text-sm font-semibold text-gray-500 mb-3">最新値</h2>
          <SummaryPanel items={summary} />
        </section>

        {/* チャートセクション */}
        <section className="bg-white dark:bg-gray-800 rounded-xl shadow p-4 space-y-4">
          {/* コントロール */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            {/* 期間選択 */}
            <div className="flex gap-1">
              {PERIODS.map((p) => (
                <button
                  key={p.days}
                  onClick={() => setPeriodDays(p.days)}
                  className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                    periodDays === p.days
                      ? "bg-blue-600 text-white"
                      : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
                  }`}
                >
                  {p.label}
                </button>
              ))}
            </div>

            {/* 正規化トグル */}
            <label className="flex items-center gap-2 text-sm cursor-pointer select-none">
              <div
                onClick={() => setNormalize((v) => !v)}
                className={`w-9 h-5 rounded-full transition-colors relative ${
                  normalize ? "bg-blue-600" : "bg-gray-300 dark:bg-gray-600"
                }`}
              >
                <span
                  className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
                    normalize ? "translate-x-4" : ""
                  }`}
                />
              </div>
              正規化（初日=100）
            </label>
          </div>

          {/* 指標トグル */}
          <IndicatorToggle
            indicators={indicators}
            selected={selected}
            onToggle={toggleIndicator}
          />

          {/* チャート */}
          <div className="relative">
            {loading && (
              <div className="absolute inset-0 flex items-center justify-center bg-white/60 dark:bg-gray-800/60 z-10 rounded">
                <span className="text-sm text-gray-400 animate-pulse">読み込み中...</span>
              </div>
            )}
            <Chart data={chartData} normalize={normalize} />
          </div>
        </section>
      </main>
    </div>
  );
}
