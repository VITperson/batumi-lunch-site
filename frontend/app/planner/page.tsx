"use client";

import Image from "next/image";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { isAxiosError } from "axios";

import {
  DayOfferStatus,
  MenuDay,
  MenuWeekSummary,
  PlannerPreset,
  getCurrentMenu,
  getMenuWeeks,
  getPlannerPresets,
  MenuResponse,
} from "@/lib/api/endpoints/menu";
import {
  OrderCalcItem,
  OrderCalcRequest,
  PlannerWeekSelectionRequest,
  calculatePlannerOrder,
} from "@/lib/api/endpoints/orders";

const STORAGE_KEY = "planner-state:v2";
const DAY_ORDER = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"] as const;
const MAX_PORTIONS = 8;
const MAX_WEEKS = 8;

type Selection = {
  offerId: string;
  day: string;
  portions: number;
};

type WeekPlan = {
  weekStart: string | null;
  selections: Record<string, Selection>;
  enabled: boolean;
};

type PlannerState = {
  weeks: WeekPlan[];
  weeksCount: number;
  repeatWeeks: boolean;
  address: string;
  promoCode: string;
};

const DEFAULT_STATE: PlannerState = {
  weeks: [createWeekPlan(null)],
  weeksCount: 1,
  repeatWeeks: true,
  address: "",
  promoCode: "",
};

function loadInitialState(): PlannerState {
  if (typeof window === "undefined") {
    return DEFAULT_STATE;
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return DEFAULT_STATE;
    }
    const parsed = JSON.parse(raw) as Partial<PlannerState> & {
      weekStart?: string | null;
      selections?: Record<string, Selection>;
    };

    if (Array.isArray((parsed as any).weeks)) {
      const rawWeeks = (parsed as any).weeks as Array<Partial<WeekPlan>>;
      const weeks = rawWeeks.map((week, index) => ({
        weekStart: typeof week?.weekStart === "string" ? week.weekStart : null,
        selections: normalizeSelections(week?.selections),
        enabled: index === 0 ? true : week?.enabled !== false,
      }));
      const weeksCount = clampNumber(parsed.weeksCount ?? weeks.length ?? 1, 1, MAX_WEEKS);
      const repeatWeeks = parsed.repeatWeeks ?? true;
      const baseWeekStart = weeks[0]?.weekStart ?? null;
      const normalizedWeeks = ensureWeeks(weeks.length > 0 ? weeks : [createWeekPlan(baseWeekStart)], weeksCount, baseWeekStart, repeatWeeks);
      return {
        weeks: normalizedWeeks,
        weeksCount,
        repeatWeeks,
        address: parsed.address ?? "",
        promoCode: parsed.promoCode ?? "",
      };
    }

    const legacySelections = normalizeSelections(parsed.selections);
    const legacyWeekStart = parsed.weekStart ?? null;
    const repeatWeeks = parsed.repeatWeeks ?? true;
    const weeksCount = clampNumber(parsed.weeksCount ?? 1, 1, MAX_WEEKS);
    const baseWeek = createWeekPlan(legacyWeekStart, true, legacySelections);
    return {
      weeks: ensureWeeks([baseWeek], weeksCount, legacyWeekStart, repeatWeeks),
      weeksCount,
      repeatWeeks,
      address: parsed.address ?? "",
      promoCode: parsed.promoCode ?? "",
    };
  } catch (error) {
    console.warn("Failed to restore planner state", error);
    return DEFAULT_STATE;
  }
}

function normalizeSelections(input: unknown): Record<string, Selection> {
  if (!input || typeof input !== "object") {
    return {};
  }
  const result: Record<string, Selection> = {};
  for (const [offerId, rawValue] of Object.entries(input as Record<string, unknown>)) {
    if (!rawValue || typeof rawValue !== "object") {
      continue;
    }
    const value = rawValue as Partial<Selection>;
    const id = typeof value.offerId === "string" ? value.offerId : offerId;
    const day = typeof value.day === "string" ? value.day : "";
    const rawPortions = Number(value.portions);
    const portions = Number.isFinite(rawPortions) && rawPortions > 0 ? Math.min(Math.floor(rawPortions), MAX_PORTIONS) : 1;
    result[id] = { offerId: id, day, portions };
  }
  return result;
}

function clampNumber(value: number, min: number, max: number): number {
  if (Number.isNaN(value)) {
    return min;
  }
  return Math.min(Math.max(Math.floor(value), min), max);
}

function shiftWeekStart(base: string | null, offset: number): string | null {
  if (!base) {
    return null;
  }
  const date = new Date(`${base}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  date.setUTCDate(date.getUTCDate() + offset * 7);
  return date.toISOString().slice(0, 10);
}

function cloneSelections(source: Record<string, Selection>): Record<string, Selection> {
  const entries = Object.entries(source).map(([key, value]) => [key, { ...value }]);
  return Object.fromEntries(entries);
}

function createWeekPlan(
  weekStart: string | null,
  enabled = true,
  selections: Record<string, Selection> = {},
): WeekPlan {
  return {
    weekStart,
    enabled,
    selections: cloneSelections(selections),
  };
}

function ensureWeeks(
  weeks: WeekPlan[],
  targetCount: number,
  baseWeekStart: string | null,
  repeatWeeks: boolean,
): WeekPlan[] {
  const normalized: WeekPlan[] = [];
  const base = weeks[0] ?? createWeekPlan(baseWeekStart);
  const baseSelections = cloneSelections(base.selections);
  for (let index = 0; index < targetCount; index += 1) {
    const existing = weeks[index];
    const computedStart = shiftWeekStart(baseWeekStart, index);
    if (index === 0) {
      normalized.push({
        weekStart: computedStart ?? existing?.weekStart ?? base.weekStart ?? baseWeekStart,
        enabled: true,
        selections: existing ? cloneSelections(existing.selections) : cloneSelections(baseSelections),
      });
      continue;
    }

    const selections = repeatWeeks
      ? cloneSelections(baseSelections)
      : existing
        ? cloneSelections(existing.selections)
        : {};
    normalized.push({
      weekStart: computedStart ?? existing?.weekStart ?? null,
      enabled: existing?.enabled ?? true,
      selections,
    });
  }
  return normalized;
}

function areSelectionMapsEqual(left: Record<string, Selection>, right: Record<string, Selection>): boolean {
  const leftKeys = Object.keys(left);
  const rightKeys = Object.keys(right);
  if (leftKeys.length !== rightKeys.length) {
    return false;
  }
  for (const key of leftKeys) {
    const a = left[key];
    const b = right[key];
    if (!b || a.offerId !== b.offerId || a.day !== b.day || a.portions !== b.portions) {
      return false;
    }
  }
  return true;
}

function areWeeksEqual(left: WeekPlan[], right: WeekPlan[]): boolean {
  if (left.length !== right.length) {
    return false;
  }
  for (let index = 0; index < left.length; index += 1) {
    const a = left[index];
    const b = right[index];
    if (!b) {
      return false;
    }
    if (a.weekStart !== b.weekStart || a.enabled !== b.enabled) {
      return false;
    }
    if (!areSelectionMapsEqual(a.selections, b.selections)) {
      return false;
    }
  }
  return true;
}

function syncRepeatedWeeks(weeks: WeekPlan[], baseSelections: Record<string, Selection>): WeekPlan[] {
  if (weeks.length <= 1) {
    return weeks;
  }
  const synchronized: WeekPlan[] = [weeks[0]];
  let changed = false;
  for (let index = 1; index < weeks.length; index += 1) {
    const current = weeks[index];
    const nextSelections = cloneSelections(baseSelections);
    if (areSelectionMapsEqual(current.selections, nextSelections)) {
      synchronized.push(current);
    } else {
      synchronized.push({ ...current, selections: nextSelections });
      changed = true;
    }
  }
  return changed ? synchronized : weeks;
}

function formatWeekTitle(weekStart: string | null, index: number): string {
  if (!weekStart) {
    return index === 0 ? "Ближайшая неделя" : `Неделя ${index + 1}`;
  }
  const date = new Date(`${weekStart}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) {
    return index === 0 ? "Ближайшая неделя" : `Неделя ${index + 1}`;
  }
  return new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "2-digit" }).format(date);
}

