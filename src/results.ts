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
  riderFeiId?: string;
  horseFeiId?: string;
  combinationId?: string;
  placing?: string;
  showJumpingTimePenalties?: number;
  totalScore?: number | null;
  status?: 'completed' | 'eliminated' | 'retired' | 'withdrawn' | string;
  merStatus?: string;
  eventUrl?: string;
  sourceUrl?: string;
  venue?: string;
};

export type PredictionEvidence = {
  targetLevel: string;
  predictedDressageScore: number;
  predictedXcJumpPenalties: number;
  predictedXcTimePenalties: number;
  predictedShowJumpingPenalties: number;
  predictedShowJumpingTimePenalties: number;
  predictedFinalScoreLow: number;
  predictedFinalScoreHigh: number;
  averageDressageCurrentLevel: number | null;
  averageDressageOneLevelBelow: number | null;
  averageFinalScore: number | null;
  xcClearJumpingRate: number;
  xcTimePenaltyAverage: number;
  sjRailAverage: number;
  completionRate: number;
  eliminationRetirementRate: number;
  bestScore: number | null;
  worstScore: number | null;
  recent3RunAverage: number | null;
  recent5RunAverage: number | null;
  trendDirection: 'improving' | 'flat' | 'declining';
  levelReliability: 'proven' | 'stepping up' | 'inconsistent' | 'developing';
  countryPattern: string;
  venuePattern: string;
  sameLevelResultCount: number;
  horseResultCount: number;
  combinationResultCount: number;
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
  predictedLowScore: number;
  predictedHighScore: number;
  evidence: PredictionEvidence;
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
  result.totalScore ?? roundToTenths(
      result.dressageScore +
        result.showJumpingPenalties +
        (result.showJumpingTimePenalties ?? 0) +
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
  const evidence = buildPredictionEvidence(results, targetCombinationKey, recentResults[0].level);

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
    predictedLowScore: evidence.predictedFinalScoreLow,
    predictedHighScore: evidence.predictedFinalScoreHigh,
    evidence,
  };
};

