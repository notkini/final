const machineSelect = document.getElementById("machine-select");
const machineNameInput = document.getElementById("machine-name");

const existingMachineGroup = document.getElementById(
    "existing-machine-group"
);

const newMachineGroup = document.getElementById(
    "new-machine-group"
);

const existingModeButton = document.getElementById(
    "existing-mode-button"
);

const newModeButton = document.getElementById(
    "new-mode-button"
);

const saveButton = document.getElementById("save-button");
const formMessage = document.getElementById("form-message");

let machineMode = "existing";
let currentMachineId = null;


const shiftFields = {
    shift_a_start: document.getElementById("shift-a-start"),
    shift_a_end: document.getElementById("shift-a-end"),

    shift_b_start: document.getElementById("shift-b-start"),
    shift_b_end: document.getElementById("shift-b-end"),

    shift_c_start: document.getElementById("shift-c-start"),
    shift_c_end: document.getElementById("shift-c-end")
};


const mealFields = {
    breakfast_start: document.getElementById("breakfast-start"),
    lunch_start: document.getElementById("lunch-start"),
    dinner_start: document.getElementById("dinner-start")
};


/* =========================================================
   SYSTEM CLOCK
========================================================= */

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


/* =========================================================
   MESSAGE
========================================================= */

function showMessage(message, type = "") {
    if (!formMessage) {
        return;
    }

    formMessage.textContent = message;
    formMessage.className = "form-message";

    if (type) {
        formMessage.classList.add(type);
    }
}


/* =========================================================
   MACHINE MODE
========================================================= */

function setMode(mode) {
    machineMode = mode;

    existingModeButton.classList.toggle(
        "active",
        mode === "existing"
    );

    newModeButton.classList.toggle(
        "active",
        mode === "new"
    );

    existingMachineGroup.hidden =
        mode !== "existing";

    newMachineGroup.hidden =
        mode !== "new";

    showMessage("");

    if (mode === "new") {
        machineNameInput.value = "";

        clearConfiguration();
    } else {
        loadSelectedMachineConfiguration();
    }
}


/* =========================================================
   CONFIGURATION FIELDS
========================================================= */

function clearConfiguration() {
    Object.values(shiftFields).forEach(field => {
        if (field) {
            field.value = "";
        }
    });

    Object.values(mealFields).forEach(field => {
        if (field) {
            field.value = "";
        }
    });
}


function populateConfiguration(data) {
    shiftFields.shift_a_start.value =
        data.shift_a_start || "";

    shiftFields.shift_a_end.value =
        data.shift_a_end || "";

    shiftFields.shift_b_start.value =
        data.shift_b_start || "";

    shiftFields.shift_b_end.value =
        data.shift_b_end || "";

    shiftFields.shift_c_start.value =
        data.shift_c_start || "";

    shiftFields.shift_c_end.value =
        data.shift_c_end || "";

    mealFields.breakfast_start.value =
        data.breakfast_start || "";

    mealFields.lunch_start.value =
        data.lunch_start || "";

    mealFields.dinner_start.value =
        data.dinner_start || "";
}


/* =========================================================
   LOAD CURRENT CONFIGURATION
========================================================= */

async function loadCurrentConfiguration() {
    try {
        const response = await fetch("/api/config");

        if (!response.ok) {
            throw new Error(
                `Configuration API returned ${response.status}`
            );
        }

        const data = await response.json();

        currentMachineId = data.machine_id || null;

        if (
            currentMachineId &&
            machineSelect
        ) {
            machineSelect.value =
                String(currentMachineId);
        }

        populateConfiguration(data);

        return data;

    } catch (error) {
        console.error(
            "Failed to load current configuration:",
            error
        );

        clearConfiguration();

        showMessage(
            "Unable to load current machine configuration.",
            "error"
        );

        return null;
    }
}


/* =========================================================
   SELECTED MACHINE CONFIGURATION
========================================================= */

async function loadSelectedMachineConfiguration() {
    const selectedMachineId =
        Number(machineSelect.value);

    if (!selectedMachineId) {
        clearConfiguration();
        return;
    }

    /*
     * GET /api/config currently represents the
     * ACTIVE assigned machine.
     *
     * Therefore we can only automatically load the
     * current machine configuration here.
     */

    if (selectedMachineId === currentMachineId) {
        await loadCurrentConfiguration();

        showMessage("");

        return;
    }

    clearConfiguration();

    showMessage(
        "Selected machine is not currently assigned. Enter or confirm its shift configuration, then apply configuration."
    );
}


/* =========================================================
   LOAD MACHINE REGISTRY
========================================================= */

