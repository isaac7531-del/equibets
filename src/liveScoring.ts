export type CurrentEventStatus = 'live' | 'upcoming' | 'completed';

export type CurrentEventSource = {
  sourceId: string;
  name: string;
  url: string;
  fetchedAt: string;
  notes?: string;
};

export type CurrentEvent = {
  id: string;
  name: string;
  dateRange: string;
  location: string;
  country: string;
  status: CurrentEventStatus;
  sourceId: string;
  sourceUrl: string;
  sourceLabel: string;
};

export type LiveScoredStartPhase = 'dressage' | 'show_jumping' | 'cross_country' | 'final';

export type LiveScoredStart = {
  id: string;
  eventId: string;
  level: string;
  rider: string;
  horse: string;
  phase: LiveScoredStartPhase;
  dressagePenalties: number;
  showJumpingPenalties: number;
  crossCountryJumpPenalties: number;
  crossCountryTimePenalties: number;
  totalPenalties: number;
  updatedAt: string;
  sourceId: string;
};

export type RankedLiveScoredStart = LiveScoredStart & {
  rank: number;
};

export type LiveScoringSnapshot = {
  version: number;
  generatedAt: string;
  searchQuery: string;
  statusMessage: string;
  sources: CurrentEventSource[];
  events: CurrentEvent[];
  scoredStarts: LiveScoredStart[];
};

export type LiveEventSummary = CurrentEvent & {
  rankedStarts: RankedLiveScoredStart[];
};

export type LiveScoringSummary = {
  generatedAt: string;
  latestFetchedAt: string;
  eventCount: number;
  liveEventCount: number;
  scoredStartCount: number;
  hasLiveScores: boolean;
  statusLabel: string;
  eventSummaries: LiveEventSummary[];
};

const statusPriority: Record<CurrentEventStatus, number> = {
  live: 0,
  upcoming: 1,
  completed: 2,
};

export const rankLiveScoredStarts = (starts: LiveScoredStart[]): RankedLiveScoredStart[] => {
  const sortedStarts = [...starts].sort((a, b) => {
    if (a.totalPenalties !== b.totalPenalties) {
      return a.totalPenalties - b.totalPenalties;
    }

    return a.updatedAt.localeCompare(b.updatedAt);
  });

  return sortedStarts.map((start, index) => ({
    ...start,
    rank: index + 1,
  }));
};

export const sortCurrentEvents = (events: CurrentEvent[]): CurrentEvent[] =>
  [...events].sort((a, b) => {
    if (statusPriority[a.status] !== statusPriority[b.status]) {
      return statusPriority[a.status] - statusPriority[b.status];
    }

    const dateComparison = startDate(a.dateRange).localeCompare(startDate(b.dateRange));
    if (dateComparison !== 0) {
      return dateComparison;
    }

    return a.name.localeCompare(b.name);
  });

export const buildLiveScoringSummary = (snapshot: LiveScoringSnapshot): LiveScoringSummary => {
  const events = sortCurrentEvents(snapshot.events);
  const rankedStartsByEvent = new Map<string, RankedLiveScoredStart[]>();

  for (const start of rankLiveScoredStarts(snapshot.scoredStarts)) {
    const currentStarts = rankedStartsByEvent.get(start.eventId) ?? [];
    rankedStartsByEvent.set(start.eventId, [...currentStarts, start]);
  }

  const scoredStartCount = snapshot.scoredStarts.length;
  const liveEventCount = snapshot.events.filter((event) => event.status === 'live').length;

  return {
    generatedAt: snapshot.generatedAt,
    latestFetchedAt: latestFetchedAt(snapshot.sources, snapshot.generatedAt),
    eventCount: snapshot.events.length,
    liveEventCount,
    scoredStartCount,
    hasLiveScores: scoredStartCount > 0,
    statusLabel: liveStatusLabel(scoredStartCount, liveEventCount),
    eventSummaries: events.map((event) => ({
      ...event,
      rankedStarts: rankedStartsByEvent.get(event.id) ?? [],
    })),
  };
};

export const sourceNamesById = (sources: CurrentEventSource[]) =>
  new Map(sources.map((source) => [source.sourceId, source.name]));

const latestFetchedAt = (sources: CurrentEventSource[], fallback: string) => {
  if (sources.length === 0) {
    return fallback;
  }

  return sources.reduce(
    (latest, source) => (source.fetchedAt.localeCompare(latest) > 0 ? source.fetchedAt : latest),
    sources[0].fetchedAt,
  );
};

const liveStatusLabel = (scoredStartCount: number, liveEventCount: number) => {
  if (scoredStartCount > 0) {
    return 'Live scores available';
  }

  if (liveEventCount > 0) {
    return 'Live event found, waiting for scores';
  }

  return 'No active live scores found';
};

const startDate = (dateRange: string) => dateRange.split('/')[0];
