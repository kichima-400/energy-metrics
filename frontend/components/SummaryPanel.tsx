"use client";

import { useState } from "react";
import type { SummaryItem } from "@/lib/api";

const CATEGORY_ORDER = ["原油", "天然ガス", "石炭", "海運", "為替", "金利", "国内"];

const DESCRIPTIONS: Record<string, string> = {
  wti_crude:      "WTI（ウェスト・テキサス・インターミディエイト）。米国テキサス産の軽質原油で、世界の原油価格の基準指標。",
  brent_crude:    "北海ブレント原油。欧州・アフリカ・中東産原油の基準指標で、世界の石油取引の約2/3の価格決定に使用される。",
  henry_hub:      "米国ルイジアナ州ヘンリーハブの天然ガス取引価格。北米天然ガス市場の基準指標。",
  ttf_gas:        "TTF（Title Transfer Facility）。オランダの天然ガス取引ハブ価格。欧州天然ガス市場の基準指標。中東情勢やロシア供給動向に敏感に反応。単位: EUR/MWh。",
  jkm_lng:        "JKM（Japan Korea Marker）。日本・韓国向けLNGスポット価格の基準指標。アジア向けLNG取引の価格決定に使用。月次・約2ヶ月遅延。",
  gas_storage:    "EIA発表の米国天然ガス地下貯蔵量（十億立方フィート）。需給バランスの先行指標として機能。",
  coal_australia: "豪州ニューキャッスル港の一般炭（サーマルコール）スポット価格。アジア向け石炭取引の基準指標。月次・約2ヶ月遅延。",
  usd_jpy:        "米ドル対日本円の為替レート。円安はエネルギー輸入コストを押し上げるため、国内エネルギー価格に直結する重要指標。",
  fed_funds_rate: "FRB（米連邦準備制度）が設定する政策金利。世界の金融市場・ドル相場・資源需要に広範な影響を与える。月次。",
  electricity:    "総務省発表の消費者物価指数（CPI）における電気代。2020年平均=100を基準とした指数。月次・約2ヶ月遅延。",
  city_gas:       "消費者物価指数における都市ガス代。LNG輸入価格や為替の影響を受ける。2020年=100。月次・約2ヶ月遅延。",
  gasoline:       "消費者物価指数におけるガソリン価格。原油価格・為替・石油税制の影響を受ける。2020年=100。月次・約2ヶ月遅延。",
  kerosene:       "消費者物価指数における灯油価格。暖房需要の高まる冬季に注目される。2020年=100。月次・約2ヶ月遅延。",
  premium_weekly:  "資源エネルギー庁「石油製品価格調査」によるハイオクガソリンの全国平均給油所小売価格（税込）。週次・約1週間遅延。",
  gasoline_weekly: "資源エネルギー庁「石油製品価格調査」によるレギュラーガソリンの全国平均給油所小売価格（税込）。週次・約1週間遅延。",
  kerosene_weekly: "資源エネルギー庁「石油製品価格調査」による灯油（民生用）の全国平均給油所小売価格（税込）。18Lあたりの価格。週次・約1週間遅延。",
  jepx_system:    "日本卸電力取引所（JEPX）のシステムプライス。全エリアを統合した卸電力スポット価格の日次平均。",
  jepx_tokyo:     "日本卸電力取引所（JEPX）の東京エリアスポット価格の日次平均。関東地方の電力需給を反映。",
  bdry:           "Breakwave Dry Bulk Shipping ETF。バルチック海運指数（BDI）に連動するよう設計された専用ETF。穀物・石炭・鉄鉱石などのばら積み貨物の運賃動向を反映。",
  bwet:           "Breakwave Tanker Shipping ETF。原油・石油製品タンカーの運賃指数（BDTI/BCTI）に連動するよう設計された専用ETF。中東情勢に敏感に反応。",
  zim:            "ZIM Integrated Shipping Services（イスラエル系コンテナ船会社）の株価。紅海ルートへの依存度が高く、フーシ派攻撃によるスエズ運河回避の影響を最も受けた銘柄。",
};

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

function DescriptionTooltip({ text, open }: { text: string; open: boolean }) {
  if (!open) return null;
  return (
    <div className="absolute z-50 bottom-full left-0 mb-2 w-72">
      <div className="bg-gray-900 dark:bg-gray-700 text-white text-xs rounded-lg px-3 py-2 shadow-lg leading-relaxed">
        {text}
        <div className="absolute top-full left-4 border-4 border-transparent border-t-gray-900 dark:border-t-gray-700" />
      </div>
    </div>
  );
}

export default function SummaryPanel({ items }: { items: SummaryItem[] }) {
  const [openId, setOpenId] = useState<string | null>(null);

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
              {catItems.map((item) => {
                const prevMonthVal = item.diff_month !== null
                  ? item.latest_value - item.diff_month
                  : null;
                const changePct = prevMonthVal && prevMonthVal !== 0
                  ? Math.abs(item.diff_month! / prevMonthVal) * 100
                  : 0;
                const isAlert = changePct >= 5;
                const hasDesc = !!DESCRIPTIONS[item.id];

                return (
                  <div
                    key={item.id}
                    className="relative group flex items-center justify-between gap-2 rounded-lg px-1"
                  >
                    {/* PCはホバー表示、スマホはタップ表示 */}
                    {hasDesc && (
                      <>
                        {/* PC: hover */}
                        <div className="absolute z-50 bottom-full left-0 mb-2 w-72 pointer-events-none
                                        invisible group-hover:visible opacity-0 group-hover:opacity-100
                                        transition-opacity duration-150 hidden md:block">
                          <div className="bg-gray-900 dark:bg-gray-700 text-white text-xs rounded-lg px-3 py-2 shadow-lg leading-relaxed">
                            {DESCRIPTIONS[item.id]}
                            <div className="absolute top-full left-4 border-4 border-transparent border-t-gray-900 dark:border-t-gray-700" />
                          </div>
                        </div>
                        {/* スマホ: タップ */}
                        <DescriptionTooltip text={DESCRIPTIONS[item.id]} open={openId === item.id} />
                      </>
                    )}
                    <div className="min-w-0">
                      <p
                        className={`text-sm font-medium text-gray-800 dark:text-gray-100 truncate underline decoration-dotted decoration-gray-300 dark:decoration-gray-600 ${hasDesc ? "cursor-pointer" : "cursor-default"}`}
                        onClick={() => hasDesc && setOpenId(openId === item.id ? null : item.id)}
                      >
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
                        <span title={item.prev_date ? `比較元: ${item.prev_date}` : undefined}>
                          前値比({item.prev_date ?? "—"}): <DiffBadge value={item.diff_prev} />
                        </span>
                        <span className={isAlert ? "font-bold" : ""}>前月比: <DiffBadge value={item.diff_month} /></span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
