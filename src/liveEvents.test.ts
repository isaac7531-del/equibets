import { describe, expect, it } from 'vitest';
import {
  loadCurrentEventResults,
  parseCurrentEventPayload,
  searchLiveResults,
  toStoredResult,
  type CurrentEventsPayload,
} from './liveEvents';

const payload = {
  version: 1,
  generatedAt: '2026-05-15T19:00:00.000Z',
  results: [
    {
      id: 'live-1',
      rider: 'Mira Bennett',
      horse: 'Willow Run',
      eventName: 'Current Eventing Trial',
      date: '2026-05-15',
      level: 'CCI2-L',
      country: 'USA',
      dressagePercentage: 71.2,
      showJumpingPenalties: 0,
      crossCountryJumpPenalties: 0,
      optimumTimeSeconds: 342,
      actualTimeSeconds: 348,
      sourceId: 'equibets_current_events',
      sourceName: 'Equibets current events feed',
      status: 'provisional',
      phase: 'cross_country',
      collectedAt: '2026-05-15T18:55:00.000Z',
    },
    {
      id: 'live-2',
      rider: 'Avery Stone',
      horse: 'Juniper',
      eventName: 'Current Eventing Trial',
      date: '2026-05-15',
      level: 'CCI2-L',
      country: 'USA',
      dressagePercentage: 69.8,
      showJumpingPenalties: 4,
      crossCountryJumpPenalties: 0,
      optimumTimeSeconds: 342,
      actualTimeSeconds: 342,
      sourceId: 'equibets_current_events',
      sourceName: 'Equibets current events feed',
      status: 'in_progress',
      phase: 'show_jumping',
      collectedAt: '2026-05-15T18:48:00.000Z',
    },
  ],
} satisfies CurrentEventsPayload;

describe('live current-event results', () => {
  it('loads and scores a current-events feed', async () => {
    const fetcher = async () => ({
      ok: true,
      status: 200,
      json: async () => payload,
    });

    const results = await loadCurrentEventResults(fetcher);

    expect(results.map((result) => result.id)).toEqual(['live-1', 'live-2']);
    expect(results[0].score).toMatchObject({
      dressagePenalties: 28.8,
      crossCountryTimePenalties: 2.4,
      totalPenalties: 31.2,
    });
  });

  it('searches across horse, rider, event, and source fields', () => {
    const results = parseCurrentEventPayload(payload);

    expect(searchLiveResults(results, 'willow mira')).toHaveLength(1);
    expect(searchLiveResults(results, 'current cci2 usa')).toHaveLength(2);
    expect(searchLiveResults(results, 'missing')).toHaveLength(0);
  });

  it('maps pulled live results into saved result records', () => {
    const [liveResult] = parseCurrentEventPayload(payload);

    const storedResult = toStoredResult(liveResult, {
      id: 'stored-live-1',
      createdAt: '2026-05-15T19:05:00.000Z',
    });

    expect(storedResult).toMatchObject({
      id: 'stored-live-1',
      horse: 'Willow Run',
      sourceId: 'equibets_current_events',
      sourceRecordId: 'live-1',
      sourceName: 'Equibets current events feed',
      status: 'provisional',
      score: { totalPenalties: 31.2 },
    });
  });

  it('rejects malformed feed payloads', () => {
    expect(() => parseCurrentEventPayload({ results: [{ id: 'missing-fields' }] })).toThrow(
      /missing a results array/i,
    );
  });
});
