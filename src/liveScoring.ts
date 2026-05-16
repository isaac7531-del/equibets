import currentEventFeedJson from '../data/current_event_feed.json';

export type LiveEventStatus = 'live_results' | 'ride_times' | 'recent_results' | 'entries' | 'listed';

export type LiveEventDivision = {
  name: string;
  phase: string;
};

export type LiveEvent = {
  id: string;
  source_id: string;
  source_name: string;
  source_priority: number;
  event_name: string;
  start_date: string;
  end_date: string;
  location: string;
  country: string;
  status: LiveEventStatus;
  status_label: string;
  scoring_url: string;
  last_observed_at: string;
  notes: string;
  divisions: LiveEventDivision[];
};

export type LiveEventFeed = {
  version: number;
  generated_at: string;
  coverage_window: {
    from: string;
    through: string;
  };
  sources: {
    id: string;
    name: string;
    url: string;
    observed: string;
  }[];
  events: LiveEvent[];
};

export type LiveEventSummary = {
  activeResultCount: number;
  upcomingCount: number;
  recentResultCount: number;
  latestObservedAt: string;
};

const statusRank: Record<LiveEventStatus, number> = {
  live_results: 0,
  ride_times: 1,
  recent_results: 2,
  entries: 3,
  listed: 4,
};

const statusCopy: Record<LiveEventStatus, string> = {
  live_results: 'Live results',
  ride_times: 'Ride times',
  recent_results: 'Recent results',
  entries: 'Entries',
  listed: 'Listed',
};

export const currentEventFeed = currentEventFeedJson as LiveEventFeed;

export const sortLiveEvents = (events: LiveEvent[]) =>
  [...events].sort((a, b) => {
    const statusDifference = statusRank[a.status] - statusRank[b.status];
    if (statusDifference !== 0) {
      return statusDifference;
    }

    if (a.start_date !== b.start_date) {
      return a.start_date.localeCompare(b.start_date);
    }

    return a.event_name.localeCompare(b.event_name);
  });

export const summarizeLiveEvents = (events: LiveEvent[]): LiveEventSummary => ({
  activeResultCount: events.filter((event) => event.status === 'live_results' || event.status === 'ride_times').length,
  upcomingCount: events.filter((event) => event.status === 'entries').length,
  recentResultCount: events.filter((event) => event.status === 'recent_results').length,
  latestObservedAt: events
    .map((event) => event.last_observed_at)
    .sort()
    .at(-1) ?? '',
});

export const statusLabel = (status: LiveEventStatus) => statusCopy[status];

export const formatEventDateRange = (event: Pick<LiveEvent, 'start_date' | 'end_date'>) => {
  if (event.start_date === event.end_date) {
    return formatDate(event.start_date);
  }

  return `${formatDate(event.start_date)} - ${formatDate(event.end_date)}`;
};

export const formatObservedAt = (isoDate: string) => {
  if (!isoDate) {
    return 'Not refreshed yet';
  }

  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'UTC',
  }).format(new Date(isoDate));
};

const formatDate = (isoDate: string) =>
  new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(`${isoDate}T00:00:00Z`));
