import currentLiveScores from '../data/current_live_scores.json';

export type CurrentEvent = {
  event_id: string;
  name: string;
  date_label: string;
  start_date: string;
  end_date: string;
  location: string;
  country: string;
  status: string;
  source_id: string;
  source_url: string;
};

export type LiveScore = {
  event_id: string;
  event_name: string;
  event_date: string;
  location: string;
  country: string;
  division: string;
  phase: string;
  rider_name: string;
  horse_name: string;
  score: number;
  source_id: string;
  source_priority: number;
  source_url: string;
  collected_at: string;
};

export type LiveScoreFeed = {
  version: number;
  generated_at: string;
  source: {
    id: string;
    name: string;
    url: string;
  };
  events: CurrentEvent[];
  scores: LiveScore[];
};

export const liveScoreFeed = currentLiveScores as LiveScoreFeed;

export const sortLiveScoresByBestScore = (scores: LiveScore[]) =>
  [...scores].sort((a, b) => {
    if (a.score !== b.score) {
      return a.score - b.score;
    }

    return `${a.event_name}${a.division}${a.rider_name}`.localeCompare(`${b.event_name}${b.division}${b.rider_name}`);
  });

export const formatLiveTimestamp = (value: string) => {
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) {
    return 'Unknown';
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(timestamp);
};

export const formatEventStatus = (status: string) =>
  status
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
