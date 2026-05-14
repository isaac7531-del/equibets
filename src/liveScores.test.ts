import { describe, expect, it } from 'vitest';
import { getDisplayLiveEvents, getLiveScoreSummary, normalizeLiveScoreSnapshot } from './liveScores';

const snapshot = normalizeLiveScoreSnapshot({
  version: 1,
  collected_at: '2026-05-14T23:04:00Z',
  coverage_note: 'test snapshot',
  events: [
    {
      id: 'finished-event',
      source_id: 'startbox',
      source_name: 'StartBox',
      source_url: 'https://example.com/finished',
      event_name: 'Finished Event',
      event_date: '2026-05-09',
      event_end_date: '2026-05-09',
      country: 'USA',
      level: 'national',
      status: 'completed',
      phase: 'final',
      notes: 'Final scores',
      leaders: [
        {
          division: 'Starter',
          place: 1,
          rider_name: 'Avery Stone',
          horse_name: 'Juniper',
          score: 29.4,
          phase: 'final',
        },
      ],
    },
    {
      id: 'active-event',
      source_id: 'data_fei',
      source_name: 'FEI',
      source_url: 'https://example.com/active',
      event_name: 'Active Event',
      event_date: '2026-05-14',
      event_end_date: '2026-05-17',
      country: 'GER',
      level: 'CCIO4*-NC-S',
      status: 'active',
      phase: 'scheduled',
      notes: 'No scores yet',
      leaders: [],
    },
  ],
});

describe('live score snapshots', () => {
  it('normalizes source payload fields for the app', () => {
    expect(snapshot.events[0].sourceId).toBe('startbox');
    expect(snapshot.events[0].leaders[0].horseName).toBe('Juniper');
  });

  it('summarizes events and best live leader', () => {
    expect(getLiveScoreSummary(snapshot)).toMatchObject({
      eventCount: 2,
      activeEventCount: 1,
      leaderCount: 1,
      bestLeader: {
        horseName: 'Juniper',
        score: 29.4,
      },
    });
  });

  it('displays active events first', () => {
    expect(getDisplayLiveEvents(snapshot).map((event) => event.id)).toEqual(['active-event', 'finished-event']);
  });
});
