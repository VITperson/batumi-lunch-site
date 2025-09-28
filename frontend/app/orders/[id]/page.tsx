"use client";

import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/auth-context";
import { cancelOrder, fetchOrder, updateOrder } from "@/lib/api/endpoints/orders";

export default function OrderDetailPage({
  params,
  searchParams,
}: {
  params: { id: string };
  searchParams?: Record<string, string | string[]>;
}) {
  const { user, accessToken, isLoading } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(searchParams?.edit === "1");
  const [newCount, setNewCount] = useState(1);

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  const orderQuery = useQuery({
    queryKey: ["order", params.id],
    queryFn: () => {
      if (!accessToken) throw new Error("no token");
      return fetchOrder(accessToken, params.id);
    },
    enabled: Boolean(accessToken),
  });

  useEffect(() => {
    if (orderQuery.data) {
      setNewCount(orderQuery.data.count);
    }
  }, [orderQuery.data]);

  const updateMutation = useMutation({
    mutationFn: async (count: number) => {
      if (!accessToken) throw new Error("no token");
      return updateOrder(accessToken, params.id, { count });
    },
    onSuccess: (order) => {
      queryClient.invalidateQueries({ queryKey: ["orders", "mine"] });
      queryClient.setQueryData(["order", params.id], order);
      setIsEditing(false);
    },
  });

  const cancelMutation = useMutation({
    mutationFn: async () => {
      if (!accessToken) throw new Error("no token");
      return cancelOrder(accessToken, params.id);
    },
    onSuccess: (order) => {
      queryClient.invalidateQueries({ queryKey: ["orders", "mine"] });
      queryClient.setQueryData(["order", params.id], order);
    },
  });

  if (!user || !accessToken) {
    return <p className="text-sm text-slate-600 dark:text-slate-300">Требуется авторизация…</p>;
  }

  if (orderQuery.isLoading || !orderQuery.data) {
    return <p className="text-sm text-slate-600 dark:text-slate-300">Загружаем заказ…</p>;
  }

  const order = orderQuery.data;
  const canModify = order.status === "new";

  return (
    <section className="card space-y-6 p-6 sm:p-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <span className="eyebrow">Детали заказа</span>
          <h1 className="mt-3 text-3xl font-semibold text-slate-900 dark:text-slate-100">Заказ {order.id}</h1>
          <p className="text-sm text-slate-500 dark:text-slate-300">{order.day}</p>
        </div>
        <span className="rounded-full border border-slate-200/70 bg-white/70 px-3 py-1 text-xs font-medium uppercase text-slate-600 dark:border-slate-700/70 dark:bg-slate-900/70 dark:text-slate-300">
          {order.status}
        </span>
      </div>

      <div className="surface-muted space-y-2 p-4">
        <h2 className="text-sm font-semibold text-slate-500 dark:text-slate-300">Блюда</h2>
        <ul className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
          {order.menu.map((dish) => (
            <li key={dish} className="flex items-start gap-2">
              <span className="mt-1 h-1.5 w-1.5 rounded-full bg-slate-400" />
              <span>{dish}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="surface-muted p-4">
          <h3 className="text-sm font-semibold text-slate-500 dark:text-slate-300">Адрес</h3>
          <p className="mt-2 text-sm text-slate-700 dark:text-slate-200">{order.address ?? "Не указан"}</p>
        </div>
        <div className="surface-muted p-4">
          <h3 className="text-sm font-semibold text-slate-500 dark:text-slate-300">Телефон</h3>
          <p className="mt-2 text-sm text-slate-700 dark:text-slate-200">{order.phone ?? "Не указан"}</p>
        </div>
      </div>

      {canModify && (
        <div className="surface-muted p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-slate-500 dark:text-slate-300">Количество</h3>
              <p className="text-sm text-slate-700 dark:text-slate-200">Текущее: {order.count}</p>
            </div>
            <button className="btn-ghost" onClick={() => setIsEditing((prev) => !prev)}>
              {isEditing ? "Отменить" : "Изменить"}
            </button>
          </div>
          {isEditing && (
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <select
                className="rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-sm shadow-inner shadow-white/40 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200"
                value={newCount}
                onChange={(event) => setNewCount(Number(event.target.value))}
              >
                {[1, 2, 3, 4].map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
              <button
                className="btn-primary disabled:bg-sky-200 disabled:text-sky-500"
                onClick={() => updateMutation.mutate(newCount)}
                disabled={updateMutation.isPending}
              >
                Сохранить
              </button>
            </div>
          )}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 text-sm">
        <Link href="/account/orders" className="text-slate-500 hover:text-slate-700 dark:text-slate-300 dark:hover:text-slate-100">
          &larr; Назад к списку
        </Link>
        {canModify && (
          <button
            className="inline-flex items-center rounded-full border border-red-300/70 bg-red-50/80 px-4 py-2 text-sm font-medium text-red-600 transition hover:bg-red-100"
            onClick={() => cancelMutation.mutate()}
            disabled={cancelMutation.isPending}
          >
            Отменить заказ
          </button>
        )}
      </div>
    </section>
  );
}
