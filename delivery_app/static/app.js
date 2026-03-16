const state = {
  session: null,
  locations: [],
  customers: [],
  selectedLocation: null,
  selectedCustomer: null,
  geo: null,
  recentCustomers: [],
};

const MAX_RECENT_CUSTOMERS = 6;
const statusText = document.getElementById("status-text");
const entryScreen = document.getElementById("screen-entry");
const reportScreen = document.getElementById("screen-report");
const doneScreen = document.getElementById("screen-done");
const locationSheet = document.getElementById("location-sheet");
const locationList = document.getElementById("location-list");
const recentPanel = document.getElementById("recent-panel");
const recentList = document.getElementById("recent-list");
const customerList = document.getElementById("customer-list");
const customerSearch = document.getElementById("customer-search");
const selectedLocationPill = document.getElementById("selected-location-pill");
const selectedCustomerName = document.getElementById("selected-customer-name");
const selectedLocationName = document.getElementById("selected-location-name");
const doneShopName = document.getElementById("done-shop-name");
const photoInput = document.getElementById("photo-input");
const photoPreview = document.getElementById("photo-preview");
const cameraEmpty = document.getElementById("camera-empty");
const geoStatus = document.getElementById("geo-status");

function setStatus(text) {
  statusText.textContent = text;
}

function getUserStorageKey() {
  const userId = state.session?.user?.lineUserId || "guest-preview";
  return `delivery_recent_customers:${userId}`;
}

function readRecentCustomers() {
  try {
    const raw = window.localStorage.getItem(getUserStorageKey());
    state.recentCustomers = raw ? JSON.parse(raw) : [];
  } catch (_error) {
    state.recentCustomers = [];
  }
}

function writeRecentCustomers() {
  window.localStorage.setItem(getUserStorageKey(), JSON.stringify(state.recentCustomers.slice(0, MAX_RECENT_CUSTOMERS)));
}

function showScreen(screen) {
  [entryScreen, reportScreen, doneScreen].forEach((node) => node.classList.add("hidden"));
  screen.classList.remove("hidden");
}

function showLocationSheet(visible) {
  locationSheet.classList.toggle("hidden", !visible);
  locationSheet.setAttribute("aria-hidden", visible ? "false" : "true");
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "include",
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail || "Request failed");
  }
  return payload;
}

async function ensureSession() {
  const session = await api("/api/session");
  state.session = session;
  if (session.authenticated) {
    readRecentCustomers();
    setStatus(session.guestMode ? "Ready" : session.user.displayName);
    return;
  }

  if (!window.liff || !session.liffId) {
    throw new Error("LINE login unavailable");
  }

  await window.liff.init({ liffId: session.liffId });
  if (!window.liff.isLoggedIn()) {
    window.liff.login();
    return;
  }

  const idToken = window.liff.getIDToken();
  if (!idToken) {
    throw new Error("LINE token missing");
  }

  const login = await api("/api/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id_token: idToken }),
  });
  state.session = login;
  readRecentCustomers();
  setStatus(login.user.displayName);
}

function setSelectedLocation(location) {
  state.selectedLocation = location;
  selectedLocationPill.textContent = location?.name || "Pick";
}

function renderLocations() {
  locationList.innerHTML = "";
  if (!state.locations.length) {
    locationList.innerHTML = '<div class="empty-state">No location</div>';
    return;
  }
  const template = document.getElementById("location-item-template");
  state.locations.forEach((location) => {
    const node = template.content.firstElementChild.cloneNode(true);
    node.querySelector(".selection-title").textContent = location.name;
    node.querySelector(".selection-meta").textContent = `${location.customerCount} shops`;
    if (state.selectedLocation && state.selectedLocation.id === location.id) {
      node.classList.add("is-active");
    }
    node.addEventListener("click", () => {
      setSelectedLocation(location);
      showLocationSheet(false);
      loadCustomers().catch((error) => setStatus(error.message));
    });
    locationList.appendChild(node);
  });
}

function renderRecentCustomers() {
  const visibleRecents = state.recentCustomers.filter((customer) => {
    return !state.selectedLocation || customer.locationId === state.selectedLocation.id;
  });

  recentList.innerHTML = "";
  recentPanel.classList.toggle("hidden", visibleRecents.length === 0);
  if (!visibleRecents.length) {
    return;
  }

  const template = document.getElementById("recent-item-template");
  visibleRecents.forEach((customer) => {
    const node = template.content.firstElementChild.cloneNode(true);
    node.querySelector(".selection-title").textContent = customer.name;
    node.querySelector(".selection-meta").textContent = customer.locationName || customer.customerCode || "Shop";
    node.addEventListener("click", () => {
      if (!state.selectedLocation || state.selectedLocation.id !== customer.locationId) {
        const location = state.locations.find((row) => row.id === customer.locationId);
        if (location) {
          setSelectedLocation(location);
          renderLocations();
          loadCustomers(customer.customerId).catch((error) => setStatus(error.message));
          return;
        }
      }
      chooseCustomer(customer);
    });
    recentList.appendChild(node);
  });
}

function renderCustomers() {
  customerList.innerHTML = "";
  if (!state.customers.length) {
    customerList.innerHTML = '<div class="empty-state">No shop</div>';
    return;
  }
  const template = document.getElementById("customer-item-template");
  state.customers.forEach((customer) => {
    const node = template.content.firstElementChild.cloneNode(true);
    node.querySelector(".selection-title").textContent = customer.name;
    node.querySelector(".selection-meta").textContent = customer.customerCode || customer.phone || customer.locationName || "Shop";
    node.addEventListener("click", () => chooseCustomer(customer));
    customerList.appendChild(node);
  });
}

