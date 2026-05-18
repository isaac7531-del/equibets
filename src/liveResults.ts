export type LiveScoreResult = {
  source_id: string;
  source_record_id: string;
  rider_name: string;
  horse_name: string;
  event_name: string;
  event_date: string;
  level: string;
  country: string;
  dressage_score: number;
  show_jumping_penalties: number;
  cross_country_jump_penalties: number;
  cross_country_time_penalties: number;
  finishing_score: number;
  collected_at: string;
  is_user_entered: boolean;
};

export type LiveScorePayload = {
  version: number;
  generated_at: string;
  window: {
    start_date: string;
    end_date: string;
  };
  result_count: number;
  source_ids: string[];
  results: LiveScoreResult[];
};

export const LIVE_SCORES_URL = '/data/live_scores.json';

export const fetchLiveScores = async (
  fetcher: typeof fetch = fetch,
): Promise<LiveScorePayload | null> => {
  const response = await fetcher(LIVE_SCORES_URL, { cache: 'no-store' });
  if (!response.ok) {
    return null;
  }

  const payload = (await response.json()) as Partial<LiveScorePayload>;
  if (!Array.isArray(payload.results) || !payload.window) {
    return null;
  }

  return {
    version: typeof payload.version === 'number' ? payload.version : 1,
    generated_at: typeof payload.generated_at === 'string' ? payload.generated_at : '',
    window: {
      start_date: payload.window.start_date,
      end_date: payload.window.end_date,
    },
    result_count: typeof payload.result_count === 'number' ? payload.result_count : payload.results.length,
    source_ids: Array.isArray(payload.source_ids) ? payload.source_ids : [],
    results: sortLiveScores(payload.results.filter(isLiveScoreResult)),
  };
};

export const sortLiveScores = (results: LiveScoreResult[]) =>
  [...results].sort((a, b) => {
    if (a.event_date !== b.event_date) {
      return a.event_date.localeCompare(b.event_date);
    }
    if (a.event_name !== b.event_name) {
      return a.event_name.localeCompare(b.event_name);
    }
    if (a.level !== b.level) {
      return a.level.localeCompare(b.level);
    }
    if (a.finishing_score !== b.finishing_score) {
      return a.finishing_score - b.finishing_score;
    }

    return `${a.rider_name} ${a.horse_name}`.localeCompare(`${b.rider_name} ${b.horse_name}`);
  });

const isLiveScoreResult = (value: unknown): value is LiveScoreResult => {
  if (!value || typeof value !== 'object') {
    return false;
  }

  const result = value as LiveScoreResult;
  return (
    typeof result.rider_name === 'string' &&
    typeof result.horse_name === 'string' &&
    typeof result.event_name === 'string' &&
    typeof result.event_date === 'string' &&
    typeof result.finishing_score === 'number'
  );
};
