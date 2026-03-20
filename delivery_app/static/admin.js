const reportGrid = document.getElementById("report-grid");
const reportDrawer = document.getElementById("report-drawer");
const adminStatus = document.getElementById("admin-status");
const filterForm = document.getElementById("admin-filters");
const resetFiltersButton = document.getElementById("reset-filters");
const loadOlderReportsButton = document.getElementById("load-older-reports");
const locationCheckboxGrid = document.getElementById("location-ids");
const usersGrid = document.getElementById("users-grid");
const usersStatus = document.getElementById("users-status");
const userSearchInput = document.getElementById("user-search");
const adminTabs = Array.from(document.querySelectorAll(".admin-tab"));
const adminPanels = {
  reports: document.getElementById("admin-tab-reports"),
  users: document.getElementById("admin-tab-users"),
};

const state = {
  locations: [],
  reports: [],
  users: [],
  selectedReportId: null,
  reportCursor: null,
  hasMoreReports: false,
};

const bangkokFormatter = new Intl.DateTimeFormat("en-GB", {
  timeZone: "Asia/Bangkok",
  hour: "2-digit",
  minute: "2-digit",
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour12: false,
});

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatBangkokDate(value) {
  if (!value) {
    return "-";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "-";
  }
  const parts = Object.fromEntries(
    bangkokFormatter.formatToParts(parsed).map((part) => [part.type, part.value])
  );
  return `${parts.hour}:${parts.minute} ${parts.day}/${parts.month}/${parts.year}`;
}

function normalizeNumber(value) {
  const numeric = typeof value === "number" ? value : Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function formatCoordinate(value) {
  const numeric = normalizeNumber(value);
  return numeric === null ? "-" : numeric.toFixed(5);
}

function formatAccuracy(value) {
  const numeric = normalizeNumber(value);
  return numeric === null ? "-" : `${Math.round(numeric)} m`;
}

function buildMapUrl(latitude, longitude) {
  const lat = normalizeNumber(latitude);
  const lng = normalizeNumber(longitude);
  if (lat === null || lng === null) {
    return null;
  }
  return `https://www.google.com/maps?q=${lat},${lng}`;
}

function buildVariantUrl(photoUrl, variant) {
  return `${photoUrl}${photoUrl.includes("?") ? "&" : "?"}variant=${variant}`;
}

function getSelectedLocationIds() {
  return Array.from(locationCheckboxGrid.querySelectorAll('input[type="checkbox"]:checked')).map((input) => input.value);
}

function buildLocationChip(location, selectedIds = []) {
  const checked = selectedIds.includes(location.id) ? "checked" : "";
  return `
    <label class="sidebar-check">
      <input type="checkbox" value="${escapeHtml(location.id)}" ${checked}>
      <span>${escapeHtml(location.name)}</span>
    </label>
  `;
}

function setActiveTab(tabName) {
  adminTabs.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.tab === tabName);
  });
  Object.entries(adminPanels).forEach(([name, panel]) => {
    panel.classList.toggle("hidden", name !== tabName);
  });
}

function populateLocations(locations) {
  locationCheckboxGrid.innerHTML = locations.map((location) => buildLocationChip(location)).join("");
}

function getSelectedReport() {
  return state.reports.find((report) => report.id === state.selectedReportId) || null;
}

function syncSelectedReportCard() {
  const selectedId = state.selectedReportId;
  Array.from(reportGrid.querySelectorAll(".report-card")).forEach((card) => {
    card.classList.toggle("is-active", Number(card.dataset.reportId) === selectedId);
  });
}

