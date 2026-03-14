const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Indicator = {
  id: string;
  label: string;
  unit: string;
  frequency: string;
  category: string;
};

export type ChartSeries = {
  id: string;
  label: string;
  unit: string;
  category: string;
  values: (number | null)[];
};

export type ChartData = {
  dates: string[];
  series: ChartSeries[];
};

export type SummaryItem = {
  id: string;
  label: string;
  unit: string;
  category: string;
  latest_value: number;
  latest_date: string;
  diff_prev: number | null;
  diff_month: number | null;
};

export async function fetchIndicators(): Promise<Indicator[]> {
  const res = await fetch(`${API_BASE}/api/indicators`);
  if (!res.ok) throw new Error("指標一覧の取得に失敗しました");
  return res.json();
}

export async function fetchChart(
  ids: string[],
  start: string,
  end: string
): Promise<ChartData> {
  const params = new URLSearchParams();
  ids.forEach((id) => params.append("ids", id));
  params.set("start", start);
  params.set("end", end);
  const res = await fetch(`${API_BASE}/api/chart?${params}`);
  if (!res.ok) throw new Error("チャートデータの取得に失敗しました");
  return res.json();
}

export async function fetchSummary(): Promise<SummaryItem[]> {
  const res = await fetch(`${API_BASE}/api/summary`);
  if (!res.ok) throw new Error("サマリーデータの取得に失敗しました");
  return res.json();
}
