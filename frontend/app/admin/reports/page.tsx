"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/auth-context";
import { fetchOrdersForWeek } from "@/lib/api/endpoints/orders";

function getCurrentMonday(): string {
  const today = new Date();
  const monday = new Date(today);
  const diff = monday.getDay() === 0 ? -6 : 1 - monday.getDay();
  monday.setDate(monday.getDate() + diff);
  return monday.toISOString().split("T")[0];
}

export default function ReportsPage() {
  const { user, accessToken, isLoading } = useAuth();
  const router = useRouter();
  const [weekStart, setWeekStart] = useState(getCurrentMonday());

  useEffect(() => {
    if (!isLoading && user?.role !== "admin") {
      router.replace("/");
    }
  }, [isLoading, user, router]);

  const ordersQuery = useQuery({
    queryKey: ["orders", "week", weekStart],
    queryFn: () => {
      if (!accessToken) throw new Error("no token");
      return fetchOrdersForWeek(accessToken, weekStart);
    },
    enabled: Boolean(accessToken),
  });

  const summary = useMemo(() => {
    const totals: Record<string, number> = {};
    let total = 0;
    if (!ordersQuery.data) return { totals, total };
    for (const order of ordersQuery.data) {
      totals[order.day] = (totals[order.day] ?? 0) + order.count;
      total += order.count;
    }
    return { totals, total };
  }, [ordersQuery.data]);

  if (!user || user.role !== "admin" || !accessToken) {
    return <p className="text-sm text-slate-600 dark:text-slate-300">Требуется доступ администратора.</p>;
  }

  return (
    <section className="space-y-6">
      <header className="card flex flex-col gap-4 p-5 sm:flex-row sm:items-end sm:justify-between sm:p-6">
        <div>
          <span className="eyebrow">Аналитика</span>
          <h1 className="mt-3 text-2xl font-semibold text-slate-900 dark:text-slate-100 sm:text-3xl">Отчёты по заказам</h1>
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Агрегация заказов по дням недели.</p>
        </div>
        <div className="flex items-center gap-3 text-sm text-slate-600 dark:text-slate-300">
          <label className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">Неделя от</label>
          <input
            type="date"
            className="rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-sm shadow-inner shadow-white/40 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200"
            value={weekStart}
            onChange={(event) => setWeekStart(event.target.value)}
          />
        </div>
      </header>

      {ordersQuery.isLoading ? (
        <p className="text-sm text-slate-600 dark:text-slate-300">Загружаем данные…</p>
      ) : ordersQuery.data?.length ? (
        <div className="card space-y-4 p-5 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-slate-600 dark:text-slate-300">
            <span>
              Всего порций: <span className="font-semibold text-slate-900 dark:text-slate-100">{summary.total}</span>
            </span>
            <span>Дней в отчёте: {Object.keys(summary.totals).length}</span>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
                <th className="py-2">День</th>
                <th className="py-2">Количество</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(summary.totals).map(([day, count]) => (
                <tr key={day} className="border-t border-slate-100 dark:border-slate-800/60">
                  <td className="py-2 font-medium text-slate-700 dark:text-slate-200">{day}</td>
                  <td className="py-2 text-slate-600 dark:text-slate-300">{count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="text-sm text-slate-600 dark:text-slate-300">За указанный период заказов нет.</p>
      )}
    </section>
  );
}
