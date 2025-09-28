"use client";

import Link from "next/link";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/auth/auth-context";

const PASSWORD_MIN_LENGTH = 8;

type FormValues = {
  email: string;
  password: string;
  confirmPassword: string;
  fullName?: string;
  phone?: string;
  address?: string;
};

export default function RegisterPage() {
  const router = useRouter();
  const { register: submitRegistration, user, isLoading } = useAuth();

  const {
    register: formRegister,
    handleSubmit,
    formState: { errors, isSubmitting },
    watch,
  } = useForm<FormValues>({
    defaultValues: {
      email: "",
      password: "",
      confirmPassword: "",
      fullName: "",
      phone: "",
      address: "",
    },
  });

  useEffect(() => {
    if (user) {
      router.replace("/order/new");
    }
  }, [router, user]);

  const passwordsMatch = () => {
    const [password, confirmPassword] = watch(["password", "confirmPassword"]);
    return password === confirmPassword;
  };

  const onSubmit = async (values: FormValues) => {
    if (!passwordsMatch()) {
      alert("Пароли не совпадают");
      return;
    }
    try {
      await submitRegistration({
        email: values.email,
        password: values.password,
        fullName: values.fullName?.trim() ? values.fullName.trim() : undefined,
        phone: values.phone?.trim() ? values.phone.trim() : undefined,
        address: values.address?.trim() ? values.address.trim() : undefined,
      });
    } catch (error: unknown) {
      console.error(error);
      alert("Не удалось зарегистрироваться. Возможно, email уже используется.");
    }
  };

  return (
    <section className="card mx-auto max-w-2xl space-y-6 p-6 sm:p-8">
      <div className="space-y-2 text-center">
        <span className="eyebrow mx-auto">Создайте новый аккаунт</span>
        <h1 className="text-2xl font-semibold text-slate-900 dark:text-slate-100 sm:text-3xl">Регистрация</h1>
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Расскажите немного о себе, и мы будем привозить домашние блюда тогда, когда вам удобно.
        </p>
      </div>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2 text-left">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-200">
              Email <span className="text-rose-500">*</span>
            </label>
            <input
              type="email"
              className="w-full rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-sm text-slate-700 shadow-inner shadow-white/40 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700/70 dark:bg-slate-800/80 dark:text-slate-100"
              placeholder="user@example.com"
              required
              aria-required="true"
              {...formRegister("email", { required: true })}
            />
          </div>
          <div className="space-y-2 text-left">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Полное имя</label>
            <input
              type="text"
              className="w-full rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-sm text-slate-700 shadow-inner shadow-white/40 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700/70 dark:bg-slate-800/80 dark:text-slate-100"
              placeholder="Иван Иванов"
              {...formRegister("fullName")}
            />
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2 text-left">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Телефон</label>
            <input
              type="tel"
              inputMode="tel"
              className="w-full rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-sm text-slate-700 shadow-inner shadow-white/40 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700/70 dark:bg-slate-800/80 dark:text-slate-100"
              placeholder="+995..."
              {...formRegister("phone", {
                pattern: {
                  value: /^\+?[\d\s]+$/,
                  message: "Разрешены только цифры, пробелы и ведущий +",
                },
              })}
            />
            {errors.phone && <p className="text-xs text-rose-500">{errors.phone.message}</p>}
          </div>
          <div className="space-y-2 text-left">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-200">Адрес доставки</label>
            <input
              type="text"
              className="w-full rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-sm text-slate-700 shadow-inner shadow-white/40 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700/70 dark:bg-slate-800/80 dark:text-slate-100"
              placeholder="ул. Руставели, 10"
              {...formRegister("address")}
            />
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2 text-left">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-200">
              Пароль <span className="text-rose-500">*</span>
            </label>
            <input
              type="password"
              className="w-full rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-sm text-slate-700 shadow-inner shadow-white/40 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700/70 dark:bg-slate-800/80 dark:text-slate-100"
              placeholder="Не менее 8 символов"
              required
              aria-required="true"
              {...formRegister("password", { required: true, minLength: PASSWORD_MIN_LENGTH })}
            />
          </div>
          <div className="space-y-2 text-left">
            <label className="text-sm font-medium text-slate-700 dark:text-slate-200">
              Повторите пароль <span className="text-rose-500">*</span>
            </label>
            <input
              type="password"
              className="w-full rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2 text-sm text-slate-700 shadow-inner shadow-white/40 focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-200 dark:border-slate-700/70 dark:bg-slate-800/80 dark:text-slate-100"
              required
              aria-required="true"
              {...formRegister("confirmPassword", { required: true, minLength: PASSWORD_MIN_LENGTH })}
            />
          </div>
        </div>
        <button type="submit" className="btn-primary w-full" disabled={isLoading || isSubmitting}>
          Создать аккаунт
        </button>
      </form>
      <p className="text-center text-sm text-slate-600 dark:text-slate-300">
        Уже зарегистрированы? {" "}
        <Link href="/login" className="text-sky-600 hover:underline dark:text-sky-300">
          Войти
        </Link>
      </p>
    </section>
  );
}
