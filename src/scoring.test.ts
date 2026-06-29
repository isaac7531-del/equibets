import { describe, expect, it } from 'vitest';
import {
  buildRiderLevelDirectory,
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
      level: 'CCI2-S',
      country: 'GBR',
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

  it('groups each rider horses by level', () => {
    const baseResult = {
      eventName: 'Event',
      date: '2026-05-13',
      country: 'USA',
      notes: '',
      dressagePercentage: 70,
      showJumpingPenalties: 0,
      crossCountryJumpPenalties: 0,
      optimumTimeSeconds: 300,
      actualTimeSeconds: 300,
      createdAt: '2026-05-13T10:00:00.000Z',
      score: calculateScore({
        dressagePercentage: 70,
        showJumpingPenalties: 0,
        crossCountryJumpPenalties: 0,
        optimumTimeSeconds: 300,
        actualTimeSeconds: 300,
      }),
    };
    const results = [
      { ...baseResult, id: '1', rider: 'Avery Stone', horse: 'Juniper', level: 'Training' },
      { ...baseResult, id: '2', rider: 'Avery Stone', horse: 'Oakley', level: 'Novice' },
      { ...baseResult, id: '3', rider: 'Avery Stone', horse: 'Juniper', level: 'Training' },
      { ...baseResult, id: '4', rider: 'Morgan Lee', horse: 'Copperfield', level: 'Preliminary' },
    ] satisfies StoredResult[];

    expect(buildRiderLevelDirectory(results, 'Avery Stone')).toEqual([
      {
        rider: 'Avery Stone',
        levels: [
          { level: 'Novice', horses: ['Oakley'] },
          { level: 'Training', horses: ['Juniper'] },
        ],
      },
    ]);
  });
});
