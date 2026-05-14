import liveScoresPayload from '../data/live_scores.json';

export type LiveScore = {
  horse_name: string;
  rider_name: string;
  division: string;
  place: string;
  dressage_score: number;
  cross_country_jump_penalties: number;
  cross_country_time_penalties: number;
  show_jumping_penalties: number;
  show_jumping_time_penalties: number;
  total_penalties: number;
  status: string;
};

export type LiveEvent = {
  id: string;
  name: string;
  source_id: string;
  source_name: string;
  source_url: string;
  country: string;
  date_label: string;
  collected_at: string;
  status: string;
  scores: LiveScore[];
};

export type LiveScoreWithEvent = LiveScore & {
  eventId: string;
  eventName: string;
  sourceName: string;
  sourceUrl: string;
  collectedAt: string;
};

export type LiveScoringPayload = {
  version: number;
  collected_at: string;
  search_queries: string[];
  events: LiveEvent[];
};

export const liveScoringFeed = liveScoresPayload as LiveScoringPayload;

export const phaseTotal = (score: LiveScore) =>
  roundToTenths(
    score.dressage_score +
      score.cross_country_jump_penalties +
      score.cross_country_time_penalties +
      score.show_jumping_penalties +
      score.show_jumping_time_penalties,
  );

export const flattenLiveScores = (events: LiveEvent[] = liveScoringFeed.events): LiveScoreWithEvent[] =>
  events.flatMap((event) =>
    event.scores.map((score) => ({
      ...score,
      eventId: event.id,
      eventName: event.name,
      sourceName: event.source_name,
      sourceUrl: event.source_url,
      collectedAt: event.collected_at,
    })),
  );

export const sortByLiveScore = (scores: LiveScoreWithEvent[]) =>
  [...scores].sort((a, b) => {
    if (a.total_penalties !== b.total_penalties) {
      return a.total_penalties - b.total_penalties;
    }

    return `${a.eventName}${a.division}${a.horse_name}`.localeCompare(`${b.eventName}${b.division}${b.horse_name}`);
  });

export const getLiveScoreRows = (limit = 8, events: LiveEvent[] = liveScoringFeed.events) =>
  sortByLiveScore(flattenLiveScores(events)).slice(0, limit);

export const formatCollectedAt = (value: string) =>
  new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));

const roundToTenths = (value: number) => Math.round(value * 10) / 10;
