import { describe, expect, it } from 'vitest';
import {
  currentEventLeaderCount,
  currentEventScoreFeed,
  formatCollectedAt,
  liveCurrentEvents,
  sortCurrentEvents,
  type CurrentEventScore,
} from './currentEvents';

describe('current event score feed', () => {
  it('loads current public eventing scores with source metadata', () => {
    expect(currentEventScoreFeed.collected_at).toBe('2026-05-17T01:02:23.610Z');
    expect(currentEventScoreFeed.events.map((event) => event.id)).toContain('startbox-ramtap-sht0526');
    expect(currentEventLeaderCount()).toBe(18);
  });

  it('sorts live events ahead of older final results by event date', () => {
    const sortedEventIds = sortCurrentEvents(currentEventScoreFeed.events).map((event) => event.id);

    expect(sortedEventIds.slice(0, 2)).toEqual(['startbox-lynnleigh-sht0526', 'startbox-ramtap-sht0526']);
    expect(sortedEventIds.at(-1)).toBe('startbox-hitching-ht0526');
  });

  it('filters the current live and provisional events', () => {
    const events = [
      { id: 'final', status: 'final', date_range: '2026-05-01', name: 'Final' },
      { id: 'live', status: 'live', date_range: '2026-05-02', name: 'Live' },
    ].map(
      (event) =>
        ({
          ...event,
          leaders: [],
          location: 'US',
          notes: '',
          source_id: 'source',
          source_name: 'Source',
          source_url: 'https://example.com',
        }) as CurrentEventScore,
    );

    expect(liveCurrentEvents(events).map((event) => event.id)).toEqual(['live']);
  });

  it('formats the feed refresh time in UTC', () => {
    expect(formatCollectedAt('2026-05-17T01:02:23.610Z')).toContain('UTC');
  });
});
