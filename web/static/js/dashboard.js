const REFRESH_INTERVAL = 1000;

function formatDuration(seconds) {
    const value = Math.max(
        0,
        Math.floor(Number(seconds) || 0)
    );

    const hours = Math.floor(value / 3600);
    const minutes = Math.floor((value % 3600) / 60);
    const secs = value % 60;

    return [hours, minutes, secs]
        .map(number => String(number).padStart(2, "0"))
        .join(":");
}

function formatDateTime(value) {
    if (!value) {
        return "--";
    }

    return new Intl.DateTimeFormat("en-IN", {
        dateStyle: "medium",
        timeStyle: "medium"
    }).format(new Date(value));
}

function setConnectionState(online) {
    const indicator = document.getElementById("connectionIndicator");
    const text = document.getElementById("connectionText");

    indicator.className = online
        ? "signal-indicator online"
        : "signal-indicator offline";

    text.textContent = online
        ? "SYSTEM ONLINE"
        : "SYSTEM OFFLINE";
}

function updateMachineState(data) {
    const rawStatus = data.status || "UNKNOWN";
    const stateText = document.getElementById("machineStatus");
    const stateLamp = document.getElementById("machineStatusDot");
    const breakNotice = document.getElementById("breakNotice");
    const breakTitle = document.getElementById("breakTitle");

    stateLamp.className = "state-lamp";
    stateText.className = "state-text";
    breakNotice.className = "break-notice";

    if (rawStatus === "UNASSIGNED") {
        stateText.textContent = "MONITORING DISABLED";
        stateLamp.classList.add("offline");
        
        // Clear the break banner
        breakNotice.className = "break-notice";
        breakTitle.textContent = "";

        return;
    }

    if (data.active_meal) {
        const meal = data.active_meal.toUpperCase();

        stateText.textContent = meal + " BREAK";
        stateLamp.classList.add("break");
        stateText.classList.add("break");

        breakNotice.classList.add("active");
        breakTitle.textContent = meal + " BREAK ACTIVE";

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
        const response = await fetch("/api/status", {
            cache: "no-store"
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Status API failed");
        }

        if (isUnassignedMachine(data)) {
            document.getElementById("machineName").textContent = "No machine assigned";
            document.getElementById("currentShift").textContent = "--";
            document.getElementById("uptime").textContent = "00:00:00";
            document.getElementById("downtime").textContent = "00:00:00";
            document.getElementById("efficiency").textContent = "0.00%";
            document.getElementById("efficiencyBar").style.width = "0%";
            document.getElementById("lastUpdated").textContent = "--";

            updateMachineState({
                status: "UNASSIGNED"
            });

            setConnectionState(true);
            return;
        }

        document.getElementById("machineName").textContent = data.machine || "--";
        
        document.getElementById("currentShift").textContent = data.current_shift
            ? `SHIFT ${data.current_shift}`
            : "--";

        document.getElementById("uptime").textContent = formatDuration(data.uptime_seconds);
        document.getElementById("downtime").textContent = formatDuration(data.downtime_seconds);

        const efficiency = Number(data.efficiency_pct || 0);

        document.getElementById("efficiency").textContent = `${efficiency.toFixed(2)}%`;
        document.getElementById("efficiencyBar").style.width = `${Math.min(efficiency, 100)}%`;

        document.getElementById("lastUpdated").textContent = formatDateTime(data.last_updated);

        updateMachineState(data);
        setConnectionState(true);

    } catch (error) {
        console.error("Status load failed:", error);
        setConnectionState(false);
    }
}

function getShiftState(row) {
    if (row.is_final) {
        return `<span class="industrial-badge completed">COMPLETED</span>`;
    }

    const elapsed = Number(row.uptime_seconds || 0) + Number(row.downtime_seconds || 0);

    if (elapsed > 0) {
        return `<span class="industrial-badge active">ACTIVE</span>`;
    }

    return `<span class="industrial-badge waiting">WAITING</span>`;
}

async function loadToday() {
    try {
        const response = await fetch("/api/today", {
            cache: "no-store"
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Today API failed");
        }

        if (isUnassignedMachine(data)) {
            document.getElementById("todayDate").textContent = "--";
            document.getElementById("shiftSummary").innerHTML = `
                <tr>
                    <td colspan="5">No machine assigned.</td>
                </tr>
            `;
            return;
        }

        document.getElementById("todayDate").textContent = data.date || "--";
        const body = document.getElementById("shiftSummary");

        body.innerHTML = data.shifts.map(row => {
            const efficiency = Number(row.efficiency_pct || 0);

            return `
                <tr>
                    <td><strong>SHIFT ${row.shift}</strong></td>
                    <td>${formatDuration(row.uptime_seconds)}</td>
                    <td>${formatDuration(row.downtime_seconds)}</td>
                    <td><strong>${efficiency.toFixed(2)}%</strong></td>
                    <td>${getShiftState(row)}</td>
                </tr>
            `;
        }).join("");

    } catch (error) {
        console.error("Today load failed:", error);
    }
}

/**
 * Converts an absolute timestamp (ms) into a left-offset
 * percentage within [rangeStart, rangeStart + totalRange].
 * Shared by the hour scale, state segments, meal overlay and
 * the now-indicator so they all stay on one consistent axis.
 */
function pctOf(timeMs, rangeStart, totalRange) {
    return ((timeMs - rangeStart) / totalRange) * 100;
}

/**
 * Splits [start, end] around any overlapping gaps, returning only
 * the sub-intervals that fall outside every gap. Used so a state
 * segment never gets drawn across a period the machine had no
 * monitor attached — that period should render blank, not carry
 * the last known color forward.
 */
function subtractGaps(start, end, gaps) {
    let pieces = [[start, end]];

    gaps.forEach(gap => {
        const gapStart = new Date(gap.start).getTime();
        const gapEnd = new Date(gap.end).getTime();

        pieces = pieces.flatMap(([pieceStart, pieceEnd]) => {
            if (gapEnd <= pieceStart || gapStart >= pieceEnd) {
                return [[pieceStart, pieceEnd]];
            }

            const remaining = [];

            if (gapStart > pieceStart) {
                remaining.push([pieceStart, gapStart]);
            }

            if (gapEnd < pieceEnd) {
                remaining.push([gapEnd, pieceEnd]);
            }

            return remaining;
        });
    });

    return pieces;
}

function renderHourScale(scale, grid, rangeStart, rangeEnd, totalRange) {
    const tick = new Date(rangeStart);
    tick.setMinutes(0, 0, 0);

    if (tick.getTime() < rangeStart) {
        tick.setHours(tick.getHours() + 1);
    }

    while (tick.getTime() <= rangeEnd) {
        const left = pctOf(tick.getTime(), rangeStart, totalRange);

        const label = document.createElement("span");
        label.className = "hour-label";
        label.style.left = `${left}%`;
        label.textContent = tick.toLocaleTimeString("en-IN", {
            hour: "2-digit",
            minute: "2-digit",
            hour12: false
        });
        scale.appendChild(label);

        const line = document.createElement("div");
        line.className = "tick";
        line.style.left = `${left}%`;
        grid.appendChild(line);

        tick.setHours(tick.getHours() + 1);
    }
}

function renderStateSegments(timeline, events, rangeStart, rangeEnd, totalRange, gaps) {
    events.forEach((event, index) => {
        const start = new Date(event.event_time).getTime();

        const next = index < events.length - 1
            ? new Date(events[index + 1].event_time).getTime()
            : Math.min(Date.now(), rangeEnd);

        const segmentStart = Math.max(start, rangeStart);
        const segmentEnd = Math.min(next, rangeEnd);

        if (segmentEnd <= segmentStart) {
            return;
        }

        subtractGaps(segmentStart, segmentEnd, gaps).forEach(([pieceStart, pieceEnd]) => {
            if (pieceEnd <= pieceStart) {
                return;
            }

            const left = pctOf(pieceStart, rangeStart, totalRange);
            const width = pctOf(pieceEnd, rangeStart, totalRange) - left;

            const segment = document.createElement("div");
            segment.className = `timeline-segment ${event.state === "UP" ? "up" : "down"}`;
            segment.style.left = `${left}%`;
            segment.style.width = `${width}%`;
            segment.title = `${event.state}\n${formatDateTime(event.event_time)}`;

            timeline.appendChild(segment);
        });
    });
}

/**
 * Identifies the current time window. The hour scale, grid and
 * meal overlay only need to be rebuilt when this changes (e.g.
 * once per shift day) — not on every 1-second refresh tick.
 */
function getTimelineWindowKey(data) {
    return `${data.range_start}|${data.range_end}`;
}

function renderTimeline(data, rebuildAxis) {
    const timeline = document.getElementById("timeline");
    const scale = document.getElementById("timelineScale");
    const grid = document.getElementById("timelineGrid");

    const events = data.events || [];

    if (!events.length) {
        timeline.innerHTML = `<div class="timeline-empty">No machine state events.</div>`;
        return;
    }

    const rangeStart = new Date(data.range_start).getTime();
    const rangeEnd = new Date(data.range_end).getTime();
    const totalRange = rangeEnd - rangeStart;

    if (totalRange <= 0) {
        return;
    }

    if (rebuildAxis) {
        scale.innerHTML = "";
        grid.innerHTML = "";
        renderHourScale(scale, grid, rangeStart, rangeEnd, totalRange);
    }

    // The bar itself is cheap to redraw and must update every
    // tick: the segment for the currently active state keeps
    // growing towards "now".
    timeline.innerHTML = "";
    renderStateSegments(timeline, events, rangeStart, rangeEnd, totalRange, data.gaps || []);
}

/**
 * Formats an ISO timestamp as a local HH:MM (24-hour) string.
 */
function formatTimeOfDay(value) {
    if (!value) {
        return "--:--";
    }

    return new Date(value).toLocaleTimeString("en-IN", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false
    });
}

/**
 * Renders meal breaks as a small plain-text timings row below the
 * legend (e.g. "BREAKFAST 10:00–11:00") instead of a colored
 * overlay on the chart.
 */
function renderMealTimings(data) {
    const container = document.getElementById("mealMarkers");
    const meals = data.meals || [];

    if (!meals.length) {
        container.innerHTML = "";
        return;
    }

    container.innerHTML = meals.map(meal => `
        <div class="meal-timing-item">
            <span class="meal-timing-dot"></span>
            <span class="meal-timing-name">${meal.name}</span>
            <span>${formatTimeOfDay(meal.start)}\u2013${formatTimeOfDay(meal.end)}</span>
        </div>
    `).join("");
}

function updateNowIndicator(data) {
    const indicator = document.getElementById("nowIndicator");

    if (!indicator || !data.range_start || !data.range_end) {
        return;
    }

    const rangeStart = new Date(data.range_start).getTime();
    const rangeEnd = new Date(data.range_end).getTime();
    const totalRange = rangeEnd - rangeStart;

    if (totalRange <= 0) {
        indicator.style.display = "none";
        return;
    }

    const left = Math.max(0, Math.min(pctOf(Date.now(), rangeStart, totalRange), 100));

    indicator.style.display = "";
    indicator.style.left = `${left}%`;
}

let currentTimelineWindow = null;

async function loadTimeline() {
    try {
        const response = await fetch("/api/timeline", {
            cache: "no-store"
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Timeline API failed");
        }

        const windowKey = getTimelineWindowKey(data);
        const rebuildAxis = windowKey !== currentTimelineWindow;
        currentTimelineWindow = windowKey;

        renderTimeline(data, rebuildAxis);

        if (rebuildAxis) {
            renderMealTimings(data);
        }

        updateNowIndicator(data);

    } catch (error) {
        console.error("Timeline load failed:", error);
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

    document.getElementById("system-time").textContent = now.toLocaleTimeString("en-IN", {
        hour12: false
    });

    document.getElementById("system-date").textContent = now.toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric"
    });
}

// Initialization
updateSystemClock();
setInterval(updateSystemClock, 1000);

refreshDashboard();
setInterval(refreshDashboard, REFRESH_INTERVAL);