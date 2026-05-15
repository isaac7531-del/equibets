import { describe, expect, it } from 'vitest';
import {
  formatEventDateRange,
  getCurrentLiveEvents,
  isLiveScoringReady,
  liveStatusLabel,
  type CurrentEventScore,
} from './liveScoring';

const event = (overrides: Partial<CurrentEventScore>): CurrentEventScore => ({
  source_id: 'startbox_eventing',
  source_event_id: 'event-1',
  source_priority: 55,
  event_name: 'Lynnleigh Farm May 16, 2026 Schooling 2-Phase Sandy, UT US',
  start_date: '2026-05-16',
  end_date: '2026-05-16',
  country: 'US',
  status: 'ride_times',
  scoring_url: 'https://example.com/scores',
  collected_at: '2026-05-15T08:02:00+00:00',
  ...overrides,
});

describe('live scoring helpers', () => {
  it('filters and sorts current events by live-scoring usefulness', () => {
    const currentEvents = getCurrentLiveEvents(
      [
        event({
          source_event_id: 'future-entry',
          event_name: 'Future Entries',
          start_date: '2026-05-23',
          end_date: '2026-05-23',
          status: 'entries',
        }),
        event({
          source_event_id: 'recent-result',
          event_name: 'Recent Result',
          start_date: '2026-05-10',
          end_date: '2026-05-10',
          status: 'results',
        }),
        event({
          source_event_id: 'too-old',
          event_name: 'Too Old',
          start_date: '2026-05-01',
          end_date: '2026-05-01',
          status: 'results',
        }),
        event({ source_event_id: 'ride-times', event_name: 'Ride Times' }),
      ],
      new Date('2026-05-15T08:02:00Z'),
      7,
      21,
    );

    expect(currentEvents.map((item) => item.source_event_id)).toEqual([
      'ride-times',
      'recent-result',
      'future-entry',
    ]);
  });

  it('formats event date ranges and status labels', () => {
    expect(liveStatusLabel('ride_times')).toBe('Ride times');
    expect(formatEventDateRange(event({ start_date: '2026-05-16', end_date: '2026-05-17' }))).toBe(
      'May 16 - May 17',
    );
  });

  it('treats ride times and results as scoring-ready', () => {
    expect(isLiveScoringReady(event({ status: 'ride_times' }))).toBe(true);
    expect(isLiveScoringReady(event({ status: 'results' }))).toBe(true);
    expect(isLiveScoringReady(event({ status: 'entries' }))).toBe(false);
  });
});
