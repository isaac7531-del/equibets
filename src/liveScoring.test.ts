import { describe, expect, it } from 'vitest';
import {
  calculateLiveTotal,
  currentEventFeed,
  getLiveScoringSummary,
  searchLiveScores,
  sortLiveScoresByBest,
  upcomingCurrentEvents,
} from './liveScoring';

describe('live current-events scoring', () => {
  it('calculates live totals from phase penalties', () => {
    expect(
      calculateLiveTotal({
        id: 'score-1',
        division: 'CCI5*-L',
        place: '1',
        rider: 'Rider',
        horse: 'Horse',
        dressage_penalties: 23.7,
        cross_country_jump_penalties: 0,
        cross_country_time_penalties: 0,
        show_jumping_jump_penalties: 0,
        show_jumping_time_penalties: 2,
        status: 'placed',
      }),
    ).toBe(25.7);
  });

  it('summarizes pulled scores and current watched events', () => {
    const summary = getLiveScoringSummary(currentEventFeed);

    expect(summary.resultCount).toBeGreaterThan(10);
    expect(summary.upcomingEventCount).toBe(6);
    expect(summary.bestScore?.horse).toBe('Paloma');
    expect(summary.bestScore?.totalPenalties).toBe(20.9);
  });

  it('searches live scores by combination, event, and division', () => {
    const badmintonResults = searchLiveScores(currentEventFeed.events, 'badminton');
    const trainingResults = searchLiveScores(currentEventFeed.events, 'training');
    const palomaResults = searchLiveScores(currentEventFeed.events, 'paloma');

    expect(badmintonResults.map((result) => result.eventName)).toContain('Badminton Horse Trials 2026');
    expect(trainingResults.map((result) => result.division)).toContain('Training TR');
    expect(palomaResults).toHaveLength(1);
    expect(palomaResults[0].rider).toBe('Abigail McEwen');
  });

  it('sorts scores from best to highest penalties', () => {
    const sortedScores = sortLiveScoresByBest(searchLiveScores(currentEventFeed.events, ''));

    expect(sortedScores.slice(0, 3).map((result) => result.totalPenalties)).toEqual([20.9, 25.7, 27.1]);
  });

  it('lists upcoming current events by start date', () => {
    const events = upcomingCurrentEvents(currentEventFeed.events);

    expect(events[0].name).toBe('Lynnleigh Farm May 16, 2026 Schooling 2-Phase');
    expect(events.at(-1)?.name).toBe('IEA Horse Trial');
  });
});
