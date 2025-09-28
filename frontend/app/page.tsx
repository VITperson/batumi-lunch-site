import Image from "next/image";
import Link from "next/link";

import { MenuCarousel } from "@/components/menu/menu-carousel";

const benefits = [
  {
    icon: "⏱️",
    title: "Удобный график",
    description:
      "Меню публикуем заранее: собирайте обеды на всю неделю или оформляйте заказ накануне до 10:00, чтобы всё успеть вовремя.",
  },
  {
    icon: "🍲",
    title: "Домашние порции",
    description:
      "Каждый обед — 110 г мяса, 300 г гарнира и 250 г салата. Вкусно, сытно и без полуфабрикатов.",
  },
  {
    icon: "🚚",
    title: "Бесплатная доставка",
    description:
      "Привозим по будням с 12:30 до 15:30. Вы платите только 15 лари за обед — доставка включена.",
  },
];

const steps = [
  {
    number: "01",
    title: "Выберите блюда",
    description: "Откройте меню, отметьте понравившиеся позиции и дни доставки.",
  },
  {
    number: "02",
    title: "Подтвердите заказ",
    description: "Закажите заранее или до 10:00 в день доставки — мы подтвердим и начнём готовить.",
  },
  {
    number: "03",
    title: "Получайте вовремя",
    description: "Курьер привезёт обеды между 12:30 и 15:30. Разогрейте и наслаждайтесь.",
  },
];

const reviews = [
  {
    quote:
      "Заказываем на всю неделю: муж берёт с собой, я остаюсь дома с ребёнком. Всегда вкусно, и не нужно думать про закупки.",
    name: "Марина, мама в декрете",
  },
  {
    quote:
      "Работаю удалённо, и раньше постоянно пропускала обеды. Теперь просто разогреваю порцию – экономлю и время, и силы.",
    name: "Александр, дизайнер",
  },
  {
    quote:
      "Порадовало, что доставка бесплатная и всегда вовремя. Порции большие, часто оставляем немного на ужин.",
    name: "Семья Кобалия",
  },
];

