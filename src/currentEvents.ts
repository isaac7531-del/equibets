import currentEventScores from '../data/current_event_scores.json';

export type CurrentEventStatus = 'live' | 'final' | 'provisional' | 'scores';

export type CurrentEventLeader = {
  division: string;
  phase: string;
  rider: string;
  horse: string;
  score: number;
  status: CurrentEventStatus;
};

export type CurrentEventScore = {
  id: string;
  name: string;
  date_range: string;
  location: string;
  source_id: string;
  source_name: string;
  source_url: string;
  status: CurrentEventStatus;
  notes: string;
  leaders: CurrentEventLeader[];
};

export type CurrentEventScoreFeed = {
  version: number;
  collected_at: string;
  summary: string;
  events: CurrentEventScore[];
};

export const currentEventScoreFeed = currentEventScores as CurrentEventScoreFeed;

const startDate = (event: CurrentEventScore) => event.date_range.split('/')[0];

export const sortCurrentEvents = (events: CurrentEventScore[]) =>
  [...events].sort((a, b) => {
    const dateSort = startDate(b).localeCompare(startDate(a));

    return dateSort === 0 ? a.name.localeCompare(b.name) : dateSort;
  });

export const liveCurrentEvents = (events: CurrentEventScore[] = currentEventScoreFeed.events) =>
  sortCurrentEvents(events).filter((event) => event.status === 'live' || event.status === 'provisional');

export const currentEventLeaderCount = (events: CurrentEventScore[] = currentEventScoreFeed.events) =>
  events.reduce((total, event) => total + event.leaders.length, 0);

export const formatCollectedAt = (collectedAt: string) =>
  new Intl.DateTimeFormat('en', {
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    month: 'short',
    timeZone: 'UTC',
    timeZoneName: 'short',
    year: 'numeric',
  }).format(new Date(collectedAt));
