import liveScoreSnapshotData from '../data/current_event_live_scores.json';

export type LiveScoreLeader = {
  division: string;
  phase: string;
  leader_name: string;
  rider_name: string | null;
  horse_name: string | null;
  score_text: string;
  score: number | null;
  results_url: string | null;
};

export type LiveScoreEvent = {
  event_name: string;
  date_label: string;
  start_date: string;
  end_date: string;
  location: string;
  status: 'current' | 'completed' | 'upcoming';
  source_id: string;
  source_url: string | null;
  leaders: LiveScoreLeader[];
  fetch_error: string | null;
};

export type LiveScoreSnapshot = {
  version: number;
  collected_at: string;
  as_of_date: string;
  source_id: string;
  source_name: string;
  archive_url: string;
  fetched_archive_url: string;
  events: LiveScoreEvent[];
};

export const liveScoreSnapshot = liveScoreSnapshotData as LiveScoreSnapshot;

export const liveScoreSummary = (snapshot: LiveScoreSnapshot) => {
  const leaderCount = snapshot.events.reduce((total, event) => total + event.leaders.length, 0);
  const lowestLeader = snapshot.events
    .flatMap((event) =>
      event.leaders.map((leader) => ({
        event,
        leader,
      })),
    )
    .filter(({ leader }) => leader.score !== null)
    .sort((a, b) => (a.leader.score ?? Number.POSITIVE_INFINITY) - (b.leader.score ?? Number.POSITIVE_INFINITY))[0];

  return {
    eventCount: snapshot.events.length,
    leaderCount,
    lowestLeader,
  };
};

export const formatLeaderName = (leader: LiveScoreLeader) => {
  if (leader.rider_name && leader.horse_name) {
    return `${leader.rider_name} / ${leader.horse_name}`;
  }

  return leader.leader_name;
};

export const formatCollectedAt = (isoDate: string) =>
  new Intl.DateTimeFormat('en', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'UTC',
  }).format(new Date(isoDate));
