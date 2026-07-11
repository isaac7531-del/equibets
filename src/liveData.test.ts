import { describe, expect, it, vi } from 'vitest';
import { loadLiveResults, loadLiveUpcomingEvents } from './liveData';

describe('liveData', () => {
  it('maps FEI result JSON into frontend result records', async () => {
    const fetcher = vi.fn(async () =>
      new Response(
        JSON.stringify({
          updated_at: '2026-07-11T12:00:00Z',
          results: [
            {
              source_id: 'data_fei',
              source_record_id: 'fei-live-1',
              source_priority: 0,
              rider_name: 'Live Rider',
              horse_name: 'Current Star',
              event_name: 'Aachen Live',
              event_date: '2026-07-11',
              level: 'CCI4*-S',
              country: 'GER',
              dressage_score: 28.4,
              show_jumping_penalties: 0,
              cross_country_jump_penalties: 0,
              cross_country_time_penalties: 1.2,
              collected_at: '2026-07-11T12:00:00Z',
              is_user_entered: false,
            },
          ],
        }),
      ),
    );

    const feed = await loadLiveResults(fetcher);

    expect(fetcher).toHaveBeenCalledWith('/data/fei_results.json', { cache: 'no-store' });
    expect(feed.updatedAt).toBe('2026-07-11T12:00:00Z');
    expect(feed.records[0]).toMatchObject({
      sourceId: 'data_fei',
      sourceRecordId: 'fei-live-1',
      riderName: 'Live Rider',
      horseName: 'Current Star',
      dressageScore: 28.4,
    });
  });

  it('maps FEI upcoming event JSON and preserves null end dates', async () => {
    const fetcher = vi.fn(async () =>
      new Response(
        JSON.stringify({
          events: [
            {
              source_id: 'data_fei',
              source_event_id: 'fei-upcoming-live',
              source_priority: 0,
              name: 'Aachen Live',
              start_date: '2026-07-11',
              end_date: null,
              country: 'GER',
              discipline: 'Eventing',
              level: 'CCI4*-S',
              source_url: 'https://data.fei.org/Calendar/EventDetail.aspx?event=live',
              collected_at: '2026-07-11T12:00:00Z',
            },
          ],
        }),
      ),
    );

    const feed = await loadLiveUpcomingEvents(fetcher);

    expect(feed.events[0]).toMatchObject({
      sourceEventId: 'fei-upcoming-live',
      name: 'Aachen Live',
      endDate: null,
    });
  });
});
