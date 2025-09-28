"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/auth-context";
import { getCurrentMenu, getOrderWindow } from "@/lib/api/endpoints/menu";
import { CreateOrderBody, createOrder } from "@/lib/api/endpoints/orders";

const DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"] as const;

const DAY_PLACEHOLDERS: Record<string, string> = {
  Понедельник: "/dishphotos/Monday.png",
  Вторник: "/dishphotos/Tuesday.png",
  Среда: "/dishphotos/Wednesday.png",
  Четверг: "/dishphotos/Thursday.png",
  Пятница: "/dishphotos/Friday.png",
};

type PageProps = {
  searchParams?: Record<string, string | string[]>;
};

export default function NewOrderPage({ searchParams }: PageProps) {
  const router = useRouter();
  const { user, accessToken, isLoading, reloadProfile } = useAuth();
  const initialDayParam = (() => {
    const value = searchParams?.day;
    if (typeof value === "string" && DAYS.includes(value as (typeof DAYS)[number])) {
      return value;
    }
    return null;
  })();

  const [step, setStep] = useState(initialDayParam ? 2 : 1);
  const [selectedDay, setSelectedDay] = useState<string | null>(initialDayParam);
  const [count, setCount] = useState(1);
  const [address, setAddress] = useState<string>("");
  const [phone, setPhone] = useState<string>("");
  const [weekMode, setWeekMode] = useState<"current" | "next">("current");
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [pendingOrder, setPendingOrder] = useState<CreateOrderBody | null>(null);
  const [duplicateInfo, setDuplicateInfo] = useState<
    | {
        orderId: string;
        day: string;
        count: number | null;
      }
    | null
  >(null);
  const confirmButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (user && user.address) {
      setAddress(user.address);
    }
    if (user && user.phone) {
      setPhone(user.phone);
    }
  }, [user]);

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);
  const orderWindowQuery = useQuery({ queryKey: ["order-window"], queryFn: () => getOrderWindow() });
  const currentMenuQuery = useQuery({ queryKey: ["menu", "current"], queryFn: () => getCurrentMenu() });
  const nextMenuQuery = useQuery({
    queryKey: ["menu", "next", orderWindowQuery.data?.weekStart],
    queryFn: () => getCurrentMenu(orderWindowQuery.data?.weekStart ?? undefined),
    enabled: Boolean(orderWindowQuery.data?.enabled && orderWindowQuery.data?.weekStart),
  });

  const menu = useMemo(() => {
    if (weekMode === "next" && nextMenuQuery.data) {
      return nextMenuQuery.data;
    }
    return currentMenuQuery.data;
  }, [weekMode, currentMenuQuery.data, nextMenuQuery.data]);

  const mutation = useMutation({
    mutationFn: async (body: CreateOrderBody) => {
      if (!accessToken) throw new Error("Отсутствует токен");
      return createOrder(accessToken, body);
    },
    onSuccess: async (order) => {
      setDuplicateInfo(null);
      setIsConfirmOpen(false);
      setPendingOrder(null);
      await reloadProfile();
      router.push(`/orders/${order.id}`);
    },
    onError: (error: any) => {
      if (error?.response?.status === 409 && error.response.data?.code === "duplicate_order") {
        const payload = error.response.data;
        setDuplicateInfo({
          orderId: payload.orderId ?? "",
          day: payload.day ?? selectedDay ?? "этот день",
          count: typeof payload.count === "number" ? payload.count : null,
        });
        setStep(1);
      } else {
        alert("Не удалось оформить заказ. Попробуйте снова.");
      }
    },
  });

  const handleOpenConfirmation = () => {
    if (!selectedDay) {
      alert("Выберите день");
      return;
    }
    const trimmedAddress = address.trim();
    const trimmedPhone = phone.trim();

    if (!trimmedAddress) {
      alert("Укажите адрес доставки");
      return;
    }
    const body: CreateOrderBody = {
      day: selectedDay,
      count,
      address: trimmedAddress,
      phone: trimmedPhone ? trimmedPhone : undefined,
      weekStart: weekMode === "next" ? orderWindowQuery.data?.weekStart ?? undefined : undefined,
    };
    setAddress(trimmedAddress);
    setPhone(trimmedPhone);
    setPendingOrder(body);
    setIsConfirmOpen(true);
  };

  const handleConfirmOrder = () => {
    if (!pendingOrder) {
      return;
    }
    mutation.mutate(pendingOrder);
  };

  const handleCloseModal = useCallback(() => {
    if (mutation.isPending) {
      return;
    }
    setIsConfirmOpen(false);
    setPendingOrder(null);
  }, [mutation.isPending]);

  useEffect(() => {
    if (!isConfirmOpen) {
      return;
    }
    confirmButtonRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        handleCloseModal();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isConfirmOpen, handleCloseModal]);

  if (!user || !accessToken) {
    return <p className="text-sm text-slate-600 dark:text-slate-300">Требуется авторизация…</p>;
  }

  if (currentMenuQuery.isLoading || !menu) {
    return <p className="text-sm text-slate-600 dark:text-slate-300">Загружаем меню…</p>;
  }

  const defaultPlaceholder = "/lunchPic.png";
  const heroDay = selectedDay ?? menu.items[0]?.day ?? null;
  const heroItem = heroDay ? menu.items.find((item) => item.day === heroDay) : undefined;
  const heroImage = defaultPlaceholder;
  const heroDishes = heroItem?.dishes.slice(0, 3) ?? [];
  const dayMenu = menu.items.find((item) => item.day === selectedDay);

  return (
    <div className="space-y-8">
      <div className="relative overflow-hidden rounded-3xl border border-white/60 bg-slate-900/70 text-white shadow-xl">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: `url(${heroImage})` }}
        />
        <div className="absolute inset-0 bg-gradient-to-br from-slate-900/80 via-slate-900/70 to-slate-900/30" />
        <div className="relative z-10 px-6 py-12 sm:px-8 md:px-16">
          <p className="text-xs uppercase tracking-[0.3em] text-white/70">Мастер оформления</p>
          <h1 className="mt-4 text-3xl font-semibold sm:text-4xl md:text-5xl">{heroDay ?? "Новый заказ"}</h1>
          <p className="mt-4 max-w-xl text-sm text-white/80 sm:text-base">
            {heroDishes.length > 0 ? heroDishes.join(" • ") : "Выберите день, чтобы увидеть состав меню."}
          </p>
        </div>
      </div>

      <section className="card space-y-8 p-6 sm:p-8">
        <header className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-baseline sm:justify-between">
          <div>
            <span className="eyebrow">Мастер оформления</span>
            <h1 className="mt-3 text-3xl font-semibold text-slate-900 dark:text-slate-100">Новый заказ</h1>
            <p className="text-sm text-slate-600 dark:text-slate-300">Шаг {step} из 3</p>
          </div>
          {orderWindowQuery.data?.enabled && (
            <div className="rounded-full border border-sky-200/70 bg-sky-50/80 px-3 py-1 text-xs text-sky-700">
              Доступен предзаказ на неделю с {orderWindowQuery.data.weekStart}
            </div>
          )}
      </header>

      {duplicateInfo && (
        <div className="rounded-2xl border border-amber-300/70 bg-amber-50/80 p-5 text-sm text-amber-800 shadow-sm">
          <h3 className="text-base font-semibold text-amber-900">
            У вас уже есть заказ на {duplicateInfo.day}
          </h3>
          <p className="mt-2 text-amber-800/80">
            {duplicateInfo.count ? `Количество: ${duplicateInfo.count}. ` : null}Вы можете изменить или отменить его в
            разделе «Мои заказы».
          </p>
          <div className="mt-4 flex flex-wrap gap-3">
            {duplicateInfo.orderId && (
              <Link href={`/orders/${duplicateInfo.orderId}`} className="btn-secondary">
                Открыть заказ
              </Link>
            )}
            <Link href="/account/orders" className="btn-ghost">
              Перейти к списку заказов
            </Link>
          </div>
        </div>
      )}

      {orderWindowQuery.data?.enabled && orderWindowQuery.data.weekStart && (
        <div className="flex flex-wrap gap-2 text-sm sm:gap-3">
          <button
            className={`rounded-full border px-4 py-2 transition ${
              weekMode === "current"
                ? "border-sky-500 bg-sky-50/80 text-sky-700"
                : "border-transparent bg-white/70 text-slate-500 hover:border-slate-200 dark:bg-slate-900/70 dark:text-slate-300"
            }`}
            onClick={() => setWeekMode("current")}
          >
            Текущая неделя
          </button>
          <button
            className={`rounded-full border px-4 py-2 transition ${
              weekMode === "next"
                ? "border-sky-500 bg-sky-50/80 text-sky-700"
                : "border-transparent bg-white/70 text-slate-500 hover:border-slate-200 dark:bg-slate-900/70 dark:text-slate-300"
            }`}
            onClick={() => setWeekMode("next")}
          >
            Следующая неделя
          </button>
        </div>
      )}

      {step === 1 && (
        <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
          {menu.items.map((item) => (
            <button
              key={item.day}
              onClick={() => {
                setSelectedDay(item.day);
                setDuplicateInfo(null);
                setStep(2);
              }}
              className={`surface-muted flex h-full flex-col gap-4 rounded-3xl border border-transparent p-6 text-left transition hover:-translate-y-1 ${
                selectedDay === item.day
                  ? "border-sky-400/60 bg-white/90 shadow-lg shadow-sky-500/10 dark:bg-slate-900/90 dark:shadow-black/40"
                  : "hover:border-sky-200/80 hover:bg-white/85 dark:hover:bg-slate-900/80"
              }`}
            >
              <div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">{item.day}</h3>
                <ul className="mt-4 space-y-3 text-sm text-slate-600 dark:text-slate-300">
                  {item.dishes.slice(0, 3).map((dish) => (
                    <li key={dish} className="flex items-start gap-3">
                      <span className="mt-1 h-1.5 w-1.5 rounded-full bg-slate-400 dark:bg-slate-500" />
                      <span>{dish}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="mt-auto rounded-2xl border border-white/70 bg-white/80 px-4 py-3 text-xs text-slate-500 shadow-inner dark:border-slate-800/70 dark:bg-slate-900/70 dark:text-slate-300">
                Подробности на следующем шаге
              </div>
            </button>
          ))}
        </div>
      )}

      {step === 2 && selectedDay && (
        <div className="space-y-6">
          <div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Выберите количество</h2>
            <div className="mt-3 flex flex-wrap gap-2 sm:gap-3">
              {[1, 2, 3, 4].map((value) => (
                <button
                  key={value}
                  onClick={() => setCount(value)}
                  className={`rounded-full border px-4 py-2 transition ${
                    count === value
                      ? "border-sky-500 bg-sky-50/80 text-sky-700"
                      : "border-slate-200 bg-white/80 text-slate-600 hover:border-slate-300 dark:border-slate-700/60 dark:bg-slate-900/70 dark:text-slate-300"
                  }`}
                >
                  {value} {value === 1 ? "обед" : value < 5 ? "обеда" : "обедов"}
                </button>
              ))}
            </div>
          </div>
          {dayMenu && (
            <div className="surface-muted p-5">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-300">Состав</h3>
              <ul className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                {dayMenu.dishes.map((dish) => (
                  <li key={dish} className="flex items-start gap-3">
                    <span className="mt-1 h-1.5 w-1.5 rounded-full bg-slate-300" />
                    <span>{dish}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="flex flex-wrap gap-3">
            <button className="btn-ghost" onClick={() => setStep(1)}>
              Назад
            </button>
            <button className="btn-primary" onClick={() => setStep(3)}>
              Далее
            </button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-6">
          <div>
            <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Адрес доставки</label>
            <textarea
              className="mt-2 w-full rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-sm text-slate-700 shadow-inner shadow-white/40 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700/70 dark:bg-slate-800/80 dark:text-slate-100"
              rows={3}
              value={address}
              onChange={(event) => setAddress(event.target.value)}
              placeholder="ул. Руставели 10, подъезд 2, этаж 5"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Телефон</label>
            <input
              className="mt-2 w-full rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-sm text-slate-700 shadow-inner shadow-white/40 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700/70 dark:bg-slate-800/80 dark:text-slate-100"
              value={phone ?? ""}
              onChange={(event) => setPhone(event.target.value)}
              placeholder="+995..."
            />
          </div>
          <div className="surface-muted p-4">
            <h3 className="text-sm font-semibold text-slate-500 dark:text-slate-300">Подтверждение</h3>
            <dl className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
              <div>
                <dt className="font-medium text-slate-700 dark:text-slate-200">День</dt>
                <dd>{selectedDay}</dd>
              </div>
              <div>
                <dt className="font-medium text-slate-700 dark:text-slate-200">Количество</dt>
                <dd>{count}</dd>
              </div>
              <div>
                <dt className="font-medium text-slate-700 dark:text-slate-200">Адрес</dt>
                <dd>{address || "—"}</dd>
              </div>
              <div>
                <dt className="font-medium text-slate-700 dark:text-slate-200">Телефон</dt>
                <dd>{phone || "—"}</dd>
              </div>
            </dl>
          </div>
          <div className="flex flex-wrap gap-3">
            <button className="btn-ghost" onClick={() => setStep(2)}>
              Назад
            </button>
            <button
              className="btn-primary disabled:bg-sky-200 disabled:text-sky-500"
              onClick={handleOpenConfirmation}
              disabled={mutation.isPending}
            >
              Подтвердить заказ
            </button>
          </div>
        </div>
      )}
      </section>
      {isConfirmOpen && pendingOrder && (
        <div className="fixed inset-0 z-50">
          <div
            className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
            aria-hidden
            onClick={handleCloseModal}
          />
          <div className="relative z-10 flex h-full items-center justify-center px-4">
            <div
              role="dialog"
              aria-modal="true"
              aria-labelledby="confirm-order-title"
              className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl dark:bg-slate-900 sm:p-8"
            >
              <h2 id="confirm-order-title" className="text-xl font-semibold text-slate-900 dark:text-slate-100">
                Подтвердите заказ
              </h2>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
                Проверьте детали заказа перед отправкой. Мы сразу начнём готовить, как только подтвердите.
              </p>
              <dl className="mt-6 space-y-3 text-sm text-slate-600 dark:text-slate-300">
                <div className="flex items-start justify-between gap-4">
                  <dt className="font-medium text-slate-700 dark:text-slate-200">День</dt>
                  <dd className="text-right text-slate-700 dark:text-slate-100">{pendingOrder.day}</dd>
                </div>
                <div className="flex items-start justify-between gap-4">
                  <dt className="font-medium text-slate-700 dark:text-slate-200">Количество</dt>
                  <dd className="text-right text-slate-700 dark:text-slate-100">{pendingOrder.count}</dd>
                </div>
                <div className="flex items-start justify-between gap-4">
                  <dt className="font-medium text-slate-700 dark:text-slate-200">Неделя доставки</dt>
                  <dd className="text-right text-slate-700 dark:text-slate-100">
                    {pendingOrder.weekStart ? `с ${pendingOrder.weekStart}` : "Текущая неделя"}
                  </dd>
                </div>
                <div className="flex items-start justify-between gap-4">
                  <dt className="font-medium text-slate-700 dark:text-slate-200">Адрес</dt>
                  <dd className="flex-1 text-right text-slate-700 dark:text-slate-100">
                    {pendingOrder.address}
                  </dd>
                </div>
                <div className="flex items-start justify-between gap-4">
                  <dt className="font-medium text-slate-700 dark:text-slate-200">Телефон</dt>
                  <dd className="text-right text-slate-700 dark:text-slate-100">
                    {pendingOrder.phone ?? "—"}
                  </dd>
                </div>
              </dl>
              <div className="mt-8 flex flex-wrap gap-3">
                <button
                  ref={confirmButtonRef}
                  className="btn-primary flex-1 disabled:bg-sky-200 disabled:text-sky-500"
                  onClick={handleConfirmOrder}
                  disabled={mutation.isPending}
                >
                  {mutation.isPending ? "Оформляем заказ…" : "Подтвердить"}
                </button>
                <button
                  type="button"
                  className="btn-ghost flex-1"
                  onClick={handleCloseModal}
                  disabled={mutation.isPending}
                >
                  Изменить данные
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
