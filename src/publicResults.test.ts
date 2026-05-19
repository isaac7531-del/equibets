import { describe, expect, it } from 'vitest';
import { formatPublicUpdatedAt, loadPublicResults, selectCurrentEventResults } from './publicResults';

describe('public FEI result feed', () => {
  const payload = {
    updated_at: '2026-05-19T00:01:08+00:00',
    results: [
      {
        source_id: 'data_fei',
        source_record_id: 'older',
        rider_name: 'Older Rider',
        horse_name: 'Older Horse',
        event_name: 'Earlier Horse Trials',
        event_date: '2026-04-01',
        level: 'CCI2*-S',
        country: 'GBR',
        dressage_score: 30.2,
        show_jumping_penalties: 4,
        cross_country_jump_penalties: 0,
        cross_country_time_penalties: 1.6,
        collected_at: '2026-05-19T00:01:08+00:00',
      },
      {
        source_id: 'data_fei',
        source_record_id: 'current',
        rider_name: 'Alex Rider',
        horse_name: 'Pocket Rocket',
        event_name: 'Current Horse Trials',
        event_date: '2026-05-19',
        level: 'CCI3*-S',
        country: 'USA',
        dressage_score: 31.1,
        show_jumping_penalties: 0,
        cross_country_jump_penalties: 0,
        cross_country_time_penalties: 2.4,
        collected_at: '2026-05-19T00:01:08+00:00',
      },
    ],
  };

  it('loads public results and calculates finishing scores', () => {
    const snapshot = loadPublicResults(payload);

    expect(snapshot.updatedAt).toBe('2026-05-19T00:01:08+00:00');
    expect(snapshot.results[0]).toMatchObject({
      id: 'current',
      eventName: 'Current Horse Trials',
      totalPenalties: 33.5,
    });
  });

  it('selects scores from the current event window', () => {
    const snapshot = loadPublicResults(payload);
    const currentResults = selectCurrentEventResults(snapshot.results, new Date('2026-05-19T12:00:00Z'));

    expect(currentResults.map((result) => result.id)).toEqual(['current']);
  });

  it('formats the refresh timestamp without relying on locale output', () => {
    expect(formatPublicUpdatedAt('2026-05-19T00:01:08+00:00')).toBe('2026-05-19 00:01 UTC');
    expect(formatPublicUpdatedAt(null)).toBe('No public refresh yet');
  });
});
