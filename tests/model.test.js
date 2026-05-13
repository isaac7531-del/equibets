const test = require("node:test");
const assert = require("node:assert/strict");
const { riderCombinations, events } = require("../js/data.js");
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
