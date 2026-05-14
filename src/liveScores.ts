import currentEventScoresPayload from '../data/current_event_scores.json';

export type LiveEventStatus = 'active' | 'recent' | 'completed' | 'upcoming';

export type LiveScoreLeader = {
  division: string;
  place: number;
  riderName: string;
  horseName: string;
  score: number;
  phase: string;
};

export type LiveEventScore = {
  id: string;
  sourceId: string;
  sourceName: string;
  sourceUrl: string;
  eventName: string;
  eventDate: string;
  eventEndDate: string;
  country: string;
  level: string;
  status: LiveEventStatus;
  phase: string;
  leaders: LiveScoreLeader[];
  notes: string;
};

export type LiveScoreSnapshot = {
  version: number;
  collectedAt: string;
  coverageNote: string;
  events: LiveEventScore[];
};

export type LiveScoreSummary = {
  collectedAt: string;
  eventCount: number;
  activeEventCount: number;
  leaderCount: number;
  bestLeader?: LiveScoreLeader & {
    eventName: string;
    sourceName: string;
  };
};

type RawLiveScoreLeader = {
  division: string;
  place: number;
  rider_name: string;
  horse_name: string;
  score: number;
  phase: string;
};

type RawLiveEventScore = {
  id: string;
  source_id: string;
  source_name: string;
  source_url: string;
  event_name: string;
  event_date: string;
  event_end_date: string;
  country: string;
  level: string;
  status: LiveEventStatus;
  phase: string;
  leaders: RawLiveScoreLeader[];
  notes: string;
};

type RawLiveScoreSnapshot = {
  version: number;
  collected_at: string;
  coverage_note: string;
  events: RawLiveEventScore[];
};

const statusSortOrder: Record<LiveEventStatus, number> = {
  active: 0,
  recent: 1,
  completed: 2,
  upcoming: 3,
};

export const normalizeLiveScoreSnapshot = (snapshot: RawLiveScoreSnapshot): LiveScoreSnapshot => ({
  version: snapshot.version,
  collectedAt: snapshot.collected_at,
  coverageNote: snapshot.coverage_note,
  events: snapshot.events.map((event) => ({
    id: event.id,
    sourceId: event.source_id,
    sourceName: event.source_name,
    sourceUrl: event.source_url,
    eventName: event.event_name,
    eventDate: event.event_date,
    eventEndDate: event.event_end_date,
    country: event.country,
    level: event.level,
    status: event.status,
    phase: event.phase,
    leaders: event.leaders.map((leader) => ({
      division: leader.division,
      place: leader.place,
      riderName: leader.rider_name,
      horseName: leader.horse_name,
      score: leader.score,
      phase: leader.phase,
    })),
    notes: event.notes,
  })),
});

export const liveScoreSnapshot = normalizeLiveScoreSnapshot(currentEventScoresPayload as RawLiveScoreSnapshot);

export const getDisplayLiveEvents = (snapshot = liveScoreSnapshot) =>
  [...snapshot.events].sort((left, right) => {
    const statusDelta = statusSortOrder[left.status] - statusSortOrder[right.status];
    if (statusDelta !== 0) {
      return statusDelta;
    }

    return right.eventDate.localeCompare(left.eventDate);
  });

export const getLiveScoreSummary = (snapshot = liveScoreSnapshot): LiveScoreSummary => {
  const scoredLeaders = snapshot.events
    .flatMap((event) =>
      event.leaders.map((leader) => ({
        ...leader,
        eventName: event.eventName,
        sourceName: event.sourceName,
      })),
    )
    .sort((left, right) => {
      if (left.score !== right.score) {
        return left.score - right.score;
      }

      return left.riderName.localeCompare(right.riderName);
    });

  return {
    collectedAt: snapshot.collectedAt,
    eventCount: snapshot.events.length,
    activeEventCount: snapshot.events.filter((event) => event.status === 'active').length,
    leaderCount: scoredLeaders.length,
    bestLeader: scoredLeaders[0],
  };
};

export const formatSnapshotTime = (isoTimestamp: string) =>
  new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(isoTimestamp));
