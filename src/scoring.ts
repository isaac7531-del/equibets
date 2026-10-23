export type EventingScoreInput = {
  dressagePercentage: number;
  showJumpingPenalties: number;
  crossCountryJumpPenalties: number;
  optimumTimeSeconds: number;
  actualTimeSeconds: number;
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
  level: string;
  country: string;
  notes: string;
  createdAt: string;
  score: EventingScore;
};

export type RiderLevelDirectory = {
  rider: string;
  levels: {
    level: string;
    horses: string[];
  }[];
};

export const roundToTenths = (value: number) => Math.round(value * 10) / 10;

export const calculateScore = (input: EventingScoreInput): EventingScore => {
  const dressagePenalties = roundToTenths(100 - input.dressagePercentage);
  const secondsOverOptimum = Math.max(0, input.actualTimeSeconds - input.optimumTimeSeconds);
  const crossCountryTimePenalties = roundToTenths(secondsOverOptimum * 0.4);
  const totalPenalties = roundToTenths(
    dressagePenalties +
      input.showJumpingPenalties +
      input.crossCountryJumpPenalties +
      crossCountryTimePenalties,
  );

  return {
    dressagePenalties,
    showJumpingPenalties: input.showJumpingPenalties,
    crossCountryJumpPenalties: input.crossCountryJumpPenalties,
    crossCountryTimePenalties,
    totalPenalties,
  };
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

export const resultLevel = (result: Pick<StoredResult, 'level'>) => result.level || 'Unspecified';

export const buildRiderLevelDirectory = (results: StoredResult[], selectedRider = 'all'): RiderLevelDirectory[] => {
  const directory = new Map<string, Map<string, Set<string>>>();

  results.forEach((result) => {
    if (selectedRider !== 'all' && result.rider !== selectedRider) {
      return;
    }

    const riderLevels = directory.get(result.rider) ?? new Map<string, Set<string>>();
    const level = resultLevel(result);
    const horses = riderLevels.get(level) ?? new Set<string>();
    horses.add(result.horse);
    riderLevels.set(level, horses);
    directory.set(result.rider, riderLevels);
  });

  return [...directory.entries()]
    .sort(([riderA], [riderB]) => riderA.localeCompare(riderB))
    .map(([rider, levels]) => ({
      rider,
      levels: [...levels.entries()]
        .sort(([levelA], [levelB]) => levelA.localeCompare(levelB))
        .map(([level, horses]) => ({
          level,
          horses: [...horses].sort((horseA, horseB) => horseA.localeCompare(horseB)),
        })),
    }));
};
