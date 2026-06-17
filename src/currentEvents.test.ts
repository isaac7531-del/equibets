import { describe, expect, it } from 'vitest';
import { currentEventStatus, normalizeCurrentEventsPayload } from './currentEvents';

describe('current event feed', () => {
  it('normalizes public FEI calendar events', () => {
    const feed = normalizeCurrentEventsPayload({
      updated_at: '2026-06-17T00:00:00+00:00',
      window_start: '2026-06-17',
      window_end: '2026-06-24',
      events: [
        {
          source_event_id: 'fei-1',
          name: 'Aachen CCIO4*-S',
          url: 'https://data.fei.org/Calendar/EventDetail.aspx?event=1',
          start_date: '2026-06-17',
          end_date: '2026-06-20',
          country: 'GER',
          discipline: 'Eventing',
          level: 'CCIO4*-S',
        },
        {
          source_event_id: 'bad',
          name: '',
          url: '',
        },
      ],
    });

    expect(feed.events).toEqual([
      {
        sourceEventId: 'fei-1',
        name: 'Aachen CCIO4*-S',
        url: 'https://data.fei.org/Calendar/EventDetail.aspx?event=1',
        startDate: '2026-06-17',
        endDate: '2026-06-20',
        country: 'GER',
        discipline: 'Eventing',
        level: 'CCIO4*-S',
      },
    ]);
  });

  it('labels current event status from the date window', () => {
    const today = new Date('2026-06-17T12:00:00.000Z');

    expect(currentEventStatus({ startDate: '2026-06-16', endDate: '2026-06-18' }, today)).toBe('Live now');
    expect(currentEventStatus({ startDate: '2026-06-20', endDate: '2026-06-22' }, today)).toBe('Upcoming');
    expect(currentEventStatus({ startDate: '2026-06-10', endDate: '2026-06-12' }, today)).toBe(
      'Recently finished',
    );
  });
});