function formatCurrency(amount: number, currency: string): string {
  if (Number.isNaN(amount)) return "0";
  const value = amount / 100;
  const suffix = currency === "GEL" ? "₾" : currency;
  return `${value.toFixed(2)} ${suffix}`;
}

function sortDays(days: MenuDay[]): MenuDay[] {
  const order = new Map<string, number>(DAY_ORDER.map((day, index) => [day, index]));
  return [...days].sort((a, b) => {
    const left = order.get(a.day) ?? 0;
    const right = order.get(b.day) ?? 0;
    return left - right;
  });
}

type SelectionEntry = {
  menuDay: MenuDay;
  selection: Selection;
};

function buildSelectionEntries(menuDays: MenuDay[], selections: Record<string, Selection>): SelectionEntry[] {
  const order = new Map<string, number>(DAY_ORDER.map((day, index) => [day, index]));
  const pairs: SelectionEntry[] = [];
  for (const item of menuDays) {
    if (!item.offerId) continue;
    const selection = selections[item.offerId];
    if (!selection) continue;
    pairs.push({ menuDay: item, selection });
  }
  return pairs.sort((a, b) => {
    const left = order.get(a.menuDay.day) ?? 0;
    const right = order.get(b.menuDay.day) ?? 0;
    return left - right;
  });
}

