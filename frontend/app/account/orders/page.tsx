"use client";

import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/auth-context";
import { fetchMyOrders } from "@/lib/api/endpoints/orders";

export default function AccountOrdersPage() {
  const { user, accessToken, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  const { data: orders, isLoading: ordersLoading } = useQuery({
    queryKey: ["orders", "mine"],
    queryFn: () => {
      if (!accessToken) throw new Error("no token");
      return fetchMyOrders(accessToken);
    },
    enabled: Boolean(accessToken),
  });

  if (!user || !accessToken) {
    return <p className="text-sm text-slate-600 dark:text-slate-300">Требуется авторизация…</p>;
  }

  if (ordersLoading) {
    return <p className="text-sm text-slate-600 dark:text-slate-300">Загружаем ваши заказы…</p>;
  }

  if (!orders || orders.length === 0) {
    return (
      <div className="card space-y-4 p-5 sm:p-6">
        <p className="text-slate-600 dark:text-slate-300">У вас пока нет заказов.</p>
        <Link href="/order/new" className="btn-primary w-fit">
          Сделать заказ
        </Link>
      </div>
    );
  }

  return (
    <section className="space-y-6">
      <header className="card p-5 sm:p-6">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 sm:text-3xl">Мои заказы</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Управляйте доставкой, смотрите состав блюд и редактируйте активные заказы прямо отсюда.
        </p>
      </header>
      <div className="grid gap-4">
        {orders.map((order) => (
          <article key={order.id} className="card p-5 sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{order.day}</h2>
                <p className="text-sm text-slate-500 dark:text-slate-300">
                  Доставка {new Date(order.deliveryDate).toLocaleDateString("ru-RU")}
                </p>
              </div>
              <span className="rounded-full border border-slate-200/70 bg-white/70 px-3 py-1 text-xs font-medium uppercase text-slate-500 dark:border-slate-700/70 dark:bg-slate-900/70 dark:text-slate-300">
                {order.status}
              </span>
            </div>
            <ul className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
              {order.menu.map((item) => (
                <li key={item} className="flex items-start gap-2">
                  <span className="mt-1 h-1.5 w-1.5 rounded-full bg-slate-400" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            <div className="mt-4 flex flex-wrap gap-3 text-sm">
              <Link href={`/orders/${order.id}`} className="btn-secondary">
                Детали
              </Link>
              {order.status === "new" && (
                <Link href={`/orders/${order.id}?edit=1`} className="btn-ghost">
                  Изменить
                </Link>
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
