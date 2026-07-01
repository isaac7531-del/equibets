import { describe, expect, it } from 'vitest';
import { horseProfileFromForm, sortHorseProfiles } from './horseProfiles';

describe('horse profile helpers', () => {
  it('normalizes saved horse profile data', () => {
    const profile = horseProfileFromForm(
      {
        name: '  Pocket Rocket ',
        registeredName: 'Pocket Rocket II ',
        feiId: ' 107bh10 ',
        country: ' gbr ',
        sex: 'Gelding',
        birthYear: '2014',
        color: 'Bay',
        owner: 'Stone Eventing',
        notes: '  Verified from FEI ',
      },
      'horse-1',
      '2026-06-30T00:00:00.000Z',
    );

    expect(profile.name).toBe('Pocket Rocket');
    expect(profile.feiId).toBe('107BH10');
    expect(profile.country).toBe('GBR');
    expect(profile.notes).toBe('Verified from FEI');
  });

  it('sorts horse profiles by display name', () => {
    const profiles = sortHorseProfiles([
      {
        id: '2',
        name: 'Zephyr',
        registeredName: '',
        feiId: '',
        country: 'USA',
        sex: '',
        birthYear: '',
        color: '',
        owner: '',
        notes: '',
        createdAt: '2026-06-30T00:00:01.000Z',
      },
      {
        id: '1',
        name: 'Atlas Bay',
        registeredName: '',
        feiId: '',
        country: 'GBR',
        sex: '',
        birthYear: '',
        color: '',
        owner: '',
        notes: '',
        createdAt: '2026-06-30T00:00:00.000Z',
      },
    ]);

    expect(profiles.map((profile) => profile.name)).toEqual(['Atlas Bay', 'Zephyr']);
  });
});
