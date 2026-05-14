import liveEventData from '../data/live_event_results.json';
import { calculateScoreFromPenalties, type EventingScore } from './scoring';

type RawLiveResult = (typeof liveEventData.results)[number];

export type LiveEventResult = {
  id: string;
  sourceId: string;
  sourceUrl: string;
  riderName: string;
  horseName: string;
  eventName: string;
  eventDate: string;
  level: string;
  division: string;
  country: string;
  placing: number;
  status: string;
  score: EventingScore;
};

export const liveEventSnapshot = {
  collectedAt: liveEventData.collected_at,
  summary: liveEventData.summary,
  searchQueries: liveEventData.search_queries,
  sources: liveEventData.sources,
};

const toLiveEventResult = (result: RawLiveResult): LiveEventResult => ({
  id: result.source_record_id,
  sourceId: result.source_id,
  sourceUrl: result.source_url,
  riderName: result.rider_name,
  horseName: result.horse_name,
  eventName: result.event_name,
  eventDate: result.event_date,
  level: result.level,
  division: result.division,
  country: result.country,
  placing: result.placing,
  status: result.status,
  score: calculateScoreFromPenalties({
    dressagePenalties: result.dressage_score,
    showJumpingPenalties: result.show_jumping_penalties,
    crossCountryJumpPenalties: result.cross_country_jump_penalties,
    crossCountryTimePenalties: result.cross_country_time_penalties,
  }),
});

export const liveResults = liveEventData.results.map(toLiveEventResult);

export const rankedLiveResults = [...liveResults].sort((a, b) => {
  if (a.score.totalPenalties !== b.score.totalPenalties) {
    return a.score.totalPenalties - b.score.totalPenalties;
  }
  if (a.eventDate !== b.eventDate) {
    return b.eventDate.localeCompare(a.eventDate);
  }
  return a.placing - b.placing;
});

export const liveEventCount = new Set(liveResults.map((result) => result.eventName)).size;
