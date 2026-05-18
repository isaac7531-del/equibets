import { describe, expect, it, vi } from 'vitest';
import { fetchLiveScoringFeed, formatFeedUpdatedAt, normalizeLiveScoringFeed } from './liveScoring';

describe('live scoring feed', () => {
  it('normalizes current event leaderboards', () => {
    const feed = normalizeLiveScoringFeed({
      version: 1,
      feed_type: 'current_event_live_scoring',
      updated_at: '2026-05-18T20:00:00+00:00',
      date_window: {
        start_date: '2026-05-14',
        end_date: '2026-05-19',
      },
      source_ids: ['data_fei'],
      summary: {
        result_count: 1,
        leaderboard_count: 1,
      },
      events: [
        {
          event_key: 'spring-international',
          event_name: 'Spring International',
          event_date: '2026-05-18',
          level: 'CCI2',
          country: 'GBR',
          leader_count: 1,
          leaders: [
            {
              rank: 1,
              rider_name: 'Blair Smith',
              horse_name: 'Juniper',
              finishing_score: 29,
              dressage_score: 29,
              show_jumping_penalties: 0,
              cross_country_jump_penalties: 0,
              cross_country_time_penalties: 0,
              source_id: 'data_fei',
              source_record_id: 'fei-1',
              collected_at: '2026-05-18T20:00:00+00:00',
            },
          ],
        },
      ],
    });

    expect(feed.summary.result_count).toBe(1);
    expect(feed.events[0].leaders[0].horse_name).toBe('Juniper');
  });

  it('fetches the public feed without browser caching', async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        events: [],
        summary: {
          result_count: 0,
          leaderboard_count: 0,
        },
      }),
    });

    await expect(fetchLiveScoringFeed(fetcher)).resolves.toMatchObject({
      summary: {
        result_count: 0,
        leaderboard_count: 0,
      },
    });
    expect(fetcher).toHaveBeenCalledWith('/current_event_scores.json', { cache: 'no-store' });
  });

  it('formats the feed update timestamp in UTC', () => {
    expect(formatFeedUpdatedAt('2026-05-18T20:03:00+00:00')).toBe('2026-05-18 20:03 UTC');
  });
});