function renderReportDrawer(report) {
  if (!report) {
    reportDrawer.classList.add("is-empty");
    reportDrawer.innerHTML = `
      <div class="drawer-empty">
        <p class="toolbar-label">Preview</p>
        <h2>Select a report</h2>
        <p>Pick any photo to inspect the visit details.</p>
      </div>
    `;
    return;
  }

  const mapUrl = buildMapUrl(report.latitude, report.longitude);
  const displayUrl = buildVariantUrl(report.photoUrl, "display");
  reportDrawer.classList.remove("is-empty");
  reportDrawer.innerHTML = `
    <div class="drawer-head">
      <div>
        <p class="toolbar-label">Visit detail</p>
        <h2>${escapeHtml(report.customerName)}</h2>
      </div>
      <span class="drawer-location">${escapeHtml(report.locationName)}</span>
    </div>
    <a class="drawer-photo-link" href="${escapeHtml(report.photoUrl)}" target="_blank" rel="noreferrer">
      <img class="drawer-photo" src="${escapeHtml(displayUrl)}" alt="Visit report photo">
    </a>
    <div class="drawer-actions">
      ${mapUrl ? `<a class="secondary-button drawer-button" href="${escapeHtml(mapUrl)}" target="_blank" rel="noreferrer">Map</a>` : ""}
      <a class="ghost-button drawer-button" href="${escapeHtml(report.photoUrl)}" target="_blank" rel="noreferrer">Original</a>
    </div>
    <dl class="drawer-meta">
      <div>
        <dt>User</dt>
        <dd>${escapeHtml(report.userName)}</dd>
      </div>
      <div>
        <dt>Location</dt>
        <dd>${escapeHtml(report.locationName)}</dd>
      </div>
      <div>
        <dt>Taken</dt>
        <dd>${formatBangkokDate(report.capturedAtClient)}</dd>
      </div>
      <div>
        <dt>Saved</dt>
        <dd>${formatBangkokDate(report.receivedAtServer)}</dd>
      </div>
      <div>
        <dt>Lat</dt>
        <dd>${formatCoordinate(report.latitude)}</dd>
      </div>
      <div>
        <dt>Lng</dt>
        <dd>${formatCoordinate(report.longitude)}</dd>
      </div>
      <div>
        <dt>Acc</dt>
        <dd>${formatAccuracy(report.accuracyM)}</dd>
      </div>
      <div>
        <dt>LINE ID</dt>
        <dd>${escapeHtml(report.lineUserId)}</dd>
      </div>
    </dl>
  `;
}

function renderReports(reports) {
  state.reports = reports;
  reportGrid.innerHTML = "";

  if (!reports.length) {
    state.selectedReportId = null;
    adminStatus.textContent = "No reports found for the current filters.";
    renderReportDrawer(null);
    return;
  }

  adminStatus.textContent = `${reports.length} report(s) loaded.`;
  if (!reports.some((report) => report.id === state.selectedReportId)) {
    state.selectedReportId = reports[0].id;
  }

  reports.forEach((report) => {
    const card = document.createElement("article");
    card.className = "report-card";
    card.dataset.reportId = String(report.id);
    card.innerHTML = `
      <button class="report-card-button" type="button">
        <div class="report-thumb-wrap">
          <img
            src="${escapeHtml(buildVariantUrl(report.photoUrl, "thumb"))}"
            alt="Visit report photo"
            loading="lazy"
            decoding="async"
          >
          <span class="report-card-location">${escapeHtml(report.locationName)}</span>
        </div>
        <div class="report-card-copy">
          <h3>${escapeHtml(report.customerName)}</h3>
          <p class="report-card-user">${escapeHtml(report.userName)}</p>
          <p class="report-card-time">${formatBangkokDate(report.capturedAtClient)}</p>
        </div>
      </button>
    `;
    card.querySelector(".report-card-button").addEventListener("click", () => {
      state.selectedReportId = report.id;
      syncSelectedReportCard();
      renderReportDrawer(report);
    });
    reportGrid.appendChild(card);
  });

  syncSelectedReportCard();
  renderReportDrawer(getSelectedReport());
}

function appendReports(reports) {
  if (!reports.length) {
    return;
  }

  const existingIds = new Set(state.reports.map((report) => report.id));
  const merged = state.reports.concat(reports.filter((report) => !existingIds.has(report.id)));
  renderReports(merged);
}

function buildUserLocationChips(user) {
  return state.locations
    .map((location) => {
      const checked = user.allowedLocationIds.includes(location.id) ? "checked" : "";
      return `
        <label class="choice-chip">
          <input type="checkbox" value="${escapeHtml(location.id)}" ${checked}>
          <span>${escapeHtml(location.name)}</span>
        </label>
      `;
    })
    .join("");
}

function buildUserAccessMode(user) {
  return `
    <div class="segment-control" role="radiogroup" aria-label="Location access">
      <label class="segment-option">
        <input type="radio" name="access-${escapeHtml(user.lineUserId)}" value="all" ${user.accessMode === "all" ? "checked" : ""}>
        <span>All locations</span>
      </label>
      <label class="segment-option">
        <input type="radio" name="access-${escapeHtml(user.lineUserId)}" value="assigned" ${user.accessMode === "assigned" ? "checked" : ""}>
        <span>Selected locations</span>
      </label>
    </div>
  `;
}

function getUserCardAccessMode(card) {
  return card.querySelector('input[type="radio"]:checked')?.value || "all";
}

function getUserCardSelectedLocationIds(card) {
  return Array.from(card.querySelectorAll('.user-location-checkboxes input[type="checkbox"]:checked'))
    .map((input) => input.value)
    .sort();
}

