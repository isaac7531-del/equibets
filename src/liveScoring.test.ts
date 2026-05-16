import { afterEach, describe, expect, it, vi } from 'vitest';
import { loadLiveScoreFeed, liveTotal, normalizeLiveFeed, searchLiveScores } from './liveScoring';

describe('live scoring feeds', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('normalizes nested current-event feeds and keeps the highest priority source', () => {
    const feed = normalizeLiveFeed({
      generated_at: '2026-05-16T19:00:00+00:00',
      events: [
        {
          source_id: 'usea',
          source_priority: 50,
          name: 'Current Spring International',
          date: '2026-05-16',
          level: 'CCI3',
          country: 'GBR',
          collected_at: '2026-05-16T18:55:00+00:00',
          results: [
            {
              source_record_id: 'usea-1',
              rider_name: 'Avery Stone',
              horse_name: 'Juniper',
              dressage_score: 31.2,
            },
            {
              source_id: 'data_fei',
              source_record_id: 'fei-1',
              source_priority: 0,
              rider_name: 'Avery Stone',
              horse_name: 'Juniper',
              dressage_score: 29.4,
              show_jumping_penalties: 4,
              phase_statuses: {
                dressage: 'complete',
                show_jumping: 'complete',
                cross_country: 'not_started',
              },
            },
          ],
        },
      ],
    });

    expect(feed.sourceIds).toEqual(['data_fei']);
    expect(feed.scores).toHaveLength(1);
    expect(feed.scores[0].sourceId).toBe('data_fei');
    expect(liveTotal(feed.scores[0])).toBe(33.4);
  });

  it('searches live rows by combination, event, and source', () => {
    const feed = normalizeLiveFeed({
      results: [
        liveRow({ source_record_id: '1', rider_name: 'Avery Stone', horse_name: 'Juniper' }),
        liveRow({ source_record_id: '2', rider_name: 'Jordan Lee', horse_name: 'River Fox', event_name: 'Autumn CCI' }),
      ],
    });

    expect(searchLiveScores(feed.scores, 'juniper spring data_fei').map((score) => score.horseName)).toEqual(['Juniper']);
  });

  it('loads and merges configured feed urls', async () => {
    const fetch = vi.fn(async (url: string) => ({
      ok: true,
      json: async () => ({
        generated_at: url.includes('two') ? '2026-05-16T19:05:00+00:00' : '2026-05-16T19:00:00+00:00',
        results: [liveRow({ source_record_id: url.includes('two') ? '2' : '1', horse_name: url.includes('two') ? 'River Fox' : 'Juniper' })],
      }),
    }));
    vi.stubGlobal('fetch', fetch);

    const feed = await loadLiveScoreFeed(['/feed-one.json', '/feed-two.json']);

    expect(fetch).toHaveBeenCalledTimes(2);
    expect(feed.generatedAt).toBe('2026-05-16T19:05:00+00:00');
    expect(feed.scores.map((score) => score.horseName)).toEqual(['Juniper', 'River Fox']);
  });
});

const liveRow = (overrides: Record<string, unknown>) => ({
  source_id: 'data_fei',
  source_record_id: 'fei-live',
  source_priority: 0,
  rider_name: 'Avery Stone',
  horse_name: 'Juniper',
  event_name: 'Spring CCI',
  event_date: '2026-05-16',
  level: 'CCI3',
  country: 'GBR',
  dressage_score: 29.4,
  collected_at: '2026-05-16T19:00:00+00:00',
  ...overrides,
});
