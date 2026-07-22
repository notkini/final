let uptimeDowntimeChart = null;
let efficiencyTrendChart = null;
let currentRange = "7d"; 
let selectedMonth = new Date().getMonth() + 1;
let selectedYear = new Date().getFullYear();

function formatDuration(seconds) {
    seconds = Math.max(
        0,
        Math.floor(Number(seconds) || 0)
    );

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;

    return [hours, minutes, remainingSeconds]
        .map(value => String(value).padStart(2, "0"))
        .join(":");
}

function formatDate(value) {
    if (!value) {
        return "-";
    }

    return new Date(`${value}T00:00:00`).toLocaleDateString();
}

function populateMonthDropdown() {
    const select = document.getElementById("month-select");
    if (!select) return;

    select.innerHTML = "";

    const months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December"
    ];

    months.forEach((month, index) => {
        const option = document.createElement("option");
        option.value = index + 1;
        option.textContent = month;
        select.appendChild(option);
    });

    select.value = selectedMonth;
}

function populateMonthYearDropdown() {
    const select = document.getElementById("month-year-select");
    if (!select) return;

    select.innerHTML = "";

    const currentYear = new Date().getFullYear();

    for (let year = currentYear; year >= currentYear - 10; year--) {
        const option = document.createElement("option");
        option.value = year;
        option.textContent = year;
        select.appendChild(option);
    }

    select.value = selectedYear;
}

function populateYearDropdown() {
    const select = document.getElementById("year-select");
    if (!select) return;

    select.innerHTML = "";
    const currentYear = new Date().getFullYear();

    for (let year = currentYear; year >= currentYear - 10; year--) {
        const option = document.createElement("option");
        
        option.value = year;
        option.textContent = year;
        
        select.appendChild(option);
    }

    select.value = selectedYear;
}

function hideAllPanels() {
    document.getElementById("month-panel").style.display = "none";
    document.getElementById("date-panel").style.display = "none";
    document.getElementById("year-panel").style.display = "none";
    document.getElementById("custom-filters").style.display = "none";
}

function showPanel(panelId) {
    hideAllPanels();
    document.getElementById(panelId).style.display = "block";
}

function renderUptimeDowntimeChart(data) {
    const canvas = document.getElementById("uptime-downtime-chart");

    if (!canvas || typeof Chart === "undefined") {
        return;
    }

    if (uptimeDowntimeChart) {
        uptimeDowntimeChart.destroy();
    }

    uptimeDowntimeChart = new Chart(canvas, {
        type: "doughnut",
        data: {
            labels: ["Uptime", "Downtime"],
            datasets: [
                {
                    data: [
                        Number(data.total_uptime_seconds) || 0,
                        Number(data.total_downtime_seconds) || 0
                    ],
                    backgroundColor: ["#22c55e", "#ef4444"],
                    borderWidth: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "70%",
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        color: "#cbd5e1"
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context){
                            const total =
                                context.dataset.data.reduce((a,b)=>a+b,0);

                            const value = context.raw;

                            const percent =
                                ((value/total)*100).toFixed(1);

                            return `${context.label}: ${percent}%`;
                        }
                    }
                }
            }
        }
    });
}

function renderEfficiencyTrendChart(rows) {
    const canvas = document.getElementById("efficiency-trend-chart");

    if (!canvas || typeof Chart === "undefined") {
        return;
    }

    if (efficiencyTrendChart) {
        efficiencyTrendChart.destroy();
    }

    efficiencyTrendChart = new Chart(canvas, {
        type: "line",
        data: {
            labels: rows.map(row => formatDate(row.date)),
            datasets: [
                {
                    label: "Efficiency %",
                    data: rows.map(row => Number(row.efficiency_pct) || 0),
                    borderColor: "#2563eb",
                    backgroundColor: "rgba(37, 99, 235, 0.15)",
                    fill: true,
                    tension: 0.3,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: "Efficiency %",
                        color: "#94a3b8"
                    },
                    ticks: {
                        color: "#94a3b8"
                    },
                    grid: {
                        color: "rgba(148, 163, 184, 0.12)"
                    }
                },
                x: {
                    ticks: {
                        color: "#94a3b8"
                    },
                    grid: {
                        display: false
                    }
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: "#cbd5e1"
                    }
                }
            }
        }
    });
}

