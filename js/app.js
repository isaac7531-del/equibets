(function initialiseApp(global) {
  const { riderCombinations, events } = global.EquiBetsData;
  const { rankEventPredictions, getTeamRecommendations } = global.EquiBetsModel;
  const storage = global.localStorage;
  const favouriteKey = "equibets:favourites";
  const guessKey = "equibets:team-guesses";

  const state = {
    favourites: readStoredArray(favouriteKey),
    guesses: readStoredObject(guessKey),
    selectedEventId: events[0].id
  };

  const elements = {
    heroPick: document.querySelector("#hero-pick"),
    heroScore: document.querySelector("#hero-score"),
    heroConfidence: document.querySelector("#hero-confidence"),
    statsGrid: document.querySelector("#stats-grid"),
    combinationGrid: document.querySelector("#combination-grid"),
    combinationSearch: document.querySelector("#combination-search"),
    eventTabs: document.querySelector("#event-tabs"),
    eventPanel: document.querySelector("#event-panel"),
    guessForm: document.querySelector("#guess-form"),
    guessEvent: document.querySelector("#guess-event"),
    guessCountry: document.querySelector("#guess-country"),
    guessOptions: document.querySelector("#guess-options"),
    savedGuesses: document.querySelector("#saved-guesses"),
    clearGuesses: document.querySelector("#clear-guesses"),
    menuToggle: document.querySelector(".menu-toggle"),
    navLinks: document.querySelector("#primary-nav")
  };

  function readStoredArray(key) {
    try {
      const parsed = JSON.parse(storage.getItem(key) || "[]");
      return Array.isArray(parsed) ? parsed : [];
    } catch (_error) {
      return [];
    }
  }

  function readStoredObject(key) {
    try {
      const parsed = JSON.parse(storage.getItem(key) || "{}");
      return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
    } catch (_error) {
      return {};
    }
  }

  function persist() {
    storage.setItem(favouriteKey, JSON.stringify(state.favourites));
    storage.setItem(guessKey, JSON.stringify(state.guesses));
  }

  function getEvent(eventId = state.selectedEventId) {
    return events.find((event) => event.id === eventId) || events[0];
  }

  function getCombination(combinationId) {
    return riderCombinations.find((combination) => combination.id === combinationId);
  }

  function render() {
    renderHero();
    renderStats();
    renderCombinations();
    renderEventTabs();
    renderEventPanel();
    renderGuessForm();
    renderSavedGuesses();
  }

  function renderHero() {
    const top = rankEventPredictions(riderCombinations, events[0])[0];
    elements.heroPick.textContent = `${top.combination.rider} + ${top.combination.horse}`;
    elements.heroScore.textContent = `${events[0].name}: predicted ${top.prediction.predictedScore} penalties with ${top.prediction.confidence}% confidence.`;
    elements.heroConfidence.style.width = `${top.prediction.confidence}%`;
  }

  function renderStats() {
    const topEvent = getEvent();
    const topPrediction = rankEventPredictions(riderCombinations, topEvent)[0];
    const guessesCount = Object.values(state.guesses).filter(Boolean).length;
    elements.statsGrid.innerHTML = [
      statCard("Followed combinations", state.favourites.length, "Saved favourites stay highlighted everywhere."),
      statCard("Upcoming events", events.length, "Includes World Equestrian Games and Olympics scenarios."),
      statCard(
        "Best predicted score",
        topPrediction.prediction.predictedScore,
        `${topPrediction.combination.rider} at ${topEvent.name}.`
      ),
      statCard("Saved team guesses", guessesCount, "Event and country selections stored locally."),
      statCard(
        "Highest confidence",
        `${topPrediction.prediction.confidence}%`,
        "Confidence reflects form, reliability, recency, and event fit."
      ),
      statCard("Countries tracked", new Set(riderCombinations.map((item) => item.country)).size, "Ready for team comparisons.")
    ].join("");
  }

  function statCard(label, value, description) {
    return `<article class="stat-card"><span>${label}</span><strong>${value}</strong><p>${description}</p></article>`;
  }

  function renderCombinations() {
    const query = elements.combinationSearch.value.trim().toLowerCase();
    const filtered = riderCombinations.filter((combination) => {
      const searchable = `${combination.rider} ${combination.horse} ${combination.country}`.toLowerCase();
      return searchable.includes(query);
    });

    elements.combinationGrid.innerHTML = filtered.map(renderCombinationCard).join("");
  }

  function renderCombinationCard(combination) {
    const isFavourite = state.favourites.includes(combination.id);
    const initials = `${combination.rider[0]}${combination.horse[0]}`;

    return `
      <article class="combination-card">
        <div class="card-top">
          <div class="avatar" aria-hidden="true">${initials}</div>
          <span class="tag">${combination.shortCountry}</span>
        </div>
        <div>
          <h3>${combination.rider}</h3>
          <p>${combination.horse} · ${combination.country}</p>
        </div>
        <p>${combination.notes}</p>
        <div class="metrics">
          ${metric("Base", combination.baseScore)}
          ${metric("Form", combination.formScore)}
          ${metric("Reliability", `${combination.reliability}%`)}
        </div>
        <div class="card-actions">
          <button class="button ${isFavourite ? "primary" : "ghost"}" data-favourite="${combination.id}" aria-pressed="${isFavourite}">
            ${isFavourite ? "Following" : "Follow"}
          </button>
        </div>
      </article>
    `;
  }

  function metric(label, value) {
    return `<div class="metric"><strong>${value}</strong><span>${label}</span></div>`;
  }

  function renderEventTabs() {
    elements.eventTabs.innerHTML = events
      .map(
        (event) => `
          <button class="tab-button" type="button" role="tab" data-event-tab="${event.id}" aria-selected="${event.id === state.selectedEventId}">
            ${event.name}
          </button>
        `
      )
      .join("");
  }

  function renderEventPanel() {
    const event = getEvent();
    const predictions = rankEventPredictions(riderCombinations, event).slice(0, 6);

    elements.eventPanel.innerHTML = `
      <div class="event-detail">
        <aside class="event-summary">
          <p class="eyebrow">${event.date}</p>
          <h3>${event.name}</h3>
          <p>${event.venue}</p>
          <p>${event.summary}</p>
          <div class="metrics">
            ${metric("Pressure", event.pressure)}
            ${metric("Terrain", event.terrainDemand)}
            ${metric("Uncertainty", event.uncertainty)}
          </div>
        </aside>
        <div class="forecast-grid">
          ${predictions.map((entry, index) => renderPredictionCard(entry, index)).join("")}
        </div>
      </div>
    `;
  }

  function renderPredictionCard({ combination, prediction }, index) {
    const favouriteLabel = state.favourites.includes(combination.id) ? '<span class="tag">Following</span>' : "";

    return `
      <article class="event-card ${index === 0 ? "featured" : ""}">
        <div class="card-top">
          <span class="rank">#${index + 1}</span>
          <span class="risk ${prediction.risk}">${prediction.risk} risk</span>
        </div>
        <div>
          <h3>${combination.rider} + ${combination.horse}</h3>
          <p>${combination.country}</p>
        </div>
        <p class="prediction-score">${prediction.predictedScore} penalties</p>
        <div class="prediction-meta">
          <span>${prediction.confidence}% confidence</span>
          <span>Range ${prediction.scoreRange.low}-${prediction.scoreRange.high}</span>
          <span>Data quality ${prediction.factors.dataQuality}%</span>
          ${favouriteLabel}
        </div>
      </article>
    `;
  }

  function renderGuessForm() {
    const selectedEvent = getEvent(elements.guessEvent.value || state.selectedEventId);
    const country = elements.guessCountry.value || selectedEvent.countries[0];

    elements.guessEvent.innerHTML = events
      .map((event) => `<option value="${event.id}" ${event.id === selectedEvent.id ? "selected" : ""}>${event.name}</option>`)
      .join("");
    elements.guessCountry.innerHTML = selectedEvent.countries
      .map((item) => `<option value="${item}" ${item === country ? "selected" : ""}>${item}</option>`)
      .join("");

    const key = getGuessKey(selectedEvent.id, country);
    const savedIds = state.guesses[key] || [];
    const recommended = getTeamRecommendations(riderCombinations, selectedEvent, country);
    const options = riderCombinations
      .filter((combination) => combination.country === country)
      .map((combination) => {
        const prediction = recommended.find((entry) => entry.combination.id === combination.id)?.prediction;
        const predictionText = prediction ? ` · forecast ${prediction.predictedScore}` : "";
        return `
          <label>
            <input type="checkbox" name="team-combination" value="${combination.id}" ${savedIds.includes(combination.id) ? "checked" : ""} />
            <span>${combination.rider} + ${combination.horse}${predictionText}</span>
          </label>
        `;
      })
      .join("");

    elements.guessOptions.innerHTML = options || "<p>No combinations for this country yet.</p>";
  }

  function renderSavedGuesses() {
    const entries = Object.entries(state.guesses).filter(([, ids]) => ids.length > 0);

    if (entries.length === 0) {
      elements.savedGuesses.innerHTML = '<p class="muted-text">No saved guesses yet. Pick an event, country, and up to four combinations.</p>';
      return;
    }

    elements.savedGuesses.innerHTML = entries
      .map(([key, ids]) => {
        const [eventId, country] = key.split("::");
        const event = getEvent(eventId);
        const names = ids
          .map(getCombination)
          .filter(Boolean)
          .map((combination) => `${combination.rider} + ${combination.horse}`);

        return `
          <article class="saved-guess">
            <h4>${country} · ${event.name}</h4>
            <div class="guess-tags">
              ${names.map((name) => `<span class="tag">${name}</span>`).join("")}
            </div>
          </article>
        `;
      })
      .join("");
  }

  function getGuessKey(eventId, country) {
    return `${eventId}::${country}`;
  }

  function bindEvents() {
    elements.menuToggle.addEventListener("click", () => {
      const isOpen = elements.navLinks.classList.toggle("open");
      elements.menuToggle.setAttribute("aria-expanded", String(isOpen));
    });

    elements.navLinks.addEventListener("click", () => {
      elements.navLinks.classList.remove("open");
      elements.menuToggle.setAttribute("aria-expanded", "false");
    });

    elements.combinationSearch.addEventListener("input", renderCombinations);

    document.addEventListener("click", (event) => {
      const favouriteButton = event.target.closest("[data-favourite]");
      const eventButton = event.target.closest("[data-event-tab]");

      if (favouriteButton) {
        toggleFavourite(favouriteButton.dataset.favourite);
      }

      if (eventButton) {
        state.selectedEventId = eventButton.dataset.eventTab;
        elements.guessEvent.value = state.selectedEventId;
        render();
      }
    });

    elements.guessEvent.addEventListener("change", renderGuessForm);
    elements.guessCountry.addEventListener("change", renderGuessForm);

    elements.guessOptions.addEventListener("change", (event) => {
      if (event.target.name !== "team-combination") {
        return;
      }

      const checked = [...elements.guessOptions.querySelectorAll("input:checked")];
      if (checked.length > 4) {
        event.target.checked = false;
        alert("Team guesses are limited to four combinations.");
      }
    });

    elements.guessForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const eventId = elements.guessEvent.value;
      const country = elements.guessCountry.value;
      const ids = [...elements.guessOptions.querySelectorAll("input:checked")].map((input) => input.value);
      state.guesses[getGuessKey(eventId, country)] = ids;
      persist();
      renderStats();
      renderSavedGuesses();
    });

    elements.clearGuesses.addEventListener("click", () => {
      state.guesses = {};
      persist();
      render();
    });
  }

  function toggleFavourite(combinationId) {
    if (state.favourites.includes(combinationId)) {
      state.favourites = state.favourites.filter((id) => id !== combinationId);
    } else {
      state.favourites = [...state.favourites, combinationId];
    }

    persist();
    render();
  }

  bindEvents();
  render();
})(window);
