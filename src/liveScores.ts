export type PublicLiveScore = {
  sourceId: string;
  sourceRecordId: string;
  riderName: string;
  horseName: string;
  eventName: string;
  eventDate: string;
  level: string;
  country: string;
  dressageScore: number;
  showJumpingPenalties: number;
  crossCountryJumpPenalties: number;
  crossCountryTimePenalties: number;
  finishingScore: number;
  collectedAt: string;
};

export type LiveScoreboard = {
  version: number;
  generatedAt: string;
  window: {
    startDate: string;
    endDate: string;
  };
  latestCollectedAt: string | null;
  resultCount: number;
  scores: PublicLiveScore[];
};

const LIVE_SCORES_URL = '/live_scores.json';

type LiveScoreboardPayload = {
  version?: unknown;
  generated_at?: unknown;
  window?: {
    start_date?: unknown;
    end_date?: unknown;
  };
  latest_collected_at?: unknown;
  result_count?: unknown;
  scores?: unknown;
};

type PublicLiveScorePayload = {
  source_id?: unknown;
  source_record_id?: unknown;
  rider_name?: unknown;
  horse_name?: unknown;
  event_name?: unknown;
  event_date?: unknown;
  level?: unknown;
  country?: unknown;
  dressage_score?: unknown;
  show_jumping_penalties?: unknown;
  cross_country_jump_penalties?: unknown;
  cross_country_time_penalties?: unknown;
  finishing_score?: unknown;
  collected_at?: unknown;
};

export const loadLiveScoreboard = async (fetcher: typeof fetch = fetch): Promise<LiveScoreboard | null> => {
  try {
    const response = await fetcher(LIVE_SCORES_URL, { cache: 'no-store' });
    if (!response.ok) {
      return null;
    }

    return normalizeScoreboard((await response.json()) as LiveScoreboardPayload);
  } catch {
    return null;
  }
};

export const normalizeScoreboard = (payload: LiveScoreboardPayload): LiveScoreboard | null => {
  if (!payload.window || !Array.isArray(payload.scores)) {
    return null;
  }

  const scores = payload.scores.map(normalizeScore).filter((score): score is PublicLiveScore => score !== null);

  return {
    version: numberValue(payload.version),
    generatedAt: stringValue(payload.generated_at),
    window: {
      startDate: stringValue(payload.window.start_date),
      endDate: stringValue(payload.window.end_date),
    },
    latestCollectedAt: nullableStringValue(payload.latest_collected_at),
    resultCount: numberValue(payload.result_count, scores.length),
    scores,
  };
};

const normalizeScore = (payload: unknown): PublicLiveScore | null => {
  if (!payload || typeof payload !== 'object') {
    return null;
  }

  const score = payload as PublicLiveScorePayload;
  const riderName = stringValue(score.rider_name);
  const horseName = stringValue(score.horse_name);
  const eventName = stringValue(score.event_name);
  const eventDate = stringValue(score.event_date);
  if (!riderName || !horseName || !eventName || !eventDate) {
    return null;
  }

  return {
    sourceId: stringValue(score.source_id),
    sourceRecordId: stringValue(score.source_record_id),
    riderName,
    horseName,
    eventName,
    eventDate,
    level: stringValue(score.level),
    country: stringValue(score.country),
    dressageScore: numberValue(score.dressage_score),
    showJumpingPenalties: numberValue(score.show_jumping_penalties),
    crossCountryJumpPenalties: numberValue(score.cross_country_jump_penalties),
    crossCountryTimePenalties: numberValue(score.cross_country_time_penalties),
    finishingScore: numberValue(score.finishing_score),
    collectedAt: stringValue(score.collected_at),
  };
};

const stringValue = (value: unknown, fallback = '') => (typeof value === 'string' ? value : fallback);

const nullableStringValue = (value: unknown) => (typeof value === 'string' ? value : null);

const numberValue = (value: unknown, fallback = 0) => (typeof value === 'number' && Number.isFinite(value) ? value : fallback);
