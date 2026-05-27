import { Activity, AlertTriangle, BadgePercent, Goal, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";

import type { Prediction } from "@/lib/api";

function percent(value: number): string {
  return `${Math.round(value * 1000) / 10}%`;
}

export function DemoDashboard({ prediction }: { prediction: Prediction }) {
  const oneXTwo = prediction.markets["1X2"] ?? [];
  const valueFlags = oneXTwo.filter((item) => item.ev && item.ev > 0.03);

  return (
    <main className="min-h-screen bg-paper text-ink">
      <section className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-6 px-5 py-8 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-pitch">
              Football Predictor 2026
            </p>
            <h1 className="mt-2 max-w-3xl text-4xl font-semibold tracking-normal md:text-6xl">
              Dashboard de predicciones demo
            </h1>
            <p className="mt-4 max-w-2xl text-base text-neutral-600">
              Predicciones con datos semilla, EV básico y estado explícito de validación.
            </p>
          </div>
          <div className="flex items-center gap-2 rounded-md border border-alert/30 bg-alert/10 px-4 py-3 text-sm font-medium text-alert">
            <AlertTriangle className="h-4 w-4" />
            No validado para producción
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-5 px-5 py-6 md:grid-cols-4">
        <Metric icon={<Activity />} label="Estado" value="Demo" />
        <Metric icon={<Goal />} label="xG local" value={prediction.expected_goals_home.toFixed(2)} />
        <Metric icon={<Goal />} label="xG visitante" value={prediction.expected_goals_away.toFixed(2)} />
        <Metric icon={<BadgePercent />} label="+EV flags" value={String(valueFlags.length)} />
      </section>

      <section className="mx-auto grid max-w-7xl gap-5 px-5 pb-10 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-lg border border-line bg-white p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-2xl font-semibold">
                {prediction.match.home_team.name} vs {prediction.match.away_team.name}
              </h2>
              <p className="mt-1 text-sm text-neutral-600">
                {prediction.match.stage} · {prediction.match.venue.city}, {prediction.match.venue.country}
              </p>
            </div>
            <ShieldCheck className="h-6 w-6 text-pitch" />
          </div>

          <div className="mt-6 overflow-hidden rounded-md border border-line">
            <table className="w-full text-left text-sm">
              <thead className="bg-neutral-100 text-neutral-600">
                <tr>
                  <th className="px-4 py-3">Selección</th>
                  <th className="px-4 py-3">Modelo</th>
                  <th className="px-4 py-3">Odds</th>
                  <th className="px-4 py-3">EV</th>
                  <th className="px-4 py-3">Tier</th>
                </tr>
              </thead>
              <tbody>
                {oneXTwo.map((row) => (
                  <tr key={row.selection} className="border-t border-line">
                    <td className="px-4 py-3 font-medium">{row.selection}</td>
                    <td className="px-4 py-3">{percent(row.probability)}</td>
                    <td className="px-4 py-3">{row.odds?.toFixed(2) ?? "-"}</td>
                    <td className="px-4 py-3">{row.ev ? percent(row.ev) : "-"}</td>
                    <td className="px-4 py-3">{row.confidence_tier ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="rounded-lg border border-line bg-white p-5">
          <h2 className="text-xl font-semibold">Mercados demo</h2>
          <div className="mt-5 space-y-5">
            {Object.entries(prediction.markets)
              .filter(([market]) => market !== "1X2")
              .map(([market, rows]) => (
                <div key={market}>
                  <h3 className="text-sm font-semibold uppercase tracking-wide text-neutral-500">
                    {market}
                  </h3>
                  <div className="mt-2 space-y-2">
                    {rows.map((row) => (
                      <div key={row.selection} className="flex items-center justify-between rounded-md bg-neutral-100 px-3 py-2">
                        <span>{row.selection}</span>
                        <span className="font-semibold">{percent(row.probability)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
          </div>
          <p className="mt-6 rounded-md bg-gold/10 p-3 text-sm text-neutral-700">
            {prediction.disclaimer}
          </p>
        </div>
      </section>
    </main>
  );
}

function Metric({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-line bg-white p-4">
      <div className="flex items-center gap-2 text-neutral-500">
        <span className="h-5 w-5">{icon}</span>
        <span className="text-sm">{label}</span>
      </div>
      <div className="mt-3 text-2xl font-semibold">{value}</div>
    </div>
  );
}
