import { calculateScore, type EventingScore, type EventingScoreInput, type StoredResult } from './scoring';

export const CURRENT_EVENTS_FEED_URL = '/current-events.json';

export type LiveResultStatus = 'official' | 'provisional' | 'in_progress';

export type LiveEventResult = EventingScoreInput & {
  id: string;
  rider: string;
  horse: string;
  eventName: string;
  date: string;
  level: string;
  country: string;
  sourceId: string;
  sourceName: string;
  sourceUrl?: string;
  status: LiveResultStatus;
  phase: string;
  collectedAt: string;
};

export type LiveScoredResult = LiveEventResult & {
  score: EventingScore;
};

export type CurrentEventsPayload = {
  version: number;
  generatedAt: string;
  results: LiveEventResult[];
};

type CurrentEventsResponse = Pick<Response, 'ok' | 'status' | 'json'>;
type CurrentEventsFetcher = (input: RequestInfo | URL, init?: RequestInit) => Promise<CurrentEventsResponse>;

const liveStatuses = new Set<LiveResultStatus>(['official', 'provisional', 'in_progress']);

export const parseCurrentEventPayload = (payload: unknown): LiveScoredResult[] => {
  if (!isCurrentEventsPayload(payload)) {
    throw new Error('Current-events feed is missing a results array.');
  }

  return sortLiveScoreboard(payload.results.map(toLiveScoredResult));
};

export const loadCurrentEventResults = async (
  fetcher: CurrentEventsFetcher = fetch,
  feedUrl = CURRENT_EVENTS_FEED_URL,
): Promise<LiveScoredResult[]> => {
  const response = await fetcher(feedUrl, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Current-events feed returned ${response.status}.`);
  }

  return parseCurrentEventPayload(await response.json());
};

export const searchLiveResults = (results: LiveScoredResult[], query: string): LiveScoredResult[] => {
  const terms = query
    .trim()
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean);

  if (terms.length === 0) {
    return results;
  }

  return results.filter((result) => {
    const haystack = [
      result.rider,
      result.horse,
      result.eventName,
      result.level,
      result.country,
      result.sourceName,
      result.status,
    ]
      .join(' ')
      .toLowerCase();

    return terms.every((term) => haystack.includes(term));
  });
};

export const sortLiveScoreboard = (results: LiveScoredResult[]): LiveScoredResult[] =>
  [...results].sort((a, b) => {
    if (a.score.totalPenalties !== b.score.totalPenalties) {
      return a.score.totalPenalties - b.score.totalPenalties;
    }

    return Date.parse(b.collectedAt) - Date.parse(a.collectedAt);
  });

export const toStoredResult = (
  result: LiveScoredResult,
  options: { id?: string; createdAt?: string } = {},
): StoredResult => {
  const createdAt = options.createdAt ?? new Date().toISOString();

  return {
    id: options.id ?? `live-${result.sourceId}-${result.id}-${createdAt}`,
    rider: result.rider,
    horse: result.horse,
    eventName: result.eventName,
    date: result.date,
    level: result.level,
    country: result.country,
    dressagePercentage: result.dressagePercentage,
    showJumpingPenalties: result.showJumpingPenalties,
    crossCountryJumpPenalties: result.crossCountryJumpPenalties,
    optimumTimeSeconds: result.optimumTimeSeconds,
    actualTimeSeconds: result.actualTimeSeconds,
    sourceId: result.sourceId,
    sourceRecordId: result.id,
    sourceName: result.sourceName,
    sourceUrl: result.sourceUrl,
    status: result.status,
    collectedAt: result.collectedAt,
    notes: `Pulled from ${result.sourceName} (${formatLiveStatus(result.status)})`,
    createdAt,
    score: result.score,
  };
};

export const formatLiveStatus = (status: LiveResultStatus) =>
  status
    .split('_')
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(' ');

const toLiveScoredResult = (result: LiveEventResult): LiveScoredResult => ({
  ...result,
  score: calculateScore(result),
});

const isCurrentEventsPayload = (payload: unknown): payload is CurrentEventsPayload => {
  if (!payload || typeof payload !== 'object' || !Array.isArray((payload as CurrentEventsPayload).results)) {
    return false;
  }

  return (payload as CurrentEventsPayload).results.every(isLiveEventResult);
};

const isLiveEventResult = (value: unknown): value is LiveEventResult => {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const result = value as LiveEventResult;
  return (
    hasText(result.id) &&
    hasText(result.rider) &&
    hasText(result.horse) &&
    hasText(result.eventName) &&
    hasText(result.date) &&
    hasText(result.level) &&
    hasText(result.country) &&
    hasText(result.sourceId) &&
    hasText(result.sourceName) &&
    hasText(result.phase) &&
    hasText(result.collectedAt) &&
    liveStatuses.has(result.status) &&
    hasNumber(result.dressagePercentage) &&
    hasNumber(result.showJumpingPenalties) &&
    hasNumber(result.crossCountryJumpPenalties) &&
    hasNumber(result.optimumTimeSeconds) &&
    hasNumber(result.actualTimeSeconds)
  );
};

const hasText = (value: unknown): value is string => typeof value === 'string' && value.trim().length > 0;

const hasNumber = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);
