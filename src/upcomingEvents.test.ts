import { describe, expect, it } from 'vitest';
import { currentEvents, eventStatus, latestUpcomingEventRefresh, upcomingEvents, type UpcomingEventRecord } from './upcomingEvents';

describe('upcomingEvents', () => {
  it('ships normalized upcoming event records', () => {
    expect(upcomingEvents.length).toBeGreaterThan(0);
    expect(upcomingEvents[0]).toMatchObject({
      sourceId: 'data_fei',
      discipline: 'Eventing',
    });
  });

  it('reports latest refresh timestamp', () => {
    expect(latestUpcomingEventRefresh(upcomingEvents)).toBe('2026-04-22T08:00:00.000Z');
    expect(latestUpcomingEventRefresh([])).toBeNull();
  });

  it('marks current event rows as live on dates inside their event window', () => {
    const event: UpcomingEventRecord = {
      sourceId: 'data_fei',
      sourceEventId: 'fei-live',
      sourcePriority: 0,
      name: 'Aachen Live',
      startDate: '2026-07-10',
      endDate: '2026-07-12',
      country: 'GER',
      discipline: 'Eventing',
      level: 'CCI4*-S',
      sourceUrl: 'https://data.fei.org/Calendar/EventDetail.aspx?event=live',
      collectedAt: '2026-07-11T12:00:00Z',
    };

    expect(eventStatus(event, new Date('2026-07-11T12:00:00Z'))).toBe('live');
    expect(eventStatus(event, new Date('2026-07-09T12:00:00Z'))).toBe('upcoming');
    expect(eventStatus(event, new Date('2026-07-13T12:00:00Z'))).toBe('complete');
    expect(currentEvents([event], new Date('2026-07-11T12:00:00Z'))).toEqual([event]);
  });
});
