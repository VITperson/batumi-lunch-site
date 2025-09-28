import { apiClient } from "@/lib/api/client";

export type TokenResponse = {
  accessToken: string;
  refreshToken: string;
};

export type RegisterPayload = {
  email: string;
  password: string;
  fullName?: string;
  phone?: string;
  address?: string;
};

export type ProfileResponse = {
  id: string;
  email: string | null;
  fullName: string | null;
  phone: string | null;
  address: string | null;
  role: "customer" | "admin";
};

export type ProfileUpdatePayload = {
  fullName?: string | null;
  phone?: string | null;
  address?: string | null;
  currentPassword?: string;
  newPassword?: string;
};

export async function loginRequest(email: string, password: string): Promise<TokenResponse> {
  const client = apiClient();
  const { data } = await client.post<TokenResponse>("/auth/login", { email, password });
  return data;
}

export async function refreshRequest(refreshToken: string): Promise<TokenResponse> {
  const client = apiClient();
  const { data } = await client.post<TokenResponse>("/auth/refresh", { refreshToken });
  return data;
}

export async function registerRequest(payload: RegisterPayload): Promise<TokenResponse> {
  const client = apiClient();
  const { data } = await client.post<TokenResponse>("/auth/register", payload);
  return data;
}

export async function getProfile(accessToken: string): Promise<ProfileResponse> {
  const client = apiClient(accessToken);
  const { data } = await client.get<ProfileResponse>("/auth/me");
  return data;
}

export async function updateProfileRequest(accessToken: string, payload: ProfileUpdatePayload): Promise<ProfileResponse> {
  const client = apiClient(accessToken);
  const { data } = await client.patch<ProfileResponse>("/auth/me", payload);
  return data;
}
