"use client";

import { useTheme } from "@/components/theme/theme-context";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="relative inline-flex h-8 w-16 items-center justify-between rounded-full border border-slate-200/70 bg-white/80 px-2 shadow-sm transition focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 dark:border-slate-700/70 dark:bg-slate-800/80"
      aria-pressed={isDark}
      aria-label="Переключить тему"
    >
      <span className="sr-only">Переключить тему оформления</span>
      <span
        aria-hidden
        className={`pointer-events-none text-base transition-opacity ${isDark ? "opacity-30" : "opacity-100"}`}
      >
        ☀️
      </span>
      <span
        aria-hidden
        className={`pointer-events-none text-base transition-opacity ${isDark ? "opacity-100" : "opacity-30"}`}
      >
        🌙
      </span>
      <span
        aria-hidden
        className={`pointer-events-none absolute left-1 top-1 h-6 w-6 rounded-full bg-white shadow transition-transform duration-200 ease-out dark:bg-slate-700 ${
          isDark ? "translate-x-8" : "translate-x-0"
        }`}
      />
    </button>
  );
}
