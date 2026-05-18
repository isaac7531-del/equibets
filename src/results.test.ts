import { describe, expect, it } from 'vitest';
import {
  combinationKey,
  consolidateResults,
  finishingScore,
  predictFinishingScore,
  resultFromStoredResult,
  type EventingResultRecord,
} from './results';
import { calculateScore, type StoredResult } from './scoring';

const result = (overrides: Partial<EventingResultRecord> = {}): EventingResultRecord => ({
  sourceId: 'data_fei',
  sourceRecordId: 'fei-1',
  sourcePriority: 0,
  riderName: 'Alex Rider',
  horseName: 'Pocket Rocket',
  eventName: 'Spring Horse Trials',
  eventDate: '2026-03-01',
  level: 'CCI2-S',
  country: 'GBR',
  dressageScore: 30.2,
  showJumpingPenalties: 4,
  crossCountryJumpPenalties: 0,
  crossCountryTimePenalties: 1.6,
  collectedAt: '2026-03-08T00:00:00.000Z',
  isUserEntered: false,
  ...overrides,
});

describe('result consolidation and prediction', () => {
  it('adds all phase penalties for a finishing score', () => {
    expect(finishingScore(result())).toBe(35.8);
  });

  it('keeps official source data ahead of duplicate user scores', () => {
    const userScore = result({
      sourceId: 'user_submission',
      sourceRecordId: 'user-1',
      sourcePriority: 100,
      dressageScore: 31,
      collectedAt: '2026-03-09T00:00:00.000Z',
      isUserEntered: true,
    });

    expect(consolidateResults([userScore, result()])).toHaveLength(1);
    expect(consolidateResults([userScore, result()])[0].sourceId).toBe('data_fei');
  });

  it('predicts likely score from recent consolidated starts', () => {
    const results = [
      result({ sourceRecordId: 'fei-1', eventDate: '2026-01-01', dressageScore: 32 }),
      result({ sourceRecordId: 'fei-2', eventDate: '2026-02-01', dressageScore: 30 }),
      result({
        sourceId: 'user_submission',
        sourceRecordId: 'user-3',
        sourcePriority: 100,
        eventName: 'Local Combined Training',
        eventDate: '2026-03-01',
        dressageScore: 29,
        showJumpingPenalties: 0,
        collectedAt: '2026-03-04T00:00:00.000Z',
        isUserEntered: true,
      }),
    ];

    const prediction = predictFinishingScore(results, combinationKey(result()));

    expect(prediction?.recentResultCount).toBe(3);
    expect(prediction?.confidence).toBe('medium');
    expect(prediction?.sourceIds).toEqual(['data_fei', 'user_submission']);
    expect(prediction?.likelyFinishingScore).toBe(33.4);
  });

  it('converts locally saved calculator results into consolidated records', () => {
    const savedResult: StoredResult = {
      id: 'local-1',
      rider: 'Avery Stone',
      horse: 'Juniper',
      eventName: 'Spring Horse Trials',
      date: '2026-05-18',
      level: 'Training',
      country: 'USA',
      notes: '',
      dressagePercentage: 70,
      showJumpingPenalties: 4,
      crossCountryJumpPenalties: 0,
      optimumTimeSeconds: 300,
      actualTimeSeconds: 300,
      createdAt: '2026-05-18T12:00:00.000Z',
      score: calculateScore({
        dressagePercentage: 70,
        showJumpingPenalties: 4,
        crossCountryJumpPenalties: 0,
        optimumTimeSeconds: 300,
        actualTimeSeconds: 300,
      }),
    };

    expect(resultFromStoredResult(savedResult)).toMatchObject({
      sourceId: 'user_submission',
      riderName: 'Avery Stone',
      horseName: 'Juniper',
      dressageScore: 30,
    });
  });
});
