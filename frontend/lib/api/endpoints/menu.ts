import { apiClient } from "@/lib/api/client";

export type DayOfferStatus = "available" | "sold_out" | "closed";

export type MenuDayPrice = {
  amount: number;
  currency: string;
};

export type MenuDay = {
  day: string;
  offerId: string | null;
  status: DayOfferStatus;
  dishes: string[];
  photoUrl?: string | null;
  price: MenuDayPrice;
  calories?: number | null;
  allergens: string[];
  portionLimit?: number | null;
  portionsReserved: number;
  portionsAvailable?: number | null;
  badge?: string | null;
  orderDeadline?: string | null;
  notes?: string | null;
};

export type MenuResponse = {
  week: string;
  weekStart: string | null;
  items: MenuDay[];
};

export type MenuUpdateRequest = {
  items: string[];
};

export type MenuWeekRequest = {
  title: string;
};

export type MenuWeekSummary = {
  label: string;
  weekStart: string | null;
  isCurrent: boolean;
};

type MenuQueryInput = string | { date?: string | null; weekStart?: string | null } | undefined;

export async function getCurrentMenu(input?: MenuQueryInput): Promise<MenuResponse> {
  const client = apiClient();
  const params: Record<string, string> = {};
  if (typeof input === "string") {
    params.date = input;
  } else if (input && typeof input === "object") {
    if (input.weekStart) {
      params.weekStart = input.weekStart;
    } else if (input.date) {
      params.date = input.date;
    }
  }
  const { data } = await client.get<MenuResponse>("/menu/week", { params });
  return data;
}

export async function getMenuWeeks(): Promise<MenuWeekSummary[]> {
  const client = apiClient();
  const { data } = await client.get<MenuWeekSummary[]>("/menu/weeks");
  return data;
}

export type PlannerPreset = {
  id: string;
  slug: string;
  title: string;
  description?: string | null;
  days: string[];
  portions: number;
};

export async function getPlannerPresets(): Promise<PlannerPreset[]> {
  const client = apiClient();
  const { data } = await client.get<PlannerPreset[]>("/menu/presets");
  return data;
}

export type OrderWindowRequest = {
  enabled: boolean;
  weekStart?: string | null;
};

export type OrderWindowState = {
  enabled: boolean;
  weekStart: string | null;
};

export async function getOrderWindow(): Promise<OrderWindowState> {
  const client = apiClient();
  const { data } = await client.get<OrderWindowState>("/menu/order-window");
  return data;
}
