import type { StoredResult } from './scoring';
import type { HorseProfile } from './horseProfiles';

const RESULTS_STORAGE_KEY = 'equibets.results';
const HORSE_PROFILES_STORAGE_KEY = 'equibets.horseProfiles';

export const loadResults = (): StoredResult[] => {
  return loadArray<StoredResult>(RESULTS_STORAGE_KEY);
};

export const saveResults = (results: StoredResult[]) => {
  window.localStorage.setItem(RESULTS_STORAGE_KEY, JSON.stringify(results));
};

export const loadHorseProfiles = (): HorseProfile[] => {
  return loadArray<HorseProfile>(HORSE_PROFILES_STORAGE_KEY);
};

export const saveHorseProfiles = (profiles: HorseProfile[]) => {
  window.localStorage.setItem(HORSE_PROFILES_STORAGE_KEY, JSON.stringify(profiles));
};

const loadArray = <T>(storageKey: string): T[] => {
  if (typeof window === 'undefined') {
    return [];
  }

  const rawResults = window.localStorage.getItem(storageKey);
  if (!rawResults) {
    return [];
  }

  try {
    const parsedResults = JSON.parse(rawResults);
    return Array.isArray(parsedResults) ? parsedResults : [];
  } catch {
    return [];
  }
};
