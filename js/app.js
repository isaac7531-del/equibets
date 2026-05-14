(function initialiseApp(global) {
  const { feiSearchPages, riderCombinations, allResultRows, events } = global.EquiBetsData;
  const { rankEventPredictions, getTeamRecommendations } = global.EquiBetsModel;
  const storage = global.localStorage;
  const favouriteKey = "equibets:favourites";
  const guessKey = "equibets:team-guesses";

  const state = {
    favourites: readStoredArray(favouriteKey),
    guesses: readStoredObject(guessKey),
    selectedEventId: events[0].id,
    selectedEventLevel: "all",
    selectedResultId: riderCombinations[0].id,
    globalQuery: "",
    globalFilter: "all"
  };

  const elements = {
    heroPick: document.querySelector("#hero-pick"),
    heroScore: document.querySelector("#hero-score"),
    heroConfidence: document.querySelector("#hero-confidence"),
    statsGrid: document.querySelector("#stats-grid"),
    combinationGrid: document.querySelector("#combination-grid"),
    combinationSearch: document.querySelector("#combination-search"),
    globalSearch: document.querySelector("#global-search"),
    globalSearchTabs: document.querySelector("#global-search-tabs"),
    databaseSummary: document.querySelector("#database-summary"),
    allRidersList: document.querySelector("#all-riders-list"),
    allResultsList: document.querySelector("#all-results-list"),
    eventTabs: document.querySelector("#event-tabs"),
    eventLevelTabs: document.querySelector("#event-level-tabs"),
    eventPanel: document.querySelector("#event-panel"),
    starEventGrid: document.querySelector("#star-event-grid"),
    resultsCombination: document.querySelector("#results-combination"),
    resultDetail: document.querySelector("#result-detail"),
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
    renderGlobalSearch();
    renderResultsPicker();
    renderResultDetail();
    renderEventLevelTabs();
    renderEventTabs();
    renderEventPanel();
    renderStarEvents();
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
    const fiveStarCount = events.filter((event) => event.level === "5-star").length;
    const fourStarCount = events.filter((event) => event.level === "4-star").length;
    elements.statsGrid.innerHTML = [
      statCard("Followed combinations", state.favourites.length, "Saved favourites stay highlighted everywhere."),
      statCard("Result rows", allResultRows.length, "Searchable rider and event history records."),
      statCard("Upcoming events", events.length, "Includes championships plus 5-star and 4-star events."),
      statCard(
        "Best predicted score",
        topPrediction.prediction.predictedScore,
        `${topPrediction.combination.rider} at ${topEvent.name}.`
      ),
      statCard("Saved team guesses", guessesCount, "Event and country selections stored locally."),
      statCard("Star events", fiveStarCount + fourStarCount, "5-star and 4-star form checks.")
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
          <a class="button secondary" href="#results" data-result-link="${combination.id}">
            Previous results
          </a>
          <a class="button ghost" href="${feiSearchPages.rankings}" target="_blank" rel="noreferrer">
            FEI rankings
          </a>
        </div>
      </article>
    `;
  }

  function metric(label, value) {
    return `<div class="metric"><strong>${value}</strong><span>${label}</span></div>`;
  }

  function renderGlobalSearch() {
    const riders = getFilteredRiders();
    const results = getFilteredResults();
    const showRiders = state.globalFilter === "all" || state.globalFilter === "riders";
    const showResults = state.globalFilter === "all" || state.globalFilter === "results";

    elements.globalSearchTabs.innerHTML = [
      { id: "all", label: "All" },
      { id: "riders", label: "Riders" },
      { id: "results", label: "Results" }
    ]
      .map(
        (filter) => `
          <button class="tab-button" type="button" role="tab" data-global-filter="${filter.id}" aria-selected="${filter.id === state.globalFilter}">
            ${filter.label}
          </button>
        `
      )
      .join("");

    elements.databaseSummary.innerHTML = `
      <article class="stat-card">
        <span>Search scope</span>
        <strong>${riders.length + results.length}</strong>
        <p>${riders.length} rider combinations and ${results.length} result rows match${state.globalQuery ? ` "${state.globalQuery}"` : ""}.</p>
      </article>
    `;

    elements.allRidersList.parentElement.hidden = !showRiders;
    elements.allResultsList.parentElement.hidden = !showResults;
    elements.allRidersList.innerHTML = riders.length
      ? riders.map(renderRiderSearchResult).join("")
      : '<p class="muted-text">No riders match this search.</p>';
    elements.allResultsList.innerHTML = results.length
      ? results.map(renderResultSearchRow).join("")
      : '<p class="muted-text">No results match this search.</p>';
  }

  function getFilteredRiders() {
    const query = state.globalQuery.trim().toLowerCase();
    if (!query) {
      return riderCombinations;
    }

    return riderCombinations.filter((combination) =>
      `${combination.rider} ${combination.horse} ${combination.country} ${combination.shortCountry}`
        .toLowerCase()
        .includes(query)
    );
  }

  function getFilteredResults() {
    const query = state.globalQuery.trim().toLowerCase();
    if (!query) {
      return allResultRows;
    }

    return allResultRows.filter((result) =>
      `${result.rider} ${result.horse} ${result.country} ${result.shortCountry} ${result.event} ${result.level} ${result.year} ${result.placing}`
        .toLowerCase()
        .includes(query)
    );
  }

  function renderRiderSearchResult(combination) {
    return `
      <article class="search-result-card">
        <div>
          <span class="tag">${combination.shortCountry}</span>
          <h4>${combination.rider} + ${combination.horse}</h4>
          <p>${combination.country} · ${combination.previousResults.length} result rows</p>
        </div>
        <a class="button secondary" href="#results" data-result-link="${combination.id}">Open results</a>
      </article>
    `;
  }

  function renderResultSearchRow(result) {
    return `
      <article class="search-result-card">
        <div>
          <span class="tag">${result.level}</span>
          <h4>${result.rider} + ${result.horse}</h4>
          <p>${result.year} ${result.event} · ${result.placing} · ${result.finishingScore.toFixed(1)} penalties</p>
        </div>
        <a class="button ghost" href="${result.sourceUrl}" target="_blank" rel="noreferrer">${result.source}</a>
      </article>
    `;
  }

  function renderResultsPicker() {
    elements.resultsCombination.innerHTML = riderCombinations
      .map(
        (combination) =>
          `<option value="${combination.id}" ${combination.id === state.selectedResultId ? "selected" : ""}>${combination.rider} + ${combination.horse}</option>`
      )
      .join("");
  }

  function renderResultDetail() {
    const combination = getCombination(state.selectedResultId) || riderCombinations[0];
    const results = [...combination.previousResults].sort((left, right) => right.year - left.year);
    const bestScore = Math.min(...results.map((result) => result.finishingScore));
    const averageScore = results.reduce((total, result) => total + result.finishingScore, 0) / results.length;

    elements.resultDetail.innerHTML = `
      <article class="result-profile">
        <div>
          <p class="eyebrow">${combination.shortCountry} result page</p>
          <h3>${combination.rider} + ${combination.horse}</h3>
          <p>${combination.notes}</p>
          <div class="source-links" aria-label="FEI lookup links">
            <a href="${feiSearchPages.person}" target="_blank" rel="noreferrer">FEI Person Search</a>
            <a href="${feiSearchPages.horse}" target="_blank" rel="noreferrer">FEI Horse Search</a>
            <a href="${feiSearchPages.calendar}" target="_blank" rel="noreferrer">FEI Calendar Search</a>
            <a href="${feiSearchPages.rankings}" target="_blank" rel="noreferrer">FEI World Rankings</a>
          </div>
        </div>
        <div class="metrics">
          ${metric("Best", bestScore.toFixed(1))}
          ${metric("Average", averageScore.toFixed(1))}
          ${metric("Starts", results.length)}
        </div>
      </article>
      <div class="result-table-wrap">
        <table class="result-table">
          <thead>
            <tr>
              <th>Year</th>
              <th>Event</th>
              <th>Level</th>
              <th>Placing</th>
              <th>Final</th>
              <th>Dressage</th>
              <th>XC</th>
              <th>SJ</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            ${results
              .map(
                (result) => `
                  <tr>
                    <td>${result.year}</td>
                    <td>${result.event}</td>
                    <td><span class="tag">${result.level}</span></td>
                    <td>${result.placing}</td>
                    <td>${result.finishingScore.toFixed(1)}</td>
                    <td>${result.dressage.toFixed(1)}</td>
                    <td>${result.crossCountry.toFixed(1)}</td>
                    <td>${result.showJumping.toFixed(1)}</td>
                    <td><a href="${result.sourceUrl}" target="_blank" rel="noreferrer">${result.source || "FEI lookup"}</a></td>
                  </tr>
                `
              )
              .join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  function getFilteredEvents() {
    if (state.selectedEventLevel === "all") {
      return events;
    }

    return events.filter((event) => event.level === state.selectedEventLevel);
  }

  function renderEventLevelTabs() {
    const levels = [
      { id: "all", label: "All events" },
      { id: "championship", label: "Championships" },
      { id: "5-star", label: "5-star" },
      { id: "4-star", label: "4-star" }
    ];

    elements.eventLevelTabs.innerHTML = levels
      .map(
        (level) => `
          <button class="tab-button level-tab" type="button" role="tab" data-event-level="${level.id}" aria-selected="${level.id === state.selectedEventLevel}">
            ${level.label}
          </button>
        `
      )
      .join("");
  }

  function renderEventTabs() {
    const filteredEvents = getFilteredEvents();

    if (!filteredEvents.some((event) => event.id === state.selectedEventId)) {
      state.selectedEventId = filteredEvents[0]?.id || events[0].id;
    }

    elements.eventTabs.innerHTML = filteredEvents
      .map(
        (event) => `
          <button class="tab-button" type="button" role="tab" data-event-tab="${event.id}" aria-selected="${event.id === state.selectedEventId}">
            ${event.name} · ${formatLevel(event.level)}
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
          <p>${event.venue} · ${formatLevel(event.level)}</p>
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

  function renderStarEvents() {
    const starEvents = events.filter((event) => event.level === "5-star" || event.level === "4-star");
    const grouped = ["5-star", "4-star"]
      .map((level) => {
        const cards = starEvents
          .filter((event) => event.level === level)
          .map((event) => {
            const topPrediction = rankEventPredictions(riderCombinations, event)[0];
            return `
              <article class="star-event-card">
                <span class="tag">${formatLevel(event.level)}</span>
                <h3>${event.name}</h3>
                <p>${event.venue} · ${event.date}</p>
                <p>${event.summary}</p>
                <div class="metrics">
                  ${metric("Top forecast", topPrediction.prediction.predictedScore)}
                  ${metric("Confidence", `${topPrediction.prediction.confidence}%`)}
                  ${metric("Pressure", event.pressure)}
                </div>
                <button class="button ghost" type="button" data-open-event="${event.id}">View predictions</button>
              </article>
            `;
          })
          .join("");

        return `
          <section class="star-event-group" aria-label="${formatLevel(level)} events">
            <h3>${formatLevel(level)} events</h3>
            <div class="card-grid">${cards}</div>
          </section>
        `;
      })
      .join("");

    elements.starEventGrid.innerHTML = grouped;
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

  function formatLevel(level) {
    if (level === "5-star") {
      return "5-star";
    }

    if (level === "4-star") {
      return "4-star";
    }

    return "Championship";
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
    elements.globalSearch.addEventListener("input", () => {
      state.globalQuery = elements.globalSearch.value;
      renderGlobalSearch();
    });

    document.addEventListener("click", (event) => {
      const favouriteButton = event.target.closest("[data-favourite]");
      const eventButton = event.target.closest("[data-event-tab]");
      const levelButton = event.target.closest("[data-event-level]");
      const resultLink = event.target.closest("[data-result-link]");
      const openEventButton = event.target.closest("[data-open-event]");
      const globalFilterButton = event.target.closest("[data-global-filter]");

      if (favouriteButton) {
        toggleFavourite(favouriteButton.dataset.favourite);
      }

      if (eventButton) {
        state.selectedEventId = eventButton.dataset.eventTab;
        elements.guessEvent.value = state.selectedEventId;
        render();
      }

      if (levelButton) {
        state.selectedEventLevel = levelButton.dataset.eventLevel;
        render();
      }

      if (globalFilterButton) {
        state.globalFilter = globalFilterButton.dataset.globalFilter;
        renderGlobalSearch();
      }

      if (resultLink) {
        state.selectedResultId = resultLink.dataset.resultLink;
        renderResultsPicker();
        renderResultDetail();
      }

      if (openEventButton) {
        const eventToOpen = getEvent(openEventButton.dataset.openEvent);
        state.selectedEventLevel = eventToOpen.level;
        state.selectedEventId = eventToOpen.id;
        render();
        document.querySelector("#events").scrollIntoView({ behavior: "smooth" });
      }
    });

    elements.resultsCombination.addEventListener("change", () => {
      state.selectedResultId = elements.resultsCombination.value;
      renderResultDetail();
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
