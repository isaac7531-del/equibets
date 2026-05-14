(function attachData(global) {
  const feiSearchPages = {
    person: "https://data.fei.org/Person/Search.aspx",
    horse: "https://data.fei.org/Horse/Search.aspx",
    calendar: "https://data.fei.org/Calendar/Search.aspx"
  };

  const riderCombinations = [
    {
      id: "ros-canter-lordships-graffalo",
      rider: "Ros Canter",
      horse: "Lordships Graffalo",
      country: "Great Britain",
      shortCountry: "GBR",
      baseScore: 25.8,
      formScore: 94,
      reliability: 92,
      championshipExperience: 96,
      internationalStarts: 24,
      lastResultDays: 36,
      trend: 2.2,
      stamina: 91,
      travelResilience: 88,
      climateFitness: 83,
      notes: "Elite championship record with consistently low finishing scores."
    },
    {
      id: "laura-collett-london-52",
      rider: "Laura Collett",
      horse: "London 52",
      country: "Great Britain",
      shortCountry: "GBR",
      baseScore: 27.2,
      formScore: 91,
      reliability: 89,
      championshipExperience: 94,
      internationalStarts: 29,
      lastResultDays: 52,
      trend: 1.4,
      stamina: 86,
      travelResilience: 84,
      climateFitness: 82,
      notes: "Proven under pressure and usually competitive after dressage."
    },
    {
      id: "tom-mcewen-jl-dublin",
      rider: "Tom McEwen",
      horse: "JL Dublin",
      country: "Great Britain",
      shortCountry: "GBR",
      baseScore: 29.4,
      formScore: 87,
      reliability: 84,
      championshipExperience: 91,
      internationalStarts: 21,
      lastResultDays: 44,
      trend: 1.1,
      stamina: 88,
      travelResilience: 87,
      climateFitness: 81,
      notes: "Strong all-rounder with a high championship ceiling."
    },
    {
      id: "michael-jung-chipmunk-frh",
      rider: "Michael Jung",
      horse: "Chipmunk FRH",
      country: "Germany",
      shortCountry: "GER",
      baseScore: 26.6,
      formScore: 90,
      reliability: 90,
      championshipExperience: 98,
      internationalStarts: 31,
      lastResultDays: 61,
      trend: 0.8,
      stamina: 88,
      travelResilience: 90,
      climateFitness: 86,
      notes: "Benchmark dressage quality and exceptional championship history."
    },
    {
      id: "julia-krajewski-mandy",
      rider: "Julia Krajewski",
      horse: "Nickel 21",
      country: "Germany",
      shortCountry: "GER",
      baseScore: 30.1,
      formScore: 86,
      reliability: 83,
      championshipExperience: 93,
      internationalStarts: 19,
      lastResultDays: 74,
      trend: 1.7,
      stamina: 84,
      travelResilience: 82,
      climateFitness: 80,
      notes: "Fast improver with Olympic-level rider experience."
    },
    {
      id: "sandra-auffarth-viamant-du-matz",
      rider: "Sandra Auffarth",
      horse: "Viamant du Matz",
      country: "Germany",
      shortCountry: "GER",
      baseScore: 31.6,
      formScore: 82,
      reliability: 81,
      championshipExperience: 88,
      internationalStarts: 26,
      lastResultDays: 49,
      trend: 0.6,
      stamina: 89,
      travelResilience: 83,
      climateFitness: 79,
      notes: "Reliable cross-country profile with strong team value."
    },
    {
      id: "boyd-martin-fedarman-b",
      rider: "Boyd Martin",
      horse: "Fedarman B",
      country: "United States",
      shortCountry: "USA",
      baseScore: 32.4,
      formScore: 84,
      reliability: 80,
      championshipExperience: 90,
      internationalStarts: 25,
      lastResultDays: 42,
      trend: 1.2,
      stamina: 87,
      travelResilience: 86,
      climateFitness: 84,
      notes: "High-mileage championship rider with strong travel resilience."
    },
    {
      id: "tamie-smith-mai-baum",
      rider: "Tamie Smith",
      horse: "Mai Baum",
      country: "United States",
      shortCountry: "USA",
      baseScore: 30.8,
      formScore: 85,
      reliability: 79,
      championshipExperience: 84,
      internationalStarts: 18,
      lastResultDays: 93,
      trend: -0.2,
      stamina: 82,
      travelResilience: 78,
      climateFitness: 83,
      notes: "Excellent best-case score, with confidence sensitive to recency."
    },
    {
      id: "will-coleman-off-the-record",
      rider: "Will Coleman",
      horse: "Off The Record",
      country: "United States",
      shortCountry: "USA",
      baseScore: 33.1,
      formScore: 81,
      reliability: 82,
      championshipExperience: 86,
      internationalStarts: 22,
      lastResultDays: 68,
      trend: 0.4,
      stamina: 85,
      travelResilience: 80,
      climateFitness: 82,
      notes: "Consistent jumping profile and dependable team option."
    },
    {
      id: "tim-price-falco",
      rider: "Tim Price",
      horse: "Falco",
      country: "New Zealand",
      shortCountry: "NZL",
      baseScore: 29.9,
      formScore: 88,
      reliability: 86,
      championshipExperience: 92,
      internationalStarts: 27,
      lastResultDays: 58,
      trend: 1.0,
      stamina: 90,
      travelResilience: 91,
      climateFitness: 84,
      notes: "Experienced traveller with a strong finishing-score floor."
    },
    {
      id: "jonelle-price-mcclaren",
      rider: "Jonelle Price",
      horse: "McClaren",
      country: "New Zealand",
      shortCountry: "NZL",
      baseScore: 31.2,
      formScore: 84,
      reliability: 84,
      championshipExperience: 91,
      internationalStarts: 23,
      lastResultDays: 55,
      trend: 0.9,
      stamina: 88,
      travelResilience: 90,
      climateFitness: 82,
      notes: "Aggressive championship competitor with strong time performance."
    },
    {
      id: "yasmin-ingham-banzai-du-loir",
      rider: "Yasmin Ingham",
      horse: "Banzai du Loir",
      country: "Great Britain",
      shortCountry: "GBR",
      baseScore: 28.1,
      formScore: 89,
      reliability: 85,
      championshipExperience: 90,
      internationalStarts: 20,
      lastResultDays: 47,
      trend: 1.5,
      stamina: 86,
      travelResilience: 82,
      climateFitness: 81,
      notes: "Medal-level pairing with a sharp recent-form profile."
    }
  ];

  const previousResultsByCombination = {
    "ros-canter-lordships-graffalo": [
      { event: "Badminton Horse Trials", level: "5-star", year: 2024, placing: "1st", finishingScore: 35.3, dressage: 26.0, crossCountry: 5.6, showJumping: 3.7 },
      { event: "European Championships", level: "Championship", year: 2023, placing: "1st", finishingScore: 21.3, dressage: 21.3, crossCountry: 0, showJumping: 0 },
      { event: "Burghley Horse Trials", level: "5-star", year: 2022, placing: "2nd", finishingScore: 26.8, dressage: 22.1, crossCountry: 4.7, showJumping: 0 }
    ],
    "laura-collett-london-52": [
      { event: "Luhmuhlen Horse Trials", level: "5-star", year: 2023, placing: "1st", finishingScore: 20.3, dressage: 20.3, crossCountry: 0, showJumping: 0 },
      { event: "Tokyo Olympics", level: "Championship", year: 2021, placing: "Team gold", finishingScore: 25.8, dressage: 25.8, crossCountry: 0, showJumping: 0 },
      { event: "Blenheim Palace", level: "4-star", year: 2022, placing: "3rd", finishingScore: 29.6, dressage: 24.4, crossCountry: 1.2, showJumping: 4.0 }
    ],
    "tom-mcewen-jl-dublin": [
      { event: "Kentucky Three-Day Event", level: "5-star", year: 2024, placing: "2nd", finishingScore: 33.8, dressage: 28.0, crossCountry: 1.8, showJumping: 4.0 },
      { event: "European Championships", level: "Championship", year: 2023, placing: "Team gold", finishingScore: 34.9, dressage: 27.8, crossCountry: 3.1, showJumping: 4.0 },
      { event: "Bramham International", level: "4-star", year: 2022, placing: "1st", finishingScore: 29.9, dressage: 27.1, crossCountry: 2.8, showJumping: 0 }
    ],
    "michael-jung-chipmunk-frh": [
      { event: "Aachen CHIO", level: "4-star", year: 2024, placing: "1st", finishingScore: 25.6, dressage: 22.7, crossCountry: 2.9, showJumping: 0 },
      { event: "Tokyo Olympics", level: "Championship", year: 2021, placing: "8th", finishingScore: 32.1, dressage: 21.1, crossCountry: 7.0, showJumping: 4.0 },
      { event: "European Championships", level: "Championship", year: 2019, placing: "1st", finishingScore: 20.9, dressage: 20.9, crossCountry: 0, showJumping: 0 }
    ],
    "julia-krajewski-mandy": [
      { event: "Tokyo Olympics", level: "Championship", year: 2021, placing: "1st", finishingScore: 26.0, dressage: 25.2, crossCountry: 0.8, showJumping: 0 },
      { event: "Luhmuhlen Horse Trials", level: "5-star", year: 2024, placing: "4th", finishingScore: 36.7, dressage: 29.1, crossCountry: 3.6, showJumping: 4.0 },
      { event: "Boekelo Nations Cup", level: "4-star", year: 2023, placing: "2nd", finishingScore: 31.4, dressage: 27.0, crossCountry: 0.4, showJumping: 4.0 }
    ],
    "sandra-auffarth-viamant-du-matz": [
      { event: "Aachen CHIO", level: "4-star", year: 2024, placing: "5th", finishingScore: 32.8, dressage: 28.4, crossCountry: 0.4, showJumping: 4.0 },
      { event: "European Championships", level: "Championship", year: 2023, placing: "Team silver", finishingScore: 37.9, dressage: 30.7, crossCountry: 3.2, showJumping: 4.0 },
      { event: "Pau Horse Trials", level: "5-star", year: 2022, placing: "6th", finishingScore: 39.5, dressage: 31.9, crossCountry: 3.6, showJumping: 4.0 }
    ],
    "boyd-martin-fedarman-b": [
      { event: "Maryland 5 Star", level: "5-star", year: 2023, placing: "2nd", finishingScore: 32.4, dressage: 29.8, crossCountry: 2.6, showJumping: 0 },
      { event: "Pan American Games", level: "Championship", year: 2023, placing: "Team silver", finishingScore: 33.7, dressage: 30.1, crossCountry: 3.6, showJumping: 0 },
      { event: "Carolina International", level: "4-star", year: 2024, placing: "4th", finishingScore: 34.8, dressage: 31.2, crossCountry: 3.6, showJumping: 0 }
    ],
    "tamie-smith-mai-baum": [
      { event: "Kentucky Three-Day Event", level: "5-star", year: 2023, placing: "1st", finishingScore: 24.2, dressage: 24.2, crossCountry: 0, showJumping: 0 },
      { event: "World Championships", level: "Championship", year: 2022, placing: "9th", finishingScore: 32.8, dressage: 24.0, crossCountry: 4.8, showJumping: 4.0 },
      { event: "Morven Park", level: "4-star", year: 2023, placing: "2nd", finishingScore: 29.7, dressage: 25.7, crossCountry: 0, showJumping: 4.0 }
    ],
    "will-coleman-off-the-record": [
      { event: "Aachen CHIO", level: "4-star", year: 2023, placing: "3rd", finishingScore: 31.6, dressage: 28.0, crossCountry: 3.6, showJumping: 0 },
      { event: "Maryland 5 Star", level: "5-star", year: 2022, placing: "5th", finishingScore: 37.1, dressage: 29.5, crossCountry: 3.6, showJumping: 4.0 },
      { event: "Tokyo Olympics", level: "Championship", year: 2021, placing: "Team silver", finishingScore: 52.7, dressage: 33.2, crossCountry: 15.5, showJumping: 4.0 }
    ],
    "tim-price-falco": [
      { event: "Pau Horse Trials", level: "5-star", year: 2021, placing: "1st", finishingScore: 27.4, dressage: 22.1, crossCountry: 1.3, showJumping: 4.0 },
      { event: "World Championships", level: "Championship", year: 2022, placing: "5th", finishingScore: 26.2, dressage: 25.6, crossCountry: 0.6, showJumping: 0 },
      { event: "Millstreet International", level: "4-star", year: 2024, placing: "2nd", finishingScore: 30.9, dressage: 27.3, crossCountry: 3.6, showJumping: 0 }
    ],
    "jonelle-price-mcclaren": [
      { event: "Luhmuhlen Horse Trials", level: "5-star", year: 2022, placing: "2nd", finishingScore: 32.8, dressage: 29.6, crossCountry: 3.2, showJumping: 0 },
      { event: "World Championships", level: "Championship", year: 2022, placing: "Team bronze", finishingScore: 36.4, dressage: 30.4, crossCountry: 2.0, showJumping: 4.0 },
      { event: "Blenheim Palace", level: "4-star", year: 2023, placing: "4th", finishingScore: 34.3, dressage: 29.1, crossCountry: 1.2, showJumping: 4.0 }
    ],
    "yasmin-ingham-banzai-du-loir": [
      { event: "World Championships", level: "Championship", year: 2022, placing: "1st", finishingScore: 23.2, dressage: 22.0, crossCountry: 1.2, showJumping: 0 },
      { event: "Kentucky Three-Day Event", level: "5-star", year: 2024, placing: "3rd", finishingScore: 35.6, dressage: 26.0, crossCountry: 5.6, showJumping: 4.0 },
      { event: "Bramham International", level: "4-star", year: 2023, placing: "1st", finishingScore: 27.9, dressage: 25.1, crossCountry: 2.8, showJumping: 0 }
    ]
  };

  const combinationsWithResults = riderCombinations.map((combination) => ({
    ...combination,
    previousResults: (previousResultsByCombination[combination.id] || []).map((result) => ({
      source: "FEI lookup",
      sourceUrl: feiSearchPages.calendar,
      ...result
    }))
  }));

  const events = [
    {
      id: "weg-aachen-2026",
      name: "World Equestrian Games",
      level: "championship",
      venue: "Aachen, Germany",
      date: "2026-08-12",
      technicality: 9,
      terrainDemand: 86,
      travelDemand: 78,
      climateStress: 64,
      pressure: 92,
      uncertainty: 12,
      countries: ["Great Britain", "Germany", "United States", "New Zealand"],
      summary: "Championship pressure, technical cross-country questions, and deep European fields."
    },
    {
      id: "olympics-la-2028",
      name: "Olympics",
      level: "championship",
      venue: "Los Angeles, United States",
      date: "2028-07-21",
      technicality: 8,
      terrainDemand: 80,
      travelDemand: 88,
      climateStress: 82,
      pressure: 98,
      uncertainty: 22,
      countries: ["Great Britain", "Germany", "United States", "New Zealand"],
      summary: "Maximum pressure with heat, travel, selection volatility, and longer-range uncertainty."
    },
    {
      id: "pau-nations-cup-2026",
      name: "FEI Nations Cup Final",
      level: "championship",
      venue: "Pau, France",
      date: "2026-10-23",
      technicality: 7,
      terrainDemand: 76,
      travelDemand: 65,
      climateStress: 58,
      pressure: 76,
      uncertainty: 9,
      countries: ["Great Britain", "Germany", "United States", "New Zealand"],
      summary: "Useful team-form indicator with lower pressure than a championship."
    },
    {
      id: "badminton-2027",
      name: "Badminton Horse Trials",
      level: "5-star",
      venue: "Badminton, Great Britain",
      date: "2027-05-06",
      technicality: 10,
      terrainDemand: 94,
      travelDemand: 62,
      climateStress: 55,
      pressure: 88,
      uncertainty: 15,
      countries: ["Great Britain", "Germany", "United States", "New Zealand"],
      summary: "One of the toughest CCI5*-L tests, valuable for stamina and jumping reliability signals."
    },
    {
      id: "kentucky-2027",
      name: "Kentucky Three-Day Event",
      level: "5-star",
      venue: "Lexington, United States",
      date: "2027-04-22",
      technicality: 9,
      terrainDemand: 88,
      travelDemand: 86,
      climateStress: 70,
      pressure: 84,
      uncertainty: 13,
      countries: ["Great Britain", "Germany", "United States", "New Zealand"],
      summary: "A major North American CCI5*-L with useful travel and championship selection read-through."
    },
    {
      id: "burghley-2027",
      name: "Burghley Horse Trials",
      level: "5-star",
      venue: "Stamford, Great Britain",
      date: "2027-09-02",
      technicality: 10,
      terrainDemand: 96,
      travelDemand: 64,
      climateStress: 58,
      pressure: 87,
      uncertainty: 16,
      countries: ["Great Britain", "Germany", "United States", "New Zealand"],
      summary: "Demanding CCI5*-L terrain makes this a strong test for proven cross-country stamina."
    },
    {
      id: "bramham-2027",
      name: "Bramham International",
      level: "4-star",
      venue: "Wetherby, Great Britain",
      date: "2027-06-10",
      technicality: 8,
      terrainDemand: 84,
      travelDemand: 58,
      climateStress: 54,
      pressure: 72,
      uncertainty: 10,
      countries: ["Great Britain", "Germany", "United States", "New Zealand"],
      summary: "A CCI4*-L selection checkpoint for combinations stepping toward championship teams."
    },
    {
      id: "boekelo-2027",
      name: "Boekelo Nations Cup",
      level: "4-star",
      venue: "Enschede, Netherlands",
      date: "2027-10-07",
      technicality: 7,
      terrainDemand: 78,
      travelDemand: 66,
      climateStress: 57,
      pressure: 74,
      uncertainty: 11,
      countries: ["Great Britain", "Germany", "United States", "New Zealand"],
      summary: "A team-format CCI4*-L event that helps compare national depth and selection options."
    },
    {
      id: "blenheim-2027",
      name: "Blenheim Palace International",
      level: "4-star",
      venue: "Woodstock, Great Britain",
      date: "2027-09-16",
      technicality: 7,
      terrainDemand: 80,
      travelDemand: 60,
      climateStress: 56,
      pressure: 70,
      uncertainty: 10,
      countries: ["Great Britain", "Germany", "United States", "New Zealand"],
      summary: "A CCI4*-L form builder for younger horses and combinations returning to peak fitness."
    }
  ];

  global.EquiBetsData = {
    feiSearchPages,
    riderCombinations: combinationsWithResults,
    events
  };

  if (typeof module !== "undefined") {
    module.exports = global.EquiBetsData;
  }
})(typeof window !== "undefined" ? window : globalThis);
