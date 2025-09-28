"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/auth-context";

type FormValues = {
  email: string;
  password: string;
};

export default function LoginPage() {
  const { register, handleSubmit, formState } = useForm<FormValues>({
    defaultValues: { email: "", password: "" },
  });
  const { login, isLoading, user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (user) {
      router.replace("/order/new");
    }
  }, [router, user]);

  const onSubmit = async (values: FormValues) => {
    try {
      await login(values.email, values.password);
    } catch (error) {
      console.error(error);
      alert("Неверный логин или пароль");
    }
  };

  return (
    <section className="card mx-auto max-w-md p-6 sm:p-8">
      <div className="space-y-2 text-center">
        <span className="eyebrow mx-auto">Добро пожаловать обратно</span>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 sm:text-3xl">Вход в систему</h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">Войдите, чтобы продолжить заказывать готовые обеды для себя и семьи.</p>
      </div>
      <form onSubmit={handleSubmit(onSubmit)} className="mt-8 space-y-5">
        <div className="space-y-2 text-left">
          <label className="text-sm font-medium text-slate-700 dark:text-slate-200">
            Email <span className="text-rose-500">*</span>
          </label>
          <input
            type="email"
            className="w-full rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-sm text-slate-700 shadow-inner shadow-white/40 focus:border-сky-400 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700/70 dark:bg-slate-800/80 dark:text-slate-100"
            placeholder="user@example.com"
            required
            aria-required="true"
            {...register("email", { required: true })}
          />
        </div>
        <div className="space-y-2 text-left">
          <label className="text-sm font-medium text-slate-700 dark:text-slate-200">
            Пароль <span className="text-rose-500">*</span>
          </label>
          <input
            type="password"
            className="w-full rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-sm text-slate-700 shadow-inner shadow-white/40 focus:border-сky-400 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700/70 dark:bg-slate-800/80 dark:text-slate-100"
            required
            aria-required="true"
            {...register("password", { required: true })}
          />
        </div>
        <button type="submit" className="btn-primary w-full" disabled={isLoading || formState.isSubmitting}>
          Войти
        </button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-600 dark:text-slate-300">
        Нет аккаунта? {" "}
        <Link href="/register" className="text-sky-600 hover:underline dark:text-sky-300">
          Зарегистрироваться
        </Link>
      </p>
    </section>
  );
}
