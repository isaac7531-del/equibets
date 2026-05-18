import { describe, expect, it, vi } from 'vitest';
import { LIVE_SCORES_URL, fetchLiveScores, sortLiveScores, type LiveScoreResult } from './liveResults';

const baseResult = {
  source_id: 'data_fei',
  source_record_id: 'fei-1',
  rider_name: 'Alex Rider',
  horse_name: 'Pocket Rocket',
  event_name: 'Spring Horse Trials',
  event_date: '2026-05-18',
  level: 'CCI2',
  country: 'GBR',
  dressage_score: 30.2,
  show_jumping_penalties: 4,
  cross_country_jump_penalties: 0,
  cross_country_time_penalties: 1.6,
  finishing_score: 35.8,
  collected_at: '2026-05-18T12:00:00+00:00',
  is_user_entered: false,
} satisfies LiveScoreResult;

describe('live results feed', () => {
  it('fetches and normalizes the live scoring payload', async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        version: 1,
        generated_at: '2026-05-18T18:00:00+00:00',
        window: {
          start_date: '2026-05-17',
          end_date: '2026-05-19',
        },
        results: [baseResult],
      }),
    });

    const payload = await fetchLiveScores(fetcher as unknown as typeof fetch);

    expect(fetcher).toHaveBeenCalledWith(LIVE_SCORES_URL, { cache: 'no-store' });
    expect(payload?.result_count).toBe(1);
    expect(payload?.results[0].finishing_score).toBe(35.8);
  });

  it('returns null when no live scoring payload has been published', async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({}),
    });

    await expect(fetchLiveScores(fetcher as unknown as typeof fetch)).resolves.toBeNull();
  });

  it('sorts current event scores by event and lowest penalties', () => {
    const sorted = sortLiveScores([
      { ...baseResult, source_record_id: '2', rider_name: 'Zoe Rider', finishing_score: 36.1 },
      { ...baseResult, source_record_id: '1', rider_name: 'Avery Rider', finishing_score: 31.2 },
    ]);

    expect(sorted.map((result) => result.rider_name)).toEqual(['Avery Rider', 'Zoe Rider']);
  });
});
