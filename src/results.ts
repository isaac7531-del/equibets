import type { StoredResult } from './scoring';

export const USER_ENTERED_PRIORITY = 100;

export type EventingResultRecord = {
  sourceId: string;
  sourceRecordId: string;
  sourcePriority: number;
  riderName: string;
  horseName: string;
  eventName: string;
  eventDate: string;
  level: string;
  country: string;
  dressageScore: number;
  showJumpingPenalties: number;
  crossCountryJumpPenalties: number;
  crossCountryTimePenalties: number;
  collectedAt: string;
  isUserEntered: boolean;
};

export type CombinationPrediction = {
  riderName: string;
  horseName: string;
  likelyFinishingScore: number;
  recentResultCount: number;
  bestRecentScore: number;
  worstRecentScore: number;
  sourceIds: string[];
  confidence: 'low' | 'medium' | 'high';
};

export const SOURCE_LABELS: Record<string, string> = {
  data_fei: 'FEI',
  british_eventing: 'British Eventing',
  equestrian_australia: 'Equestrian Australia',
  equestrian_sports_new_zealand: 'ESNZ',
  usea: 'USEA',
  user_submission: 'My score',
};

export const roundToTenths = (value: number) => Math.round(value * 10) / 10;

export const finishingScore = (result: EventingResultRecord) =>
  roundToTenths(
    result.dressageScore +
      result.showJumpingPenalties +
      result.crossCountryJumpPenalties +
      result.crossCountryTimePenalties,
  );

export const slug = (value: string) => value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');

export const combinationKey = (result: Pick<EventingResultRecord, 'riderName' | 'horseName'>) =>
  `${slug(result.riderName)}::${slug(result.horseName)}`;

export const resultKey = (result: EventingResultRecord) =>
  `${combinationKey(result)}::${slug(result.eventName)}::${result.eventDate}::${slug(result.level)}`;

export const consolidateResults = (results: EventingResultRecord[]) => {
  const selected = new Map<string, EventingResultRecord>();

  for (const result of results) {
    const key = resultKey(result);
    const existing = selected.get(key);

    if (!existing || isBetterResult(result, existing)) {
      selected.set(key, result);
    }
  }

  return [...selected.values()].sort((a, b) => {
    if (a.eventDate !== b.eventDate) {
      return b.eventDate.localeCompare(a.eventDate);
    }

    return `${a.riderName} ${a.horseName}`.localeCompare(`${b.riderName} ${b.horseName}`);
  });
};

export const resultFromStoredResult = (result: StoredResult): EventingResultRecord => ({
  sourceId: 'user_submission',
  sourceRecordId: result.id,
  sourcePriority: USER_ENTERED_PRIORITY,
  riderName: result.rider,
  horseName: result.horse,
  eventName: result.eventName,
  eventDate: result.date,
  level: result.level || 'Unspecified',
  country: result.country || 'N/A',
  dressageScore: result.score.dressagePenalties,
  showJumpingPenalties: result.score.showJumpingPenalties,
  crossCountryJumpPenalties: result.score.crossCountryJumpPenalties,
  crossCountryTimePenalties: result.score.crossCountryTimePenalties,
  collectedAt: result.createdAt,
  isUserEntered: true,
});

export const predictFinishingScore = (
  results: EventingResultRecord[],
  targetCombinationKey: string,
  recentResultLimit = 5,
): CombinationPrediction | null => {
  const recentResults = consolidateResults(results)
    .filter((result) => combinationKey(result) === targetCombinationKey)
    .sort((a, b) => b.eventDate.localeCompare(a.eventDate))
    .slice(0, recentResultLimit);

  if (recentResults.length === 0) {
    return null;
  }

  let weightedScoreTotal = 0;
  let weightTotal = 0;
  for (const [index, result] of recentResults.entries()) {
    const weight = recentResults.length - index;
    weightedScoreTotal += finishingScore(result) * weight;
    weightTotal += weight;
  }

  const scores = recentResults.map(finishingScore);
  return {
    riderName: recentResults[0].riderName,
    horseName: recentResults[0].horseName,
    likelyFinishingScore: roundToTenths(weightedScoreTotal / weightTotal),
    recentResultCount: recentResults.length,
    bestRecentScore: Math.min(...scores),
    worstRecentScore: Math.max(...scores),
    sourceIds: [...new Set(recentResults.map((result) => result.sourceId))].sort(),
    confidence: confidence(recentResults.length),
  };
};

export const combinationOptions = (results: EventingResultRecord[]) =>
  [...new Map(results.map((result) => [combinationKey(result), result])).entries()]
    .map(([key, result]) => ({
      key,
      label: `${result.horseName} / ${result.riderName}`,
    }))
    .sort((a, b) => a.label.localeCompare(b.label));

export const filterResults = (results: EventingResultRecord[], query: string) => {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) {
    return results;
  }

  return results.filter((result) =>
    [
      result.horseName,
      result.riderName,
      result.eventName,
      result.level,
      result.country,
      SOURCE_LABELS[result.sourceId] ?? result.sourceId,
    ]
      .join(' ')
      .toLowerCase()
      .includes(normalizedQuery),
  );
};

export const latestCollectedAt = (results: EventingResultRecord[]) =>
  results.reduce<string | null>((latest, result) => {
    if (!latest || result.collectedAt > latest) {
      return result.collectedAt;
    }

    return latest;
  }, null);

const isBetterResult = (candidate: EventingResultRecord, existing: EventingResultRecord) => {
  if (candidate.sourcePriority !== existing.sourcePriority) {
    return candidate.sourcePriority < existing.sourcePriority;
  }
  if (candidate.isUserEntered !== existing.isUserEntered) {
    return !candidate.isUserEntered;
  }

  return candidate.collectedAt > existing.collectedAt;
};

const confidence = (resultCount: number): CombinationPrediction['confidence'] => {
  if (resultCount >= 5) {
    return 'high';
  }
  if (resultCount >= 3) {
    return 'medium';
  }
  return 'low';
};
