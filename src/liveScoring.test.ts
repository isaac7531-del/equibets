import { describe, expect, it } from 'vitest';
import {
  formatLiveStatus,
  normalizeCurrentEventResults,
  searchLiveResults,
  sortLiveLeaderboard,
  type RawCurrentEventResult,
} from './liveScoring';

const rawResult = (overrides: Partial<RawCurrentEventResult> = {}): RawCurrentEventResult => ({
  source_id: 'data_fei',
  source_record_id: 'fei-current-1',
  rider_name: 'Alex Rider',
  horse_name: 'Pocket Rocket',
  event_name: 'Current Spring International',
  event_date: '2026-05-15',
  level: 'CCI3',
  country: 'GBR',
  dressage_score: 28.4,
  show_jumping_penalties: 0,
  cross_country_jump_penalties: 0,
  cross_country_time_penalties: 1.2,
  collected_at: '2026-05-15T01:00:00+00:00',
  status: 'cross_country',
  ...overrides,
});

describe('live scoring', () => {
  it('normalizes current event records into scored leaderboard rows', () => {
    const [result] = normalizeCurrentEventResults([rawResult()]);

    expect(result.id).toBe('data_fei:fei-current-1');
    expect(result.score.totalPenalties).toBe(29.6);
    expect(result.division).toBe('CCI3');
  });

  it('searches live results by horse, rider, event, level, country, or status', () => {
    const results = normalizeCurrentEventResults([
      rawResult(),
      rawResult({
        source_record_id: 'fei-current-2',
        horse_name: 'Harbor Master',
        event_name: 'Coastal Horse Trials',
        status: 'dressage',
      }),
    ]);

    expect(searchLiveResults(results, 'pocket')).toHaveLength(1);
    expect(searchLiveResults(results, 'coastal')).toHaveLength(1);
    expect(searchLiveResults(results, 'dressage')[0].horse).toBe('Harbor Master');
  });

  it('sorts lower live totals first and prefers more complete status on ties', () => {
    const results = normalizeCurrentEventResults([
      rawResult({ horse_name: 'Tie Dressage', status: 'dressage', cross_country_time_penalties: 0 }),
      rawResult({ source_record_id: 'fei-current-2', horse_name: 'Tie Final', status: 'final', cross_country_time_penalties: 0 }),
      rawResult({ source_record_id: 'fei-current-3', horse_name: 'Higher Score', dressage_score: 35 }),
    ]);

    expect(sortLiveLeaderboard(results).map((result) => result.horse)).toEqual([
      'Tie Final',
      'Tie Dressage',
      'Higher Score',
    ]);
  });

  it('formats status labels for display', () => {
    expect(formatLiveStatus('cross_country')).toBe('Cross Country');
  });
});
