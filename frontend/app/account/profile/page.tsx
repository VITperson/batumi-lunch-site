"use client";

import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/auth-context";

const PASSWORD_MIN_LENGTH = 8;

type FormValues = {
  email: string;
  fullName: string;
  phone: string;
  address: string;
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
};

export default function AccountProfilePage() {
  const { user, isLoading, updateProfile } = useAuth();
  const router = useRouter();
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  const defaultValues = useMemo(
    () => ({
      email: user?.email ?? "",
      fullName: user?.fullName ?? "",
      phone: user?.phone ?? "",
      address: user?.address ?? "",
      currentPassword: "",
      newPassword: "",
      confirmPassword: "",
    }),
    [user]
  );

  const {
    register,
    handleSubmit,
    watch,
    reset,
    formState: { isSubmitting, errors },
  } = useForm<FormValues>({ defaultValues });

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  useEffect(() => {
    reset(defaultValues);
  }, [defaultValues, reset]);

  if (!user) {
    return <p className="text-sm text-slate-600 dark:text-slate-300">Требуется авторизация…</p>;
  }

  const onSubmit = async (values: FormValues) => {
    setStatusMessage(null);
    if (values.newPassword && values.newPassword.length < PASSWORD_MIN_LENGTH) {
      alert(`Новый пароль должен содержать не менее ${PASSWORD_MIN_LENGTH} символов`);
      return;
    }
    if (values.newPassword && values.newPassword !== values.confirmPassword) {
      alert("Новый пароль и подтверждение не совпадают");
      return;
    }

    try {
      const updatedProfile = await updateProfile({
        fullName: values.fullName.trim() ? values.fullName.trim() : null,
        phone: values.phone.trim() ? values.phone.trim() : null,
        address: values.address.trim() ? values.address.trim() : null,
        currentPassword: values.newPassword ? values.currentPassword : undefined,
        newPassword: values.newPassword ? values.newPassword : undefined,
      });
      setStatusMessage("Данные успешно обновлены");
      if (updatedProfile) {
        reset({
          email: updatedProfile.email ?? "",
          fullName: updatedProfile.fullName ?? "",
          phone: updatedProfile.phone ?? "",
          address: updatedProfile.address ?? "",
          currentPassword: "",
          newPassword: "",
          confirmPassword: "",
        });
      }
    } catch (error) {
      console.error(error);
      alert("Не удалось сохранить изменения. Проверьте введённые данные.");
    }
  };

  const newPassword = watch("newPassword");

  return (
    <section className="space-y-6">
      <header className="card p-5 sm:p-6">
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 sm:text-3xl">Личный кабинет</h1>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Обновляйте контактные данные и при необходимости меняйте пароль для доступа к сервису.
        </p>
      </header>

      <form onSubmit={handleSubmit(onSubmit)} className="card space-y-6 p-5 sm:p-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Email</label>
            <input
              type="email"
              value={user.email ?? ""}
              readOnly
              className="w-full cursor-not-allowed rounded-xl border border-slate-200/80 bg-slate-100/90 px-3 py-2 text-sm text-slate-500 shadow-inner shadow-white/40 dark:border-slate-700/60 dark:bg-slate-800/70 dark:text-slate-300"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Полное имя</label>
            <input
              type="text"
              className="w-full rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-sm text-slate-700 shadow-inner shadow-white/40 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700/70 dark:bg-slate-800/80 dark:text-slate-100"
              placeholder="Иван Иванов"
              {...register("fullName")}
            />
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Телефон</label>
            <input
              type="tel"
              inputMode="tel"
              className="w-full rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-sm text-slate-700 shadow-inner shadow-white/40 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700/70 dark:bg-slate-800/80 dark:text-slate-100"
              placeholder="+995..."
              {...register("phone", {
                pattern: {
                  value: /^\+?[\d\s]+$/,
                  message: "Разрешены только цифры, пробелы и ведущий +",
                },
              })}
            />
            {errors.phone && <p className="text-xs text-rose-500">{errors.phone.message}</p>}
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Адрес доставки</label>
            <input
              type="text"
              className="w-full rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-sm text-slate-700 shadow-inner shadow-white/40 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700/70 dark:bg-slate-800/80 dark:text-slate-100"
              placeholder="ул. Руставели, 10"
              {...register("address")}
            />
          </div>
        </div>

        <div className="space-y-3 rounded-2xl border border-white/70 bg-white/80 p-4 shadow-inner dark:border-slate-800/70 dark:bg-slate-900/70">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Смена пароля</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Оставьте поля пустыми, если не хотите изменять пароль. Текущий пароль обязателен только при вводе нового.
          </p>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700 dark:text-slate-200">
                Текущий пароль{newPassword ? <span className="text-rose-500"> *</span> : null}
              </label>
              <input
                type="password"
                className="w-full rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-sm text-slate-700 shadow-inner shadow-white/40 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700/70 dark:bg-slate-800/80 dark:text-slate-100"
                {...register("currentPassword")}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Новый пароль</label>
              <input
                type="password"
                className="w-full rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-sm text-slate-700 shadow-inner shadow-white/40 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700/70 dark:bg-slate-800/80 dark:text-slate-100"
                placeholder="Минимум 8 символов"
                {...register("newPassword")}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-slate-700 dark:text-slate-200">
                Повторите новый пароль{newPassword ? <span className="text-rose-500"> *</span> : null}
              </label>
              <input
                type="password"
                className="w-full rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-sm text-slate-700 shadow-inner shadow-white/40 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700/70 dark:bg-slate-800/80 dark:text-slate-100"
                {...register("confirmPassword")}
              />
            </div>
          </div>
        </div>

        <button type="submit" className="btn-primary w-full" disabled={isSubmitting}>
          Сохранить изменения
        </button>
        {statusMessage && <p className="text-sm text-emerald-600 dark:text-emerald-400">{statusMessage}</p>}
      </form>
    </section>
  );
}
