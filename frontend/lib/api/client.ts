import axios from "axios";

const baseURL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function apiClient(token?: string) {
  return axios.create({
    baseURL: `${baseURL}/api/v1`,
    headers: token
      ? {
          Authorization: `Bearer ${token}`,
        }
      : undefined,
  });
}
