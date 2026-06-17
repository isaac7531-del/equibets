export type LiveScoreEntry = {
  rank: number;
  rider_name: string;
  horse_name: string;
  finishing_score: number;
  dressage_score: number;
  show_jumping_penalties: number;
  cross_country_jump_penalties: number;
  cross_country_time_penalties: number;
  source_id: string;
  source_record_id: string;
  collected_at: string;
};

export type LiveScoreEvent = {
  event_name: string;
  event_date: string;
  level: string;
  country: string;
  latest_collected_at: string;
  entry_count: number;
  leader: LiveScoreEntry | null;
  entries: LiveScoreEntry[];
};

export type LiveScoreFeed = {
  version: number;
  source_id: string;
  updated_at: string;
  window_start: string | null;
  window_end: string | null;
  event_count: number;
  score_count: number;
  events: LiveScoreEvent[];
};

const LIVE_FEED_URL = '/live_scores.json';

export const loadLiveScoreFeed = async (url = LIVE_FEED_URL): Promise<LiveScoreFeed | null> => {
  if (typeof fetch === 'undefined') {
    return null;
  }

  try {
    const response = await fetch(url, { cache: 'no-store' });
    if (!response.ok) {
      return null;
    }

    const payload: unknown = await response.json();
    return isLiveScoreFeed(payload) ? payload : null;
  } catch {
    return null;
  }
};

export const formatFeedDateRange = (feed: Pick<LiveScoreFeed, 'window_start' | 'window_end'>) => {
  if (!feed.window_start && !feed.window_end) {
    return 'current event window';
  }

  if (feed.window_start === feed.window_end) {
    return feed.window_start ?? 'current event window';
  }

  return `${feed.window_start ?? 'open'} to ${feed.window_end ?? 'open'}`;
};

export const formatTimestamp = (value: string) => {
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(timestamp);
};

const isLiveScoreFeed = (value: unknown): value is LiveScoreFeed => {
  if (!isRecord(value)) {
    return false;
  }

  return (
    value.version === 1 &&
    typeof value.source_id === 'string' &&
    typeof value.updated_at === 'string' &&
    typeof value.event_count === 'number' &&
    typeof value.score_count === 'number' &&
    Array.isArray(value.events) &&
    value.events.every(isLiveScoreEvent)
  );
};

const isLiveScoreEvent = (value: unknown): value is LiveScoreEvent => {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.event_name === 'string' &&
    typeof value.event_date === 'string' &&
    typeof value.level === 'string' &&
    typeof value.country === 'string' &&
    typeof value.latest_collected_at === 'string' &&
    typeof value.entry_count === 'number' &&
    (value.leader === null || isLiveScoreEntry(value.leader)) &&
    Array.isArray(value.entries) &&
    value.entries.every(isLiveScoreEntry)
  );
};

const isLiveScoreEntry = (value: unknown): value is LiveScoreEntry => {
  if (!isRecord(value)) {
    return false;
  }

  return (
    typeof value.rank === 'number' &&
    typeof value.rider_name === 'string' &&
    typeof value.horse_name === 'string' &&
    typeof value.finishing_score === 'number' &&
    typeof value.dressage_score === 'number' &&
    typeof value.show_jumping_penalties === 'number' &&
    typeof value.cross_country_jump_penalties === 'number' &&
    typeof value.cross_country_time_penalties === 'number' &&
    typeof value.source_id === 'string' &&
    typeof value.source_record_id === 'string' &&
    typeof value.collected_at === 'string'
  );
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;
