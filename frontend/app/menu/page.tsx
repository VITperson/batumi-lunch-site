"use client";

import Link from "next/link";
import { ChangeEvent, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { ru } from "date-fns/locale";

import {
  getCurrentMenu,
  getMenuWeeks,
  getOrderWindow,
  type MenuWeekSummary,
} from "@/lib/api/endpoints/menu";

const dayPlaceholders: Record<string, string> = {
  Понедельник: "/dishphotos/Monday.png",
  Вторник: "/dishphotos/Tuesday.png",
  Среда: "/dishphotos/Wednesday.png",
  Четверг: "/dishphotos/Thursday.png",
  Пятница: "/dishphotos/Friday.png",
};

export default function MenuPage() {
  const [selectedWeekStart, setSelectedWeekStart] = useState<string | null>(null);

  const { data: weeks } = useQuery({ queryKey: ["menu-weeks"], queryFn: getMenuWeeks });
  const { data: windowState } = useQuery({ queryKey: ["order-window"], queryFn: getOrderWindow });
  const { data: menu, isLoading } = useQuery({
    queryKey: ["menu", selectedWeekStart ?? "current"],
    queryFn: () => getCurrentMenu(selectedWeekStart ?? undefined),
  });

  useEffect(() => {
    if (!weeks || weeks.length === 0) return;
    const preferred = weeks.find((week) => week.isCurrent)?.weekStart ?? weeks[0].weekStart ?? null;
    if (preferred !== selectedWeekStart) {
      setSelectedWeekStart(preferred);
    }
  }, [weeks, selectedWeekStart]);

  const weekOptions = useMemo(() => {
    if (!weeks) return [] as MenuWeekSummary[];
    return weeks;
  }, [weeks]);

  const handleWeekChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value;
    setSelectedWeekStart(value === "" ? null : value);
  };

  if (isLoading || !menu) {
    return <p className="text-secondary">Загружаем меню…</p>;
  }

  const weekStartLabel = menu.weekStart ? format(parseISO(menu.weekStart), "d MMMM", { locale: ru }) : null;
  const selectValue = selectedWeekStart ?? "";

  return (
    <div className="space-y-8">
      <header className="card p-6 sm:p-8">
        <div className="flex flex-col gap-6 md:flex-row md:flex-wrap md:items-start md:justify-between">
          <div>
            <span className="eyebrow">Меню недели</span>
            <h1 className="mt-4 text-3xl font-semibold text-primary">{menu.week}</h1>
            {weekStartLabel && <p className="mt-2 text-secondary">План доставки с {weekStartLabel}</p>}
          </div>
          <div className="flex w-full flex-col gap-4 md:w-auto md:items-end">
            {weekOptions.length > 0 && (
              <div className="flex w-full flex-col gap-2 text-sm text-secondary md:w-64">
                <label htmlFor="week-select" className="font-semibold text-primary">
                  Выберите неделю
                </label>
                <select
                  id="week-select"
                  value={selectValue}
                  onChange={handleWeekChange}
                  className="w-full rounded-full border border-outline bg-surface px-4 py-2 text-sm text-primary focus:outline-none focus:ring-2 focus:ring-[color:var(--color-info)]"
                >
                  {weekOptions.map((option) => (
                    <option key={`${option.weekStart ?? option.label}`} value={option.weekStart ?? ""}>
                      {option.label}
                      {option.isCurrent ? " • текущая" : ""}
                    </option>
                  ))}
                </select>
              </div>
            )}
            {windowState && (
              <div className="surface-muted w-full rounded-2xl p-4 text-sm text-secondary md:max-w-sm">
                {windowState.enabled && windowState.weekStart ? (
                  <>
                    <p className="font-semibold text-primary">Предзаказ открыт</p>
                    <p className="mt-1">
                      Оформляйте заказы на новую неделю до {format(parseISO(windowState.weekStart), "d MMMM", { locale: ru })}.
                    </p>
                  </>
                ) : (
                  <>
                    <p className="font-semibold text-primary">Предзаказ закрыт</p>
                    <p className="mt-1">Мы сообщим, когда окно открытия появится в рассылке и Telegram.</p>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 lg:gap-6">
        {menu.items.map((day) => (
          <Link key={day.day} href={`/order/new?day=${encodeURIComponent(day.day)}`} className="group">
            <article className="card h-full p-5 transition hover:-translate-y-1 hover:shadow-[0_25px_55px_-35px_rgba(27,27,27,0.45)] sm:p-6">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold text-primary transition group-hover:text-info">{day.day}</h2>
                <span className="rounded-full border border-outline bg-[color:var(--color-chip)]/60 px-3 py-1 text-xs font-medium text-secondary">
                  {day.dishes.length} блюд
                </span>
              </div>
              <ul className="mt-4 space-y-2 text-sm text-secondary">
                {day.dishes.map((dish) => (
                  <li key={dish} className="flex items-start gap-2">
                    <span className="mt-1 h-1.5 w-1.5 rounded-full bg-[color:var(--color-primary)]/40" />
                    <span>{dish}</span>
                  </li>
                ))}
              </ul>
              <div className="mt-4 overflow-hidden rounded-2xl border border-outline">
                <img
                  src={day.photoUrl || dayPlaceholders[day.day] || "/dishphotos/Monday.png"}
                  alt={`Фото меню ${day.day}`}
                  className="aspect-[4/3] w-full object-cover sm:aspect-[3/2]"
                />
              </div>
            </article>
          </Link>
        ))}
      </section>
    </div>
  );
}