function isUserCardDirty(card) {
  const originalMode = card.dataset.originalMode || "all";
  const originalIds = (card.dataset.originalLocationIds || "").split(",").filter(Boolean);
  const currentMode = getUserCardAccessMode(card);
  const currentIds = currentMode === "assigned" ? getUserCardSelectedLocationIds(card) : [];
  return originalMode !== currentMode || originalIds.join(",") !== currentIds.join(",");
}

function syncUserCardState(card) {
  const accessMode = getUserCardAccessMode(card);
  const locationField = card.querySelector(".user-location-field");
  const locationInputs = Array.from(card.querySelectorAll('.user-location-checkboxes input[type="checkbox"]'));
  const accessBadge = card.querySelector(".access-badge");
  const saveState = card.querySelector(".save-state");
  const saveButton = card.querySelector(".user-save-button");
  const isAssigned = accessMode === "assigned";

  locationField.classList.toggle("is-disabled", !isAssigned);
  locationInputs.forEach((input) => {
    input.disabled = !isAssigned;
  });

  accessBadge.textContent = isAssigned ? "Selected locations" : "All locations";
  accessBadge.classList.toggle("is-assigned", isAssigned);
  accessBadge.classList.toggle("is-all", !isAssigned);

  const dirty = isUserCardDirty(card);
  saveState.textContent = dirty ? "Unsaved changes" : "Saved";
  saveState.classList.toggle("is-dirty", dirty);
  saveButton.disabled = !dirty;
}

function renderUsers(users) {
  const query = userSearchInput.value.trim().toLowerCase();
  const visibleUsers = users.filter((user) => {
    if (!query) {
      return true;
    }
    return (
      user.displayName.toLowerCase().includes(query) ||
      user.lineUserId.toLowerCase().includes(query)
    );
  });

  usersGrid.innerHTML = "";
  if (!users.length) {
    usersStatus.textContent = "No logged-in users yet.";
    return;
  }

  usersStatus.textContent = query
    ? `${visibleUsers.length} of ${users.length} user(s)`
    : `${users.length} user(s) loaded.`;

  if (!visibleUsers.length) {
    usersGrid.innerHTML = '<div class="empty-state">No users match this search.</div>';
    return;
  }

  visibleUsers.forEach((user) => {
    const card = document.createElement("article");
    card.className = "user-card";
    card.dataset.lineUserId = user.lineUserId;
    card.dataset.originalMode = user.accessMode;
    card.dataset.originalLocationIds = user.allowedLocationIds.slice().sort().join(",");
    card.innerHTML = `
      <div class="user-card-main">
        <div class="user-identity">
          <div class="user-title-row">
            <h3>${escapeHtml(user.displayName)}</h3>
            <span class="user-status">${escapeHtml(user.status)}</span>
          </div>
          <p class="user-subline">${escapeHtml(user.lineUserId)}</p>
          <p class="user-subline">Last login ${formatBangkokDate(user.lastLoginAt)}</p>
        </div>
        <span class="access-badge ${user.accessMode === "assigned" ? "is-assigned" : "is-all"}">
          ${user.accessMode === "assigned" ? "Selected locations" : "All locations"}
        </span>
      </div>
      <div class="user-access-shell">
        ${buildUserAccessMode(user)}
        <label class="field user-location-field">
          <span>Locations</span>
          <div class="chip-filter-grid user-location-checkboxes">
            ${buildUserLocationChips(user)}
          </div>
        </label>
      </div>
      <div class="user-actions-row">
        <span class="save-state">Saved</span>
        <button class="primary-button user-save-button" type="button" disabled>Save</button>
      </div>
    `;

    const modeInputs = Array.from(card.querySelectorAll('.segment-control input[type="radio"]'));
    const locationInputs = Array.from(card.querySelectorAll('.user-location-checkboxes input[type="checkbox"]'));
    const saveButton = card.querySelector(".user-save-button");

    modeInputs.forEach((input) => {
      input.addEventListener("change", () => {
        syncUserCardState(card);
      });
    });
    locationInputs.forEach((input) => {
      input.addEventListener("change", () => {
        syncUserCardState(card);
      });
    });

    saveButton.addEventListener("click", async () => {
      const selectedMode = getUserCardAccessMode(card);
      const selectedLocationIds = selectedMode === "assigned" ? getUserCardSelectedLocationIds(card) : [];
      saveButton.disabled = true;
      saveButton.textContent = "Saving...";
      try {
        const response = await fetch(`/admin/access/users/${encodeURIComponent(user.lineUserId)}/locations`, {
          method: "PUT",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            access_mode: selectedMode,
            location_ids: selectedLocationIds,
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail || "Failed to save user access.");
        }

        card.dataset.originalMode = payload.accessMode;
        card.dataset.originalLocationIds = payload.allowedLocationIds.slice().sort().join(",");
        const userIndex = state.users.findIndex((candidate) => candidate.lineUserId === user.lineUserId);
        if (userIndex >= 0) {
          state.users[userIndex] = {
            ...state.users[userIndex],
            accessMode: payload.accessMode,
            allowedLocationIds: payload.allowedLocationIds,
          };
        }
        usersStatus.textContent = `Saved ${user.displayName}.`;
        syncUserCardState(card);
      } catch (error) {
        usersStatus.textContent = error.message || "Failed to save user access.";
      } finally {
        saveButton.textContent = "Save";
        syncUserCardState(card);
      }
    });

    usersGrid.appendChild(card);
    syncUserCardState(card);
  });
}

