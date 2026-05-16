import { describe, expect, it } from 'vitest';
import {
  calculatePenaltyScore,
  calculateScore,
  formatSeconds,
  parseTimeToSeconds,
  sortByBestScore,
  type StoredResult,
} from './scoring';

describe('eventing scoring', () => {
  it('calculates dressage and time penalties in tenths', () => {
    expect(
      calculateScore({
        dressagePercentage: 68.7,
        showJumpingPenalties: 4,
        crossCountryJumpPenalties: 20,
        optimumTimeSeconds: 330,
        actualTimeSeconds: 338,
      }),
    ).toEqual({
      dressagePenalties: 31.3,
      showJumpingPenalties: 4,
      crossCountryJumpPenalties: 20,
      crossCountryTimePenalties: 3.2,
      totalPenalties: 58.5,
    });
  });

  it('does not add cross-country time penalties when under optimum', () => {
    expect(
      calculateScore({
        dressagePercentage: 72,
        showJumpingPenalties: 0,
        crossCountryJumpPenalties: 0,
        optimumTimeSeconds: 330,
        actualTimeSeconds: 326,
      }).totalPenalties,
    ).toBe(28);
  });

  it('calculates live scores from phase penalties', () => {
    expect(
      calculatePenaltyScore({
        dressagePenalties: 29.24,
        showJumpingPenalties: 4,
        crossCountryJumpPenalties: 0,
        crossCountryTimePenalties: 1.63,
      }),
    ).toEqual({
      dressagePenalties: 29.2,
      showJumpingPenalties: 4,
      crossCountryJumpPenalties: 0,
      crossCountryTimePenalties: 1.6,
      totalPenalties: 34.8,
    });
  });

  it('parses and formats course times', () => {
    expect(parseTimeToSeconds(5, 7)).toBe(307);
    expect(formatSeconds(307)).toBe('5:07');
  });

  it('sorts saved scores from best to highest penalties', () => {
    const baseResult = {
      rider: 'Rider',
      horse: 'Horse',
      eventName: 'Event',
      date: '2026-05-13',
      notes: '',
      dressagePercentage: 70,
      showJumpingPenalties: 0,
      crossCountryJumpPenalties: 0,
      optimumTimeSeconds: 300,
      actualTimeSeconds: 300,
    };
    const results = [
      {
        ...baseResult,
        id: '2',
        createdAt: '2026-05-13T10:00:01.000Z',
        score: calculateScore({ ...baseResult, dressagePercentage: 65 }),
      },
      {
        ...baseResult,
        id: '1',
        createdAt: '2026-05-13T10:00:00.000Z',
        score: calculateScore({ ...baseResult, dressagePercentage: 70 }),
      },
    ] satisfies StoredResult[];

    expect(sortByBestScore(results).map((result) => result.id)).toEqual(['1', '2']);
  });
});
