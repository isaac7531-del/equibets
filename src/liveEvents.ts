import currentEventsPayload from '../data/current_events.json';

export type LiveEventStatus = 'live' | 'upcoming' | 'complete';

export type LiveEventResult = {
  place: string;
  start_number: number | null;
  rider_name: string;
  horse_name: string;
  country: string;
  dressage_score: number | null;
  show_jumping_penalties: number | null;
  cross_country_jump_penalties: number | null;
  cross_country_time_penalties: number | null;
  total_penalties: number | null;
  phase: string;
};

export type CurrentEvent = {
  id: string;
  name: string;
  country: string;
  region: string;
  level: string;
  start_date: string;
  end_date: string;
  status: LiveEventStatus;
  source_id: string;
  source_name: string;
  source_url: string;
  last_checked_at: string;
  notes: string;
  results: LiveEventResult[];
};

type CurrentEventsPayload = {
  generated_at: string;
  events: CurrentEvent[];
};

export const currentEventsSnapshot = currentEventsPayload as CurrentEventsPayload;

export const currentEvents = [...currentEventsSnapshot.events].sort((a, b) => {
  if (a.status !== b.status) {
    return a.status === 'live' ? -1 : 1;
  }

  return a.start_date.localeCompare(b.start_date) || a.name.localeCompare(b.name);
});

export const rankedLiveResults = (results: LiveEventResult[]) =>
  [...results].sort((a, b) => {
    if (a.total_penalties === null && b.total_penalties === null) {
      return a.rider_name.localeCompare(b.rider_name) || a.horse_name.localeCompare(b.horse_name);
    }
    if (a.total_penalties === null) {
      return 1;
    }
    if (b.total_penalties === null) {
      return -1;
    }

    return a.total_penalties - b.total_penalties || a.rider_name.localeCompare(b.rider_name);
  });

export const topLiveResults = (event: CurrentEvent, limit = 3) => rankedLiveResults(event.results).slice(0, limit);

export const liveEventsWithScores = (events: CurrentEvent[] = currentEvents) =>
  events.filter((event) => event.status === 'live' && event.results.length > 0);

export const filterCurrentEvents = (query: string, events: CurrentEvent[] = currentEvents) => {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) {
    return events;
  }

  return events.filter((event) => {
    const eventValues = [
      event.name,
      event.country,
      event.region,
      event.level,
      event.source_name,
      event.status,
    ];
    const resultValues = event.results.flatMap((result) => [
      result.rider_name,
      result.horse_name,
      result.country,
      result.phase,
    ]);

    return [...eventValues, ...resultValues].some((value) => value.toLowerCase().includes(normalizedQuery));
  });
};

export const formatScore = (score: number | null) => (score === null ? '--' : score.toFixed(1));

export const formatEventDateRange = (event: CurrentEvent) => {
  if (event.start_date === event.end_date) {
    return event.start_date;
  }

  return `${event.start_date} to ${event.end_date}`;
};
