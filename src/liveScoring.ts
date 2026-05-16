export type LiveDivision = {
  name: string;
  phase_status: string;
  entry_status_url: string | null;
  times_url: string | null;
  scores_url?: string | null;
};

export type LiveScoreBreakdown = {
  dressagePenalties?: number | null;
  showJumpingPenalties?: number | null;
  crossCountryJumpPenalties?: number | null;
  crossCountryTimePenalties?: number | null;
  totalPenalties?: number | null;
};

export type LiveScoreEntry = {
  id: string;
  riderName: string;
  horseName: string;
  division: string;
  status: string;
  score: LiveScoreBreakdown | null;
};

export type LiveEvent = {
  id: string;
  source_id: string;
  source_name: string;
  name: string;
  date_label: string;
  starts_on: string;
  ends_on: string;
  location: string;
  country: string;
  status: 'completed' | 'live' | 'upcoming' | string;
  score_status: string;
  result_url: string;
  divisions: LiveDivision[];
  entries: LiveScoreEntry[];
};

export type LiveScoringSnapshot = {
  version: number;
  generated_at: string;
  sources: Array<{
    id: string;
    name: string;
    url: string;
  }>;
  events: LiveEvent[];
};

export type RankedLiveEntry = {
  event: LiveEvent;
  entry: LiveScoreEntry;
  totalPenalties: number | null;
};

export type LiveSnapshotSummary = {
  eventCount: number;
  liveEventCount: number;
  divisionCount: number;
  entryCount: number;
  scoredEntryCount: number;
  sourceCount: number;
};

const roundToTenths = (value: number) => Math.round(value * 10) / 10;

const isFiniteNumber = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);

export const liveEntryTotal = (entry: LiveScoreEntry): number | null => {
  if (!entry.score) {
    return null;
  }

  if (isFiniteNumber(entry.score.totalPenalties)) {
    return entry.score.totalPenalties;
  }

  if (!isFiniteNumber(entry.score.dressagePenalties)) {
    return null;
  }

  return roundToTenths(
    entry.score.dressagePenalties +
      (entry.score.showJumpingPenalties ?? 0) +
      (entry.score.crossCountryJumpPenalties ?? 0) +
      (entry.score.crossCountryTimePenalties ?? 0),
  );
};

export const rankLiveEntries = (snapshot: LiveScoringSnapshot): RankedLiveEntry[] =>
  snapshot.events
    .flatMap((event) =>
      event.entries.map((entry) => ({
        event,
        entry,
        totalPenalties: liveEntryTotal(entry),
      })),
    )
    .sort((a, b) => {
      if (a.totalPenalties === null && b.totalPenalties === null) {
        return a.entry.horseName.localeCompare(b.entry.horseName);
      }
      if (a.totalPenalties === null) {
        return 1;
      }
      if (b.totalPenalties === null) {
        return -1;
      }
      if (a.totalPenalties !== b.totalPenalties) {
        return a.totalPenalties - b.totalPenalties;
      }
      return a.entry.horseName.localeCompare(b.entry.horseName);
    });

export const summarizeLiveSnapshot = (snapshot: LiveScoringSnapshot): LiveSnapshotSummary => {
  const rankedEntries = rankLiveEntries(snapshot);

  return {
    eventCount: snapshot.events.length,
    liveEventCount: snapshot.events.filter((event) => event.status === 'live').length,
    divisionCount: snapshot.events.reduce((total, event) => total + event.divisions.length, 0),
    entryCount: rankedEntries.length,
    scoredEntryCount: rankedEntries.filter((entry) => entry.totalPenalties !== null).length,
    sourceCount: new Set(snapshot.sources.map((source) => source.id)).size,
  };
};

export const formatDateRange = (event: LiveEvent) =>
  event.starts_on === event.ends_on ? event.starts_on : `${event.starts_on} to ${event.ends_on}`;

export const scoreStatusLabel = (status: string) =>
  status
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => `${part.charAt(0).toUpperCase()}${part.slice(1)}`)
    .join(' ') || 'Unknown';

export const formatGeneratedAt = (generatedAt: string) => generatedAt.replace('T', ' ').replace(/:00Z$/, ' UTC');
