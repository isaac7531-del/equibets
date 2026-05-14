import { describe, expect, it } from 'vitest';
import { getLiveScoreRows, liveScoringFeed, phaseTotal } from './liveScoring';

describe('live scoring feed', () => {
  it('loads current-event rows from the seeded public-results feed', () => {
    expect(liveScoringFeed.events).toHaveLength(2);
    expect(liveScoringFeed.events[0].source_id).toBe('usea');
  });

  it('ranks live rows by lowest current finishing score', () => {
    expect(getLiveScoreRows(3).map((score) => score.horse_name)).toEqual([
      'Weekapaug Groove',
      'Lost at Sea',
      'Hacker',
    ]);
  });

  it('keeps phase totals aligned with source totals', () => {
    const score = liveScoringFeed.events[0].scores.find((row) => row.horse_name === 'EHF Casiro Royale');

    expect(score).toBeDefined();
    expect(phaseTotal(score!)).toBe(46.3);
  });
});
