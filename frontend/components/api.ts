export const apiBase = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000/api/v1";

export async function apiGet(path: string) {
  const token = localStorage.getItem("token");
  const res = await fetch(`${apiBase}${path}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function apiRequest(path: string, method: string, body?: unknown) {
  const token = localStorage.getItem("token");
  const res = await fetch(`${apiBase}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
