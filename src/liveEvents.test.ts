import { describe, expect, it } from 'vitest';
import {
  currentEvents,
  filterCurrentEvents,
  liveEventsWithScores,
  rankedLiveResults,
  topLiveResults,
  type LiveEventResult,
} from './liveEvents';

describe('live current events', () => {
  it('loads pulled live scoring events before upcoming events', () => {
    expect(liveEventsWithScores().map((event) => event.id)).toEqual([
      'marbach-ccio4-nc-s-2026',
      'belsay-international-cci4s-2026',
    ]);
    expect(currentEvents.at(-1)?.id).toBe('millstreet-international-2026');
  });

  it('filters by horse, rider, event, and source fields', () => {
    expect(filterCurrentEvents('gypsie').map((event) => event.id)).toEqual(['belsay-international-cci4s-2026']);
    expect(filterCurrentEvents('rechenstelle').map((event) => event.id)).toEqual([
      'marbach-ccio4-nc-s-2026',
      'millstreet-international-2026',
    ]);
  });

  it('ranks available live scores ahead of missing scores', () => {
    const results = [
      {
        place: '',
        start_number: null,
        rider_name: 'Pending Rider',
        horse_name: 'Pending Horse',
        country: 'GBR',
        dressage_score: null,
        show_jumping_penalties: null,
        cross_country_jump_penalties: null,
        cross_country_time_penalties: null,
        total_penalties: null,
        phase: 'start times',
      },
      {
        place: '1st',
        start_number: 1,
        rider_name: 'Scored Rider',
        horse_name: 'Scored Horse',
        country: 'GBR',
        dressage_score: 27.1,
        show_jumping_penalties: null,
        cross_country_jump_penalties: null,
        cross_country_time_penalties: null,
        total_penalties: 27.1,
        phase: 'dressage',
      },
    ] satisfies LiveEventResult[];

    expect(rankedLiveResults(results)[0].rider_name).toBe('Scored Rider');
  });

  it('returns the top live rows for an event', () => {
    const belsay = currentEvents.find((event) => event.id === 'belsay-international-cci4s-2026');

    expect(belsay).toBeDefined();
    expect(topLiveResults(belsay!, 2).map((result) => result.total_penalties)).toEqual([28.8, 28.8]);
  });
});
