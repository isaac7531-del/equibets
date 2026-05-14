import { describe, expect, it } from 'vitest';
import { currentEventFeed, scoreCurrentEventStart, searchCurrentEventResults } from './currentEvents';

describe('current event live scoring', () => {
  it('scores completed and missing phases as a live total', () => {
    const liveScore = scoreCurrentEventStart(currentEventFeed.results[0]);

    expect(liveScore.score.totalPenalties).toBe(38.6);
    expect(liveScore.completedPhaseCount).toBe(4);
    expect(liveScore.phaseLabel).toBe('XC live');
  });

  it('searches current results by horse, rider, event, level, country, and source', () => {
    expect(searchCurrentEventResults('copper')).toHaveLength(1);
    expect(searchCurrentEventResults('mara')[0].horseName).toBe('Copper Chance');
    expect(searchCurrentEventResults('cci3-s')[0].eventName).toBe('Chatsworth International');
    expect(searchCurrentEventResults('usea')[0].riderName).toBe('Finn Brooks');
  });

  it('sorts by most complete live scores before lower-score partial phases', () => {
    const scores = searchCurrentEventResults('');

    expect(scores[0].horseName).toBe('Orchard Lane');
    expect(scores[0].score.totalPenalties).toBe(36.9);
    expect(scores.at(-1)?.horseName).toBe('Maple Run');
  });
});
