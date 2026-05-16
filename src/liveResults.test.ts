import { describe, expect, it, vi } from 'vitest';
import { buildCurrentEventSearches, liveResultFromRecord, pullLiveResultsFromUrl } from './liveResults';

describe('current event live results', () => {
  it('builds source-prioritized searches with FEI first', () => {
    const searches = buildCurrentEventSearches({
      eventName: 'Badminton Horse Trials',
      rider: 'Avery Stone',
      horse: 'Juniper',
      region: 'uk',
      year: 2026,
    });

    expect(searches[0].sourceId).toBe('data_fei');
    expect(searches.map((search) => search.sourceId)).toContain('british_eventing');
    expect(searches[0].query).toContain('Badminton Horse Trials');
    expect(searches[0].query).toContain('site:data.fei.org');
  });

  it('normalizes public result records into live scores', () => {
    const liveResult = liveResultFromRecord({
      source_id: 'data_fei',
      source_record_id: 'fei-2026-1',
      rider_name: 'Avery Stone',
      horse_name: 'Juniper',
      event_name: 'Spring International',
      event_date: '2026-05-16',
      level: 'CCI3',
      country: 'GBR',
      dressage_score: 28.4,
      show_jumping_penalties: 4,
      cross_country_jump_penalties: 0,
      cross_country_time_penalties: 1.2,
      collected_at: '2026-05-16T04:00:00.000Z',
    });

    expect(liveResult.score.totalPenalties).toBe(33.6);
    expect(liveResult.sourceName).toBe('FEI Database');
    expect(liveResult.isLiveResult).toBe(true);
  });

  it('pulls and sorts live results from a JSON feed', async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        results: [
          {
            source_id: 'usea',
            source_record_id: '2',
            rider_name: 'Second Rider',
            horse_name: 'Second Horse',
            event_name: 'Current Horse Trials',
            event_date: '2026-05-16',
            dressage_score: 34,
            show_jumping_penalties: 4,
            cross_country_jump_penalties: 0,
            cross_country_time_penalties: 0,
          },
          {
            source_id: 'data_fei',
            source_record_id: '1',
            rider_name: 'Best Rider',
            horse_name: 'Best Horse',
            event_name: 'Current Horse Trials',
            event_date: '2026-05-16',
            dressage_score: 27,
            show_jumping_penalties: 0,
            cross_country_jump_penalties: 0,
            cross_country_time_penalties: 0,
          },
        ],
      }),
    });

    const liveResults = await pullLiveResultsFromUrl('https://example.com/results.json', fetcher);

    expect(fetcher).toHaveBeenCalledWith('https://example.com/results.json', {
      headers: { Accept: 'application/json' },
    });
    expect(liveResults.map((result) => result.horse)).toEqual(['Best Horse', 'Second Horse']);
  });
});
