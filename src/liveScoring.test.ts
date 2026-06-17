import { afterEach, describe, expect, it, vi } from 'vitest';
import { formatFeedDateRange, loadLiveScoreFeed } from './liveScoring';

const liveFeed = {
  version: 1,
  source_id: 'data_fei',
  updated_at: '2026-06-17T13:00:00+00:00',
  window_start: '2026-06-16',
  window_end: '2026-06-18',
  event_count: 1,
  score_count: 1,
  events: [
    {
      event_name: 'Current Horse Trials',
      event_date: '2026-06-17',
      level: 'CCI3*-S',
      country: 'GBR',
      latest_collected_at: '2026-06-17T12:00:00+00:00',
      entry_count: 1,
      leader: {
        rank: 1,
        rider_name: 'Morgan Lee',
        horse_name: 'Copperfield',
        finishing_score: 28,
        dressage_score: 28,
        show_jumping_penalties: 0,
        cross_country_jump_penalties: 0,
        cross_country_time_penalties: 0,
        source_id: 'data_fei',
        source_record_id: 'fei-1',
        collected_at: '2026-06-17T12:00:00+00:00',
      },
      entries: [
        {
          rank: 1,
          rider_name: 'Morgan Lee',
          horse_name: 'Copperfield',
          finishing_score: 28,
          dressage_score: 28,
          show_jumping_penalties: 0,
          cross_country_jump_penalties: 0,
          cross_country_time_penalties: 0,
          source_id: 'data_fei',
          source_record_id: 'fei-1',
          collected_at: '2026-06-17T12:00:00+00:00',
        },
      ],
    },
  ],
};

describe('live scoring feed', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('loads and validates a live score feed', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue(liveFeed),
      }),
    );

    await expect(loadLiveScoreFeed()).resolves.toEqual(liveFeed);
  });

  it('returns null for missing or malformed feeds', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: vi.fn().mockResolvedValue({ version: 1, events: 'not-array' }),
      }),
    );

    await expect(loadLiveScoreFeed()).resolves.toBeNull();
  });

  it('formats live feed date windows', () => {
    expect(formatFeedDateRange(liveFeed)).toBe('2026-06-16 to 2026-06-18');
    expect(formatFeedDateRange({ window_start: null, window_end: null })).toBe('current event window');
  });
});
