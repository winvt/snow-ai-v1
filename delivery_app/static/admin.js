const reportGrid = document.getElementById("report-grid");
const adminStatus = document.getElementById("admin-status");
const filterForm = document.getElementById("admin-filters");

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
    card.innerHTML = `
      <img src="${report.photoUrl}" alt="Visit report photo">
      <h3>${report.customerName}</h3>
      <p>${report.locationName}</p>
      <p>By ${report.userName}</p>
      <p>Captured: ${report.capturedAtClient || "-"}</p>
      <p>Server: ${report.receivedAtServer || "-"}</p>
      <p>${report.latitude.toFixed(5)}, ${report.longitude.toFixed(5)}</p>
    `;
    reportGrid.appendChild(card);
  });
}

async function loadReports(event) {
  if (event) {
    event.preventDefault();
  }
  const params = new URLSearchParams(new FormData(filterForm));
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
loadReports();

