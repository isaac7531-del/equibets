export type HorseProfile = {
  id: string;
  name: string;
  registeredName: string;
  feiId: string;
  country: string;
  sex: string;
  birthYear: string;
  color: string;
  owner: string;
  notes: string;
  createdAt: string;
};

export type HorseProfileFormState = Omit<HorseProfile, 'id' | 'createdAt'>;

export const createDefaultHorseProfileForm = (): HorseProfileFormState => ({
  name: '',
  registeredName: '',
  feiId: '',
  country: 'GBR',
  sex: '',
  birthYear: '',
  color: '',
  owner: '',
  notes: '',
});

export const horseProfileFromForm = (
  form: HorseProfileFormState,
  id: string,
  createdAt: string,
): HorseProfile => ({
  id,
  name: form.name.trim(),
  registeredName: form.registeredName.trim(),
  feiId: form.feiId.trim().toUpperCase(),
  country: form.country.trim().toUpperCase(),
  sex: form.sex.trim(),
  birthYear: form.birthYear.trim(),
  color: form.color.trim(),
  owner: form.owner.trim(),
  notes: form.notes.trim(),
  createdAt,
});

export const sortHorseProfiles = (profiles: HorseProfile[]) =>
  [...profiles].sort((a, b) => a.name.localeCompare(b.name) || a.createdAt.localeCompare(b.createdAt));
