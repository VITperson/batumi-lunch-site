import { apiClient } from "@/lib/api/client";

export type OrderPayload = {
  id: string;
  day: string;
  count: number;
  menu: string[];
  status: string;
  address: string | null;
  phone: string | null;
  deliveryWeekStart: string;
  deliveryDate: string;
  nextWeek: boolean;
  createdAt: string;
  updatedAt: string;
};

export type OrderListResponse = {
  orders: OrderPayload[];
};

export type CreateOrderBody = {
  day: string;
  count: number;
  address: string;
  phone?: string | null;
  weekStart?: string | null;
};

export type PlannerSelectionRequest = {
  offerId: string;
  portions: number;
};

export type PlannerWeekSelectionRequest = {
  weekStart?: string | null;
  enabled: boolean;
  selections: PlannerSelectionRequest[];
};

export type OrderCalcRequest = {
  selections: PlannerSelectionRequest[];
  promoCode?: string | null;
  address?: string | null;
  weeks?: PlannerWeekSelectionRequest[];
};

export type OrderCalcItem = {
  offerId: string;
  day: string;
  status: string;
  requestedPortions: number;
  acceptedPortions: number;
  unitPrice: number;
  currency: string;
  subtotal: number;
  message?: string | null;
};

export type OrderCalcResponse = {
  items: OrderCalcItem[];
  subtotal: number;
  discount: number;
  total: number;
  currency: string;
  warnings: string[];
  promoCode?: string | null;
  promoCodeError?: string | null;
  deliveryZone?: string | null;
  deliveryAvailable: boolean;
  weeks: PlannerWeekQuote[];
};

export type PlannerWeekQuote = {
  weekStart: string | null;
  label: string | null;
  enabled: boolean;
  menuStatus: string;
  items: OrderCalcItem[];
  subtotal: number;
  currency: string | null;
  warnings: string[];
};

export type PlannerCheckoutRequest = {
  address: string;
  promoCode?: string | null;
  repeatWeeks: boolean;
  weeksCount: number;
  selections: PlannerSelectionRequest[];
  weeks?: PlannerWeekSelectionRequest[];
};

export type PlannerCheckoutWeek = {
  index: number;
  weekStart: string | null;
  label: string | null;
  enabled: boolean;
  menuStatus: string;
  subtotal: number;
  currency: string | null;
  warnings: string[];
};

export type PlannerCheckoutResponse = {
  templateId: string;
  subtotal: number;
  discount: number;
  total: number;
  currency: string;
  promoCode?: string | null;
  deliveryZone?: string | null;
  deliveryAvailable: boolean;
  weeks: PlannerCheckoutWeek[];
};

export async function createOrder(token: string, body: CreateOrderBody): Promise<OrderPayload> {
  const client = apiClient(token);
  const { data } = await client.post<OrderPayload>("/orders", body);
  return data;
}

export async function calculatePlannerOrder(body: OrderCalcRequest): Promise<OrderCalcResponse> {
  const client = apiClient();
  const { data } = await client.post<OrderCalcResponse>("/orders/calc", body);
  return data;
}

export async function checkoutPlannerOrder(
  token: string,
  body: PlannerCheckoutRequest,
): Promise<PlannerCheckoutResponse> {
  const client = apiClient(token);
  const { data } = await client.post<PlannerCheckoutResponse>("/orders/checkout", body);
  return data;
}

export async function fetchMyOrders(token: string): Promise<OrderPayload[]> {
  const client = apiClient(token);
  const { data } = await client.get<OrderListResponse>("/orders", { params: { mine: 1 } });
  return data.orders;
}

export async function fetchOrdersForWeek(token: string, weekStart: string): Promise<OrderPayload[]> {
  const client = apiClient(token);
  const { data } = await client.get<OrderListResponse>("/orders", { params: { week: weekStart } });
  return data.orders;
}

export async function fetchOrder(token: string, id: string): Promise<OrderPayload> {
  const client = apiClient(token);
  const { data } = await client.get<OrderPayload>(`/orders/${id}`);
  return data;
}

export async function updateOrder(token: string, id: string, body: { count?: number; address?: string }): Promise<OrderPayload> {
  const client = apiClient(token);
  const { data } = await client.patch<OrderPayload>(`/orders/${id}`, body);
  return data;
}

export async function cancelOrder(token: string, id: string, reason?: string): Promise<OrderPayload> {
  const client = apiClient(token);
  const { data } = await client.post<OrderPayload>(`/orders/${id}/cancel`, { reason });
  return data;
}
