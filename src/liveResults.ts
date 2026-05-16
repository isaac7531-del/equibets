import { calculatePenaltyScore, type EventingScore } from './scoring';

const DEFAULT_LIVE_RESULTS_ENDPOINT = '/live-results.json';

type JsonObject = Record<string, unknown>;

export type LiveResultStatus = 'final' | 'in_progress' | 'provisional' | 'unknown';

export type LiveEventResult = {
  id: string;
  sourceId: string;
  sourceName: string;
  rider: string;
  horse: string;
  eventName: string;
  eventDate: string;
  level: string;
  country: string;
  status: LiveResultStatus;
  collectedAt: string | null;
  score: EventingScore;
};

export type LiveEventResultsSnapshot = {
  endpoint: string;
  collectedAt: string | null;
  sourceId: string;
  sourceName: string;
  results: LiveEventResult[];
};

type LiveResultsFetcher = (
  input: string,
  init?: RequestInit,
) => Promise<Pick<Response, 'json' | 'ok' | 'status' | 'statusText'>>;

export const getLiveResultsEndpoint = () => {
  const configuredEndpoint = import.meta.env.VITE_LIVE_RESULTS_URL;
  return configuredEndpoint?.trim() || DEFAULT_LIVE_RESULTS_ENDPOINT;
};

export const fetchLiveEventResults = async (
  endpoint = getLiveResultsEndpoint(),
  fetcher: LiveResultsFetcher = fetch,
): Promise<LiveEventResultsSnapshot> => {
  const response = await fetcher(endpoint, {
    cache: 'no-store',
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Live results request failed with ${response.status} ${response.statusText}`.trim());
  }

  return parseLiveResultsFeed(await response.json(), endpoint);
};

export const parseLiveResultsFeed = (payload: unknown, endpoint = getLiveResultsEndpoint()): LiveEventResultsSnapshot => {
  const feed = objectValue(payload, 'live results feed');
  const source = optionalObject(feed.source);
  const sourceId = optionalString(source, ['id']) ?? optionalString(feed, ['sourceId', 'source_id']) ?? 'live_feed';
  const sourceName = optionalString(source, ['name']) ?? optionalString(feed, ['sourceName', 'source_name']) ?? sourceId;
  const collectedAt = optionalString(feed, ['collectedAt', 'collected_at']);
  const rawResults = arrayValue(feed.results, 'results');

  return {
    endpoint,
    collectedAt,
    sourceId,
    sourceName,
    results: sortLiveEventResults(
      rawResults.map((rawResult, index) =>
        normalizeLiveEventResult(objectValue(rawResult, `results[${index}]`), {
          collectedAt,
          sourceId,
          sourceName,
        }),
      ),
    ),
  };
};

export const filterLiveResults = (results: LiveEventResult[], query: string) => {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) {
    return results;
  }

  return results.filter((result) =>
    [result.rider, result.horse, result.eventName, result.level, result.country]
      .join(' ')
      .toLowerCase()
      .includes(normalizedQuery),
  );
};

export const sortLiveEventResults = (results: LiveEventResult[]) =>
  [...results].sort((a, b) => {
    if (a.score.totalPenalties !== b.score.totalPenalties) {
      return a.score.totalPenalties - b.score.totalPenalties;
    }

    if (a.eventDate !== b.eventDate) {
      return b.eventDate.localeCompare(a.eventDate);
    }

    return `${a.horse}${a.rider}`.localeCompare(`${b.horse}${b.rider}`);
  });

const normalizeLiveEventResult = (
  result: JsonObject,
  defaults: Pick<LiveEventResult, 'collectedAt' | 'sourceId' | 'sourceName'>,
): LiveEventResult => {
  const sourceId = optionalString(result, ['sourceId', 'source_id']) ?? defaults.sourceId;
  const sourceName = optionalString(result, ['sourceName', 'source_name']) ?? defaults.sourceName;
  const rider = requiredString(result, ['rider', 'riderName', 'rider_name']);
  const horse = requiredString(result, ['horse', 'horseName', 'horse_name']);
  const eventName = requiredString(result, ['eventName', 'event_name']);
  const eventDate = requiredString(result, ['eventDate', 'event_date', 'date']);
  const level = optionalString(result, ['level']) ?? 'Unspecified';
  const country = optionalString(result, ['country']) ?? 'Unknown';
  const collectedAt = optionalString(result, ['collectedAt', 'collected_at']) ?? defaults.collectedAt;
  const status = normalizeStatus(optionalString(result, ['status']));

  return {
    id:
      optionalString(result, ['id', 'sourceRecordId', 'source_record_id']) ??
      `${sourceId}:${eventDate}:${eventName}:${rider}:${horse}`,
    sourceId,
    sourceName,
    rider,
    horse,
    eventName,
    eventDate,
    level,
    country,
    status,
    collectedAt,
    score: calculatePenaltyScore({
      dressagePenalties: requiredNumber(result, ['dressagePenalties', 'dressageScore', 'dressage_score']),
      showJumpingPenalties: optionalNumber(result, ['showJumpingPenalties', 'show_jumping_penalties']) ?? 0,
      crossCountryJumpPenalties:
        optionalNumber(result, ['crossCountryJumpPenalties', 'cross_country_jump_penalties']) ?? 0,
      crossCountryTimePenalties:
        optionalNumber(result, ['crossCountryTimePenalties', 'cross_country_time_penalties']) ?? 0,
    }),
  };
};

const normalizeStatus = (status: string | null): LiveResultStatus => {
  const normalizedStatus = status?.toLowerCase().replace(/[\s-]+/g, '_');

  if (normalizedStatus === 'final' || normalizedStatus === 'in_progress' || normalizedStatus === 'provisional') {
    return normalizedStatus;
  }

  return 'unknown';
};

const objectValue = (value: unknown, label: string): JsonObject => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`${label} must be an object`);
  }

  return value as JsonObject;
};

const optionalObject = (value: unknown): JsonObject => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return {};
  }

  return value as JsonObject;
};

const arrayValue = (value: unknown, label: string): unknown[] => {
  if (!Array.isArray(value)) {
    throw new Error(`${label} must be an array`);
  }

  return value;
};

const requiredString = (values: JsonObject, keys: string[]) => {
  const value = optionalString(values, keys);
  if (!value) {
    throw new Error(`${keys[0]} must be a non-empty string`);
  }

  return value;
};

const optionalString = (values: JsonObject, keys: string[]) => {
  for (const key of keys) {
    const value = values[key];
    if (typeof value === 'string' && value.trim()) {
      return value.trim();
    }
  }

  return null;
};

const requiredNumber = (values: JsonObject, keys: string[]) => {
  const value = optionalNumber(values, keys);
  if (value === null) {
    throw new Error(`${keys[0]} must be a number`);
  }

  return value;
};

const optionalNumber = (values: JsonObject, keys: string[]) => {
  for (const key of keys) {
    const value = values[key];
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }
  }

  return null;
};
