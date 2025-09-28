"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/components/auth/auth-context";

const adminLinks = [
  { href: "/admin/menu", title: "Меню", description: "Редактируйте блюда недели и фото меню." },
  { href: "/admin/reports", title: "Отчёты", description: "Просматривайте сводку заказов по дням и неделям." },
  { href: "/admin/broadcast", title: "Рассылки", description: "Отправляйте HTML-уведомления клиентам." },
];

export default function AdminHomePage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && user?.role !== "admin") {
      router.replace("/");
    }
  }, [isLoading, user, router]);

  if (!user || user.role !== "admin") {
    return <p className="text-sm text-slate-600 dark:text-slate-300">Требуется доступ администратора.</p>;
  }

  return (
    <section className="space-y-6">
      <header className="card p-5 sm:p-6">
        <span className="eyebrow">Зона администрирования</span>
        <h1 className="mt-3 text-2xl font-semibold text-slate-900 dark:text-slate-100 sm:text-3xl">Админ-панель</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Управляйте меню, окнами заказов и уведомлениями.</p>
      </header>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {adminLinks.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="card h-full p-5 transition hover:shadow-2xl hover:shadow-sky-500/10 sm:p-6"
          >
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{item.title}</h2>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{item.description}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}
