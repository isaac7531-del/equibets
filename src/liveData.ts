import type { EventingResultRecord } from './results';
import type { UpcomingEventRecord } from './upcomingEvents';

export const LIVE_RESULTS_URL = '/data/fei_results.json';
export const LIVE_UPCOMING_EVENTS_URL = '/data/upcoming_events.json';

type Fetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

type LoadedResultFeed = {
  records: EventingResultRecord[];
  updatedAt: string | null;
};

type LoadedUpcomingEventFeed = {
  events: UpcomingEventRecord[];
  updatedAt: string | null;
};

export const loadLiveResults = async (
  fetcher: Fetcher = fetch,
  url = LIVE_RESULTS_URL,
): Promise<LoadedResultFeed> => {
  const payload = await fetchJson(fetcher, url);
  const results = Array.isArray(payload.results) ? payload.results : [];
  return {
    records: results.map(resultFromPayload).filter((result): result is EventingResultRecord => result !== null),
    updatedAt: stringValue(payload.updated_at),
  };
};

export const loadLiveUpcomingEvents = async (
  fetcher: Fetcher = fetch,
  url = LIVE_UPCOMING_EVENTS_URL,
): Promise<LoadedUpcomingEventFeed> => {
  const payload = await fetchJson(fetcher, url);
  const events = Array.isArray(payload.events) ? payload.events : [];
  return {
    events: events.map(upcomingEventFromPayload).filter((event): event is UpcomingEventRecord => event !== null),
    updatedAt: stringValue(payload.updated_at),
  };
};

const fetchJson = async (fetcher: Fetcher, url: string): Promise<Record<string, unknown>> => {
  const response = await fetcher(url, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Live data request failed: ${response.status}`);
  }
  const payload: unknown = await response.json();
  if (!isObject(payload)) {
    throw new Error('Live data response must be a JSON object');
  }
  return payload;
};

const resultFromPayload = (payload: unknown): EventingResultRecord | null => {
  if (!isObject(payload)) {
    return null;
  }
  const record = {
    sourceId: stringValue(payload.source_id),
    sourceRecordId: stringValue(payload.source_record_id),
    sourcePriority: numberValue(payload.source_priority),
    riderName: stringValue(payload.rider_name),
    horseName: stringValue(payload.horse_name),
    eventName: stringValue(payload.event_name),
    eventDate: stringValue(payload.event_date),
    level: stringValue(payload.level),
    country: stringValue(payload.country),
    dressageScore: numberValue(payload.dressage_score),
    showJumpingPenalties: numberValue(payload.show_jumping_penalties),
    crossCountryJumpPenalties: numberValue(payload.cross_country_jump_penalties),
    crossCountryTimePenalties: numberValue(payload.cross_country_time_penalties),
    collectedAt: stringValue(payload.collected_at),
    isUserEntered: booleanValue(payload.is_user_entered),
  };

  return Object.values(record).some((value) => value === null) ? null : (record as EventingResultRecord);
};

const upcomingEventFromPayload = (payload: unknown): UpcomingEventRecord | null => {
  if (!isObject(payload)) {
    return null;
  }
  const event = {
    sourceId: stringValue(payload.source_id),
    sourceEventId: stringValue(payload.source_event_id),
    sourcePriority: numberValue(payload.source_priority),
    name: stringValue(payload.name),
    startDate: stringValue(payload.start_date),
    endDate: nullableStringValue(payload.end_date),
    country: stringValue(payload.country),
    discipline: stringValue(payload.discipline),
    level: stringValue(payload.level),
    sourceUrl: stringValue(payload.source_url),
    collectedAt: stringValue(payload.collected_at),
  };

  const requiredValues = [
    event.sourceId,
    event.sourceEventId,
    event.sourcePriority,
    event.name,
    event.startDate,
    event.country,
    event.discipline,
    event.level,
    event.sourceUrl,
    event.collectedAt,
  ];

  return requiredValues.some((value) => value === null) ? null : (event as UpcomingEventRecord);
};

const isObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const stringValue = (value: unknown) => (typeof value === 'string' && value ? value : null);
const nullableStringValue = (value: unknown) => (value === null ? null : stringValue(value));
const numberValue = (value: unknown) => (typeof value === 'number' && Number.isFinite(value) ? value : null);
const booleanValue = (value: unknown) => (typeof value === 'boolean' ? value : null);
