import { describe, expect, it } from 'vitest';
import { filterLiveResults, parseLiveResultsFeed } from './liveResults';

const liveFeed = {
  collected_at: '2026-05-16T17:00:00Z',
  source: {
    id: 'data_fei',
    name: 'FEI Database',
  },
  results: [
    {
      source_record_id: 'fei-2',
      rider_name: 'Blair Morgan',
      horse_name: 'North Star',
      event_name: 'May International Horse Trials',
      event_date: '2026-05-16',
      level: 'CCI3*-S',
      country: 'GBR',
      dressage_score: 31.6,
      show_jumping_penalties: 0,
      cross_country_jump_penalties: 0,
      cross_country_time_penalties: 4.4,
      status: 'in progress',
    },
    {
      id: 'local-1',
      sourceId: 'usea',
      sourceName: 'United States Eventing Association results',
      rider: 'Avery Stone',
      horse: 'Juniper',
      eventName: 'Current Spring Horse Trials',
      eventDate: '2026-05-16',
      level: 'Training',
      country: 'USA',
      dressagePenalties: 29.2,
      showJumpingPenalties: 4,
      crossCountryJumpPenalties: 0,
      crossCountryTimePenalties: 0,
      status: 'provisional',
    },
  ],
};

describe('live results feed', () => {
  it('normalizes feed results and sorts the live leaderboard by penalties', () => {
    const snapshot = parseLiveResultsFeed(liveFeed, '/live-results.json');

    expect(snapshot.endpoint).toBe('/live-results.json');
    expect(snapshot.collectedAt).toBe('2026-05-16T17:00:00Z');
    expect(snapshot.results.map((result) => result.horse)).toEqual(['Juniper', 'North Star']);
    expect(snapshot.results[0]).toMatchObject({
      sourceId: 'usea',
      sourceName: 'United States Eventing Association results',
      rider: 'Avery Stone',
      score: {
        dressagePenalties: 29.2,
        showJumpingPenalties: 4,
        crossCountryJumpPenalties: 0,
        crossCountryTimePenalties: 0,
        totalPenalties: 33.2,
      },
      status: 'provisional',
    });
    expect(snapshot.results[1].status).toBe('in_progress');
  });

  it('filters live results by horse, rider, event, level, or country', () => {
    const snapshot = parseLiveResultsFeed(liveFeed);

    expect(filterLiveResults(snapshot.results, 'juniper').map((result) => result.rider)).toEqual(['Avery Stone']);
    expect(filterLiveResults(snapshot.results, 'CCI3').map((result) => result.horse)).toEqual(['North Star']);
    expect(filterLiveResults(snapshot.results, 'usa').map((result) => result.horse)).toEqual(['Juniper']);
  });
});
