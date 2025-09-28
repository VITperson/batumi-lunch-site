"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/components/auth/auth-context";
import { getCurrentMenu, getOrderWindow, MenuResponse } from "@/lib/api/endpoints/menu";
import {
  setOrderWindow,
  updateMenuDay,
  updateWeekTitle,
  uploadMenuPhoto,
} from "@/lib/api/endpoints/admin";

const DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"] as const;

type DayFormState = Record<string, string>;

export default function AdminMenuPage() {
  const { user, accessToken, isLoading } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [dayValues, setDayValues] = useState<DayFormState>({});
  const [weekTitle, setWeekTitle] = useState("");

  useEffect(() => {
    if (!isLoading && user?.role !== "admin") {
      router.replace("/");
    }
  }, [isLoading, user, router]);

  const menuQuery = useQuery({
    queryKey: ["menu", "admin"],
    queryFn: () => getCurrentMenu(),
  });
  const windowQuery = useQuery({ queryKey: ["order-window"], queryFn: () => getOrderWindow() });

  useEffect(() => {
    if (menuQuery.data) {
      setWeekTitle(menuQuery.data.week);
      const payload: DayFormState = {};
      for (const day of menuQuery.data.items) {
        payload[day.day] = day.dishes.join("\n");
      }
      setDayValues(payload);
    }
  }, [menuQuery.data]);

  const weekMutation = useMutation({
    mutationFn: async (label: string) => {
      if (!accessToken) throw new Error("no token");
      return updateWeekTitle(accessToken, { title: label });
    },
    onSuccess: (data) => {
      queryClient.setQueryData<MenuResponse>(["menu", "admin"], data);
    },
  });

  const dayMutation = useMutation({
    mutationFn: async ({ day, items }: { day: string; items: string[] }) => {
      if (!accessToken) throw new Error("no token");
      return updateMenuDay(accessToken, day, { items });
    },
    onSuccess: (data) => {
      queryClient.setQueryData<MenuResponse>(["menu", "admin"], data);
    },
  });

  const windowMutation = useMutation({
    mutationFn: async (enabled: boolean) => {
      if (!accessToken) throw new Error("no token");
      return setOrderWindow(accessToken, {
        enabled,
        weekStart: windowQuery.data?.weekStart ?? undefined,
      });
    },
    onSuccess: () => {
      windowQuery.refetch();
    },
  });

  const photoMutation = useMutation({
    mutationFn: async ({ day, file }: { day: string; file: File }) => {
      if (!accessToken) throw new Error("no token");
      return uploadMenuPhoto(accessToken, day, file);
    },
    onSuccess: () => {
      menuQuery.refetch();
    },
  });

  if (!user || user.role !== "admin" || !accessToken) {
    return <p>Требуется доступ администратора.</p>;
  }

  if (menuQuery.isLoading || !menuQuery.data) {
    return <p>Загружаем меню…</p>;
  }

  const handleSaveDay = (day: string) => {
    const items = dayValues[day]
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    dayMutation.mutate({ day, items });
  };

  const handleWeekTitleSubmit = (event: FormEvent) => {
    event.preventDefault();
    weekMutation.mutate(weekTitle);
  };

  return (
    <section className="space-y-6">
      <div className="card p-5 sm:p-6">
        <span className="eyebrow">Редактор меню</span>
        <h1 className="mt-3 text-2xl font-semibold text-slate-900 dark:text-slate-100 sm:text-3xl">Меню недели</h1>
        <form onSubmit={handleWeekTitleSubmit} className="mt-4 flex flex-wrap gap-3 text-sm">
          <input
            className="flex-1 min-w-[220px] rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 shadow-inner shadow-white/40 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200"
            value={weekTitle}
            onChange={(event) => setWeekTitle(event.target.value)}
          />
          <button className="btn-primary" type="submit" disabled={weekMutation.isPending}>
            Сохранить
          </button>
        </form>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {DAYS.map((day) => (
          <div key={day} className="card p-5 sm:p-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{day}</h2>
              <label className="cursor-pointer text-xs font-medium text-sky-600">
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    if (file) {
                      photoMutation.mutate({ day, file });
                      event.target.value = "";
                    }
                  }}
                />
                Загрузить фото
              </label>
            </div>
            <textarea
              className="mt-3 h-40 w-full rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-sm shadow-inner shadow-white/40 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200"
              value={dayValues[day] ?? ""}
              onChange={(event) => setDayValues((prev) => ({ ...prev, [day]: event.target.value }))}
            />
            <button
              className="mt-3 w-full rounded-full border border-sky-500/70 bg-white/80 px-3 py-2 text-sm font-medium text-sky-600 transition hover:bg-sky-50"
              onClick={() => handleSaveDay(day)}
              disabled={dayMutation.isPending}
            >
              Сохранить блюда
            </button>
          </div>
        ))}
      </div>

      <div className="card p-5 sm:p-6">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Окно заказов</h2>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          {windowQuery.data?.enabled
            ? `Предзаказ на следующую неделю открыт до ${windowQuery.data.weekStart ?? "уточнения"}`
            : "Предзаказ на следующую неделю закрыт"}
        </p>
        <button
          className="mt-4 btn-primary"
          onClick={() => windowMutation.mutate(!windowQuery.data?.enabled)}
          disabled={windowMutation.isPending}
        >
          {windowQuery.data?.enabled ? "Закрыть предзаказ" : "Открыть предзаказ"}
        </button>
      </div>
    </section>
  );
}
