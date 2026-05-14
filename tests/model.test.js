const test = require("node:test");
const assert = require("node:assert/strict");
const { feiSearchPages, riderCombinations, allResultRows, events } = require("../js/data.js");
const {
  calculatePrediction,
  rankEventPredictions,
  getTeamRecommendations
} = require("../js/model.js");

test("event predictions are ranked by the lowest eventing score", () => {
  const predictions = rankEventPredictions(riderCombinations, events[0]);

  assert.equal(predictions.length, riderCombinations.length);

  for (let index = 1; index < predictions.length; index += 1) {
    assert.ok(
      predictions[index - 1].prediction.predictedScore <= predictions[index].prediction.predictedScore,
      "predicted scores should be sorted ascending"
    );
  }
});

test("prediction output includes bounded confidence and a usable score range", () => {
  const prediction = calculatePrediction(riderCombinations[0], events[1]);

  assert.ok(prediction.predictedScore > 0);
  assert.ok(prediction.confidence >= 35);
  assert.ok(prediction.confidence <= 96);
  assert.ok(prediction.scoreRange.low < prediction.predictedScore);
  assert.ok(prediction.scoreRange.high > prediction.predictedScore);
  assert.match(prediction.risk, /^(low|medium|high)$/);
});

test("team recommendations stay within the chosen country and team size", () => {
  const recommendations = getTeamRecommendations(riderCombinations, events[0], "Great Britain", 4);

  assert.ok(recommendations.length <= 4);
  assert.ok(recommendations.length > 0);
  assert.ok(recommendations.every((entry) => entry.combination.country === "Great Britain"));
});

test("higher event uncertainty reduces confidence for the same combination", () => {
  const combination = riderCombinations[0];
  const stableEvent = { ...events[0], uncertainty: 4 };
  const uncertainEvent = { ...events[0], uncertainty: 35 };

  const stablePrediction = calculatePrediction(combination, stableEvent);
  const uncertainPrediction = calculatePrediction(combination, uncertainEvent);

  assert.ok(stablePrediction.confidence > uncertainPrediction.confidence);
});

test("calendar data includes 5-star and 4-star upcoming events", () => {
  const levels = new Set(events.map((event) => event.level));

  assert.ok(levels.has("5-star"));
  assert.ok(levels.has("4-star"));
  assert.ok(events.filter((event) => event.level === "5-star").length >= 3);
  assert.ok(events.filter((event) => event.level === "4-star").length >= 3);
});

test("rider database covers expanded international countries", () => {
  const countries = new Set(riderCombinations.map((combination) => combination.country));

  assert.equal(riderCombinations.length, 18);
  assert.ok(countries.has("France"));
  assert.ok(countries.has("Australia"));
  assert.ok(countries.has("Ireland"));
  assert.ok(countries.has("Japan"));
  assert.ok(countries.has("Switzerland"));
  assert.ok(countries.has("Netherlands"));
  assert.ok(events.every((event) => event.countries.length >= countries.size));
});

test("every combination has previous result rows for result pages", () => {
  assert.ok(riderCombinations.every((combination) => combination.previousResults.length >= 3));
  assert.equal(
    allResultRows.length,
    riderCombinations.reduce((total, combination) => total + combination.previousResults.length, 0)
  );
  assert.ok(
    riderCombinations.every((combination) =>
      combination.previousResults.every((result) => typeof result.finishingScore === "number")
    )
  );
});

test("all result rows expose searchable rider and event fields", () => {
  const badmintonRows = allResultRows.filter((result) =>
    `${result.rider} ${result.horse} ${result.event} ${result.level} ${result.country}`.toLowerCase().includes("badminton")
  );

  assert.ok(badmintonRows.length > 0);
  assert.ok(allResultRows.every((result) => result.rider && result.horse && result.event && result.sourceUrl));
});

test("website result rows link back to FEI lookup pages", () => {
  assert.equal(feiSearchPages.person, "https://data.fei.org/Person/Search.aspx");
  assert.equal(feiSearchPages.horse, "https://data.fei.org/Horse/Search.aspx");
  assert.equal(feiSearchPages.calendar, "https://data.fei.org/Calendar/Search.aspx");
  assert.equal(feiSearchPages.rankings, "https://data.fei.org/Ranking/Search.aspx");
  assert.ok(
    riderCombinations.every((combination) =>
      combination.previousResults.every((result) => result.sourceUrl === feiSearchPages.calendar)
    )
  );
});
