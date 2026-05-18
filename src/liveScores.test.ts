import { describe, expect, it } from 'vitest';
import { loadLiveScoreboard, normalizeScoreboard } from './liveScores';

const payload = {
  version: 1,
  generated_at: '2026-05-18T13:00:00+00:00',
  window: {
    start_date: '2026-05-11',
    end_date: '2026-05-19',
  },
  latest_collected_at: '2026-05-18T12:00:00+00:00',
  result_count: 1,
  scores: [
    {
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
    },
  ],
};

describe('live score loading', () => {
  it('normalizes generated current-event scoreboards', () => {
    const scoreboard = normalizeScoreboard(payload);

    expect(scoreboard?.window.startDate).toBe('2026-05-11');
    expect(scoreboard?.latestCollectedAt).toBe('2026-05-18T12:00:00+00:00');
    expect(scoreboard?.scores[0].horseName).toBe('Pocket Rocket');
    expect(scoreboard?.scores[0].finishingScore).toBe(35.8);
  });

  it('returns null when live score JSON is unavailable', async () => {
    const fetcher: typeof fetch = async () => new Response('', { status: 404 });

    await expect(loadLiveScoreboard(fetcher)).resolves.toBeNull();
  });

  it('loads scoreboards through fetch', async () => {
    const fetcher: typeof fetch = async () => new Response(JSON.stringify(payload), { status: 200 });

    const scoreboard = await loadLiveScoreboard(fetcher);

    expect(scoreboard?.resultCount).toBe(1);
    expect(scoreboard?.scores[0].sourceId).toBe('data_fei');
  });
});
