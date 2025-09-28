"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";

import { useAuth } from "@/components/auth/auth-context";
import { createBroadcastRequest } from "@/lib/api/endpoints/admin";

export default function BroadcastPage() {
  const { user, accessToken, isLoading } = useAuth();
  const router = useRouter();
  const [channels, setChannels] = useState("email,sms");
  const [html, setHtml] = useState("<h1>Batumi Lunch</h1><p>Свежие новости меню!</p>");

  useEffect(() => {
    if (!isLoading && user?.role !== "admin") {
      router.replace("/");
    }
  }, [isLoading, user, router]);

  const mutation = useMutation({
    mutationFn: async () => {
      if (!accessToken) throw new Error("no token");
      const channelsList = channels
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
      return createBroadcastRequest(accessToken, { channels: channelsList, html });
    },
    onSuccess: () => {
      alert("Рассылка поставлена в очередь");
    },
    onError: (error: any) => {
      if (error?.response?.status === 429) {
        alert("Слишком часто. Подождите перед следующей рассылкой.");
      } else {
        alert("Не удалось отправить рассылку");
      }
    },
  });

  if (!user || user.role !== "admin" || !accessToken) {
    return <p className="text-sm text-slate-600 dark:text-slate-300">Требуется доступ администратора.</p>;
  }

  return (
    <section className="space-y-6">
      <header className="card p-5 sm:p-6">
        <span className="eyebrow">Коммуникации</span>
        <h1 className="mt-3 text-2xl font-semibold text-slate-900 dark:text-slate-100 sm:text-3xl">Рассылка клиентов</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Отправляйте HTML-сообщения по каналам связи.</p>
      </header>
      <div className="card space-y-5 p-5 sm:p-6">
        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Каналы (через запятую)</label>
          <input
            className="w-full rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-sm shadow-inner shadow-white/40 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200"
            value={channels}
            onChange={(event) => setChannels(event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <label className="text-sm font-medium text-slate-700 dark:text-slate-200">HTML сообщение</label>
          <textarea
            className="h-48 w-full rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-sm font-mono shadow-inner shadow-white/40 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200"
            value={html}
            onChange={(event) => setHtml(event.target.value)}
          />
        </div>
        <button className="btn-primary w-fit" onClick={() => mutation.mutate()} disabled={mutation.isPending}>
          Отправить
        </button>
      </div>
    </section>
  );
}
