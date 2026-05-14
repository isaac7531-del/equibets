export type EventingScoreInput = {
  dressagePercentage: number;
  showJumpingPenalties: number;
  crossCountryJumpPenalties: number;
  optimumTimeSeconds: number;
  actualTimeSeconds: number;
};

export type EventingPenaltyInput = {
  dressagePenalties: number;
  showJumpingPenalties: number;
  crossCountryJumpPenalties: number;
  crossCountryTimePenalties: number;
};

export type EventingScore = {
  dressagePenalties: number;
  showJumpingPenalties: number;
  crossCountryJumpPenalties: number;
  crossCountryTimePenalties: number;
  totalPenalties: number;
};

export type StoredResult = EventingScoreInput & {
  id: string;
  rider: string;
  horse: string;
  eventName: string;
  date: string;
  notes: string;
  createdAt: string;
  score: EventingScore;
};

export const roundToTenths = (value: number) => Math.round(value * 10) / 10;

export const calculateScoreFromPenalties = (input: EventingPenaltyInput): EventingScore => {
  const dressagePenalties = roundToTenths(input.dressagePenalties);
  const showJumpingPenalties = roundToTenths(input.showJumpingPenalties);
  const crossCountryJumpPenalties = roundToTenths(input.crossCountryJumpPenalties);
  const crossCountryTimePenalties = roundToTenths(input.crossCountryTimePenalties);
  const totalPenalties = roundToTenths(
    dressagePenalties + showJumpingPenalties + crossCountryJumpPenalties + crossCountryTimePenalties,
  );

  return {
    dressagePenalties,
    showJumpingPenalties,
    crossCountryJumpPenalties,
    crossCountryTimePenalties,
    totalPenalties,
  };
};

export const calculateScore = (input: EventingScoreInput): EventingScore => {
  const dressagePenalties = roundToTenths(100 - input.dressagePercentage);
  const secondsOverOptimum = Math.max(0, input.actualTimeSeconds - input.optimumTimeSeconds);
  const crossCountryTimePenalties = roundToTenths(secondsOverOptimum * 0.4);

  return calculateScoreFromPenalties({
    dressagePenalties,
    showJumpingPenalties: input.showJumpingPenalties,
    crossCountryJumpPenalties: input.crossCountryJumpPenalties,
    crossCountryTimePenalties,
  });
};

export const parseTimeToSeconds = (minutes: number, seconds: number) => {
  const normalizedMinutes = Number.isFinite(minutes) ? Math.max(0, minutes) : 0;
  const normalizedSeconds = Number.isFinite(seconds) ? Math.max(0, seconds) : 0;

  return normalizedMinutes * 60 + normalizedSeconds;
};

export const formatSeconds = (totalSeconds: number) => {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
};

export const sortByBestScore = (results: StoredResult[]) =>
  [...results].sort((a, b) => {
    if (a.score.totalPenalties !== b.score.totalPenalties) {
      return a.score.totalPenalties - b.score.totalPenalties;
    }

    return a.createdAt.localeCompare(b.createdAt);
  });
