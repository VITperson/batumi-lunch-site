"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { useAuth } from "@/components/auth/auth-context";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { SocialLinks } from "./social-links";

type NavItem = { href: string; label: string };

function NavLink({ href, label, onNavigate }: NavItem & { onNavigate?: () => void }) {
  const pathname = usePathname();
  const isActive = pathname === href;
  const base =
    "inline-flex items-center rounded-full px-4 py-2 text-sm font-medium transition focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-info)]";
  const active = "bg-[color:var(--color-chip)] text-primary shadow-sm";
  const inactive = "text-secondary hover:bg-[color:var(--color-chip)]/60 hover:text-primary";

  return (
    <Link
      href={href}
      className={`${base} ${isActive ? active : inactive}`}
      onClick={onNavigate}
    >
      {label}
    </Link>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout, isLoading } = useAuth();
  const pathname = usePathname();
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  useEffect(() => {
    setIsMobileNavOpen(false);
  }, [pathname]);

  const navItems = useMemo(() => {
    const baseItems: NavItem[] = [{ href: "/menu", label: "Меню" }];
    if (user) {
      baseItems.push({ href: "/order/new", label: "Новый заказ" });
    }
    if (user?.role === "admin") {
      baseItems.push({ href: "/admin", label: "Админ" });
    }
    return baseItems;
  }, [user]);

  const year = new Date().getFullYear();

  return (
    <div className="relative flex min-h-screen flex-col overflow-hidden">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <Image
          src="/kitchen.png"
          alt=""
          fill
          className="object-cover opacity-85 blur-[2px]"
          priority
        />
        <div className="absolute inset-0 bg-white/60 dark:bg-slate-950/65" />
        <div className="absolute -top-32 left-[-10%] h-64 w-64 rounded-full bg-sky-300/30 blur-3xl dark:bg-sky-500/20" />
        <div className="absolute top-[-40px] right-[-80px] h-80 w-80 rounded-full bg-emerald-200/30 blur-3xl dark:bg-emerald-400/20" />
        <div className="absolute bottom-[-120px] left-1/2 h-96 w-96 -translate-x-1/2 rounded-full bg-indigo-200/20 blur-3xl dark:bg-indigo-500/20" />
      </div>

      <header className="relative z-20 border-b border-white/60 bg-white/80 backdrop-blur-xl dark:border-slate-800/80 dark:bg-slate-900/70">
        <div className="mx-auto flex w-full max-w-screen-2xl items-center justify-between gap-4 px-4 py-3 sm:px-6 sm:py-4 lg:px-8 xl:px-10">
          <div className="flex flex-1 items-center gap-3">
            <Link href="/" className="flex items-center gap-2" aria-label="Batumi Lunch — перейти на главную">
              <Image
                src="/logo_no_bg.png"
                alt="Логотип Batumi Lunch"
                width={40}
                height={40}
                className="h-10 w-auto"
                priority
              />
              <span className="text-lg font-semibold text-primary dark:text-primary">Batumi Lunch</span>
            </Link>
          </div>
          <nav className="hidden items-center gap-2 md:flex">
            {navItems.map((item) => (
              <NavLink key={item.href} {...item} />
            ))}
          </nav>
          <div className="flex items-center gap-2 text-sm text-secondary">
            <SocialLinks className="hidden items-center gap-2 sm:flex" size="sm" />
            <ThemeToggle />
            {isLoading ? (
              <span className="hidden text-secondary sm:inline">Загрузка…</span>
            ) : user ? (
              <UserMenuTrigger user={user} onLogout={logout} />
            ) : (
              <div className="hidden items-center gap-2 sm:flex">
                <Link href="/register" className="btn-primary text-xs">
                  Регистрация
                </Link>
                <Link href="/login" className="btn-secondary text-xs">
                  Войти
                </Link>
              </div>
            )}
            <button
              type="button"
              className="inline-flex items-center justify-center rounded-full border border-outline bg-surface p-2 text-secondary shadow-sm transition hover:bg-[color:var(--color-chip)]/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-info)] md:hidden"
              aria-expanded={isMobileNavOpen}
              aria-controls="primary-navigation"
              aria-label={isMobileNavOpen ? "Закрыть меню" : "Открыть меню"}
              onClick={() => setIsMobileNavOpen((prev) => !prev)}
            >
              <svg
                className="h-5 w-5"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                {isMobileNavOpen ? (
                  <path d="M6 18L18 6M6 6l12 12" />
                ) : (
                  <path d="M4 7h16M4 12h16M4 17h16" />
                )}
              </svg>
            </button>
          </div>
        </div>
      </header>

      {isMobileNavOpen && (
        <div className="fixed inset-0 z-30 bg-slate-900/40 backdrop-blur-sm md:hidden">
          <div className="absolute inset-x-4 top-20 rounded-3xl border border-white/60 bg-white/95 p-6 shadow-2xl dark:border-slate-800/80 dark:bg-slate-900/95">
            <nav id="primary-navigation" className="flex flex-col gap-2">
              {navItems.map((item) => (
                <NavLink key={item.href} {...item} onNavigate={() => setIsMobileNavOpen(false)} />
              ))}
            </nav>
            <div className="mt-6 flex flex-col gap-3 text-sm">
              {isLoading ? (
                <span className="text-secondary">Загрузка…</span>
              ) : user ? (
                <UserMenuSheet user={user} onClose={() => setIsMobileNavOpen(false)} onLogout={logout} />
              ) : (
                <>
                  <Link
                    href="/register"
                    className="btn-primary w-full text-center text-xs"
                    onClick={() => setIsMobileNavOpen(false)}
                  >
                    Регистрация
                  </Link>
                  <Link
                    href="/login"
                    className="btn-secondary w-full text-center text-xs"
                    onClick={() => setIsMobileNavOpen(false)}
                  >
                    Войти
                  </Link>
                </>
              )}
              <SocialLinks className="mt-4 flex items-center gap-3" />
            </div>
          </div>
        </div>
      )}

      <main
        id="main-content"
        className="relative z-10 mx-auto flex w-full max-w-screen-2xl flex-1 flex-col px-4 py-10 sm:px-6 sm:py-12 lg:px-8 lg:py-14 xl:px-10"
      >
        <div className="space-y-10 sm:space-y-12 lg:space-y-16">{children}</div>
      </main>

      <footer className="relative z-20 border-t border-white/60 bg-white/70 backdrop-blur-xl dark:border-slate-800/80 dark:bg-slate-900/70">
        <div className="mx-auto w-full max-w-screen-2xl px-4 py-4 text-xs text-secondary sm:px-6 lg:px-8 xl:px-10">
          <div className="flex w-full flex-col items-center gap-4 sm:flex-row sm:items-center sm:gap-6">
            <span className="text-center sm:flex-1 sm:text-left">© {year} Batumi Lunch. Все права защищены.</span>
            <SocialLinks className="flex items-center justify-center gap-2 sm:flex-none sm:justify-center" />
            <span className="text-center sm:flex-1 sm:text-right">С любовью к тем, кто ценит домашнюю еду и свободное время.</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

type UserMenuProps = {
  user: {
    email: string | null;
    fullName: string | null;
  };
  onLogout: () => void;
};

function UserMenuTrigger({ user, onLogout }: UserMenuProps) {
  const name = user.fullName?.trim() || user.email || "Профиль";
  const [isOpen, setIsOpen] = useState(false);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handler = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("pointerdown", handler);
    return () => {
      document.removeEventListener("pointerdown", handler);
      if (closeTimer.current) {
        clearTimeout(closeTimer.current);
      }
    };
  }, []);

  const openMenu = () => {
    if (closeTimer.current) {
      clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
    setIsOpen(true);
  };

  const scheduleClose = () => {
    if (closeTimer.current) {
      clearTimeout(closeTimer.current);
    }
    closeTimer.current = setTimeout(() => setIsOpen(false), 150);
  };

  return (
    <div ref={containerRef} className="relative hidden sm:block" onMouseLeave={scheduleClose}>
      <button
        type="button"
        onMouseEnter={openMenu}
        onClick={() => setIsOpen((prev) => !prev)}
        onFocus={openMenu}
        className="max-w-[12rem] truncate rounded-full border border-outline bg-surface px-4 py-2 text-xs font-medium text-secondary shadow-sm transition hover:bg-[color:var(--color-chip)]/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-info)]"
      >
        {name}
      </button>
      {isOpen ? <UserMenuContent onMouseEnter={openMenu} onMouseLeave={scheduleClose} onLogout={onLogout} /> : null}
    </div>
  );
}

function UserMenuContent({ onLogout, onMouseEnter, onMouseLeave }: { onLogout: () => void; onMouseEnter: () => void; onMouseLeave: () => void }) {
  return (
    <div
      className="absolute right-0 top-full z-40 mt-2 w-44 rounded-2xl border border-white/70 bg-white/95 p-2 shadow-xl dark:border-slate-800/70 dark:bg-slate-900/95"
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      <Link
        href="/account/orders"
        className="block rounded-lg px-3 py-2 text-sm text-secondary transition hover:bg-[color:var(--color-chip)]/60"
      >
        Мои заказы
      </Link>
      <Link
        href="/account/profile"
        className="block rounded-lg px-3 py-2 text-sm text-secondary transition hover:bg-[color:var(--color-chip)]/60"
      >
        Личный кабинет
      </Link>
      <button
        type="button"
        onClick={onLogout}
        className="mt-1 flex w-full items-center justify-between rounded-lg px-3 py-2 text-sm text-rose-600 transition hover:bg-rose-50 dark:text-rose-300 dark:hover:bg-rose-500/10"
      >
        Выйти
      </button>
    </div>
  );
}

type UserMenuSheetProps = {
  user: {
    email: string | null;
    fullName: string | null;
  };
  onLogout: () => void;
  onClose: () => void;
};

function UserMenuSheet({ user, onLogout, onClose }: UserMenuSheetProps) {
  const name = user.fullName?.trim() || user.email || "Профиль";

  return (
    <div className="flex flex-col gap-3">
      <div className="rounded-xl border border-outline bg-surface p-3 text-sm text-secondary">
        {name}
      </div>
      <Link
        href="/account/orders"
        className="btn-secondary w-full text-xs"
        onClick={onClose}
      >
        Мои заказы
      </Link>
      <Link
        href="/account/profile"
        className="btn-ghost w-full text-xs"
        onClick={onClose}
      >
        Личный кабинет
      </Link>
      <button
        type="button"
        className="btn-ghost w-full text-xs text-rose-600"
        onClick={() => {
          onClose();
          onLogout();
        }}
      >
        Выйти
      </button>
    </div>
  );
}
