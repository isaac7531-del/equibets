export type UpcomingEventRecord = {
  sourceId: string;
  sourceEventId: string;
  sourcePriority: number;
  name: string;
  startDate: string;
  endDate: string | null;
  country: string;
  discipline: string;
  level: string;
  sourceUrl: string;
  collectedAt: string;
};

export const upcomingEvents: UpcomingEventRecord[] = [
  {
    sourceId: 'data_fei',
    sourceEventId: 'fei-upcoming-badminton-2026',
    sourcePriority: 0,
    name: 'Badminton Horse Trials',
    startDate: '2026-05-01',
    endDate: '2026-05-05',
    country: 'GBR',
    discipline: 'Eventing',
    level: 'CCI5*-L',
    sourceUrl: 'https://data.fei.org/Calendar/Search.aspx',
    collectedAt: '2026-04-22T08:00:00.000Z',
  },
  {
    sourceId: 'data_fei',
    sourceEventId: 'fei-upcoming-aachen-2026',
    sourcePriority: 0,
    name: 'CHIO Aachen',
    startDate: '2026-06-26',
    endDate: '2026-07-05',
    country: 'GER',
    discipline: 'Eventing',
    level: 'CCI4*-S',
    sourceUrl: 'https://data.fei.org/Calendar/Search.aspx',
    collectedAt: '2026-04-22T08:00:00.000Z',
  },
  {
    sourceId: 'data_fei',
    sourceEventId: 'fei-upcoming-maryland-2026',
    sourcePriority: 0,
    name: 'Maryland 5 Star',
    startDate: '2026-10-15',
    endDate: '2026-10-18',
    country: 'USA',
    discipline: 'Eventing',
    level: 'CCI5*-L',
    sourceUrl: 'https://data.fei.org/Calendar/Search.aspx',
    collectedAt: '2026-04-22T08:00:00.000Z',
  },
];

export const latestUpcomingEventRefresh = (events: UpcomingEventRecord[]) =>
  events.reduce<string | null>((latest, event) => {
    if (!latest || event.collectedAt > latest) {
      return event.collectedAt;
    }

    return latest;
  }, null);

export type UpcomingEventStatus = 'live' | 'upcoming' | 'complete';

export const eventStatus = (event: UpcomingEventRecord, today = new Date()): UpcomingEventStatus => {
  const todayKey = dateKey(today);
  const startKey = event.startDate;
  const endKey = event.endDate ?? event.startDate;

  if (startKey <= todayKey && todayKey <= endKey) {
    return 'live';
  }
  if (todayKey < startKey) {
    return 'upcoming';
  }
  return 'complete';
};

export const currentEvents = (events: UpcomingEventRecord[], today = new Date()) =>
  events.filter((event) => eventStatus(event, today) === 'live');

const dateKey = (value: Date) => value.toISOString().slice(0, 10);
