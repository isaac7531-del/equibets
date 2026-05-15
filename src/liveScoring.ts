import currentEventFeed from '../data/current_event_results.json';
import { roundToTenths, type EventingScore } from './scoring';

export type LiveResultStatus = 'not_started' | 'dressage' | 'show_jumping' | 'cross_country' | 'final';

export type RawCurrentEventResult = {
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
  collected_at: string;
  status: LiveResultStatus;
  division?: string;
  source_url?: string;
};

type CurrentEventFeed = {
  collected_at: string;
  results: RawCurrentEventResult[];
};

export type LiveScoredResult = {
  id: string;
  sourceId: string;
  rider: string;
  horse: string;
  eventName: string;
  date: string;
  level: string;
  country: string;
  division: string;
  status: LiveResultStatus;
  collectedAt: string;
  sourceUrl?: string;
  score: EventingScore;
};

const statusRank: Record<LiveResultStatus, number> = {
  not_started: 0,
  dressage: 1,
  show_jumping: 2,
  cross_country: 3,
  final: 4,
};

export const liveFeedUpdatedAt = (currentEventFeed as CurrentEventFeed).collected_at;

export const liveScoredResults = normalizeCurrentEventResults((currentEventFeed as CurrentEventFeed).results);

export function normalizeCurrentEventResults(results: RawCurrentEventResult[]): LiveScoredResult[] {
  return results.map((result) => {
    const score = {
      dressagePenalties: roundToTenths(result.dressage_score),
      showJumpingPenalties: roundToTenths(result.show_jumping_penalties),
      crossCountryJumpPenalties: roundToTenths(result.cross_country_jump_penalties),
      crossCountryTimePenalties: roundToTenths(result.cross_country_time_penalties),
      totalPenalties: roundToTenths(
        result.dressage_score +
          result.show_jumping_penalties +
          result.cross_country_jump_penalties +
          result.cross_country_time_penalties,
      ),
    };

    return {
      id: `${result.source_id}:${result.source_record_id}`,
      sourceId: result.source_id,
      rider: result.rider_name,
      horse: result.horse_name,
      eventName: result.event_name,
      date: result.event_date,
      level: result.level,
      country: result.country,
      division: result.division ?? result.level,
      status: result.status,
      collectedAt: result.collected_at,
      sourceUrl: result.source_url,
      score,
    };
  });
}

export function searchLiveResults(results: LiveScoredResult[], query: string) {
  const normalizedQuery = normalizeSearchText(query);
  if (!normalizedQuery) {
    return results;
  }

  return results.filter((result) =>
    normalizeSearchText(
      [
        result.rider,
        result.horse,
        result.eventName,
        result.level,
        result.division,
        result.country,
        result.status,
      ].join(' '),
    ).includes(normalizedQuery),
  );
}

export function sortLiveLeaderboard(results: LiveScoredResult[]) {
  return [...results].sort((a, b) => {
    if (a.score.totalPenalties !== b.score.totalPenalties) {
      return a.score.totalPenalties - b.score.totalPenalties;
    }

    if (a.status !== b.status) {
      return statusRank[b.status] - statusRank[a.status];
    }

    return `${a.eventName}${a.horse}`.localeCompare(`${b.eventName}${b.horse}`);
  });
}

export function formatLiveStatus(status: LiveResultStatus) {
  return status
    .split('_')
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(' ');
}

export function formatFeedTimestamp(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function normalizeSearchText(value: string) {
  return value.toLocaleLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
}
