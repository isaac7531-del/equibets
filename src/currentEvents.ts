export type PublicCurrentEvent = {
  sourceEventId: string;
  name: string;
  url: string;
  startDate: string | null;
  endDate: string | null;
  country: string;
  discipline: string;
  level: string;
};

export type CurrentEventFeed = {
  updatedAt: string | null;
  windowStart: string | null;
  windowEnd: string | null;
  events: PublicCurrentEvent[];
};

type RawCurrentEventsPayload = {
  updated_at?: unknown;
  window_start?: unknown;
  window_end?: unknown;
  events?: unknown;
};

type RawCurrentEvent = {
  source_event_id?: unknown;
  name?: unknown;
  url?: unknown;
  start_date?: unknown;
  end_date?: unknown;
  country?: unknown;
  discipline?: unknown;
  level?: unknown;
};

export class CurrentEventsUnavailableError extends Error {
  constructor(message = 'Current event feed is not available') {
    super(message);
    this.name = 'CurrentEventsUnavailableError';
  }
}

export const loadCurrentEvents = async (
  fetchEvents: typeof fetch = fetch,
): Promise<CurrentEventFeed> => {
  const response = await fetchEvents('/current_events.json', {
    cache: 'no-store',
  });

  if (!response.ok) {
    throw new CurrentEventsUnavailableError();
  }

  return normalizeCurrentEventsPayload(await response.json());
};

export const normalizeCurrentEventsPayload = (payload: unknown): CurrentEventFeed => {
  if (!isObject(payload)) {
    throw new CurrentEventsUnavailableError('Current event feed is malformed');
  }

  const rawPayload = payload as RawCurrentEventsPayload;
  const rawEvents = Array.isArray(rawPayload.events) ? rawPayload.events : [];

  return {
    updatedAt: optionalString(rawPayload.updated_at),
    windowStart: optionalString(rawPayload.window_start),
    windowEnd: optionalString(rawPayload.window_end),
    events: rawEvents.map(normalizeCurrentEvent).filter((event): event is PublicCurrentEvent => event !== null),
  };
};

export const currentEventStatus = (
  event: Pick<PublicCurrentEvent, 'startDate' | 'endDate'>,
  today = new Date(),
) => {
  const todayKey = dateKey(today);
  const startKey = event.startDate;
  const endKey = event.endDate ?? event.startDate;

  if (!startKey) {
    return 'Date pending';
  }
  if (startKey <= todayKey && (!endKey || todayKey <= endKey)) {
    return 'Live now';
  }
  if (startKey > todayKey) {
    return 'Upcoming';
  }
  return 'Recently finished';
};

const normalizeCurrentEvent = (value: unknown): PublicCurrentEvent | null => {
  if (!isObject(value)) {
    return null;
  }

  const rawEvent = value as RawCurrentEvent;
  const name = optionalString(rawEvent.name);
  const url = optionalString(rawEvent.url);

  if (!name || !url) {
    return null;
  }

  return {
    sourceEventId: optionalString(rawEvent.source_event_id) || url,
    name,
    url,
    startDate: optionalDate(rawEvent.start_date),
    endDate: optionalDate(rawEvent.end_date),
    country: optionalString(rawEvent.country) || 'Unknown',
    discipline: optionalString(rawEvent.discipline) || 'Eventing',
    level: optionalString(rawEvent.level) || 'Unknown',
  };
};

const optionalString = (value: unknown) => (typeof value === 'string' && value ? value : null);

const optionalDate = (value: unknown) => {
  const text = optionalString(value);
  if (!text) {
    return null;
  }

  return /^\d{4}-\d{2}-\d{2}$/.test(text) ? text : null;
};

const dateKey = (date: Date) => date.toISOString().slice(0, 10);

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);