function PlannerStatusBadge({ status }: { status: DayOfferStatus }) {
  const map: Record<DayOfferStatus, { label: string; tone: string }> = {
    available: { label: "Доступно", tone: "bg-emerald-100 text-emerald-700" },
    sold_out: { label: "Раскуплено", tone: "bg-amber-100 text-amber-700" },
    closed: { label: "Закрыто", tone: "bg-slate-200 text-slate-600" },
  };
  const payload = map[status];
  return (
    <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${payload.tone}`}>
      {payload.label}
    </span>
  );
}

type PageProps = {
  searchParams?: Record<string, string | string[]>;
};

export default function PlannerPage({ searchParams }: PageProps) {
  const initialDayParam = useMemo(() => {
    const raw = searchParams?.day;
    return typeof raw === "string" ? raw : null;
  }, [searchParams]);

  const [plannerState, setPlannerState] = useState<PlannerState>(loadInitialState);
  const [isWeeksModalOpen, setWeeksModalOpen] = useState(false);

  const primaryWeek = plannerState.weeks[0] ?? createWeekPlan(null);
  const activeWeekStart = primaryWeek.weekStart;

  const menuQuery = useQuery({
    queryKey: ["planner", "menu", activeWeekStart ?? "current"],
    queryFn: async () => {
      try {
        return await getCurrentMenu(activeWeekStart ? { weekStart: activeWeekStart } : undefined);
      } catch (error) {
        if (isAxiosError(error) && error.response?.status === 404) {
          return null;
        }
        throw error;
      }
    },
    retry: false,
  });
  const weeksQuery = useQuery({ queryKey: ["planner", "weeks"], queryFn: () => getMenuWeeks() });
  const presetsQuery = useQuery({ queryKey: ["planner", "presets"], queryFn: () => getPlannerPresets() });

  const menu = menuQuery.data ?? null;

  const weekLabelMap = useMemo(() => {
    const map = new Map<string, string>();
    for (const item of weeksQuery.data ?? []) {
      if (item.weekStart) {
        map.set(item.weekStart, item.label);
      }
    }
    return map;
  }, [weeksQuery.data]);

  useEffect(() => {
    setPlannerState((prev) => {
      const targetCount = clampNumber(prev.weeksCount, 1, MAX_WEEKS);
      const targetWeekStart = menu?.weekStart ?? prev.weeks[0]?.weekStart ?? null;
      let weeks = ensureWeeks(prev.weeks, targetCount, targetWeekStart, prev.repeatWeeks);

      if (menu) {
        const validIds = new Set(
          menu.items.map((item) => item.offerId).filter(Boolean) as string[],
        );
        const filteredSelections = Object.fromEntries(
          Object.entries(weeks[0].selections).filter(([offerId]) => validIds.has(offerId)),
        );
        if (!areSelectionMapsEqual(filteredSelections, weeks[0].selections)) {
          weeks = [...weeks];
          weeks[0] = { ...weeks[0], selections: filteredSelections };
        }
      }

      if (prev.repeatWeeks) {
        const synced = syncRepeatedWeeks(weeks, weeks[0].selections);
        if (!areWeeksEqual(synced, weeks)) {
          weeks = synced;
        }
      }

      return areWeeksEqual(weeks, prev.weeks) ? prev : { ...prev, weeks };
    });
  }, [menu]);

  useEffect(() => {
    if (!menu || !initialDayParam) return;
    const targetDay = menu.items.find(
      (item) => item.day === initialDayParam && item.offerId && item.status === "available",
    );
    if (!targetDay?.offerId) return;
    setPlannerState((prev) => {
      const targetCount = clampNumber(prev.weeksCount, 1, MAX_WEEKS);
      const targetWeekStart = menu.weekStart ?? prev.weeks[0]?.weekStart ?? null;
      let weeks = ensureWeeks(prev.weeks, targetCount, targetWeekStart, prev.repeatWeeks);
      const current = weeks[0];
      if (!current || current.selections[targetDay.offerId]) {
        return prev;
      }
      const selections = {
        ...current.selections,
        [targetDay.offerId]: { offerId: targetDay.offerId, day: targetDay.day, portions: 1 },
      };
      weeks[0] = { ...current, selections };
      if (prev.repeatWeeks) {
        weeks = syncRepeatedWeeks(weeks, selections);
      }
      return { ...prev, weeks };
    });
  }, [menu, initialDayParam]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(plannerState));
  }, [plannerState]);

  const menuDays = useMemo(() => (menu ? sortDays(menu.items) : []), [menu]);
  const selectionEntries = useMemo(
    () => buildSelectionEntries(menuDays, primaryWeek.selections),
    [menuDays, primaryWeek.selections],
  );

  const baseSubtotalFallback = useMemo(
    () =>
      selectionEntries.reduce(
        (sum, entry) => sum + entry.selection.portions * entry.menuDay.price.amount,
        0,
      ),
    [selectionEntries],
  );

  const basePortions = useMemo(
    () => selectionEntries.reduce((sum, entry) => sum + entry.selection.portions, 0),
    [selectionEntries],
  );

  const activeWeeks = useMemo(
    () => plannerState.weeks.slice(0, clampNumber(plannerState.weeksCount, 1, MAX_WEEKS)),
    [plannerState.weeks, plannerState.weeksCount],
  );

  const totalEnabledWeeks = useMemo(() => {
    let count = 0;
    activeWeeks.forEach((week, index) => {
      if (index === 0 || week.enabled) {
        count += 1;
      }
    });
    return count;
  }, [activeWeeks]);

  const weeksPayload = useMemo<PlannerWeekSelectionRequest[]>(() => {
    const total = clampNumber(plannerState.weeksCount, 1, MAX_WEEKS);
    const baseWeekStart = plannerState.weeks[0]?.weekStart ?? null;
    const payload: PlannerWeekSelectionRequest[] = [];
    for (let index = 0; index < total; index += 1) {
      const weekPlan = plannerState.weeks[index] ?? createWeekPlan(shiftWeekStart(baseWeekStart, index));
      const baseSelections = plannerState.weeks[0]?.selections ?? {};
      const selectionsSource =
        index === 0
          ? weekPlan.selections
          : plannerState.repeatWeeks
            ? baseSelections
            : weekPlan.selections;
      payload.push({
        weekStart: weekPlan.weekStart ?? shiftWeekStart(baseWeekStart, index),
        enabled: index === 0 ? true : weekPlan.enabled,
        selections: Object.values(selectionsSource).map(({ offerId, portions }) => ({
          offerId,
          portions,
        })),
      });
    }
    return payload;
  }, [plannerState.weeks, plannerState.weeksCount, plannerState.repeatWeeks]);

  const calcPayload = useMemo<OrderCalcRequest>(() => {
    const selections = selectionEntries.map(({ selection }) => ({
      offerId: selection.offerId,
      portions: selection.portions,
    }));
    const promoCode = plannerState.promoCode.trim();
    const address = plannerState.address.trim();
    return {
      selections,
      weeks: weeksPayload,
      promoCode: promoCode.length > 0 ? promoCode : undefined,
      address: address.length > 0 ? address : undefined,
    };
  }, [selectionEntries, weeksPayload, plannerState.address, plannerState.promoCode]);

  const hasActiveSelection = weeksPayload.some((week) => week.enabled && week.selections.length > 0);

  const calcQuery = useQuery({
    queryKey: ["planner", "calc", calcPayload],
    queryFn: () => calculatePlannerOrder(calcPayload),
    enabled: hasActiveSelection,
    keepPreviousData: true,
    refetchOnWindowFocus: false,
  });

  const overallSubtotal =
    calcQuery.data?.subtotal ??
    (plannerState.repeatWeeks ? baseSubtotalFallback * totalEnabledWeeks : baseSubtotalFallback);
  const overallDiscount = calcQuery.data?.discount ?? 0;
  const overallTotal = calcQuery.data?.total ?? Math.max(overallSubtotal - overallDiscount, 0);
  const currency = calcQuery.data?.currency ?? "GEL";
  const warnings = calcQuery.data?.warnings ?? [];
  const promoError = calcQuery.data?.promoCodeError ?? null;

  const totalPortions = useMemo(() => {
    if (calcQuery.data) {
      return calcQuery.data.weeks
        .filter((week) => week.enabled)
        .reduce(
          (sum, week) =>
            sum + week.items.reduce((acc, item) => acc + item.acceptedPortions, 0),
          0,
        );
    }
    if (plannerState.repeatWeeks) {
      return basePortions * totalEnabledWeeks;
    }
    return activeWeeks.reduce((sum, week, index) => {
      if (index !== 0 && !week.enabled) {
        return sum;
      }
      if (index === 0) {
        return sum + basePortions;
      }
      return (
        sum + Object.values(week.selections).reduce((acc, selection) => acc + selection.portions, 0)
      );
    }, 0);
  }, [calcQuery.data, plannerState.repeatWeeks, basePortions, totalEnabledWeeks, activeWeeks]);

  const presets = presetsQuery.data ?? [];
  const isLoading = menuQuery.isLoading;
  const isCalculating = calcQuery.isFetching;

  const weeksBreakdown = useMemo(() => {
    if (calcQuery.data) {
      return calcQuery.data.weeks.map((week, index) => ({
        index,
        weekStart: week.weekStart ?? null,
        label:
          week.label ??
          (week.weekStart ? weekLabelMap.get(week.weekStart) : undefined) ??
          formatWeekTitle(week.weekStart ?? null, index),
        enabled: week.enabled,
        menuStatus: week.menuStatus,
        subtotal: week.subtotal,
        currency: week.currency ?? calcQuery.data!.currency,
      }));
    }
    return activeWeeks.map((week, index) => {
      const weekStart = week.weekStart ?? shiftWeekStart(activeWeeks[0]?.weekStart ?? null, index);
      return {
        index,
        weekStart,
        label: weekLabelMap.get(weekStart ?? "") ?? formatWeekTitle(weekStart, index),
        enabled: index === 0 ? true : week.enabled,
        menuStatus: index === 0 ? (menu ? "published" : "pending") : week.enabled ? "pending" : "disabled",
        subtotal: index === 0 ? baseSubtotalFallback : 0,
        currency: "GEL",
      };
    });
  }, [calcQuery.data, activeWeeks, weekLabelMap, menu, baseSubtotalFallback]);

  const primaryWeekQuote = calcQuery.data?.weeks?.[0] ?? null;
  const primaryCalcItems = primaryWeekQuote?.items ?? calcQuery.data?.items ?? [];

  const handleToggleDay = useCallback(
    (day: MenuDay) => {
      if (!day.offerId || day.status !== "available") return;
      setPlannerState((prev) => {
        const targetCount = clampNumber(prev.weeksCount, 1, MAX_WEEKS);
        const targetWeekStart = menu?.weekStart ?? prev.weeks[0]?.weekStart ?? null;
        let weeks = ensureWeeks(prev.weeks, targetCount, targetWeekStart, prev.repeatWeeks);
        const current = weeks[0];
        if (!current) return prev;
        const selections = { ...current.selections };
        if (selections[day.offerId]) {
          delete selections[day.offerId];
        } else {
          selections[day.offerId] = { offerId: day.offerId, day: day.day, portions: 1 };
        }
        weeks[0] = { ...current, selections };
        if (prev.repeatWeeks) {
          weeks = syncRepeatedWeeks(weeks, selections);
        }
        return areWeeksEqual(weeks, prev.weeks) ? prev : { ...prev, weeks };
      });
    },
    [menu],
  );

  const handleChangePortions = useCallback(
    (offerId: string, nextPortions: number) => {
      setPlannerState((prev) => {
        const targetCount = clampNumber(prev.weeksCount, 1, MAX_WEEKS);
        const targetWeekStart = menu?.weekStart ?? prev.weeks[0]?.weekStart ?? null;
        let weeks = ensureWeeks(prev.weeks, targetCount, targetWeekStart, prev.repeatWeeks);
        const current = weeks[0];
        if (!current?.selections[offerId]) {
          return prev;
        }
        const clamped = Math.min(Math.max(nextPortions, 1), MAX_PORTIONS);
        if (current.selections[offerId].portions === clamped) {
          return prev;
        }
        const selections = {
          ...current.selections,
          [offerId]: { ...current.selections[offerId], portions: clamped },
        };
        weeks[0] = { ...current, selections };
        if (prev.repeatWeeks) {
          weeks = syncRepeatedWeeks(weeks, selections);
        }
        return { ...prev, weeks };
      });
    },
    [menu],
  );

  const handleApplyPreset = useCallback(
    (preset: PlannerPreset) => {
      if (!menu) return;
      setPlannerState((prev) => {
        const targetCount = clampNumber(prev.weeksCount, 1, MAX_WEEKS);
        const targetWeekStart = menu.weekStart ?? prev.weeks[0]?.weekStart ?? null;
        let weeks = ensureWeeks(prev.weeks, targetCount, targetWeekStart, prev.repeatWeeks);
        const selections: Record<string, Selection> = {};
        for (const dayName of preset.days) {
          const menuDay = menu.items.find(
            (item) => item.day === dayName && item.offerId && item.status === "available",
          );
          if (!menuDay?.offerId) continue;
          selections[menuDay.offerId] = {
            offerId: menuDay.offerId,
            day: menuDay.day,
            portions: Math.max(1, preset.portions),
          };
        }
        weeks[0] = { ...weeks[0], selections };
        if (prev.repeatWeeks) {
          weeks = syncRepeatedWeeks(weeks, selections);
        }
        return { ...prev, weeks };
      });
    },
    [menu],
  );

  const handleClearSelection = useCallback((offerId: string) => {
    setPlannerState((prev) => {
      if (!prev.weeks.length || !prev.weeks[0].selections[offerId]) {
        return prev;
      }
      const selections = { ...prev.weeks[0].selections };
      delete selections[offerId];
      const weeks = prev.weeks.map((week, index) => {
        if (index === 0) {
          return { ...week, selections };
        }
        if (!prev.repeatWeeks) {
          return week;
        }
        return { ...week, selections: {} };
      });
      const syncedWeeks = prev.repeatWeeks ? syncRepeatedWeeks(weeks, selections) : weeks;
      return { ...prev, weeks: syncedWeeks };
    });
  }, []);

  const handleClearAll = useCallback(() => {
    setPlannerState((prev) => {
      if (!prev.weeks.length || Object.keys(prev.weeks[0].selections).length === 0) {
        return prev;
      }
      const clearedWeeks = prev.weeks.map((week, index) => {
        if (index === 0) {
          return { ...week, selections: {} };
        }
        if (!prev.repeatWeeks) {
          return week;
        }
        return { ...week, selections: {} };
      });
      const syncedWeeks = prev.repeatWeeks ? syncRepeatedWeeks(clearedWeeks, {}) : clearedWeeks;
      return { ...prev, weeks: syncedWeeks };
    });
  }, []);

  const handleAddressChange = useCallback((value: string) => {
    setPlannerState((prev) => ({ ...prev, address: value }));
  }, []);

  const handlePromoChange = useCallback((value: string) => {
    setPlannerState((prev) => ({ ...prev, promoCode: value.toUpperCase() }));
  }, []);

  const handleWeekSelect = useCallback((week: MenuWeekSummary) => {
    const baseWeekStart = week.weekStart ?? null;
    setPlannerState((prev) => ({
      ...prev,
      weeks: ensureWeeks([createWeekPlan(baseWeekStart)], clampNumber(prev.weeksCount, 1, MAX_WEEKS), baseWeekStart, prev.repeatWeeks),
    }));
  }, []);

  const handleWeeksCountChange = useCallback((value: number) => {
    const target = clampNumber(value, 1, MAX_WEEKS);
    setPlannerState((prev) => {
      if (target === prev.weeksCount) {
        return prev;
      }
      const baseWeekStart = prev.weeks[0]?.weekStart ?? null;
      const weeks = ensureWeeks(prev.weeks, target, baseWeekStart, prev.repeatWeeks);
      return { ...prev, weeksCount: target, weeks };
    });
  }, []);

  const handleRepeatToggle = useCallback((value: boolean) => {
    setPlannerState((prev) => {
      if (value === prev.repeatWeeks) {
        return prev;
      }
      const baseWeekStart = prev.weeks[0]?.weekStart ?? null;
      let weeks = ensureWeeks(prev.weeks, prev.weeksCount, baseWeekStart, value);
      if (value) {
        weeks = syncRepeatedWeeks(weeks, weeks[0].selections);
      }
      return { ...prev, repeatWeeks: value, weeks };
    });
  }, []);

  const updateWeekPlan = useCallback(
    (index: number, updater: (week: WeekPlan) => WeekPlan) => {
      setPlannerState((prev) => {
        const targetCount = clampNumber(prev.weeksCount, 1, MAX_WEEKS);
        const baseWeekStart = prev.weeks[0]?.weekStart ?? null;
        let weeks = ensureWeeks(prev.weeks, targetCount, baseWeekStart, prev.repeatWeeks);
        if (index < 0 || index >= weeks.length) {
          return prev;
        }
        const updated = updater(weeks[index]);
        weeks = weeks.map((week, idx) =>
          idx === index ? { ...updated, enabled: idx === 0 ? true : updated.enabled } : week,
        );
        if (prev.repeatWeeks && index === 0) {
          weeks = syncRepeatedWeeks(weeks, weeks[0].selections);
        }
        return areWeeksEqual(weeks, prev.weeks) ? prev : { ...prev, weeks };
      });
    },
    [],
  );

  const handleOpenWeeksModal = useCallback(() => setWeeksModalOpen(true), []);
  const handleCloseWeeksModal = useCallback(() => setWeeksModalOpen(false), []);

  const handleCheckout = useCallback(() => {
    window.alert(
      "Онлайн-оплата многонедельных заказов появится в следующей итерации. Пока что оформите заказ через менеджера — мы сохраним ваш план.",
    );
  }, []);

  const weeks = weeksQuery.data ?? [];
  const plannerPresets = presetsQuery.data ?? [];

  return (
    <>
      {/* Update usages of presets to plannerPresets in the JSX below. */}
      <div className="space-y-8 pb-16">
        <section className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-[rgba(238,214,196,0.7)] via-white to-[rgba(242,201,76,0.4)] p-6 sm:p-10 shadow-[0_30px_60px_-40px_rgba(27,27,27,0.45)]">
          <div className="grid gap-6 lg:grid-cols-[1.2fr,1fr] lg:items-center">
            <div className="space-y-4">
            <span className="inline-flex items-center gap-2 rounded-full bg-white/80 px-4 py-1 text-xs font-semibold uppercase tracking-[0.25em] text-sky-600 shadow-sm">
              Планировщик недели
            </span>
            <h1 className="text-3xl font-semibold text-slate-900 sm:text-4xl lg:text-5xl">
              Соберите идеальную неделю обедов за пару минут
            </h1>
            <p className="text-sm text-slate-600 sm:text-base">
              Отмечайте дни, выбирайте количество порций и сразу видите общую стоимость. Доставка по Батуми включена в цену.
            </p>
            <div className="flex flex-wrap gap-3 text-xs text-slate-500">
              <span className="inline-flex items-center gap-2 rounded-full bg-white/80 px-3 py-1">
                <span className="h-2 w-2 rounded-full bg-emerald-400" aria-hidden /> Свободные дни
              </span>
              <span className="inline-flex items-center gap-2 rounded-full bg-white/80 px-3 py-1">
                <span className="h-2 w-2 rounded-full bg-amber-400" aria-hidden /> Осталось мало порций
              </span>
              <span className="inline-flex items-center gap-2 rounded-full bg-white/80 px-3 py-1">
                <span className="h-2 w-2 rounded-full bg-slate-400" aria-hidden /> Недоступно к заказу
              </span>
            </div>
          </div>
          <div className="relative h-64 w-full overflow-hidden rounded-3xl bg-white/60">
            <Image src="/kitchen.png" alt="Кухня Batumi Lunch" fill className="object-cover" />
          </div>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
        <div className="space-y-6">
          <WeekSelector
            weeks={weeks}
            currentWeekStart={primaryWeek.weekStart ?? menu?.weekStart ?? null}
            onSelect={handleWeekSelect}
            isLoading={weeksQuery.isLoading}
          />

          <PlannerGrid
            isLoading={isLoading}
            menuDays={menuDays}
            selections={primaryWeek.selections}
            onToggle={handleToggleDay}
            onChangePortions={handleChangePortions}
          />

          <PresetRow presets={presets} onApply={handleApplyPreset} disabled={isLoading || presetsQuery.isLoading} />

          <FAQBlock />
        </div>

        <PlannerSummary
          selections={selectionEntries}
          calcLines={primaryCalcItems}
          subtotal={overallSubtotal}
          total={overallTotal}
          discount={overallDiscount}
          currency={currency}
          totalPortions={totalPortions}
          address={plannerState.address}
          promoCode={plannerState.promoCode}
          onAddressChange={handleAddressChange}
          onPromoChange={handlePromoChange}
          onRemoveSelection={handleClearSelection}
          onClearAll={handleClearAll}
          onCheckout={handleCheckout}
          warnings={warnings}
          promoError={promoError}
          isCalculating={isCalculating}
          disabled={!hasActiveSelection}
          weeksCount={plannerState.weeksCount}
          repeatWeeks={plannerState.repeatWeeks}
          onWeeksCountChange={handleWeeksCountChange}
          onRepeatToggle={handleRepeatToggle}
          onOpenWeeksModal={handleOpenWeeksModal}
          weeksBreakdown={weeksBreakdown}
        />
      </div>
      </div>
      <WeeksModal
        open={isWeeksModalOpen}
        onClose={handleCloseWeeksModal}
        weeks={plannerState.weeks}
        weeksCount={plannerState.weeksCount}
        repeatWeeks={plannerState.repeatWeeks}
        weekLabelMap={weekLabelMap}
        primaryMenu={menu}
        onUpdateWeek={updateWeekPlan}
      />
    </>
  );
}

type WeekSelectorProps = {
  weeks: MenuWeekSummary[];
  currentWeekStart: string | null;
  onSelect: (week: MenuWeekSummary) => void;
  isLoading: boolean;
};

function WeekSelector({ weeks, currentWeekStart, onSelect, isLoading }: WeekSelectorProps) {
  return (
    <div className="flex flex-col gap-3 rounded-3xl border border-slate-200/60 bg-white/80 p-4 shadow-sm shadow-slate-200">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Выберите неделю</h2>
          <p className="text-xs text-slate-500">По умолчанию показана ближайшая доступная неделя.</p>
        </div>
        {isLoading && <span className="text-xs text-slate-400">Загружаем…</span>}
      </div>
      <div className="flex flex-wrap gap-3">
        {weeks.map((week) => {
          const isActive = week.weekStart === currentWeekStart;
          return (
            <button
              key={week.weekStart ?? week.label}
              type="button"
              onClick={() => onSelect(week)}
              className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                isActive
                  ? "bg-slate-900 text-white shadow"
                  : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-50"
              }`}
            >
              {week.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

type PlannerGridProps = {
  menuDays: MenuDay[];
  selections: Record<string, Selection>;
  isLoading: boolean;
  onToggle: (day: MenuDay) => void;
  onChangePortions: (offerId: string, portions: number) => void;
  disabled?: boolean;
};

function PlannerGrid({ menuDays, selections, isLoading, onToggle, onChangePortions, disabled = false }: PlannerGridProps) {
  if (isLoading) {
    return (
      <div className="rounded-3xl border border-slate-200/60 bg-white/80 p-10 text-center text-sm text-slate-500 shadow-sm">
        Загружаем меню недели…
      </div>
    );
  }

  if (menuDays.length === 0) {
    return (
      <div className="rounded-3xl border border-dashed border-slate-200 bg-white/80 p-10 text-center text-sm text-slate-500 shadow-sm">
        Меню для выбранной недели ещё не опубликовано. Загляните позже — мы обновим блюда.
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {menuDays.map((day) => {
        const selection = day.offerId ? selections[day.offerId] : undefined;
        return (
          <PlannerDayCard
            key={day.day}
            day={day}
            selection={selection}
            onToggle={() => onToggle(day)}
            onChangePortions={onChangePortions}
            disabled={disabled}
          />
        );
      })}
    </div>
  );
}

type PlannerDayCardProps = {
  day: MenuDay;
  selection?: Selection;
  onToggle: () => void;
  onChangePortions: (offerId: string, portions: number) => void;
  disabled?: boolean;
};

function PlannerDayCard({ day, selection, onToggle, onChangePortions, disabled = false }: PlannerDayCardProps) {
  const isAvailable = day.status === "available" && Boolean(day.offerId);
  const isSelected = Boolean(selection);
  const portionsAvailable = day.portionsAvailable ?? null;
  const allergens = day.allergens.map((item) => item.trim()).filter(Boolean);
  const canInteract = isAvailable && !disabled;

  return (
    <article
      className={`relative overflow-hidden rounded-3xl border p-4 shadow-sm transition ${
        isSelected ? "border-sky-400/70 shadow-[0_18px_35px_-25px_rgba(15,82,186,0.7)]" : "border-slate-200/70 bg-white/85"
      } ${!isAvailable || disabled ? "opacity-60" : ""}`}
    >
      {day.photoUrl && (
        <div className="relative mb-4 h-40 w-full overflow-hidden rounded-2xl">
          <Image src={day.photoUrl} alt={day.day} fill className="object-cover" sizes="(max-width: 1024px) 100vw, 33vw" />
        </div>
      )}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">{day.day}</h3>
          {day.badge && (
            <span className="mt-1 inline-flex items-center rounded-full bg-slate-900/90 px-3 py-1 text-xs font-medium text-white">
              {day.badge}
            </span>
          )}
        </div>
        <PlannerStatusBadge status={day.status as DayOfferStatus} />
      </div>
      <ul className="mt-3 space-y-1 text-sm text-slate-600">
        {day.dishes.map((dish) => (
          <li key={dish} className="flex items-start gap-2">
            <span aria-hidden className="mt-1 h-1.5 w-1.5 rounded-full bg-slate-400" />
            <span>{dish}</span>
          </li>
        ))}
      </ul>
      <div className="mt-4 flex items-center justify-between">
        <div className="text-sm text-slate-500">
          {day.calories ? `${day.calories} ккал · ` : ""}
          {formatCurrency(day.price.amount, day.price.currency)} за порцию
        </div>
        <button
          type="button"
          onClick={onToggle}
          disabled={!canInteract}
          className={`rounded-full px-4 py-2 text-sm font-medium transition ${
            isSelected ? "bg-sky-600 text-white" : "bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50"
          } ${!canInteract ? "cursor-not-allowed opacity-70" : ""}`}
        >
          {isSelected ? (canInteract ? "Добавлено" : "Выбрано") : "Добавить"}
        </button>
      </div>
      {isSelected && day.offerId && (
        <div className="mt-4 flex items-center justify-between rounded-2xl bg-slate-100/70 px-3 py-2 text-sm">
          <span className="text-slate-600">Количество порций</span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="flex h-8 w-8 items-center justify-center rounded-full bg-white text-slate-600 ring-1 ring-slate-300 disabled:cursor-not-allowed disabled:opacity-50"
              onClick={() => onChangePortions(day.offerId!, selection!.portions - 1)}
              disabled={!canInteract}
            >
              −
            </button>
            <span className="min-w-[2ch] text-center font-semibold text-slate-900">{selection!.portions}</span>
            <button
              type="button"
              className="flex h-8 w-8 items-center justify-center rounded-full bg-white text-slate-600 ring-1 ring-slate-300 disabled:cursor-not-allowed disabled:opacity-50"
              onClick={() => onChangePortions(day.offerId!, selection!.portions + 1)}
              disabled={!canInteract}
            >
              +
            </button>
          </div>
        </div>
      )}
      {portionsAvailable !== null && (
        <p className="mt-3 text-xs text-slate-500">Осталось {portionsAvailable} порций на неделю</p>
      )}
      {allergens.length > 0 && (
        <p className="mt-2 text-xs text-slate-400">Аллергены: {allergens.join(", ")}</p>
      )}
      {day.notes && <p className="mt-2 text-xs text-slate-400">{day.notes}</p>}
    </article>
  );
}

type PresetRowProps = {
  presets: PlannerPreset[];
  onApply: (preset: PlannerPreset) => void;
  disabled?: boolean;
};

function PresetRow({ presets, onApply, disabled }: PresetRowProps) {
  if (!presets.length) return null;

  return (
    <div className="rounded-3xl border border-slate-200/60 bg-white/80 p-5 shadow-sm">
      <h3 className="text-sm font-semibold text-slate-900">Быстрые пресеты</h3>
      <div className="mt-3 flex flex-wrap gap-3">
        {presets.map((preset) => (
          <button
            key={preset.id}
            type="button"
            disabled={disabled}
            onClick={() => onApply(preset)}
            className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 transition hover:border-sky-200 hover:text-sky-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {preset.title}
            {preset.description ? (
              <span className="ml-2 text-xs text-slate-400">{preset.description}</span>
            ) : null}
          </button>
        ))}
      </div>
    </div>
  );
}

type WeeksModalProps = {
  open: boolean;
  onClose: () => void;
  weeks: WeekPlan[];
  weeksCount: number;
  repeatWeeks: boolean;
  weekLabelMap: Map<string, string>;
  primaryMenu: MenuResponse | null;
  onUpdateWeek: (index: number, updater: (week: WeekPlan) => WeekPlan) => void;
};

function WeeksModal({ open, onClose, weeks, weeksCount, repeatWeeks, weekLabelMap, primaryMenu, onUpdateWeek }: WeeksModalProps) {
  const activeWeeks = useMemo(() => weeks.slice(0, weeksCount), [weeks, weeksCount]);
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (!open) {
      setActiveIndex(0);
    } else if (activeIndex >= activeWeeks.length) {
      setActiveIndex(0);
    }
  }, [open, activeIndex, activeWeeks.length]);

  const activeWeek = activeWeeks[activeIndex] ?? activeWeeks[0];
  const weekStart = activeWeek?.weekStart ?? null;

  const weekMenuQuery = useQuery({
    queryKey: ["planner", "modal-menu", weekStart ?? "none"],
    queryFn: async () => {
      if (!weekStart) {
        return null;
      }
      try {
        return await getCurrentMenu({ weekStart });
      } catch (error) {
        if (isAxiosError(error) && error.response?.status === 404) {
          return null;
        }
        throw error;
      }
    },
    enabled: open && activeIndex > 0 && Boolean(weekStart),
    retry: false,
  });

  const weekMenu = activeIndex === 0 ? primaryMenu : weekMenuQuery.data ?? null;
  const menuDays = useMemo(() => (weekMenu ? sortDays(weekMenu.items) : []), [weekMenu]);
  const isMenuLoading = activeIndex === 0 ? false : weekMenuQuery.isLoading;
  const isEditable = !repeatWeeks || activeIndex === 0;

  const handleToggleDay = useCallback(
    (day: MenuDay) => {
      if (!isEditable || !day.offerId || !activeWeek) return;
      onUpdateWeek(activeIndex, (week) => {
        const selections = { ...week.selections };
        if (selections[day.offerId!]) {
          delete selections[day.offerId!];
        } else {
          selections[day.offerId!] = { offerId: day.offerId!, day: day.day, portions: 1 };
        }
        return { ...week, selections };
      });
    },
    [activeIndex, activeWeek, isEditable, onUpdateWeek],
  );

  const handleChangePortions = useCallback(
    (offerId: string, portions: number) => {
      if (!isEditable || !activeWeek) return;
      onUpdateWeek(activeIndex, (week) => {
        const current = week.selections[offerId];
        if (!current) {
          return week;
        }
        const clamped = Math.min(Math.max(portions, 1), MAX_PORTIONS);
        return {
          ...week,
          selections: {
            ...week.selections,
            [offerId]: { ...current, portions: clamped },
          },
        };
      });
    },
    [activeIndex, activeWeek, isEditable, onUpdateWeek],
  );

  const handleToggleWeekEnabled = useCallback(
    (index: number, enabled: boolean) => {
      if (index === 0) return;
      onUpdateWeek(index, (week) => ({ ...week, enabled }));
    },
    [onUpdateWeek],
  );

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" aria-hidden onClick={onClose} />
      <div className="relative z-10 mx-auto flex h-full max-w-5xl flex-col gap-6 overflow-y-auto px-4 py-8">
        <div className="rounded-[2rem] bg-white p-6 shadow-2xl" role="dialog" aria-modal="true" aria-labelledby="weeks-modal-title">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 id="weeks-modal-title" className="text-xl font-semibold text-slate-900">Настройка недель</h2>
              <p className="mt-1 text-sm text-slate-500">
                Управляйте расписанием на несколько недель вперёд. Выберите неделю слева, чтобы изменить выбор блюд или отключить доставку.
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full bg-slate-100 px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-200"
            >
              Закрыть
            </button>
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-[260px,1fr]">
            <div className="space-y-2">
              {activeWeeks.map((week, index) => {
                const label = weekLabelMap.get(week.weekStart ?? "") ?? formatWeekTitle(week.weekStart ?? null, index);
                const isActive = index === activeIndex;
                return (
                  <button
                    key={`${week.weekStart ?? "null"}-${index}`}
                    type="button"
                    onClick={() => setActiveIndex(index)}
                    className={`w-full rounded-2xl border px-4 py-3 text-left text-sm transition ${
                      isActive ? "border-sky-300 bg-sky-50 text-sky-800" : "border-slate-200 bg-white text-slate-600 hover:border-sky-200"
                    }`}
                  >
                    <span className="block font-medium">{index + 1}-я неделя</span>
                    <span className="block text-xs text-slate-500">{label}</span>
                    {index !== 0 && (
                      <span className={`mt-1 inline-block rounded-full px-2 py-0.5 text-[11px] ${week.enabled ? "bg-emerald-100 text-emerald-700" : "bg-slate-200 text-slate-500"}`}>
                        {week.enabled ? "Включена" : "Выключена"}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>

            <div className="space-y-4">
              {repeatWeeks && activeIndex > 0 && (
                <div className="rounded-xl bg-slate-100 px-4 py-3 text-xs text-slate-600">
                  Вы включили повтор выбранных дней. Чтобы настроить эту неделю отдельно, отключите повтор в сводке.
                </div>
              )}

              {activeIndex !== 0 && (
                <div className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3">
                  <div>
                    <p className="text-sm font-medium text-slate-700">Неделя активна</p>
                    <p className="text-xs text-slate-500">Выключенная неделя не попадёт в заказ.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleToggleWeekEnabled(activeIndex, !activeWeek?.enabled)}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${activeWeek?.enabled ? "bg-sky-600" : "bg-slate-300"}`}
                  >
                    <span className={`inline-block h-5 w-5 rounded-full bg-white shadow transition ${activeWeek?.enabled ? "translate-x-5" : "translate-x-1"}`} />
                  </button>
                </div>
              )}

              {isMenuLoading ? (
                <div className="rounded-2xl border border-slate-200/60 bg-white/80 p-10 text-center text-sm text-slate-500">
                  Загружаем меню для выбранной недели…
                </div>
              ) : weekMenu ? (
                <PlannerGrid
                  menuDays={menuDays}
                  selections={activeWeek?.selections ?? {}}
                  isLoading={false}
                  onToggle={handleToggleDay}
                  onChangePortions={handleChangePortions}
                  disabled={!isEditable}
                />
              ) : (
                <div className="rounded-2xl border border-dashed border-slate-200 bg-white/80 p-8 text-center text-sm text-slate-500">
                  Меню для этой недели ещё не опубликовано. Мы сообщим, когда оно станет доступно.
                </div>
              )}

              {activeWeek && Object.keys(activeWeek.selections).length > 0 && (
                <div className="rounded-2xl border border-slate-200/60 bg-slate-50/70 p-4 text-sm text-slate-600">
                  <p className="font-medium text-slate-700">Выбрано блюд:</p>
                  <ul className="mt-2 space-y-1 text-xs text-slate-500">
                    {Object.values(activeWeek.selections).map((selection) => (
                      <li key={`${selection.offerId}-${selection.day}`}>{selection.day} · {selection.portions} порций</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

type WeekBreakdown = {
  index: number;
  weekStart: string | null;
  label: string;
  enabled: boolean;
  menuStatus: string;
  subtotal: number;
  currency: string;
};

type PlannerSummaryProps = {
  selections: SelectionEntry[];
  calcLines: OrderCalcItem[];
  subtotal: number;
  total: number;
  discount: number;
  currency: string;
  totalPortions: number;
  address: string;
  promoCode: string;
  onAddressChange: (value: string) => void;
  onPromoChange: (value: string) => void;
  onRemoveSelection: (offerId: string) => void;
  onClearAll: () => void;
  onCheckout: () => void;
  warnings: string[];
  promoError: string | null;
  isCalculating: boolean;
  disabled: boolean;
  weeksCount: number;
  repeatWeeks: boolean;
  onWeeksCountChange: (value: number) => void;
  onRepeatToggle: (value: boolean) => void;
  onOpenWeeksModal: () => void;
  weeksBreakdown: WeekBreakdown[];
};

function PlannerSummary({
  selections,
  calcLines,
  subtotal,
  total,
  discount,
  currency,
  totalPortions,
  address,
  promoCode,
  onAddressChange,
  onPromoChange,
  onRemoveSelection,
  onClearAll,
  onCheckout,
  warnings,
  promoError,
  isCalculating,
  disabled,
  weeksCount,
  repeatWeeks,
  onWeeksCountChange,
  onRepeatToggle,
  onOpenWeeksModal,
  weeksBreakdown,
}: PlannerSummaryProps) {
  const statusLabels: Record<string, { label: string; tone: string }> = {
    published: { label: "Меню готово", tone: "text-emerald-600" },
    pending: { label: "Меню уточняется", tone: "text-amber-600" },
    empty: { label: "Нет выбранных блюд", tone: "text-slate-500" },
    disabled: { label: "Неделя выключена", tone: "text-slate-400" },
  };

  return (
    <aside className="self-start rounded-3xl border border-slate-200/70 bg-white/90 p-6 shadow-lg shadow-[rgba(27,27,27,0.05)] lg:sticky lg:top-24">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Ваш заказ</h2>
        <button
          type="button"
          onClick={onClearAll}
          className="text-sm text-slate-500 transition hover:text-slate-700"
          disabled={selections.length === 0}
        >
          Очистить
        </button>
      </div>
      <p className="mt-1 text-xs text-slate-500">Сохраняем ваш выбор автоматически — можно вернуться позже.</p>

      <div className="mt-4 space-y-4">
        {selections.length === 0 && <p className="text-sm text-slate-500">Выберите хотя бы один день, чтобы оформить заказ.</p>}
        {selections.map(({ menuDay, selection }) => {
          const line = calcLines.find((item) => item.offerId === selection.offerId);
          const accepted = line ? line.acceptedPortions : selection.portions;
          const status = line ? line.status : "ok";
          return (
            <div key={selection.offerId} className="rounded-2xl border border-slate-200/60 bg-slate-50/70 p-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-slate-900">{menuDay.day}</p>
                  <p className="text-xs text-slate-500">
                    {accepted} × {formatCurrency(menuDay.price.amount, menuDay.price.currency)}
                  </p>
                  {status !== "ok" && line?.message && (
                    <p className="mt-1 text-xs text-amber-600">{line.message}</p>
                  )}
                </div>
                <button
                  type="button"
                  onClick={() => onRemoveSelection(selection.offerId)}
                  className="text-xs text-slate-400 transition hover:text-slate-600"
                >
                  Удалить
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-6 space-y-3">
        <label className="block text-xs font-medium text-slate-600" htmlFor="planner-address">
          Адрес доставки
        </label>
        <textarea
          id="planner-address"
          className="w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm text-slate-700 shadow-inner focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-100"
          placeholder="Например: Батуми, ул. Гогуадзе 12, подъезд 2"
          value={address}
          onChange={(event) => onAddressChange(event.target.value)}
        />
      </div>

      <div className="mt-4 space-y-2">
        <label className="block text-xs font-medium text-slate-600" htmlFor="planner-promo">
          Промокод (если есть)
        </label>
        <input
          id="planner-promo"
          className="w-full rounded-2xl border border-slate-200 px-3 py-2 text-sm text-slate-700 shadow-inner focus:border-sky-400 focus:outline-none focus:ring-2 focus:ring-sky-100"
          placeholder="Например: WELCOME10"
          value={promoCode}
          onChange={(event) => onPromoChange(event.target.value)}
        />
        {promoError && <p className="text-xs text-amber-600">{promoError}</p>}
      </div>

      <div className="mt-6 space-y-4 rounded-2xl bg-slate-50/70 p-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-slate-800">Количество недель вперёд</span>
          <span className="text-sm font-semibold text-slate-900">{weeksCount}</span>
        </div>
        <input
          type="range"
          min={1}
          max={MAX_WEEKS}
          value={weeksCount}
          onChange={(event) => onWeeksCountChange(Number(event.target.value))}
          className="w-full accent-sky-500"
          aria-label="Количество недель вперёд"
        />
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-700">Повторять выбранные дни</span>
          <button
            type="button"
            role="switch"
            aria-checked={repeatWeeks}
            onClick={() => onRepeatToggle(!repeatWeeks)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${repeatWeeks ? "bg-sky-600" : "bg-slate-300"}`}
          >
            <span
              className={`inline-block h-5 w-5 rounded-full bg-white shadow transition ${repeatWeeks ? "translate-x-5" : "translate-x-1"}`}
            />
          </button>
        </div>
        <button
          type="button"
          onClick={onOpenWeeksModal}
          className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-600 transition hover:border-sky-200 hover:text-sky-600"
        >
          Просмотреть недели
        </button>
        <div className="space-y-2">
          {weeksBreakdown.map((week) => {
            const status = statusLabels[week.menuStatus] ?? statusLabels.pending;
            return (
              <div
                key={week.index}
                className="rounded-xl border border-slate-200/70 bg-white px-3 py-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-800">
                    {week.index + 1}-я неделя · {week.label}
                  </span>
                  <span className="text-sm font-semibold text-slate-900">
                    {formatCurrency(week.subtotal, week.currency || currency)}
                  </span>
                </div>
                <p className={`text-xs ${status.tone}`}>
                  {status.label}
                  {!week.enabled ? " · выключена" : ""}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      <div className="mt-6 space-y-2 text-sm text-slate-700">
        <div className="flex items-center justify-between">
          <span>Базовая стоимость</span>
          <span>{formatCurrency(subtotal, currency)}</span>
        </div>
        <div className="flex items-center justify-between">
          <span>Скидка</span>
          <span className="text-emerald-600">−{formatCurrency(discount, currency)}</span>
        </div>
        <div className="flex items-center justify-between text-base font-semibold text-slate-900">
          <span>Итого</span>
          <span>{formatCurrency(total, currency)}</span>
        </div>
        <p className="text-xs text-slate-500">Доставка уже включена в стоимость.</p>
      </div>

      {warnings.length > 0 && (
        <div className="mt-4 space-y-2 rounded-2xl bg-amber-50 px-4 py-3 text-xs text-amber-700">
          {warnings.map((warning, index) => (
            <p key={`${warning}-${index}`}>{warning}</p>
          ))}
        </div>
      )}

      <button
        type="button"
        onClick={onCheckout}
        disabled={disabled || isCalculating}
        className="mt-6 w-full rounded-full bg-slate-900 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-slate-900/20 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isCalculating ? "Пересчитываем…" : `Оформить ${totalPortions} порций за ${formatCurrency(total, currency)}`}
      </button>
    </aside>
  );
}

function FAQBlock() {
  const faqs = [
    {
      question: "Можно ли менять блюда?",
      answer: "Мы готовим фиксированное меню на неделю, поэтому замен пока нет. Но присылайте пожелания — мы учитываем их при обновлении меню.",
    },
    {
      question: "Когда привозите обеды?",
      answer: "Доставка по будням с 12:30 до 15:30. Мы заранее напишем, когда курьер будет у вас. Доставка входит в стоимость обеда.",
    },
    {
      question: "Как оплатить?",
      answer: "Сейчас оплата проходит по счёту или переводом. Онлайн-оплата появится в следующей итерации — мы сообщим дополнительно.",
    },
  ];

  return (
    <section className="rounded-3xl border border-slate-200/60 bg-white/80 p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-900">Частые вопросы</h2>
      <div className="mt-4 space-y-4 text-sm text-slate-600">
        {faqs.map((faq) => (
          <div key={faq.question}>
            <p className="font-medium text-slate-800">{faq.question}</p>
            <p className="mt-1 text-slate-600">{faq.answer}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
