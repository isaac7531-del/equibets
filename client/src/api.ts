const BASE = "/api";

export interface Event {
  id: number;
  name: string;
  date: string;
  status: string;
  created_at: string;
}

export interface Bet {
  id: number;
  event_id: number;
  description: string;
  odds: number;
  stake: number;
  result: string;
  payout: number | null;
  created_at: string;
}

async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as { error?: string }).error ?? res.statusText);
  }
  if (res.status === 204) return undefined as unknown as T;
  return res.json() as Promise<T>;
}

export const api = {
  getEvents: () => request<Event[]>("/events"),
  createEvent: (data: { name: string; date: string }) =>
    request<Event>("/events", { method: "POST", body: JSON.stringify(data) }),
  deleteEvent: (id: number) =>
    request<void>(`/events/${id}`, { method: "DELETE" }),

  getBets: (eventId?: number) =>
    request<Bet[]>(eventId ? `/bets?event_id=${eventId}` : "/bets"),
  createBet: (data: { event_id: number; description: string; odds: number; stake: number }) =>
    request<Bet>("/bets", { method: "POST", body: JSON.stringify(data) }),
  settleBet: (id: number, result: "won" | "lost") =>
    request<Bet>(`/bets/${id}/settle`, { method: "PATCH", body: JSON.stringify({ result }) }),
  deleteBet: (id: number) =>
    request<void>(`/bets/${id}`, { method: "DELETE" }),
};
