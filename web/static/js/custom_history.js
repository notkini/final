const filterForm = document.getElementById(
    "history-filter-form"
);

const machineSelect = document.getElementById(
    "machine-select"
);

const filterMessage = document.getElementById(
    "filter-message"
);

const applyButton = document.getElementById(
    "apply-filter-button"
);


let doughnutChart = null;
let barChart = null;
let efficiencyChart = null;


function formatDuration(seconds) {
    seconds = Math.max(
        0,
        Math.floor(Number(seconds) || 0)
    );

    const hours = Math.floor(
        seconds / 3600
    );

    const minutes = Math.floor(
        (seconds % 3600) / 60
    );

    const remainingSeconds = seconds % 60;

    return [
        hours,
        minutes,
        remainingSeconds
    ]
        .map(
            value => String(value).padStart(2, "0")
        )
        .join(":");
}


function formatDate(value) {
    if (!value) {
        return "-";
    }

    return new Date(
        `${value}T00:00:00`
    ).toLocaleDateString();
}


function showMessage(
    text,
    type = ""
) {
    filterMessage.textContent = text;

    filterMessage.classList.remove(
        "success",
        "error"
    );

    if (type) {
        filterMessage.classList.add(type);
    }
}


function getSelectedShifts() {
    return Array.from(
        document.querySelectorAll(
            ".shift-checkbox:checked"
        )
    ).map(
        checkbox => checkbox.value
    );
}


function getLocalDateString(date) {
    const year = date.getFullYear();

    const month = String(
        date.getMonth() + 1
    ).padStart(2, "0");

    const day = String(
        date.getDate()
    ).padStart(2, "0");

    return `${year}-${month}-${day}`;
}


function setDefaultDates() {
    const today = new Date();

    const sevenDaysAgo = new Date();

    sevenDaysAgo.setDate(
        today.getDate() - 6
    );

    document.getElementById(
        "to-date"
    ).value = getLocalDateString(today);

    document.getElementById(
        "from-date"
    ).value = getLocalDateString(
        sevenDaysAgo
    );
}


async function loadMachines() {
    const response = await fetch(
        "/api/machines",
        {
            cache: "no-store"
        }
    );

    if (!response.ok) {
        throw new Error(
            "Unable to load machines"
        );
    }

    const data = await response.json();

    machineSelect.innerHTML = "";

    if (!data.machines.length) {
        const option = document.createElement(
            "option"
        );

        option.value = "";

        option.textContent = (
            "No machines configured"
        );

        machineSelect.appendChild(option);

        return;
    }

    data.machines.forEach(machine => {
        const option = document.createElement(
            "option"
        );

        option.value = machine.id;

        option.textContent = machine.name;

        if (
            machine.id
            === data.current_machine_id
        ) {
            option.selected = true;
        }

        machineSelect.appendChild(option);
    });
}


function destroyCharts() {
    if (doughnutChart) {
        doughnutChart.destroy();

        doughnutChart = null;
    }

    if (barChart) {
        barChart.destroy();

        barChart = null;
    }

    if (efficiencyChart) {
        efficiencyChart.destroy();

        efficiencyChart = null;
    }
}


function renderDoughnutChart(data) {
    const canvas = document.getElementById(
        "custom-doughnut-chart"
    );

    if (
        !canvas
        || typeof Chart === "undefined"
    ) {
        return;
    }

    if (doughnutChart) {
        doughnutChart.destroy();
    }

    doughnutChart = new Chart(
        canvas,
        {
            type: "doughnut",

            data: {
                labels: [
                    "Uptime",
                    "Downtime"
                ],

                datasets: [
                    {
                        data: [
                            Number(
                                data.total_uptime_seconds
                            ) || 0,

                            Number(
                                data.total_downtime_seconds
                            ) || 0
                        ],

                        backgroundColor: [
                            "#22c55e",
                            "#ef4444"
                        ],

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
                    }
                }
            }
        }
    );
}


