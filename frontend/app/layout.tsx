import "../styles/globals.css";
import type { ReactNode } from "react";
import type { Metadata } from "next";

import { AppShell } from "@/components/layout/app-shell";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: {
    default: "Batumi Lunch — домашние обеды с доставкой",
    template: "%s — Batumi Lunch",
  },
  description:
    "Batumi Lunch готовит домашние обеды и бесплатно доставляет их по Батуми. Закажите заранее или до 10:00 в день доставки.",
  icons: {
    icon: "/icon.png",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ru">
      <body className="antialiased">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-white/90 focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-slate-900 focus:shadow-lg dark:focus:bg-slate-900/90 dark:focus:text-white"
        >
          Перейти к содержанию
        </a>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
