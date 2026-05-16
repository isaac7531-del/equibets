import { describe, expect, it } from 'vitest';
import { formatEventDateRange, sortLiveEvents, summarizeLiveEvents, type LiveEvent } from './liveScoring';

const event = (overrides: Partial<LiveEvent>): LiveEvent => ({
  id: 'event-1',
  source_id: 'startbox_scoring',
  source_name: 'StartBox/EventingScores',
  source_priority: 45,
  event_name: 'Current Horse Trial',
  start_date: '2026-05-16',
  end_date: '2026-05-16',
  location: 'Sandy, UT',
  country: 'USA',
  status: 'live_results',
  status_label: 'Results',
  scoring_url: 'https://example.com/results',
  last_observed_at: '2026-05-16T11:00:00Z',
  notes: '',
  divisions: [],
  ...overrides,
});

describe('live scoring feed helpers', () => {
  it('sorts active results, ride times, recent results, then entries', () => {
    const events = [
      event({ id: 'upcoming', event_name: 'Upcoming', status: 'entries', start_date: '2026-05-23' }),
      event({ id: 'times', event_name: 'Tomorrow', status: 'ride_times', start_date: '2026-05-17' }),
      event({ id: 'recent', event_name: 'Recent', status: 'recent_results', start_date: '2026-05-13' }),
      event({ id: 'live', event_name: 'Live', status: 'live_results', start_date: '2026-05-16' }),
    ];

    expect(sortLiveEvents(events).map((item) => item.id)).toEqual(['live', 'times', 'recent', 'upcoming']);
  });

  it('summarizes active, recent, and upcoming events', () => {
    const summary = summarizeLiveEvents([
      event({ status: 'live_results', last_observed_at: '2026-05-16T11:00:00Z' }),
      event({ status: 'ride_times', last_observed_at: '2026-05-16T11:05:00Z' }),
      event({ status: 'recent_results', last_observed_at: '2026-05-15T18:00:00Z' }),
      event({ status: 'entries', last_observed_at: '2026-05-16T10:00:00Z' }),
    ]);

    expect(summary).toEqual({
      activeResultCount: 2,
      upcomingCount: 1,
      recentResultCount: 1,
      latestObservedAt: '2026-05-16T11:05:00Z',
    });
  });

  it('formats single-day and multi-day date ranges', () => {
    expect(formatEventDateRange(event({ start_date: '2026-05-16', end_date: '2026-05-16' }))).toBe('May 16');
    expect(formatEventDateRange(event({ start_date: '2026-05-16', end_date: '2026-05-17' }))).toBe(
      'May 16 - May 17',
    );
  });
});
