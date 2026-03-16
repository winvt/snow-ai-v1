const reportGrid = document.getElementById("report-grid");
const adminStatus = document.getElementById("admin-status");
const filterForm = document.getElementById("admin-filters");
const locationSelect = document.getElementById("location-ids");
const usersGrid = document.getElementById("users-grid");
const usersStatus = document.getElementById("users-status");
const adminTabs = Array.from(document.querySelectorAll(".admin-tab"));
const adminPanels = {
  reports: document.getElementById("admin-tab-reports"),
  users: document.getElementById("admin-tab-users"),
};
const state = {
  locations: [],
  users: [],
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

function formatCoordinate(value) {
  return Number.isFinite(value) ? value.toFixed(5) : "-";
}

function buildMapUrl(latitude, longitude) {
  return `https://www.google.com/maps?q=${latitude},${longitude}`;
}

function getSelectedLocationIds() {
  return Array.from(locationSelect.selectedOptions).map((option) => option.value);
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
  locationSelect.innerHTML = "";
  locations.forEach((location) => {
    const option = document.createElement("option");
    option.value = location.id;
    option.textContent = location.name;
    locationSelect.appendChild(option);
  });
}

function renderReports(reports) {
  reportGrid.innerHTML = "";
  if (!reports.length) {
    adminStatus.textContent = "No reports found for the current filters.";
    return;
  }
  adminStatus.textContent = `${reports.length} report(s) loaded.`;
  reports.forEach((report) => {
    const card = document.createElement("article");
    card.className = "report-card";
    const accuracy = Number.isFinite(report.accuracyM) ? `${Math.round(report.accuracyM)} m` : "-";
    card.innerHTML = `
      <img src="${report.photoUrl}" alt="Visit report photo">
      <h3>${report.customerName}</h3>
      <p>${report.locationName}</p>
      <p>By ${report.userName}</p>
      <div class="report-meta">
        <p><strong>Taken</strong> ${formatBangkokDate(report.capturedAtClient)}</p>
        <p><strong>Saved</strong> ${formatBangkokDate(report.receivedAtServer)}</p>
        <p><strong>Lat</strong> ${formatCoordinate(report.latitude)}</p>
        <p><strong>Lng</strong> ${formatCoordinate(report.longitude)}</p>
        <p><strong>Acc</strong> ${accuracy}</p>
      </div>
      <a class="map-link" href="${buildMapUrl(report.latitude, report.longitude)}" target="_blank" rel="noreferrer">Map</a>
    `;
    reportGrid.appendChild(card);
  });
}

function buildUserLocationOptions(user) {
  return state.locations
    .map((location) => {
      const selected = user.allowedLocationIds.includes(location.id) ? "selected" : "";
      return `<option value="${location.id}" ${selected}>${location.name}</option>`;
    })
    .join("");
}

function updateUserCardState(card, accessMode) {
  const locationField = card.querySelector(".user-location-field");
  const select = card.querySelector(".user-location-select");
  const disabled = accessMode !== "assigned";
  locationField.classList.toggle("is-disabled", disabled);
  select.disabled = disabled;
}

function renderUsers(users) {
  usersGrid.innerHTML = "";
  if (!users.length) {
    usersStatus.textContent = "No logged-in users yet.";
    return;
  }

  usersStatus.textContent = `${users.length} user(s) loaded.`;
  users.forEach((user) => {
    const card = document.createElement("article");
    card.className = "user-card";
    card.dataset.lineUserId = user.lineUserId;
    card.innerHTML = `
      <div class="user-card-head">
        <div>
          <h3>${user.displayName}</h3>
          <p class="user-subline">${user.lineUserId}</p>
        </div>
        <span class="user-status">${user.status}</span>
      </div>
      <p class="user-subline">Last login ${formatBangkokDate(user.lastLoginAt)}</p>
      <label class="field">
        <span>Access</span>
        <select class="user-access-mode">
          <option value="all" ${user.accessMode === "all" ? "selected" : ""}>All locations</option>
          <option value="assigned" ${user.accessMode === "assigned" ? "selected" : ""}>Selected locations</option>
        </select>
      </label>
      <label class="field user-location-field ${user.accessMode === "assigned" ? "" : "is-disabled"}">
        <span>Locations</span>
        <select class="user-location-select" multiple size="6" ${user.accessMode === "assigned" ? "" : "disabled"}>
          ${buildUserLocationOptions(user)}
        </select>
      </label>
      <button class="primary-button user-save-button" type="button">Save</button>
    `;

    const accessModeSelect = card.querySelector(".user-access-mode");
    accessModeSelect.addEventListener("change", (event) => {
      updateUserCardState(card, event.target.value);
    });

    card.querySelector(".user-save-button").addEventListener("click", async () => {
      const selectedMode = accessModeSelect.value;
      const selectedLocationIds = Array.from(card.querySelector(".user-location-select").selectedOptions).map(
        (option) => option.value
      );
      const button = card.querySelector(".user-save-button");
      button.disabled = true;
      button.textContent = "Saving...";
      try {
        const response = await fetch(`/admin/access/users/${encodeURIComponent(user.lineUserId)}/locations`, {
          method: "PUT",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            access_mode: selectedMode,
            location_ids: selectedMode === "assigned" ? selectedLocationIds : [],
          }),
        });
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail || "Failed to save user access.");
        }
        usersStatus.textContent = `Saved ${user.displayName}.`;
        await loadUsers();
      } catch (error) {
        usersStatus.textContent = error.message || "Failed to save user access.";
      } finally {
        button.disabled = false;
        button.textContent = "Save";
      }
    });

    usersGrid.appendChild(card);
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
  if (event) {
    event.preventDefault();
  }
  const formData = new FormData(filterForm);
  formData.delete("location_ids");
  const params = new URLSearchParams(formData);
  getSelectedLocationIds().forEach((locationId) => params.append("location_ids", locationId));
  adminStatus.textContent = "Loading reports...";
  const response = await fetch(`/admin/reports?${params.toString()}`, { credentials: "include" });
  const payload = await response.json();
  if (!response.ok) {
    adminStatus.textContent = payload.detail || "Failed to load reports.";
    return;
  }
  renderReports(payload.reports);
}

filterForm.addEventListener("submit", loadReports);
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

Promise.all([loadLocations(), loadReports()])
  .catch((error) => {
    adminStatus.textContent = error.message || "Failed to load admin data.";
  });
