import currentEventFeedJson from '../data/current_events.json';
import { calculateScoreFromPenalties, type EventingScore } from './scoring';

type NullableNumber = number | null;

export type CurrentEventStart = {
  id: string;
  sourceId: string;
  sourceRecordId: string;
  sourcePriority: number;
  riderName: string;
  horseName: string;
  eventName: string;
  eventDate: string;
  level: string;
  country: string;
  dressageScore: NullableNumber;
  showJumpingPenalties: NullableNumber;
  crossCountryJumpPenalties: NullableNumber;
  crossCountryTimePenalties: NullableNumber;
  phaseStatus: string;
  collectedAt: string;
};

export type CurrentEventScore = CurrentEventStart & {
  score: EventingScore;
  completedPhaseCount: number;
  phaseLabel: string;
};

type CurrentEventFeedJson = typeof currentEventFeedJson;

export type CurrentEventFeed = {
  version: number;
  collectedAt: string;
  sourceSummary: string;
  results: CurrentEventStart[];
};

const toCurrentEventStart = (item: CurrentEventFeedJson['results'][number]): CurrentEventStart => ({
  id: item.id,
  sourceId: item.source_id,
  sourceRecordId: item.source_record_id,
  sourcePriority: item.source_priority,
  riderName: item.rider_name,
  horseName: item.horse_name,
  eventName: item.event_name,
  eventDate: item.event_date,
  level: item.level,
  country: item.country,
  dressageScore: item.dressage_score,
  showJumpingPenalties: item.show_jumping_penalties,
  crossCountryJumpPenalties: item.cross_country_jump_penalties,
  crossCountryTimePenalties: item.cross_country_time_penalties,
  phaseStatus: item.phase_status,
  collectedAt: item.collected_at,
});

export const currentEventFeed: CurrentEventFeed = {
  version: currentEventFeedJson.version,
  collectedAt: currentEventFeedJson.collected_at,
  sourceSummary: currentEventFeedJson.source_summary,
  results: currentEventFeedJson.results.map(toCurrentEventStart),
};

const penaltyOrZero = (value: NullableNumber) => (typeof value === 'number' ? value : 0);

const phaseLabel = (start: CurrentEventStart) => {
  if (start.crossCountryJumpPenalties !== null || start.crossCountryTimePenalties !== null) {
    return start.phaseStatus === 'final' ? 'Final score' : 'XC live';
  }

  if (start.showJumpingPenalties !== null) {
    return 'After show jumping';
  }

  if (start.dressageScore !== null) {
    return 'After dressage';
  }

  return 'Awaiting scores';
};

export const scoreCurrentEventStart = (start: CurrentEventStart): CurrentEventScore => {
  const completedPhaseCount = [
    start.dressageScore,
    start.showJumpingPenalties,
    start.crossCountryJumpPenalties,
    start.crossCountryTimePenalties,
  ].filter((value) => value !== null).length;

  return {
    ...start,
    completedPhaseCount,
    phaseLabel: phaseLabel(start),
    score: calculateScoreFromPenalties({
      dressagePenalties: penaltyOrZero(start.dressageScore),
      showJumpingPenalties: penaltyOrZero(start.showJumpingPenalties),
      crossCountryJumpPenalties: penaltyOrZero(start.crossCountryJumpPenalties),
      crossCountryTimePenalties: penaltyOrZero(start.crossCountryTimePenalties),
    }),
  };
};

export const sortCurrentEventScores = (scores: CurrentEventScore[]) =>
  [...scores].sort((a, b) => {
    if (a.completedPhaseCount !== b.completedPhaseCount) {
      return b.completedPhaseCount - a.completedPhaseCount;
    }

    if (a.score.totalPenalties !== b.score.totalPenalties) {
      return a.score.totalPenalties - b.score.totalPenalties;
    }

    if (a.sourcePriority !== b.sourcePriority) {
      return a.sourcePriority - b.sourcePriority;
    }

    return a.collectedAt.localeCompare(b.collectedAt);
  });

export const searchCurrentEventResults = (
  query: string,
  starts: CurrentEventStart[] = currentEventFeed.results,
) => {
  const normalizedQuery = query.trim().toLowerCase();
  const matches = normalizedQuery
    ? starts.filter((start) =>
        [start.riderName, start.horseName, start.eventName, start.level, start.country, start.sourceId]
          .join(' ')
          .toLowerCase()
          .includes(normalizedQuery),
      )
    : starts;

  return sortCurrentEventScores(matches.map(scoreCurrentEventStart));
};