function getRowLabel(row) {
    return (
        `${formatDate(row.date)} `
        + `Shift ${row.shift}`
    );
}


function renderBarChart(rows) {
    const canvas = document.getElementById(
        "custom-bar-chart"
    );

    if (
        !canvas
        || typeof Chart === "undefined"
    ) {
        return;
    }

    if (barChart) {
        barChart.destroy();
    }

    barChart = new Chart(
        canvas,
        {
            type: "bar",

            data: {
                labels: rows.map(
                    getRowLabel
                ),

                datasets: [
                    {
                        label: "Uptime Hours",

                        data: rows.map(
                            row => (
                                Number(
                                    row.uptime_seconds
                                ) / 3600
                            )
                        ),

                        backgroundColor: "#22c55e"
                    },

                    {
                        label: "Downtime Hours",

                        data: rows.map(
                            row => (
                                Number(
                                    row.downtime_seconds
                                ) / 3600
                            )
                        ),

                        backgroundColor: "#ef4444"
                    }
                ]
            },

            options: {
                responsive: true,

                maintainAspectRatio: false,

                scales: {
                    y: {
                        beginAtZero: true,

                        title: {
                            display: true,

                            text: "Hours",

                            color: "#94a3b8"
                        },

                        ticks: {
                            color: "#94a3b8"
                        },

                        grid: {
                            color:
                                "rgba(148, 163, 184, 0.12)"
                        }
                    },

                    x: {
                        ticks: {
                            color: "#94a3b8",

                            maxRotation: 45,

                            minRotation: 45
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
        }
    );
}


function renderEfficiencyChart(rows) {
    const canvas = document.getElementById(
        "custom-efficiency-chart"
    );

    if (
        !canvas
        || typeof Chart === "undefined"
    ) {
        return;
    }

    if (efficiencyChart) {
        efficiencyChart.destroy();
    }

    efficiencyChart = new Chart(
        canvas,
        {
            type: "line",

            data: {
                labels: rows.map(
                    getRowLabel
                ),

                datasets: [
                    {
                        label: "Efficiency %",

                        data: rows.map(
                            row => Number(
                                row.efficiency_pct
                            ) || 0
                        ),

                        borderColor: "#2563eb",

                        backgroundColor:
                            "rgba(37, 99, 235, 0.15)",

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
                            color:
                                "rgba(148, 163, 184, 0.12)"
                        }
                    },

                    x: {
                        ticks: {
                            color: "#94a3b8",

                            maxRotation: 45,

                            minRotation: 45
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
        }
    );
}


function renderTable(rows) {
    const body = document.getElementById(
        "custom-history-body"
    );

    body.innerHTML = "";

    if (!rows.length) {
        body.innerHTML = `
            <tr>
                <td colspan="6">

                    <div class="empty-state">
                        No records match the selected filters.
                    </div>

                </td>
            </tr>
        `;

        return;
    }

    rows.forEach(row => {
        const tableRow = document.createElement(
            "tr"
        );

        const statusText = row.is_final
            ? "Final"
            : "In Progress";

        const statusClass = row.is_final
            ? "badge-final"
            : "badge-progress";

        tableRow.innerHTML = `
            <td>
                ${formatDate(row.date)}
            </td>

            <td>
                <strong>
                    Shift ${row.shift}
                </strong>
            </td>

            <td>
                ${formatDuration(
                    row.uptime_seconds
                )}
            </td>

            <td>
                ${formatDuration(
                    row.downtime_seconds
                )}
            </td>

            <td>
                ${Number(
                    row.efficiency_pct
                ).toFixed(2)}%
            </td>

            <td>
                <span class="badge ${statusClass}">
                    ${statusText}
                </span>
            </td>
        `;

        body.appendChild(tableRow);
    });
}


function clearResults() {
    destroyCharts();

    document.getElementById(
        "custom-efficiency"
    ).textContent = "0.00%";

    document.getElementById(
        "custom-uptime"
    ).textContent = "00:00:00";

    document.getElementById(
        "custom-downtime"
    ).textContent = "00:00:00";

    document.getElementById(
        "result-description"
    ).textContent = (
        "No matching records"
    );

    renderTable([]);
}


async function loadCustomHistory() {
    const machineId = machineSelect.value;

    const fromDate = document.getElementById(
        "from-date"
    ).value;

    const toDate = document.getElementById(
        "to-date"
    ).value;

    const shifts = getSelectedShifts();


    if (!machineId) {
        showMessage(
            "Select a machine.",
            "error"
        );

        return;
    }


    if (!fromDate || !toDate) {
        showMessage(
            "Select both From Date and To Date.",
            "error"
        );

        return;
    }


    if (fromDate > toDate) {
        showMessage(
            "From Date cannot be after To Date.",
            "error"
        );

        return;
    }


    if (!shifts.length) {
        showMessage(
            "Select at least one shift.",
            "error"
        );

        return;
    }


    applyButton.disabled = true;

    showMessage(
        "Loading history..."
    );


    const params = new URLSearchParams({
        machine_id: machineId,

        from_date: fromDate,

        to_date: toDate,

        shifts: shifts.join(",")
    });


    try {
        const response = await fetch(
            `/api/history/custom?${params.toString()}`,
            {
                cache: "no-store"
            }
        );

        const data = await response.json();


        if (!response.ok) {
            showMessage(
                data.detail
                || "Unable to load history.",
                "error"
            );

            return;
        }


        document.getElementById(
            "custom-efficiency"
        ).textContent = (
            `${Number(
                data.weighted_efficiency_pct
            ).toFixed(2)}%`
        );


        document.getElementById(
            "custom-uptime"
        ).textContent = formatDuration(
            data.total_uptime_seconds
        );


        document.getElementById(
            "custom-downtime"
        ).textContent = formatDuration(
            data.total_downtime_seconds
        );


        document.getElementById(
            "result-description"
        ).textContent = (
            `${data.machine}: `
            + `${formatDate(data.from_date)} to `
            + `${formatDate(data.to_date)}`
        );


        if (!data.rows.length) {
            clearResults();

            document.getElementById(
                "result-description"
            ).textContent = (
                `${data.machine}: `
                + `${formatDate(data.from_date)} to `
                + `${formatDate(data.to_date)}`
            );

            showMessage(
                "No shift records found for the selected filters."
            );

            return;
        }


        renderDoughnutChart(data);

        renderBarChart(data.rows);

        renderEfficiencyChart(data.rows);

        renderTable(data.rows);


        showMessage(
            `${data.rows.length} shift record(s) loaded.`,
            "success"
        );

    } catch (error) {
        console.error(
            "Custom history loading failed",
            error
        );

        showMessage(
            "Unable to connect to the monitoring server.",
            "error"
        );

    } finally {
        applyButton.disabled = false;
    }
}


filterForm.addEventListener(
    "submit",
    event => {
        event.preventDefault();

        loadCustomHistory();
    }
);


async function initializePage() {
    setDefaultDates();

    try {
        await loadMachines();

        if (machineSelect.value) {
            await loadCustomHistory();
        }

    } catch (error) {
        console.error(
            "Custom history initialization failed",
            error
        );

        showMessage(
            "Unable to load machine information.",
            "error"
        );
    }
}

function updateSystemClock() {
    const now = new Date();

    const timeElement = document.getElementById("system-time");
    const dateElement = document.getElementById("system-date");

    if (timeElement) {
        timeElement.textContent = now.toLocaleTimeString(
            "en-IN",
            {
                hour12: false
            }
        );
    }

    if (dateElement) {
        dateElement.textContent = now.toLocaleDateString(
            "en-IN",
            {
                day: "2-digit",
                month: "short",
                year: "numeric"
            }
        );
    }
}

updateSystemClock();

setInterval(updateSystemClock, 1000);


initializePage();