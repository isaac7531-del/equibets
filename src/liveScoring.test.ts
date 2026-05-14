import { describe, expect, it } from 'vitest';
import {
  buildLiveScoringSummary,
  rankLiveScoredStarts,
  sortCurrentEvents,
  type CurrentEvent,
  type LiveScoredStart,
  type LiveScoringSnapshot,
} from './liveScoring';

const baseEvent = {
  dateRange: '2026-05-16',
  location: 'Fresno, CA',
  country: 'US',
  sourceId: 'startbox',
  sourceUrl: 'https://example.com/event',
  sourceLabel: 'Times',
};

const baseStart = {
  eventId: 'ram-tap',
  level: 'Training',
  rider: 'Avery Stone',
  horse: 'Juniper',
  phase: 'cross_country',
  dressagePenalties: 30.1,
  showJumpingPenalties: 0,
  crossCountryJumpPenalties: 0,
  crossCountryTimePenalties: 0,
  updatedAt: '2026-05-16T18:00:00.000Z',
  sourceId: 'startbox',
} satisfies Omit<LiveScoredStart, 'id' | 'totalPenalties'>;

describe('live scoring', () => {
  it('ranks live starts by lowest total penalties', () => {
    const starts = [
      {
        ...baseStart,
        id: 'second',
        horse: 'Oakleaf',
        totalPenalties: 31.4,
      },
      {
        ...baseStart,
        id: 'first',
        totalPenalties: 28.9,
      },
    ] satisfies LiveScoredStart[];

    expect(rankLiveScoredStarts(starts).map((start) => [start.id, start.rank])).toEqual([
      ['first', 1],
      ['second', 2],
    ]);
  });

  it('sorts live events before upcoming and completed events', () => {
    const events = [
      {
        ...baseEvent,
        id: 'completed',
        name: 'Completed Event',
        status: 'completed',
      },
      {
        ...baseEvent,
        id: 'upcoming',
        name: 'Upcoming Event',
        status: 'upcoming',
      },
      {
        ...baseEvent,
        id: 'live',
        name: 'Live Event',
        status: 'live',
      },
    ] satisfies CurrentEvent[];

    expect(sortCurrentEvents(events).map((event) => event.id)).toEqual(['live', 'upcoming', 'completed']);
  });

  it('summarizes fetched events and grouped starts', () => {
    const snapshot = {
      version: 1,
      generatedAt: '2026-05-14T22:02:00.000Z',
      searchQuery: 'eventing scores',
      statusMessage: 'Pulled live scores.',
      sources: [
        {
          sourceId: 'startbox',
          name: 'StartBox',
          url: 'https://example.com',
          fetchedAt: '2026-05-14T22:03:00.000Z',
        },
      ],
      events: [
        {
          ...baseEvent,
          id: 'ram-tap',
          name: 'Ram Tap May SHT',
          status: 'live',
        },
      ],
      scoredStarts: [
        {
          ...baseStart,
          id: 'first',
          totalPenalties: 28.9,
        },
      ],
    } satisfies LiveScoringSnapshot;

    const summary = buildLiveScoringSummary(snapshot);

    expect(summary.statusLabel).toBe('Live scores available');
    expect(summary.latestFetchedAt).toBe('2026-05-14T22:03:00.000Z');
    expect(summary.eventSummaries[0].rankedStarts[0]).toMatchObject({
      id: 'first',
      rank: 1,
    });
  });
});