async function loadLocations() {
  const response = await fetch("/admin/locations", { credentials: "include" });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Failed to load locations.");
  }
  state.locations = payload.locations;
  populateLocations(payload.locations);
  if (state.users.length) {
    renderUsers(state.users);
  }
}

async function loadUsers() {
  usersStatus.textContent = "Loading users...";
  const response = await fetch("/admin/access/users", { credentials: "include" });
  const payload = await response.json();
  if (!response.ok) {
    usersStatus.textContent = payload.detail || "Failed to load users.";
    return;
  }
  state.users = payload.users;
  renderUsers(payload.users);
}

async function loadReports(event) {
  return requestReports({ reset: true, event });
}

function buildReportParams() {
  const formData = new FormData(filterForm);
  const params = new URLSearchParams();
  for (const [key, value] of formData.entries()) {
    const text = String(value).trim();
    if (key !== "location_ids" && text) {
      params.append(key, text);
    }
  }
  getSelectedLocationIds().forEach((locationId) => params.append("location_ids", locationId));
  return params;
}

function syncLoadOlderButton() {
  loadOlderReportsButton.classList.toggle("hidden", !state.hasMoreReports);
  loadOlderReportsButton.disabled = !state.hasMoreReports;
}

async function requestReports({ reset, event } = {}) {
  if (event) {
    event.preventDefault();
  }

  const params = buildReportParams();
  if (!reset && state.reportCursor?.beforeReceivedAt) {
    params.append("before_received_at", state.reportCursor.beforeReceivedAt);
    params.append("before_id", state.reportCursor.beforeId);
  }
  adminStatus.textContent = reset ? "Loading reports..." : "Loading older reports...";
  if (!reset) {
    loadOlderReportsButton.disabled = true;
    loadOlderReportsButton.textContent = "Loading...";
  }
  const response = await fetch(`/admin/reports?${params.toString()}`, { credentials: "include" });
  const payload = await response.json();
  if (!response.ok) {
    adminStatus.textContent = payload.detail || "Failed to load reports.";
    if (!reset) {
      loadOlderReportsButton.textContent = "Load Older";
      syncLoadOlderButton();
    }
    return;
  }
  state.reportCursor = payload.nextCursor || null;
  state.hasMoreReports = Boolean(payload.hasMore);
  if (reset) {
    renderReports(payload.reports);
  } else {
    appendReports(payload.reports);
  }
  syncLoadOlderButton();
  if (!reset) {
    loadOlderReportsButton.textContent = "Load Older";
  }
}

filterForm.addEventListener("submit", loadReports);
loadOlderReportsButton.addEventListener("click", () => {
  requestReports({ reset: false }).catch((error) => {
    adminStatus.textContent = error.message || "Failed to load older reports.";
    loadOlderReportsButton.textContent = "Load Older";
    syncLoadOlderButton();
  });
});
resetFiltersButton.addEventListener("click", () => {
  filterForm.reset();
  Array.from(locationCheckboxGrid.querySelectorAll('input[type="checkbox"]')).forEach((input) => {
    input.checked = false;
  });
  requestReports({ reset: true }).catch((error) => {
    adminStatus.textContent = error.message || "Failed to load reports.";
  });
});

userSearchInput.addEventListener("input", () => {
  renderUsers(state.users);
});

adminTabs.forEach((button) => {
  button.addEventListener("click", () => {
    setActiveTab(button.dataset.tab);
    if (button.dataset.tab === "users") {
      loadUsers().catch((error) => {
        usersStatus.textContent = error.message || "Failed to load users.";
      });
    }
  });
});

Promise.all([loadLocations(), loadReports()]).catch((error) => {
  adminStatus.textContent = error.message || "Failed to load admin data.";
});
