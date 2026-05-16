export type LiveScoreLeader = {
  rider: string;
  horse: string;
  score: number;
};

export type LivePhaseLink = {
  label: string;
  url: string;
};

export type LiveDivisionScore = {
  division: string;
  phase: string;
  phase_links: LivePhaseLink[];
  leader: LiveScoreLeader | null;
};

export type LiveEventScore = {
  id: string;
  name: string;
  date_label: string;
  start_date: string;
  end_date: string;
  location: string;
  country: string;
  status: string;
  source_url: string;
  divisions: LiveDivisionScore[];
};

export type LiveScoreFeed = {
  version: number;
  generated_at: string;
  as_of_date: string;
  source_id: string;
  source_name: string;
  source_url: string;
  events: LiveEventScore[];
};

export type LiveLeaderRow = {
  event: LiveEventScore;
  division: LiveDivisionScore;
  leader: LiveScoreLeader;
};

export const getLiveLeaderRows = (feed: LiveScoreFeed): LiveLeaderRow[] =>
  feed.events.flatMap((event) =>
    event.divisions.flatMap((division) =>
      division.leader ? [{ event, division, leader: division.leader }] : [],
    ),
  );

export const sortLiveLeaderRows = (rows: LiveLeaderRow[]) =>
  [...rows].sort((a, b) => {
    if (a.leader.score !== b.leader.score) {
      return a.leader.score - b.leader.score;
    }
    if (a.event.start_date !== b.event.start_date) {
      return a.event.start_date.localeCompare(b.event.start_date);
    }
    return a.division.division.localeCompare(b.division.division);
  });

export const formatFeedTimestamp = (value: string) => {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
};
