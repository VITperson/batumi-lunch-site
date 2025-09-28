import { apiClient } from "@/lib/api/client";
import { MenuResponse, MenuUpdateRequest, MenuWeekRequest } from "@/lib/api/endpoints/menu";
import { BroadcastRequest, BroadcastResponse } from "@/lib/api/endpoints/types";
import { OrderWindowRequest, OrderWindowState } from "@/lib/api/endpoints/menu";

export async function updateWeekTitle(token: string, body: MenuWeekRequest): Promise<MenuResponse> {
  const client = apiClient(token);
  const { data } = await client.put<MenuResponse>("/admin/menu/week", body);
  return data;
}

export async function updateMenuDay(token: string, day: string, body: MenuUpdateRequest): Promise<MenuResponse> {
  const client = apiClient(token);
  const { data } = await client.put<MenuResponse>(`/admin/menu/${day}`, body);
  return data;
}

export async function uploadMenuPhoto(token: string, day: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("day", day);
  const client = apiClient(token);
  const { data } = await client.post(`/admin/menu/photo`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function setOrderWindow(token: string, body: OrderWindowRequest): Promise<OrderWindowState> {
  const client = apiClient(token);
  const { data } = await client.post<OrderWindowState>("/admin/order-window", body);
  return data;
}

export async function createBroadcastRequest(token: string, body: BroadcastRequest): Promise<BroadcastResponse> {
  const client = apiClient(token);
  const { data } = await client.post<BroadcastResponse>("/admin/broadcasts", body);
  return data;
}
