const REFRESH_INTERVAL = 5000;


function formatDuration(seconds) {
    const value = Math.max(
        0,
        Math.floor(Number(seconds) || 0)
    );

    const hours = Math.floor(value / 3600);

    const minutes = Math.floor(
        (value % 3600) / 60
    );

    const secs = value % 60;

    return [
        hours,
        minutes,
        secs
    ]
        .map(number =>
            String(number).padStart(2, "0")
        )
        .join(":");
}


function formatDateTime(value) {
    if (!value) {
        return "--";
    }

    return new Intl.DateTimeFormat(
        "en-IN",
        {
            dateStyle: "medium",
            timeStyle: "medium"
        }
    ).format(
        new Date(value)
    );
}


function setConnectionState(online) {
    const indicator = document.getElementById(
        "connectionIndicator"
    );

    const text = document.getElementById(
        "connectionText"
    );

    indicator.className = online
        ? "signal-indicator online"
        : "signal-indicator offline";

    text.textContent = online
        ? "SYSTEM ONLINE"
        : "SYSTEM OFFLINE";
}


function updateMachineState(data) {
    const rawStatus = data.status || "UNKNOWN";

    const stateText = document.getElementById(
        "machineStatus"
    );

    const stateLamp = document.getElementById(
        "machineStatusDot"
    );

    const breakNotice = document.getElementById(
        "breakNotice"
    );

    const breakTitle = document.getElementById(
        "breakTitle"
    );

    stateLamp.className = "state-lamp";
    stateText.className = "state-text";
    breakNotice.className = "break-notice";


    if (data.active_meal) {
        const meal = data.active_meal.toUpperCase();

        stateText.textContent = meal + " BREAK";

        stateLamp.classList.add("break");
        stateText.classList.add("break");

        breakNotice.classList.add("active");

        breakTitle.textContent =
            meal + " BREAK ACTIVE";

        return;
    }


    if (rawStatus === "UP") {
        stateText.textContent = "RUNNING";

        stateLamp.classList.add("up");
        stateText.classList.add("up");

        return;
    }


    if (rawStatus === "DOWN") {
        stateText.textContent = "STOPPED";

        stateLamp.classList.add("down");
        stateText.classList.add("down");

        return;
    }


    stateText.textContent = "NO DATA";
}

async function loadStatus() {
    try {
        const response = await fetch(
            "/api/status",
            {
                cache: "no-store"
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || "Status API failed"
            );
        }


        document.getElementById(
            "machineName"
        ).textContent = data.machine || "--";


        document.getElementById(
            "currentShift"
        ).textContent = data.current_shift
            ? `SHIFT ${data.current_shift}`
            : "--";


        document.getElementById(
            "uptime"
        ).textContent = formatDuration(
            data.uptime_seconds
        );


        document.getElementById(
            "downtime"
        ).textContent = formatDuration(
            data.downtime_seconds
        );


        const efficiency = Number(
            data.efficiency_pct || 0
        );


        document.getElementById(
            "efficiency"
        ).textContent =
            `${efficiency.toFixed(2)}%`;


        document.getElementById(
            "efficiencyBar"
        ).style.width =
            `${Math.min(efficiency, 100)}%`;


        document.getElementById(
            "lastUpdated"
        ).textContent = formatDateTime(
            data.last_updated
        );


        updateMachineState(data);

        setConnectionState(true);

    } catch (error) {
        console.error(
            "Status load failed:",
            error
        );

        setConnectionState(false);
    }
}


function getShiftState(row) {
    if (row.is_final) {
        return `
            <span class="industrial-badge completed">
                COMPLETED
            </span>
        `;
    }

    const elapsed = (
        Number(row.uptime_seconds || 0)
        + Number(row.downtime_seconds || 0)
    );

    if (elapsed > 0) {
        return `
            <span class="industrial-badge active">
                ACTIVE
            </span>
        `;
    }

    return `
        <span class="industrial-badge waiting">
            WAITING
        </span>
    `;
}


async function loadToday() {
    try {
        const response = await fetch(
            "/api/today",
            {
                cache: "no-store"
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || "Today API failed"
            );
        }


        document.getElementById(
            "todayDate"
        ).textContent = data.date || "--";


        const body = document.getElementById(
            "shiftSummary"
        );


        body.innerHTML = data.shifts
            .map(row => {

                const efficiency = Number(
                    row.efficiency_pct || 0
                );

                return `
                    <tr>
                        <td>
                            <strong>
                                SHIFT ${row.shift}
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
                            <strong>
                                ${efficiency.toFixed(2)}%
                            </strong>
                        </td>

                        <td>
                            ${getShiftState(row)}
                        </td>
                    </tr>
                `;
            })
            .join("");

    } catch (error) {
        console.error(
            "Today load failed:",
            error
        );
    }
}


function renderTimeline(data) {
    const timeline = document.getElementById(
        "timeline"
    );

    const events = data.events || [];


    if (!events.length) {
        timeline.innerHTML = `
            <div class="timeline-empty">
                No machine state events recorded
                for this monitoring period.
            </div>
        `;

        return;
    }


    const rangeStart = new Date(
        data.range_start
    ).getTime();

    const rangeEnd = new Date(
        data.range_end
    ).getTime();

    const totalRange = rangeEnd - rangeStart;


    if (totalRange <= 0) {
        return;
    }


    let html = "";


    events.forEach(
        (event, index) => {

            const eventStart = new Date(
                event.event_time
            ).getTime();

            const nextEvent = events[index + 1];

            const eventEnd = nextEvent
                ? new Date(
                    nextEvent.event_time
                ).getTime()
                : Math.min(
                    Date.now(),
                    rangeEnd
                );


            const start = Math.max(
                eventStart,
                rangeStart
            );

            const end = Math.min(
                eventEnd,
                rangeEnd
            );


            if (end <= start) {
                return;
            }


            const width = (
                (end - start)
                / totalRange
            ) * 100;


            html += `
                <div
                    class="timeline-segment ${
                        event.state === "UP"
                            ? "up"
                            : "down"
                    }"
                    style="width: ${width}%"
                    title="${
                        event.state
                    } | ${
                        formatDateTime(
                            event.event_time
                        )
                    }"
                ></div>
            `;
        }
    );


    timeline.innerHTML = html || `
        <div class="timeline-empty">
            No elapsed machine state data.
        </div>
    `;
}


async function loadTimeline() {
    try {
        const response = await fetch(
            "/api/timeline",
            {
                cache: "no-store"
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail || "Timeline API failed"
            );
        }

        renderTimeline(data);

    } catch (error) {
        console.error(
            "Timeline load failed:",
            error
        );
    }
}


async function refreshDashboard() {
    await Promise.all([
        loadStatus(),
        loadToday(),
        loadTimeline()
    ]);
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


refreshDashboard();


setInterval(
    refreshDashboard,
    REFRESH_INTERVAL
);