async function loadMachines() {
    try {
        const response = await fetch("/api/machines");

        if (!response.ok) {
            throw new Error(
                `Machine API returned ${response.status}`
            );
        }

        const data = await response.json();

        const machines = data.machines || [];

        currentMachineId =
            data.current_machine_id || null;

        machineSelect.innerHTML = "";

        if (!machines.length) {
            machineSelect.innerHTML = `
                <option value="">
                    No registered machines
                </option>
            `;

            setMode("new");

            return;
        }

        machines.forEach(machine => {
            const option =
                document.createElement("option");

            option.value = String(machine.id);

            option.textContent =
                `${machine.name} [${machine.code}]`;

            machineSelect.appendChild(option);
        });


        if (
            currentMachineId &&
            machines.some(
                machine =>
                    machine.id === currentMachineId
            )
        ) {
            machineSelect.value =
                String(currentMachineId);
        } else {
            machineSelect.value =
                String(machines[0].id);
        }


        await loadSelectedMachineConfiguration();

    } catch (error) {
        console.error(
            "Failed to load machine registry:",
            error
        );

        machineSelect.innerHTML = `
            <option value="">
                Failed to load machine registry
            </option>
        `;

        showMessage(
            "Unable to retrieve registered machines.",
            "error"
        );
    }
}


/* =========================================================
   BUILD PAYLOAD
========================================================= */

function buildPayload() {
    const payload = {
        shift_a_start:
            shiftFields.shift_a_start.value,

        shift_a_end:
            shiftFields.shift_a_end.value,

        shift_b_start:
            shiftFields.shift_b_start.value,

        shift_b_end:
            shiftFields.shift_b_end.value,

        shift_c_start:
            shiftFields.shift_c_start.value,

        shift_c_end:
            shiftFields.shift_c_end.value,

        breakfast_start:
            mealFields.breakfast_start.value || null,

        lunch_start:
            mealFields.lunch_start.value || null,

        dinner_start:
            mealFields.dinner_start.value || null
    };


    if (machineMode === "existing") {
        payload.machine_id =
            Number(machineSelect.value);

        payload.machine = null;
    } else {
        payload.machine_id = null;

        payload.machine =
            machineNameInput.value.trim();
    }


    return payload;
}


/* =========================================================
   VALIDATION
========================================================= */

function validateConfiguration(payload) {
    if (
        machineMode === "existing" &&
        !payload.machine_id
    ) {
        return "Select a registered machine.";
    }


    if (
        machineMode === "new" &&
        !payload.machine
    ) {
        return "Enter a machine name.";
    }


    const requiredShiftFields = [
        payload.shift_a_start,
        payload.shift_a_end,

        payload.shift_b_start,
        payload.shift_b_end,

        payload.shift_c_start,
        payload.shift_c_end
    ];


    if (
        requiredShiftFields.some(
            value => !value
        )
    ) {
        return "Configure all shift start and end times.";
    }


    return null;
}


/* =========================================================
   SAVE CONFIGURATION
========================================================= */

async function saveConfiguration() {
    const payload = buildPayload();

    const validationError =
        validateConfiguration(payload);


    if (validationError) {
        showMessage(
            validationError,
            "error"
        );

        return;
    }


    saveButton.disabled = true;

    saveButton.textContent =
        "APPLYING...";


    showMessage(
        "Updating monitor configuration..."
    );


    try {
        const response = await fetch(
            "/api/config",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify(payload)
            }
        );


        const data = await response.json();


        if (!response.ok) {
            throw new Error(
                data.detail ||
                "Configuration update failed"
            );
        }


        showMessage(
            "Monitor configuration applied successfully.",
            "success"
        );


        if (machineMode === "new") {
            machineNameInput.value = "";

            setMode("existing");
        }


        await loadMachines();


    } catch (error) {
        console.error(
            "Configuration update failed:",
            error
        );


        showMessage(
            error.message,
            "error"
        );

    } finally {
        saveButton.disabled = false;

        saveButton.textContent =
            "APPLY CONFIGURATION";
    }
}


/* =========================================================
   EVENT LISTENERS
========================================================= */

existingModeButton.addEventListener(
    "click",
    () => {
        setMode("existing");
    }
);


newModeButton.addEventListener(
    "click",
    () => {
        setMode("new");
    }
);


machineSelect.addEventListener(
    "change",
    () => {
        loadSelectedMachineConfiguration();
    }
);


saveButton.addEventListener(
    "click",
    saveConfiguration
);


/* =========================================================
   INITIALIZATION
========================================================= */

updateSystemClock();

setInterval(
    updateSystemClock,
    1000
);


loadMachines();