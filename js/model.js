(function attachModel(global) {
  const clamp = (value, min, max) => Math.min(Math.max(value, min), max);
  const round = (value, decimals = 1) => Number(value.toFixed(decimals));

  function calculatePrediction(combination, event) {
    const formAdjustment = (82 - combination.formScore) * 0.09;
    const trendAdjustment = combination.trend * -0.7;
    const championshipAdjustment = (88 - combination.championshipExperience) * 0.045;
    const reliabilityAdjustment = (86 - combination.reliability) * 0.06;
    const technicalityAdjustment = (event.technicality - 7) * 0.85;
    const terrainAdjustment = (event.terrainDemand - combination.stamina) * 0.055;
    const travelAdjustment = (event.travelDemand - combination.travelResilience) * 0.04;
    const climateAdjustment = (event.climateStress - combination.climateFitness) * 0.035;
    const pressureAdjustment = (event.pressure - combination.championshipExperience) * 0.035;

    const predictedScore =
      combination.baseScore +
      formAdjustment +
      trendAdjustment +
      championshipAdjustment +
      reliabilityAdjustment +
      technicalityAdjustment +
      terrainAdjustment +
      travelAdjustment +
      climateAdjustment +
      pressureAdjustment;

    const recencyScore = clamp(100 - combination.lastResultDays * 0.45, 38, 100);
    const startsScore = clamp(combination.internationalStarts * 4, 30, 100);
    const fitScore = clamp(
      100 -
        Math.abs(event.terrainDemand - combination.stamina) * 0.7 -
        Math.abs(event.travelDemand - combination.travelResilience) * 0.45 -
        Math.abs(event.climateStress - combination.climateFitness) * 0.25,
      35,
      100
    );

    const confidence = clamp(
      combination.reliability * 0.34 +
        combination.formScore * 0.19 +
        combination.championshipExperience * 0.18 +
        recencyScore * 0.12 +
        startsScore * 0.08 +
        fitScore * 0.09 -
        event.uncertainty * 0.7,
      35,
      96
    );

    const variance = clamp(
      10 -
        combination.reliability * 0.045 -
        combination.championshipExperience * 0.025 +
        event.uncertainty * 0.085,
      2.8,
      8.5
    );

    return {
      combinationId: combination.id,
      eventId: event.id,
      predictedScore: round(predictedScore),
      confidence: Math.round(confidence),
      scoreRange: {
        low: round(predictedScore - variance),
        high: round(predictedScore + variance)
      },
      risk: getRiskLabel(confidence, variance),
      factors: {
        form: round(formAdjustment),
        trend: round(trendAdjustment),
        eventFit: round(terrainAdjustment + travelAdjustment + climateAdjustment),
        pressure: round(pressureAdjustment),
        dataQuality: Math.round((recencyScore + startsScore + combination.reliability) / 3)
      }
    };
  }

  function getRiskLabel(confidence, variance) {
    if (confidence >= 83 && variance <= 4.7) {
      return "low";
    }

    if (confidence >= 68 && variance <= 6.4) {
      return "medium";
    }

    return "high";
  }

  function rankEventPredictions(combinations, event) {
    return combinations
      .map((combination) => ({
        combination,
        prediction: calculatePrediction(combination, event)
      }))
      .sort((left, right) => {
        if (left.prediction.predictedScore === right.prediction.predictedScore) {
          return right.prediction.confidence - left.prediction.confidence;
        }

        return left.prediction.predictedScore - right.prediction.predictedScore;
      });
  }

  function getTeamRecommendations(combinations, event, country, teamSize = 4) {
    return rankEventPredictions(
      combinations.filter((combination) => combination.country === country),
      event
    ).slice(0, teamSize);
  }

  const model = {
    calculatePrediction,
    rankEventPredictions,
    getTeamRecommendations,
    clamp,
    round
  };

  global.EquiBetsModel = model;

  if (typeof module !== "undefined") {
    module.exports = model;
  }
})(typeof window !== "undefined" ? window : globalThis);
