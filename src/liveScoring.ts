import currentEventsData from '../data/current_events.json';
import { roundToTenths } from './scoring';

export type CurrentEventStatus = 'entries' | 'times' | 'running' | 'completed';

export type CurrentEventSource = {
  id: string;
  name: string;
  url: string;
  source_type: string;
};

export type LiveScoreRecord = {
  id: string;
  division: string;
  place: string;
  rider: string;
  horse: string;
  dressage_penalties: number;
  cross_country_jump_penalties: number;
  cross_country_time_penalties: number;
  show_jumping_jump_penalties: number;
  show_jumping_time_penalties: number;
  status: string;
};

export type CurrentEvent = {
  id: string;
  name: string;
  date_label: string;
  start_date: string;
  end_date: string;
  location: string;
  country: string;
  status: CurrentEventStatus;
  source_id: string;
  scoring_url: string;
  results: LiveScoreRecord[];
};

export type CurrentEventFeed = {
  version: number;
  collected_at: string;
  query_window: {
    starts_on: string;
    ends_on: string;
    description: string;
  };
  sources: CurrentEventSource[];
  events: CurrentEvent[];
};

export type LiveScoreRow = LiveScoreRecord & {
  eventId: string;
  eventName: string;
  eventDateLabel: string;
  eventLocation: string;
  sourceId: string;
  scoringUrl: string;
  totalPenalties: number;
};

export type LiveScoringSummary = {
  collectedAt: string;
  windowLabel: string;
  resultCount: number;
  eventsWithResults: number;
  upcomingEventCount: number;
  bestScore?: LiveScoreRow;
};

export const currentEventFeed = currentEventsData as CurrentEventFeed;

export const calculateLiveTotal = (record: LiveScoreRecord) =>
  roundToTenths(
    record.dressage_penalties +
      record.cross_country_jump_penalties +
      record.cross_country_time_penalties +
      record.show_jumping_jump_penalties +
      record.show_jumping_time_penalties,
  );

export const flattenLiveScores = (events: CurrentEvent[]): LiveScoreRow[] =>
  events.flatMap((event) =>
    event.results.map((result) => ({
      ...result,
      eventId: event.id,
      eventName: event.name,
      eventDateLabel: event.date_label,
      eventLocation: event.location,
      sourceId: event.source_id,
      scoringUrl: event.scoring_url,
      totalPenalties: calculateLiveTotal(result),
    })),
  );

export const sortLiveScoresByBest = (scores: LiveScoreRow[]) =>
  [...scores].sort((a, b) => {
    if (a.totalPenalties !== b.totalPenalties) {
      return a.totalPenalties - b.totalPenalties;
    }

    return a.horse.localeCompare(b.horse);
  });

export const searchLiveScores = (events: CurrentEvent[], query: string) => {
  const normalizedQuery = query.trim().toLowerCase();
  const rows = flattenLiveScores(events);

  if (!normalizedQuery) {
    return rows;
  }

  return rows.filter((row) =>
    [row.horse, row.rider, row.eventName, row.division, row.eventLocation]
      .join(' ')
      .toLowerCase()
      .includes(normalizedQuery),
  );
};

export const upcomingCurrentEvents = (events: CurrentEvent[]) =>
  events
    .filter((event) => event.status !== 'completed')
    .sort((a, b) => a.start_date.localeCompare(b.start_date));

export const getLiveScoringSummary = (feed: CurrentEventFeed): LiveScoringSummary => {
  const allScores = sortLiveScoresByBest(flattenLiveScores(feed.events));
  const eventsWithResults = feed.events.filter((event) => event.results.length > 0).length;
  const upcomingEventCount = upcomingCurrentEvents(feed.events).length;

  return {
    collectedAt: feed.collected_at,
    windowLabel: `${feed.query_window.starts_on} to ${feed.query_window.ends_on}`,
    resultCount: allScores.length,
    eventsWithResults,
    upcomingEventCount,
    bestScore: allScores[0],
  };
};

export const sourceById = (feed: CurrentEventFeed, sourceId: string) =>
  feed.sources.find((source) => source.id === sourceId);
