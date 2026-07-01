import { describe, expect, it } from 'vitest';
import { latestUpcomingEventRefresh, upcomingEvents } from './upcomingEvents';

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
});
