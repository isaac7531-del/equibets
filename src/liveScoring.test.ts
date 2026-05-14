import { describe, expect, it } from 'vitest';
import { formatEventStatus, sortLiveScoresByBestScore, type LiveScore } from './liveScoring';

const baseScore = {
  event_id: 'event-1',
  event_name: 'Queeny Park Horse Trials',
  event_date: '2026-05-09',
  location: 'St. Louis, MO',
  country: 'USA',
  division: 'Novice',
  phase: 'Final Scores',
  source_id: 'startbox_scoring',
  source_priority: 45,
  source_url: 'https://example.com',
  collected_at: '2026-05-14T20:03:00Z',
} satisfies Omit<LiveScore, 'rider_name' | 'horse_name' | 'score'>;

describe('live scoring feed helpers', () => {
  it('sorts live scores from lowest penalties first', () => {
    const scores = [
      { ...baseScore, rider_name: 'Rider B', horse_name: 'Horse B', score: 31.2 },
      { ...baseScore, rider_name: 'Rider A', horse_name: 'Horse A', score: 23.9 },
    ];

    expect(sortLiveScoresByBestScore(scores).map((score) => score.horse_name)).toEqual(['Horse A', 'Horse B']);
  });

  it('formats feed statuses for display', () => {
    expect(formatEventStatus('times_posted')).toBe('Times Posted');
  });
});
