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

export type LiveEventScore = {
  event_key: string;
  event_name: string;
  event_date: string;
  level: string;
  country: string;
  leader_count: number;
  leaders: LiveScoreEntry[];
};

export type LiveScoringFeed = {
  version: number;
  feed_type: string;
  updated_at: string;
  date_window: {
    start_date: string;
    end_date: string;
  };
  source_ids: string[];
  summary: {
    result_count: number;
    leaderboard_count: number;
    events_found?: number;
    results_collected?: number;
  };
  events: LiveEventScore[];
};

export const EMPTY_LIVE_SCORING_FEED: LiveScoringFeed = {
  version: 1,
  feed_type: 'current_event_live_scoring',
  updated_at: '',
  date_window: {
    start_date: '',
    end_date: '',
  },
  source_ids: [],
  summary: {
    result_count: 0,
    leaderboard_count: 0,
  },
  events: [],
};

export const fetchLiveScoringFeed = async (
  fetcher: typeof fetch = globalThis.fetch,
): Promise<LiveScoringFeed> => {
  if (!fetcher) {
    throw new Error('fetch is not available');
  }

  const response = await fetcher('/current_event_scores.json', { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Live scoring feed request failed: ${response.status}`);
  }

  return normalizeLiveScoringFeed(await response.json());
};

export const normalizeLiveScoringFeed = (payload: unknown): LiveScoringFeed => {
  if (!isRecord(payload)) {
    return EMPTY_LIVE_SCORING_FEED;
  }

  const events = Array.isArray(payload.events) ? payload.events.map(normalizeEvent).filter((event) => event !== null) : [];
  const summary = isRecord(payload.summary) ? payload.summary : {};
  const dateWindow = isRecord(payload.date_window) ? payload.date_window : {};

  return {
    version: numberValue(payload.version, 1),
    feed_type: stringValue(payload.feed_type, 'current_event_live_scoring'),
    updated_at: stringValue(payload.updated_at, ''),
    date_window: {
      start_date: stringValue(dateWindow.start_date, ''),
      end_date: stringValue(dateWindow.end_date, ''),
    },
    source_ids: Array.isArray(payload.source_ids) ? payload.source_ids.filter((sourceId) => typeof sourceId === 'string') : [],
    summary: {
      result_count: numberValue(summary.result_count, events.reduce((total, event) => total + event.leaders.length, 0)),
      leaderboard_count: numberValue(summary.leaderboard_count, events.length),
      events_found: optionalNumber(summary.events_found),
      results_collected: optionalNumber(summary.results_collected),
    },
    events,
  };
};

export const formatFeedUpdatedAt = (value: string) => {
  if (!value) {
    return 'not refreshed yet';
  }

  const parsedDate = new Date(value);
  if (Number.isNaN(parsedDate.getTime())) {
    return value;
  }

  return `${parsedDate.toISOString().slice(0, 10)} ${parsedDate.toISOString().slice(11, 16)} UTC`;
};

const normalizeEvent = (event: unknown): LiveEventScore | null => {
  if (!isRecord(event)) {
    return null;
  }

  const leaders = Array.isArray(event.leaders)
    ? event.leaders.map(normalizeLeader).filter((leader) => leader !== null)
    : [];
  const eventName = stringValue(event.event_name, '');
  const eventDate = stringValue(event.event_date, '');
  const level = stringValue(event.level, 'Unknown');
  const country = stringValue(event.country, 'Unknown');

  if (!eventName || !eventDate) {
    return null;
  }

  return {
    event_key: stringValue(event.event_key, `${eventName}-${eventDate}-${level}-${country}`),
    event_name: eventName,
    event_date: eventDate,
    level,
    country,
    leader_count: numberValue(event.leader_count, leaders.length),
    leaders,
  };
};

const normalizeLeader = (leader: unknown): LiveScoreEntry | null => {
  if (!isRecord(leader)) {
    return null;
  }

  const riderName = stringValue(leader.rider_name, '');
  const horseName = stringValue(leader.horse_name, '');
  if (!riderName || !horseName) {
    return null;
  }

  return {
    rank: numberValue(leader.rank, 0),
    rider_name: riderName,
    horse_name: horseName,
    finishing_score: numberValue(leader.finishing_score, 0),
    dressage_score: numberValue(leader.dressage_score, 0),
    show_jumping_penalties: numberValue(leader.show_jumping_penalties, 0),
    cross_country_jump_penalties: numberValue(leader.cross_country_jump_penalties, 0),
    cross_country_time_penalties: numberValue(leader.cross_country_time_penalties, 0),
    source_id: stringValue(leader.source_id, ''),
    source_record_id: stringValue(leader.source_record_id, ''),
    collected_at: stringValue(leader.collected_at, ''),
  };
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const stringValue = (value: unknown, fallback: string) => (typeof value === 'string' ? value : fallback);

const numberValue = (value: unknown, fallback: number) =>
  typeof value === 'number' && Number.isFinite(value) ? value : fallback;

const optionalNumber = (value: unknown) => (typeof value === 'number' && Number.isFinite(value) ? value : undefined);