function renderDailyTable(rows) {
    const body = document.getElementById("daily-history-body");
    body.innerHTML = "";

    if (!rows.length) {
        body.innerHTML = `
            <tr>
                <td colspan="4">
                    <div class="empty-state">
                        No performance data available.
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    rows.forEach(row => {
        const tableRow = document.createElement("tr");

        tableRow.innerHTML = `
            <td>${formatDate(row.date)}</td>
            <td>${formatDuration(row.uptime_seconds)}</td>
            <td>${formatDuration(row.downtime_seconds)}</td>
            <td><strong>${Number(row.efficiency_pct).toFixed(2)}%</strong></td>
        `;

        body.appendChild(tableRow);
    });
}

function renderShiftTable(rows) {
    const body = document.getElementById("shift-history-body");
    body.innerHTML = "";

    if (!rows.length) {
        body.innerHTML = `
            <tr>
                <td colspan="6">
                    <div class="empty-state">
                        No shift records available.
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    rows.forEach(row => {
        const tableRow = document.createElement("tr");

        const statusText = row.is_final ? "Final" : "In Progress";
        const statusClass = row.is_final ? "badge-final" : "badge-progress";

        tableRow.innerHTML = `
            <td>${formatDate(row.date)}</td>
            <td><strong>Shift ${row.shift}</strong></td>
            <td>${formatDuration(row.uptime_seconds)}</td>
            <td>${formatDuration(row.downtime_seconds)}</td>
            <td>${Number(row.efficiency_pct).toFixed(2)}%</td>
            <td>
                <span class="badge ${statusClass}">
                    ${statusText}
                </span>
            </td>
        `;

        body.appendChild(tableRow);
    });
}

function showHistoryError(message) {
    document.getElementById("history-range").textContent = message;

    document.getElementById("daily-history-body").innerHTML = `
        <tr>
            <td colspan="4">
                <div class="empty-state">
                    ${message}
                </div>
            </td>
        </tr>
    `;

    document.getElementById("shift-history-body").innerHTML = `
        <tr>
            <td colspan="6">
                <div class="empty-state">
                    ${message}
                </div>
            </td>
        </tr>
    `;
}

function showUnassignedMachine() {
    document.getElementById("machine-name").textContent = "No machine assigned";
    document.getElementById("history-range").textContent = "Assign a machine from the Setup page";
    document.getElementById("overall-efficiency").textContent = "0.00%";
    document.getElementById("total-uptime").textContent = "00:00:00";
    document.getElementById("total-downtime").textContent = "00:00:00";

    renderDailyTable([]);
    renderShiftTable([]);

    if (uptimeDowntimeChart) {
        uptimeDowntimeChart.destroy();
        uptimeDowntimeChart = null;
    }

    if (efficiencyTrendChart) {
        efficiencyTrendChart.destroy();
        efficiencyTrendChart = null;
    }
}

function selectHistoryRange(range) {
    currentRange = range;

    document
        .querySelectorAll(".mode-button")
        .forEach(button => button.classList.remove("active"));

    if (range === "7d") {
        document.getElementById("tab-7-days").classList.add("active");
    } else {
        document.getElementById(`tab-${range}`).classList.add("active");
    }

    switch (range) {
        case "7d":
            hideAllPanels();
            loadHistory();
            break;

        case "month":
            populateMonthDropdown();
            populateMonthYearDropdown();
            showPanel("month-panel");
            break;

        case "date":
            showPanel("date-panel");
            break;

        case "year":
            populateYearDropdown();
            showPanel("year-panel");
            break;

        case "custom":
            showPanel("custom-filters");
            break;
    }

    console.log("Selected:", range);
}

async function loadMachines() {
    try {
        const response = await fetch("/api/machines", {
            cache: "no-store"
        });
        const data = await response.json();
        const select = document.getElementById("machine-select");
        
        select.innerHTML = "";
        
        data.machines.forEach(machine => {
            const option = document.createElement("option");
            
            option.value = machine.id;
            option.textContent = machine.name;
            
            if (machine.id === data.current_machine_id) {
                option.selected = true;
            }
            
            select.appendChild(option);
        });
        
    } catch (error) {
        console.error("Unable to load machines:", error);
    }
}

async function loadHistory() {
    try {
        const url = buildHistoryUrl("/api/history");
        if (!url) {
            return;
        }

        const response = await fetch(url, {
            cache: "no-store"
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Unable to load history");
        }

        if (typeof isUnassignedMachine === "function" && isUnassignedMachine(data)) {
            showUnassignedMachine();
            return;
        }

        const machineName = document.getElementById("machine-name");
        const historyRange = document.getElementById("history-range");

        if (machineName) {
            machineName.textContent = data.machine || "Unknown Machine";
        }

        if (historyRange) {
            historyRange.textContent =
                `${formatDate(data.from_date)} to ${formatDate(data.to_date)}`;
        }

        document.getElementById("overall-efficiency").textContent =
            `${Number(data.weighted_efficiency_pct).toFixed(2)}%`;

        document.getElementById("total-uptime").textContent =
            formatDuration(data.total_uptime_seconds);

        document.getElementById("total-downtime").textContent =
            formatDuration(data.total_downtime_seconds);

        const dailyRows = Array.isArray(data.daily) ? data.daily : [];
        const shiftRows = Array.isArray(data.shifts) ? data.shifts : [];

        renderUptimeDowntimeChart(data);
        renderEfficiencyTrendChart(dailyRows);
        renderDailyTable(dailyRows);
        renderShiftTable(shiftRows);

    } catch (error) {
        console.error("History loading failed:", error);
        showHistoryError(error.message || "Unable to load history");
    }
}

function buildHistoryUrl(baseUrl) {
    let url = `${baseUrl}?range=${currentRange}`;

    if (currentRange === "month") {
        const month = document.getElementById("month-select").value;
        const year = document.getElementById("month-year-select").value;
        url += `&year=${year}&month=${month}`;
    }

    if (currentRange === "date") {
        const date = document.getElementById("history-date").value;

        if (!date) {
            showPopup("Please select a date.");
            return;
        }

        url += `&date=${date}`;
    }

    if (currentRange === "year") {
        const year = document.getElementById("year-select").value;
        url += `&year=${year}`;
    }

    if (currentRange === "custom") {
        const machineId = document.getElementById("machine-select").value;
        const fromDate = document.getElementById("from-date").value;
        const toDate = document.getElementById("to-date").value;
        const shifts = [...document.querySelectorAll('.shift-selector input[type="checkbox"]:checked')]
            .map(cb => cb.value)
            .join(",");

        if (!machineId || !fromDate || !toDate) {
            throw new Error("Please select both From Date and To Date.");
        }

        url += `&machine_id=${machineId}&from_date=${fromDate}&to_date=${toDate}&shifts=${shifts}`;
    }

    return url;
}

async function downloadPdfReport() {

    const payload = {
        range: currentRange
    };

    if (currentRange === "month") {

        payload.month = Number(
            document.getElementById(
                "month-select"
            ).value
        );

        payload.year = Number(
            document.getElementById(
                "month-year-select"
            ).value
        );
    }

    if (currentRange === "date") {

        payload.date =
            document.getElementById(
                "history-date"
            ).value;
    }

    if (currentRange === "year") {

        payload.year = Number(
            document.getElementById(
                "year-select"
            ).value
        );
    }

    if (currentRange === "custom") {

        payload.machine_id =
            Number(
                document.getElementById(
                    "machine-select"
                ).value
            );

        payload.from_date =
            document.getElementById(
                "from-date"
            ).value;

        payload.to_date =
            document.getElementById(
                "to-date"
            ).value;

        payload.shifts =
            [...document.querySelectorAll(
                '.shift-selector input[type="checkbox"]:checked'
            )]
            .map(cb => cb.value)
            .join(",");
    }

    payload.uptime_chart =
        uptimeDowntimeChart
            ? uptimeDowntimeChart.toBase64Image()
            : null;

    payload.trend_chart =
        efficiencyTrendChart
            ? efficiencyTrendChart.toBase64Image()
            : null;

    const response = await fetch(
        "/api/history/export/pdf",
        {
            method: "POST",
            headers: {
                "Content-Type":
                    "application/json"
            },
            body: JSON.stringify(payload)
        }
    );

    if (!response.ok) {

        showPopup("Unable to generate PDF.");

        return;
    }

    const blob =
        await response.blob();

    const url =
        window.URL.createObjectURL(blob);

    const link =
        document.createElement("a");

    link.href = url;

    link.download =
        "History_Report.pdf";

    document.body.appendChild(link);

    link.click();

    link.remove();

    window.URL.revokeObjectURL(url);
}

function showPopup(message) {
    document.getElementById("popup-message").textContent = message;
    document.getElementById("popup-overlay").style.display = "flex";
}

function hidePopup() {
    document.getElementById("popup-overlay").style.display = "none";
}

function updateSystemClock() {
    const now = new Date();

    document.getElementById("system-time").textContent = now.toLocaleTimeString("en-IN", {
        hour12: false
    });

    document.getElementById("system-date").textContent = now.toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric"
    });
}

