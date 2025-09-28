"use client";

import { useCallback, useRef, KeyboardEvent } from "react";
import Image from "next/image";
import Link from "next/link";

export type MenuCarouselItem = {
  title: string;
  image: string;
  description: string;
};

interface MenuCarouselProps {
  items: MenuCarouselItem[];
}

export function MenuCarousel({ items }: MenuCarouselProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollByCard = useCallback((direction: "prev" | "next") => {
    const container = scrollRef.current;
    if (!container) return;

    const firstItem = container.querySelector<HTMLElement>("[data-carousel-item]");
    const itemWidth = firstItem?.offsetWidth ?? 300;
    const gapValue = parseFloat(getComputedStyle(container).columnGap || "24");
    const scrollAmount = itemWidth + gapValue;

    container.scrollBy({
      left: direction === "next" ? scrollAmount : -scrollAmount,
      behavior: "smooth",
    });
  }, []);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLDivElement>) => {
      if (event.key === "ArrowRight") {
        event.preventDefault();
        scrollByCard("next");
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        scrollByCard("prev");
      }
    },
    [scrollByCard],
  );

  return (
    <div className="relative">
      <div className="absolute inset-y-0 left-0 z-20 flex items-center">
        <button
          type="button"
          onClick={() => scrollByCard("prev")}
          className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-white/90 text-slate-700 shadow-lg ring-1 ring-slate-200 transition hover:bg-white focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 dark:bg-slate-900 dark:text-slate-100 dark:ring-slate-700"
          aria-label="Показать предыдущие блюда"
        >
          <span aria-hidden className="text-xl">‹</span>
        </button>
      </div>
      <div className="absolute inset-y-0 right-0 z-20 flex items-center">
        <button
          type="button"
          onClick={() => scrollByCard("next")}
          className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-white/90 text-slate-700 shadow-lg ring-1 ring-slate-200 transition hover:bg-white focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 dark:bg-slate-900 dark:text-slate-100 dark:ring-slate-700"
          aria-label="Показать следующие блюда"
        >
          <span aria-hidden className="text-xl">›</span>
        </button>
      </div>
      <div
        ref={scrollRef}
        className="flex gap-6 overflow-x-auto pb-6 pt-2 snap-x snap-mandatory"
        role="region"
        aria-roledescription="carousel"
        aria-label="Блюда недели"
        tabIndex={0}
        onKeyDown={handleKeyDown}
      >
        {items.map((item) => (
          <Link
            key={`carousel-${item.title}`}
            href={`/order/new?day=${encodeURIComponent(item.title)}`}
            data-carousel-item
            className="group relative min-w-[18rem] snap-start rounded-3xl bg-surface shadow-[0_20px_35px_-20px_rgba(27,27,27,0.55)] transition hover:-translate-y-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-info)]"
          >
            <div className="relative h-52 w-full overflow-hidden rounded-3xl">
              <Image
                src={item.image}
                alt={item.title}
                fill
                className="object-cover transition duration-500 group-hover:scale-105"
                sizes="(max-width: 1024px) 60vw, 22vw"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-[rgba(27,27,27,0.75)] via-[rgba(27,27,27,0.3)] to-transparent" />
              <div className="absolute bottom-4 left-4 right-4 space-y-2 text-white">
                <h3 className="text-lg font-semibold">{item.title}</h3>
                <p className="text-xs text-white/80">{item.description}</p>
              </div>
            </div>
            <div className="flex items-center justify-between gap-3 px-5 py-4 text-sm text-primary">
              <span className="font-semibold text-secondary transition group-hover:text-info">
                Заказать этот день
              </span>
              <span className="text-xl text-info transition group-hover:translate-x-1">→</span>
            </div>
          </Link>
        ))}
      </div>
      <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-12 bg-gradient-to-r from-white via-white/40 to-transparent dark:from-slate-950" />
      <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-12 bg-gradient-to-l from-white via-white/40 to-transparent dark:from-slate-950" />
    </div>
  );
}
