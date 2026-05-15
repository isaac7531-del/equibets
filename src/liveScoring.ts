export type CurrentEventStatus = 'entries' | 'ride_times' | 'results';

export type CurrentEventScore = {
  source_id: string;
  source_event_id: string;
  source_priority: number;
  event_name: string;
  start_date: string;
  end_date: string;
  country: string;
  status: CurrentEventStatus;
  scoring_url: string;
  collected_at: string;
};

const statusLabels: Record<CurrentEventStatus, string> = {
  entries: 'Entries',
  ride_times: 'Ride times',
  results: 'Results',
};

export const liveStatusLabel = (status: CurrentEventStatus) => statusLabels[status];

export const formatEventDateRange = (event: CurrentEventScore) => {
  const start = formatDateOnly(event.start_date);
  const end = formatDateOnly(event.end_date);

  return event.start_date === event.end_date ? start : `${start} - ${end}`;
};

export const getCurrentLiveEvents = (
  events: CurrentEventScore[],
  today: Date,
  lookbackDays = 7,
  lookaheadDays = 21,
) => {
  const todayTime = dateOnlyTime(today);
  const earliest = todayTime - lookbackDays * 24 * 60 * 60 * 1000;
  const latest = todayTime + lookaheadDays * 24 * 60 * 60 * 1000;

  return events
    .filter((event) => dateOnlyStringTime(event.end_date) >= earliest && dateOnlyStringTime(event.start_date) <= latest)
    .sort((a, b) => {
      const stateDifference = liveEventStateRank(a, today) - liveEventStateRank(b, today);
      if (stateDifference !== 0) {
        return stateDifference;
      }

      const dateDifference = dateOnlyStringTime(a.start_date) - dateOnlyStringTime(b.start_date);
      if (dateDifference !== 0) {
        return dateDifference;
      }

      return a.event_name.localeCompare(b.event_name);
    });
};

export const isLiveScoringReady = (event: CurrentEventScore) => event.status === 'ride_times' || event.status === 'results';

export const formatFeedDate = (isoDate: string) =>
  new Intl.DateTimeFormat('en', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'UTC',
  }).format(new Date(isoDate));

const liveEventStateRank = (event: CurrentEventScore, today: Date) => {
  const todayTime = dateOnlyTime(today);
  const startTime = dateOnlyStringTime(event.start_date);
  const endTime = dateOnlyStringTime(event.end_date);

  if (startTime <= todayTime && todayTime <= endTime) {
    return 0;
  }
  if (event.status === 'ride_times') {
    return 1;
  }
  if (event.status === 'results') {
    return 2;
  }
  return 3;
};

const formatDateOnly = (dateString: string) =>
  new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(`${dateString}T00:00:00Z`));

const dateOnlyStringTime = (dateString: string) => new Date(`${dateString}T00:00:00Z`).getTime();

const dateOnlyTime = (date: Date) =>
  Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