export const buildPredictionEvidence = (
  results: EventingResultRecord[],
  targetCombinationKey: string,
  targetLevel: string,
): PredictionEvidence => {
  const consolidated = consolidateResults(results);
  const targetResult = consolidated.find((result) => combinationKey(result) === targetCombinationKey);
  const horseSlug = targetResult ? slug(targetResult.horseName) : targetCombinationKey.split('::')[1] ?? '';
  const horseResults = consolidated.filter((result) => slug(result.horseName) === horseSlug);
  const combinationResults = horseResults.filter((result) => combinationKey(result) === targetCombinationKey);
  const evidenceResults = combinationResults.length > 0 ? combinationResults : horseResults;
  const completed = evidenceResults.filter(isCompleted);
  const sameLevel = completed.filter((result) => sameLevelRank(result.level, targetLevel));
  const oneBelow = completed.filter((result) => levelRank(result.level) === levelRank(targetLevel) - 1);
  const scores = completed.map(finishingScore);
  const predictedDressage = weightedPhaseAverage(evidenceResults, targetLevel, (result) => result.dressageScore);
  const predictedXcJump = weightedPhaseAverage(evidenceResults, targetLevel, (result) => result.crossCountryJumpPenalties);
  const predictedXcTime = weightedPhaseAverage(evidenceResults, targetLevel, (result) => result.crossCountryTimePenalties);
  const predictedSjJump = weightedPhaseAverage(evidenceResults, targetLevel, (result) => result.showJumpingPenalties);
  const predictedSjTime = weightedPhaseAverage(evidenceResults, targetLevel, (result) => result.showJumpingTimePenalties ?? 0);
  const predictedTotal = predictedDressage + predictedXcJump + predictedXcTime + predictedSjJump + predictedSjTime;
  const eliminationRetirementRate = rate(
    evidenceResults.filter((result) => ['eliminated', 'retired', 'withdrawn'].includes(completionStatus(result))).length,
    evidenceResults.length,
  );
  const uncertainty = Math.max(2.5, standardDeviation(scores) + eliminationRetirementRate * 8);

  return {
    targetLevel,
    predictedDressageScore: roundToTenths(predictedDressage),
    predictedXcJumpPenalties: roundToTenths(predictedXcJump),
    predictedXcTimePenalties: roundToTenths(predictedXcTime),
    predictedShowJumpingPenalties: roundToTenths(predictedSjJump),
    predictedShowJumpingTimePenalties: roundToTenths(predictedSjTime),
    predictedFinalScoreLow: roundToTenths(Math.max(0, predictedTotal - uncertainty)),
    predictedFinalScoreHigh: roundToTenths(predictedTotal + uncertainty),
    averageDressageCurrentLevel: average(sameLevel.map((result) => result.dressageScore)),
    averageDressageOneLevelBelow: average(oneBelow.map((result) => result.dressageScore)),
    averageFinalScore: average(scores),
    xcClearJumpingRate: rate(completed.filter((result) => result.crossCountryJumpPenalties === 0).length, completed.length),
    xcTimePenaltyAverage: average(completed.map((result) => result.crossCountryTimePenalties)) ?? 0,
    sjRailAverage: roundToTenths(((average(completed.map((result) => result.showJumpingPenalties)) ?? 0) / 4) * 10) / 10,
    completionRate: rate(completed.length, evidenceResults.length),
    eliminationRetirementRate,
    bestScore: scores.length ? Math.min(...scores) : null,
    worstScore: scores.length ? Math.max(...scores) : null,
    recent3RunAverage: average(scores.slice(0, 3)),
    recent5RunAverage: average(scores.slice(0, 5)),
    trendDirection: trend(scores),
    levelReliability: reliability(sameLevel.length, oneBelow.length, rate(completed.length, evidenceResults.length), eliminationRetirementRate),
    countryPattern: pattern(evidenceResults, (result) => result.country),
    venuePattern: pattern(evidenceResults, (result) => result.venue || result.eventName),
    sameLevelResultCount: sameLevel.length,
    horseResultCount: horseResults.length,
    combinationResultCount: combinationResults.length,
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
      result.status ?? 'completed',
      result.riderFeiId ?? '',
      result.horseFeiId ?? '',
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

const isCompleted = (result: EventingResultRecord) => completionStatus(result) === 'completed';

const completionStatus = (result: EventingResultRecord) => {
  const text = `${result.status ?? ''} ${result.placing ?? ''}`.toLowerCase();
  if (/\b(el|elim|eliminated)\b/.test(text)) {
    return 'eliminated';
  }
  if (/\b(ret|retired)\b/.test(text)) {
    return 'retired';
  }
  if (/\b(wd|withdrawn)\b/.test(text)) {
    return 'withdrawn';
  }
  return 'completed';
};

const weightedPhaseAverage = (
  results: EventingResultRecord[],
  targetLevel: string,
  readValue: (result: EventingResultRecord) => number,
) => {
  const values = results.filter(isCompleted).map((result, index) => {
    const recencyWeight = Math.max(1, results.length - index);
    let levelWeight = sameLevelRank(result.level, targetLevel) ? 1.5 : 0.85;
    if (levelRank(result.level) > levelRank(targetLevel)) {
      levelWeight = 1.2;
    }
    return { value: readValue(result), weight: recencyWeight * levelWeight };
  });
  const weightTotal = values.reduce((total, item) => total + item.weight, 0);
  if (weightTotal === 0) {
    return 0;
  }
  return values.reduce((total, item) => total + item.value * item.weight, 0) / weightTotal;
};

const average = (values: number[]) => {
  if (values.length === 0) {
    return null;
  }
  return roundToTenths(values.reduce((total, value) => total + value, 0) / values.length);
};

const rate = (count: number, total: number) => (total === 0 ? 0 : Math.round((count / total) * 100) / 100);

const standardDeviation = (values: number[]) => {
  if (values.length < 2) {
    return 3;
  }
  const avg = values.reduce((total, value) => total + value, 0) / values.length;
  return Math.sqrt(values.reduce((total, value) => total + (value - avg) ** 2, 0) / values.length);
};

const trend = (scores: number[]): PredictionEvidence['trendDirection'] => {
  if (scores.length < 4) {
    return 'flat';
  }
  const splitAt = Math.max(2, Math.floor(scores.length / 2));
  const newer = average(scores.slice(0, splitAt)) ?? 0;
  const older = average(scores.slice(splitAt)) ?? 0;
  if (newer <= older - 1) {
    return 'improving';
  }
  if (newer >= older + 1) {
    return 'declining';
  }
  return 'flat';
};

const reliability = (
  sameLevelCount: number,
  oneBelowCount: number,
  completionRate: number,
  eliminationRetirementRate: number,
): PredictionEvidence['levelReliability'] => {
  if (sameLevelCount >= 3 && completionRate >= 0.75 && eliminationRetirementRate <= 0.2) {
    return 'proven';
  }
  if (sameLevelCount === 0 && oneBelowCount >= 2) {
    return 'stepping up';
  }
  if (completionRate < 0.7 || eliminationRetirementRate > 0.25) {
    return 'inconsistent';
  }
  return 'developing';
};

const pattern = (results: EventingResultRecord[], readKey: (result: EventingResultRecord) => string) => {
  const buckets = new Map<string, number[]>();
  for (const result of results.filter(isCompleted)) {
    const key = readKey(result) || 'Unknown';
    buckets.set(key, [...(buckets.get(key) ?? []), finishingScore(result)]);
  }
  const candidates = [...buckets.entries()].filter(([, scores]) => scores.length >= 3);
  if (candidates.length === 0) {
    return 'not enough data';
  }
  const [bestKey, bestScores] = candidates.sort((a, b) => (average(a[1]) ?? 0) - (average(b[1]) ?? 0))[0];
  return `best at ${bestKey} (${average(bestScores)?.toFixed(1)} avg)`;
};

const sameLevelRank = (left: string, right: string) =>
  (levelRank(left) > 0 && levelRank(left) === levelRank(right)) || slug(left) === slug(right);

const levelRank = (level: string) => {
  const cci = level.toUpperCase().match(/CCI\s*(\d)/);
  if (cci) {
    return Number(cci[1]);
  }
  const normalized = level.toUpperCase();
  if (normalized.includes('ADVANCED')) {
    return 4;
  }
  if (normalized.includes('INTERMEDIATE')) {
    return 3;
  }
  if (normalized.includes('PRELIM')) {
    return 2;
  }
  if (/(TRAINING|NOVICE|CCN1)/.test(normalized)) {
    return 1;
  }
  return 0;
};
