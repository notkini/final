let uptimeDowntimeChart = null;
let efficiencyTrendChart = null;


function formatDuration(seconds) {
    seconds = Math.max(
        0,
        Math.floor(Number(seconds) || 0)
    );

    const hours = Math.floor(seconds / 3600);

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


function renderUptimeDowntimeChart(data) {
    const canvas = document.getElementById(
        "uptime-downtime-chart"
    );

    if (
        !canvas
        || typeof Chart === "undefined"
    ) {
        return;
    }

    if (uptimeDowntimeChart) {
        uptimeDowntimeChart.destroy();
    }

    uptimeDowntimeChart = new Chart(
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


function renderEfficiencyTrendChart(rows) {
    const canvas = document.getElementById(
        "efficiency-trend-chart"
    );

    if (
        !canvas
        || typeof Chart === "undefined"
    ) {
        return;
    }

    if (efficiencyTrendChart) {
        efficiencyTrendChart.destroy();
    }

    efficiencyTrendChart = new Chart(
        canvas,
        {
            type: "line",

            data: {
                labels: rows.map(
                    row => formatDate(row.date)
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
        }
    );
}


function renderDailyTable(rows) {
    const body = document.getElementById(
        "daily-history-body"
    );

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
        const tableRow = document.createElement(
            "tr"
        );

        tableRow.innerHTML = `
            <td>
                ${formatDate(row.date)}
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
                <strong>
                    ${Number(
                        row.efficiency_pct
                    ).toFixed(2)}%
                </strong>
            </td>
        `;

        body.appendChild(tableRow);
    });
}


function renderShiftTable(rows) {
    const body = document.getElementById(
        "shift-history-body"
    );

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


function showHistoryError(message) {
    document.getElementById(
        "history-range"
    ).textContent = message;

    document.getElementById(
        "daily-history-body"
    ).innerHTML = `
        <tr>
            <td colspan="4">
                <div class="empty-state">
                    ${message}
                </div>
            </td>
        </tr>
    `;

    document.getElementById(
        "shift-history-body"
    ).innerHTML = `
        <tr>
            <td colspan="6">
                <div class="empty-state">
                    ${message}
                </div>
            </td>
        </tr>
    `;
}


async function loadHistory() {
    try {
        const response = await fetch(
            "/api/history/7-days",
            {
                cache: "no-store"
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail
                || "Unable to load history"
            );
        }

        document.getElementById(
            "machine-name"
        ).textContent = (
            data.machine || "Unknown Machine"
        );

        document.getElementById(
            "history-range"
        ).textContent = (
            `${formatDate(data.from_date)} to `
            + `${formatDate(data.to_date)}`
        );

        document.getElementById(
            "overall-efficiency"
        ).textContent = (
            `${Number(
                data.weighted_efficiency_pct
            ).toFixed(2)}%`
        );

        document.getElementById(
            "total-uptime"
        ).textContent = formatDuration(
            data.total_uptime_seconds
        );

        document.getElementById(
            "total-downtime"
        ).textContent = formatDuration(
            data.total_downtime_seconds
        );

        const dailyRows = Array.isArray(
            data.daily
        )
            ? data.daily
            : [];

        const shiftRows = Array.isArray(
            data.shifts
        )
            ? data.shifts
            : [];

        renderUptimeDowntimeChart(data);

        renderEfficiencyTrendChart(
            dailyRows
        );

        renderDailyTable(
            dailyRows
        );

        renderShiftTable(
            shiftRows
        );

    } catch (error) {
        console.error(
            "History loading failed:",
            error
        );

        showHistoryError(
            error.message
            || "Unable to load history"
        );
    }
}

function updateSystemClock() {
    const now = new Date();

    document.getElementById(
        "system-time"
    ).textContent = now.toLocaleTimeString(
        "en-IN",
        {
            hour12: false
        }
    );

    document.getElementById(
        "system-date"
    ).textContent = now.toLocaleDateString(
        "en-IN",
        {
            day: "2-digit",
            month: "short",
            year: "numeric"
        }
    );
}

updateSystemClock();

setInterval(
    updateSystemClock,
    1000
);

loadHistory();