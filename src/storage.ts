import type { StoredResult } from './scoring';

const STORAGE_KEY = 'equibets.results';

export const loadResults = (): StoredResult[] => {
  if (typeof window === 'undefined') {
    return [];
  }

  const rawResults = window.localStorage.getItem(STORAGE_KEY);
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

export const saveResults = (results: StoredResult[]) => {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(results));
};