function updateRecentCustomers(customer) {
  const next = [
    {
      customerId: customer.customerId,
      name: customer.name,
      customerCode: customer.customerCode || "",
      phone: customer.phone || "",
      locationId: customer.locationId,
      locationName: customer.locationName || "",
    },
    ...state.recentCustomers.filter((row) => row.customerId !== customer.customerId),
  ];
  state.recentCustomers = next.slice(0, MAX_RECENT_CUSTOMERS);
  writeRecentCustomers();
  renderRecentCustomers();
}

function updateGeoState(status, ready = false) {
  geoStatus.textContent = status;
  geoStatus.classList.toggle("is-ready", ready);
}

function resetCaptureState() {
  photoInput.value = "";
  photoPreview.classList.add("hidden");
  photoPreview.removeAttribute("src");
  cameraEmpty.classList.remove("hidden");
  state.geo = null;
  updateGeoState("GPS NEEDED", false);
}

function previewPhoto(file) {
  if (!file) {
    photoPreview.classList.add("hidden");
    photoPreview.removeAttribute("src");
    cameraEmpty.classList.remove("hidden");
    return;
  }

  const reader = new FileReader();
  reader.onload = () => {
    photoPreview.src = reader.result;
    photoPreview.classList.remove("hidden");
    cameraEmpty.classList.add("hidden");
  };
  reader.readAsDataURL(file);
}

function captureGeolocation() {
  updateGeoState("GPS...", false);
  navigator.geolocation.getCurrentPosition(
    (position) => {
      state.geo = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
      };
      updateGeoState("GPS READY", true);
      setStatus("GPS ready");
    },
    () => {
      state.geo = null;
      updateGeoState("GPS NEEDED", false);
      setStatus("GPS needed");
    },
    { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 }
  );
}

function chooseCustomer(customer) {
  state.selectedCustomer = customer;
  selectedCustomerName.textContent = customer.name;
  selectedLocationName.textContent = customer.locationName || state.selectedLocation?.name || "-";
  resetCaptureState();
  showScreen(reportScreen);
  setStatus(customer.name);
  captureGeolocation();
}

async function loadLocations() {
  const payload = await api("/api/locations");
  state.locations = payload.locations;
  if (!state.selectedLocation && state.locations.length) {
    setSelectedLocation(state.locations[0]);
  } else if (state.selectedLocation) {
    const freshLocation = state.locations.find((row) => row.id === state.selectedLocation.id);
    if (freshLocation) {
      setSelectedLocation(freshLocation);
    }
  }
  renderLocations();
  renderRecentCustomers();
}

async function loadCustomers(focusCustomerId = null) {
  if (!state.selectedLocation) {
    state.customers = [];
    renderCustomers();
    return;
  }

  const params = new URLSearchParams();
  params.set("location_id", state.selectedLocation.id);
  if (customerSearch.value.trim()) {
    params.set("q", customerSearch.value.trim());
  }
  const payload = await api(`/api/customers?${params.toString()}`);
  state.customers = payload.customers;
  renderCustomers();
  renderRecentCustomers();
  showScreen(entryScreen);

  if (focusCustomerId) {
    const customer = payload.customers.find((row) => row.customerId === focusCustomerId);
    if (customer) {
      chooseCustomer(customer);
    }
  }
}

async function submitReport() {
  if (!state.selectedCustomer) {
    throw new Error("Pick shop");
  }
  if (!photoInput.files[0]) {
    throw new Error("Add photo");
  }
  if (!state.geo) {
    throw new Error("Need GPS");
  }

  const data = new FormData();
  data.append("client_submission_id", crypto.randomUUID());
  data.append("customer_id", state.selectedCustomer.customerId);
  data.append("latitude", state.geo.latitude);
  data.append("longitude", state.geo.longitude);
  data.append("accuracy_m", state.geo.accuracy);
  data.append("captured_at_client", new Date().toISOString());
  data.append("photo", photoInput.files[0]);

  await api("/api/reports", {
    method: "POST",
    body: data,
  });

  doneShopName.textContent = state.selectedCustomer.name;
  updateRecentCustomers(state.selectedCustomer);
  resetCaptureState();
  showScreen(doneScreen);
  setStatus("Done");
}

function showEntryAfterDone() {
  state.selectedCustomer = null;
  doneShopName.textContent = "-";
  showScreen(entryScreen);
  setStatus("Ready");
}

document.getElementById("open-location-sheet").addEventListener("click", () => showLocationSheet(true));
document.getElementById("close-location-sheet").addEventListener("click", () => showLocationSheet(false));
document.getElementById("hide-location-sheet").addEventListener("click", () => showLocationSheet(false));
document.getElementById("refresh-shops").addEventListener("click", async () => {
  try {
    await loadLocations();
    await loadCustomers();
    setStatus("Ready");
  } catch (error) {
    setStatus(error.message);
  }
});
document.getElementById("back-to-entry").addEventListener("click", () => {
  resetCaptureState();
  showScreen(entryScreen);
  setStatus("Ready");
});
document.getElementById("get-location").addEventListener("click", captureGeolocation);
document.getElementById("submit-report").addEventListener("click", () => submitReport().catch((error) => setStatus(error.message)));
document.getElementById("capture-next").addEventListener("click", showEntryAfterDone);

customerSearch.addEventListener("input", () => {
  window.clearTimeout(customerSearch._timer);
  customerSearch._timer = window.setTimeout(() => loadCustomers().catch((error) => setStatus(error.message)), 250);
});

photoInput.addEventListener("change", (event) => {
  previewPhoto(event.target.files[0]);
});

ensureSession()
  .then(loadLocations)
  .then(loadCustomers)
  .catch((error) => setStatus(error.message));