const menuPreview = [
  {
    title: "Понедельник",
    image: "/dishphotos/Monday.png",
    description: "🥟 Пельмени домашние • 🥒🥬 Салат из огурцов и капусты",
  },
  {
    title: "Вторник",
    image: "/dishphotos/Tuesday.png",
    description: "🍛 Гречка с куриной котлетой • 🥗 Свекольный салат",
  },
  {
    title: "Среда",
    image: "/dishphotos/Wednesday.png",
    description: "🍝 Спагетти с фаршем • 🥒🍅 Салат из огурцов и помидоров",
  },
  {
    title: "Четверг",
    image: "/dishphotos/Thursday.png",
    description: "🍚 Рис с куриной котлетой • 🦀 Салат с крабовыми палочками",
  },
  {
    title: "Пятница",
    image: "/dishphotos/Friday.png",
    description: "🥬 Голубцы классические • 🥒🍅 Салат из огурцов и помидоров",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-16 pb-16">
      {/* Hero */}
      <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[color:var(--color-chip)] via-[color:var(--color-surface)] to-[color:var(--color-bg)] p-6 text-primary shadow-[0_30px_60px_-40px_rgba(27,27,27,0.4)] sm:p-10 dark:from-[rgba(58,42,30,0.75)] dark:via-[color:var(--color-surface)] dark:to-[color:var(--color-bg)]">
        <div className="relative z-10 grid gap-10 lg:grid-cols-[1.2fr,1fr] lg:items-center">
          <div className="space-y-6">
            <span className="inline-flex items-center gap-2 rounded-full bg-white/70 px-4 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-sky-600 shadow-sm shadow-sky-200 dark:bg-slate-800/80 dark:text-sky-300">
              Домашние обеды с заботой о времени
            </span>
            <h1 className="text-3xl font-bold leading-tight text-primary sm:text-4xl lg:text-5xl">
              Освободите вечера — мы привезём обеды для всей семьи
            </h1>
            <p className="max-w-xl text-base text-secondary sm:text-lg">
              Закажите блюда заранее или до 10:00 в день доставки и уже в обед получите тёплую домашнюю еду. 15 лари за целый набор, доставка бесплатна.
            </p>
            <div className="flex flex-wrap gap-4">
              <Link href="/planner" className="btn-primary">
                Оформить обед
              </Link>
              <Link href="/menu" className="btn-secondary">
                Посмотреть меню
              </Link>
            </div>
            <p className="text-sm text-secondary">
              Уже более <strong>100 семей</strong> в Батуми питаются с Batumi Lunch. Присоединяйтесь!
            </p>
          </div>
          <div className="relative h-64 w-full rounded-3xl bg-surface p-4 shadow-2xl shadow-[rgba(198,61,47,0.18)] sm:h-72">
            <Image
              src="/lunchPic.png"
              alt="Набор домашних обедов"
              fill
              className="rounded-2xl object-cover"
              sizes="(max-width: 1024px) 100vw, 40vw"
              priority
            />
          </div>
        </div>
        <div className="pointer-events-none absolute inset-0">
          <div className="absolute -top-24 left-0 h-72 w-72 rounded-full bg-[rgba(242,201,76,0.35)] blur-3xl" />
          <div className="absolute -bottom-32 right-0 h-80 w-80 rounded-full bg-[rgba(46,125,50,0.2)] blur-3xl" />
        </div>
      </section>

      {/* Menu carousel */}
      <section className="space-y-6">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <div>
            <h2 className="text-2xl font-semibold text-primary">Что в меню на этой неделе</h2>
            <p className="text-sm text-secondary">
              Пролистайте подборку и выберите день, который хотите попробовать прямо сейчас.
            </p>
          </div>
          <Link href="/menu" className="text-sm font-semibold text-info hover:underline">
            Смотреть все блюда →
          </Link>
        </div>
        <MenuCarousel items={menuPreview} />
      </section>

      {/* Benefits */}
      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 lg:gap-6 xl:grid-cols-4 xl:gap-8">
        {benefits.map((benefit) => (
          <article key={benefit.title} className="card flex h-full flex-col gap-4 p-6">
            <span className="text-2xl">{benefit.icon}</span>
            <h2 className="text-lg font-semibold text-primary">{benefit.title}</h2>
            <p className="text-sm text-secondary">{benefit.description}</p>
          </article>
        ))}
      </section>

      {/* Social Proof */}
      <section className="grid gap-6 lg:grid-cols-[1.1fr,1fr] lg:gap-10">
        <div className="card space-y-4 p-6 sm:p-8">
          <h2 className="text-2xl font-semibold text-primary">Что говорят наши клиенты</h2>
          <p className="text-sm text-secondary">
            Мы готовим так, как готовили бы для своих близких. Вот что говорят семьи и специалисты, которые уже с нами.
          </p>
          <div className="grid gap-4">
            {reviews.map((review) => (
              <blockquote
                key={review.name}
                className="rounded-2xl border border-outline bg-surface p-5 text-sm italic text-secondary shadow-inner"
              >
                “{review.quote}”
                <footer className="mt-3 text-xs font-semibold not-italic text-secondary">
                  {review.name}
                </footer>
              </blockquote>
            ))}
          </div>
        </div>
        <div className="card flex h-full flex-col justify-between gap-6 p-6 sm:p-8">
          <div>
            <h3 className="text-lg font-semibold text-primary">Более 4 млрд довольных клиентов</h3>
            <p className="mt-3 text-sm text-secondary">
              Мы работаем в Батуми с 2021 года и ежедневно кормим семьи, студентов и занятых специалистов.
            </p>
            <p className="mt-2 text-sm text-secondary">
              За это время доставили уже <strong>более 1000 обедов</strong> — и это только в нашем городе.
            </p>
          </div>
          <div className="rounded-3xl bg-[color:var(--color-chip)]/60 p-6 text-center text-sm text-secondary">
            <p>
              Присоединяйтесь к сообществу, которое доверило нам свой обед. Попробуйте — и забывайте о спешке у плиты!
            </p>
          </div>
        </div>
      </section>

      {/* Detailed menu preview */}
      <section className="space-y-6">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h2 className="text-2xl font-semibold text-primary">Меню по дням</h2>
          <Link href="/menu" className="text-sm font-semibold text-info hover:underline">
            Смотреть все блюда →
          </Link>
        </div>
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {menuPreview.slice(0, 3).map((item) => (
            <Link
              key={item.title}
              href={`/planner?day=${encodeURIComponent(item.title)}`}
              className="card group overflow-hidden p-0 transition hover:-translate-y-1 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
            >
              <div className="relative h-40 w-full">
                <Image
                  src={item.image}
                  alt={item.title}
                  fill
                  className="object-cover transition duration-300 group-hover:scale-105"
                  sizes="(max-width: 1024px) 100vw, 33vw"
                />
              </div>
             <div className="p-5">
                <h3 className="text-lg font-semibold text-primary transition group-hover:text-info">{item.title}</h3>
                <p className="mt-2 text-sm text-secondary">{item.description}</p>
                <span className="mt-4 inline-flex items-center gap-2 text-xs font-semibold text-info group-hover:gap-3">
                  Оформить на этот день
                  <span aria-hidden>→</span>
                </span>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="rounded-3xl bg-[color:var(--color-chip)]/45 p-6 shadow-inner sm:p-10 dark:bg-[rgba(58,42,30,0.65)]">
        <div className="flex flex-wrap items-center justify-between gap-6">
          <div className="max-w-xl space-y-3">
            <h2 className="text-2xl font-semibold text-primary">Как оформить заказ</h2>
            <p className="text-sm text-secondary">
              Три шага отделяют вас от горячего обеда. Мы заранее готовим продукты и доставляем в удобное окно времени.
            </p>
          </div>
          <Link href="/planner" className="btn-primary">
            Перейти к оформлению
          </Link>
        </div>
        <div className="mt-8 grid gap-6 md:grid-cols-3">
          {steps.map((step) => (
            <article key={step.number} className="surface-muted p-6 transition hover:-translate-y-1">
              <span className="text-xs font-semibold uppercase tracking-[0.3em] text-info">{step.number}</span>
              <h3 className="mt-3 text-lg font-semibold text-primary">{step.title}</h3>
              <p className="mt-2 text-sm text-secondary">{step.description}</p>
            </article>
          ))}
        </div>
      </section>

      {/* Final CTA */}
      <section className="rounded-3xl bg-gradient-to-br from-[#c63d2f] to-[#b33422] p-8 text-on-primary shadow-xl sm:p-12">
        <div className="grid gap-8 lg:grid-cols-[1.2fr,1fr] lg:items-center">
          <div className="space-y-4">
            <h2 className="text-3xl font-bold sm:text-4xl">Готовим как для своей семьи</h2>
            <p className="text-sm text-on-primary/90">
              Каждый обед — 110 г мяса, 300 г гарнира, 250 г салата. Фиксированная стоимость 15 лари, доставка по Батуми бесплатно.
            </p>
            <ul className="space-y-2 text-sm text-on-primary/90">
              <li>- Меню на неделю вперёд с возможностью заказа до 10:00 в день доставки</li>
              <li>- Доставка в будни с 12:30 до 15:30 без доплат</li>
              <li>- Свежие продукты, никакого промышленного фастфуда</li>
            </ul>
            <div className="flex flex-wrap gap-4">
              <Link href="/planner" className="btn-secondary">
                Заказать обеды на неделю
              </Link>
              <Link href="/menu" className="rounded-full border border-white/60 px-6 py-3 text-sm font-semibold text-on-primary transition hover:bg-white/10">
                Посмотреть меню
              </Link>
            </div>
          </div>
          <div className="relative h-64 w-full overflow-hidden rounded-3xl bg-white/10">
            <Image
              src="/dishphotos/Friday.png"
              alt="Сервировка семейного обеда"
              fill
              className="object-cover"
              sizes="(max-width: 1024px) 100vw, 40vw"
            />
          </div>
        </div>
      </section>
    </div>
  );
}
