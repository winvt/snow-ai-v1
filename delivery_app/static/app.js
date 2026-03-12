const state = {
  session: null,
  locations: [],
  customers: [],
  selectedLocation: null,
  selectedCustomer: null,
  geo: null,
};

const statusText = document.getElementById("status-text");
const locationScreen = document.getElementById("screen-location");
const customerScreen = document.getElementById("screen-customer");
const reportScreen = document.getElementById("screen-report");
const locationList = document.getElementById("location-list");
const customerList = document.getElementById("customer-list");
const customerSearch = document.getElementById("customer-search");
const selectedCustomerName = document.getElementById("selected-customer-name");
const selectedLocationName = document.getElementById("selected-location-name");
const photoInput = document.getElementById("photo-input");
const photoPreview = document.getElementById("photo-preview");
const geoStatus = document.getElementById("geo-status");

function setStatus(text) {
  statusText.textContent = text;
}

function showScreen(screen) {
  [locationScreen, customerScreen, reportScreen].forEach((node) => node.classList.add("hidden"));
  if (screen) {
    screen.classList.remove("hidden");
  }
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
    setStatus(session.guestMode ? "Guest preview mode is active." : `Signed in as ${session.user.displayName}`);
    return;
  }

  if (!window.liff || !session.liffId) {
    throw new Error("LINE login is not configured for this environment");
  }

  await window.liff.init({ liffId: session.liffId });
  if (!window.liff.isLoggedIn()) {
    window.liff.login();
    return;
  }

  const idToken = window.liff.getIDToken();
  if (!idToken) {
    throw new Error("LINE ID token not available");
  }
  const login = await api("/api/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id_token: idToken }),
  });
  state.session = login;
  setStatus(`Signed in as ${login.user.displayName}`);
}

function renderLocations() {
  locationList.innerHTML = "";
  const template = document.getElementById("location-item-template");
  state.locations.forEach((location) => {
    const node = template.content.firstElementChild.cloneNode(true);
    node.querySelector(".selection-title").textContent = location.name;
    node.querySelector(".selection-meta").textContent = `${location.customerCount} shops`;
    node.addEventListener("click", () => {
      state.selectedLocation = location;
      loadCustomers();
    });
    locationList.appendChild(node);
  });
}

function renderCustomers() {
  customerList.innerHTML = "";
  const template = document.getElementById("customer-item-template");
  state.customers.forEach((customer) => {
    const node = template.content.firstElementChild.cloneNode(true);
    node.querySelector(".selection-title").textContent = customer.name;
    node.querySelector(".selection-meta").textContent = customer.customerCode || customer.phone || customer.locationName;
    node.addEventListener("click", () => {
      state.selectedCustomer = customer;
      selectedCustomerName.textContent = customer.name;
      selectedLocationName.textContent = customer.locationName;
      showScreen(reportScreen);
      setStatus(`Ready to upload a report for ${customer.name}`);
    });
    customerList.appendChild(node);
  });
}

async function loadLocations() {
  const payload = await api("/api/locations");
  state.locations = payload.locations;
  renderLocations();
  showScreen(locationScreen);
}

async function loadCustomers() {
  const params = new URLSearchParams();
  params.set("location_id", state.selectedLocation.id);
  if (customerSearch.value.trim()) {
    params.set("q", customerSearch.value.trim());
  }
  const payload = await api(`/api/customers?${params.toString()}`);
  state.customers = payload.customers;
  renderCustomers();
  showScreen(customerScreen);
}

function previewPhoto(file) {
  if (!file) {
    photoPreview.classList.add("hidden");
    photoPreview.removeAttribute("src");
    return;
  }
  const reader = new FileReader();
  reader.onload = () => {
    photoPreview.src = reader.result;
    photoPreview.classList.remove("hidden");
  };
  reader.readAsDataURL(file);
}

function captureGeolocation() {
  setStatus("Capturing location...");
  navigator.geolocation.getCurrentPosition(
    (position) => {
      state.geo = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
      };
      geoStatus.textContent = `Location ready: ${state.geo.latitude.toFixed(5)}, ${state.geo.longitude.toFixed(5)} (±${Math.round(state.geo.accuracy)}m)`;
      setStatus("Location captured.");
    },
    (error) => {
      geoStatus.textContent = `Location failed: ${error.message}`;
      setStatus("Location permission is required.");
    },
    { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 }
  );
}

async function submitReport() {
  if (!state.selectedCustomer) {
    throw new Error("Choose a customer first");
  }
  if (!photoInput.files[0]) {
    throw new Error("Choose a photo first");
  }
  if (!state.geo) {
    throw new Error("Capture location before uploading");
  }

  const data = new FormData();
  data.append("client_submission_id", crypto.randomUUID());
  data.append("customer_id", state.selectedCustomer.customerId);
  data.append("latitude", state.geo.latitude);
  data.append("longitude", state.geo.longitude);
  data.append("accuracy_m", state.geo.accuracy);
  data.append("captured_at_client", new Date().toISOString());
  data.append("photo", photoInput.files[0]);

  const payload = await api("/api/reports", {
    method: "POST",
    body: data,
  });
  setStatus(payload.duplicate ? "That report was already uploaded." : "Report uploaded successfully.");
  photoInput.value = "";
  previewPhoto(null);
  state.geo = null;
  geoStatus.textContent = "Location not captured yet.";
}

document.getElementById("refresh-locations").addEventListener("click", () => loadLocations().catch((error) => setStatus(error.message)));
document.getElementById("back-to-locations").addEventListener("click", () => showScreen(locationScreen));
document.getElementById("back-to-customers").addEventListener("click", () => showScreen(customerScreen));
document.getElementById("get-location").addEventListener("click", captureGeolocation);
document.getElementById("submit-report").addEventListener("click", () => submitReport().catch((error) => setStatus(error.message)));
customerSearch.addEventListener("input", () => {
  window.clearTimeout(customerSearch._timer);
  customerSearch._timer = window.setTimeout(() => loadCustomers().catch((error) => setStatus(error.message)), 250);
});
photoInput.addEventListener("change", (event) => previewPhoto(event.target.files[0]));

ensureSession()
  .then(loadLocations)
  .catch((error) => setStatus(error.message));