document
    .getElementById("popup-ok")
    .addEventListener("click", hidePopup);

document
    .getElementById("tab-7-days")
    .addEventListener("click", () => selectHistoryRange("7d"));

document
    .getElementById("tab-month")
    .addEventListener("click", () => selectHistoryRange("month"));

document
    .getElementById("tab-date")
    .addEventListener("click", () => selectHistoryRange("date"));

document
    .getElementById("tab-year")
    .addEventListener("click", () => selectHistoryRange("year"));

document
    .getElementById("tab-custom")
    .addEventListener("click", () => selectHistoryRange("custom"));

document
    .getElementById("apply-custom-filter")
    .addEventListener("click", () => {
        const fromDate = document.getElementById("from-date").value;
        const toDate = document.getElementById("to-date").value;

        if (!fromDate || !toDate) {
            showPopup("Please select both From Date and To Date.");
            return;
        }

        if (new Date(fromDate) > new Date(toDate)) {
            showPopup("From Date cannot be later than To Date.");
            return;
        }

        loadHistory();
    });

document
    .getElementById("apply-month-filter")
    .addEventListener("click", () => {
        selectedMonth = Number(
            document.getElementById("month-select").value
        );
        selectedYear = Number(
            document.getElementById("month-year-select").value
        );
        loadHistory();
    });

document
    .getElementById("apply-year-filter")
    .addEventListener("click", () => {
        selectedYear = Number(
            document.getElementById("year-select").value
        );
        loadHistory();
    });

document
    .getElementById("apply-date-filter")
    .addEventListener("click", loadHistory);

document
    .getElementById("download-excel")
    .addEventListener("click", () => {
        const url = buildHistoryUrl("/api/history/export/excel");
        if (url) {
            window.location.href = url;
        }
    });

document
    .getElementById("download-pdf")
    .addEventListener(
        "click",
        downloadPdfReport
    );

// Initial load
updateSystemClock();
setInterval(updateSystemClock, 1000);
loadMachines();
loadHistory();

const historyDate = document.getElementById("history-date");
if (historyDate) {
    historyDate.value = new Date().toISOString().split("T")[0];
}