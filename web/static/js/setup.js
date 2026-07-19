const machineSelect = document.getElementById("machine-select");
const machineNameInput = document.getElementById("machine-name");

const existingMachineGroup = document.getElementById("existing-machine-group");
const newMachineGroup = document.getElementById("new-machine-group");

const existingModeButton = document.getElementById("existing-mode-button");
const newModeButton = document.getElementById("new-mode-button");

const assignmentMachine = document.getElementById("assignment-machine");
const assignButton = document.getElementById("assign-button"); // For future wiring
const editButton = document.getElementById("edit-button");
const cancelButton = document.getElementById("cancel-button");
const saveContainer = document.getElementById("save-container");

const saveButton = document.getElementById("save-button");
const formMessage = document.getElementById("form-message");

let machineMode = "existing";
let editMode = false;
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
            { hour12: false }
        );
    }

    if (dateElement) {
        dateElement.textContent = now.toLocaleDateString(
            "en-IN",
            { day: "2-digit", month: "short", year: "numeric" }
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
   INPUT TOGGLING (EDIT MODE)
========================================================= */

function setInputsEnabled(enabled) {
    Object.values(shiftFields).forEach(field => {
        if (field) field.disabled = !enabled;
    });

    Object.values(mealFields).forEach(field => {
        if (field) field.disabled = !enabled;
    });

    if (machineMode === "existing") {
        saveContainer.hidden = !enabled;
        if (editButton) editButton.hidden = enabled;
        if (cancelButton) cancelButton.hidden = !enabled;
    } else {
        saveContainer.hidden = false;
        if (editButton) editButton.hidden = true;
        if (cancelButton) cancelButton.hidden = true;
    }
    
    // Kept for fallback, though we are setting this explicitly in events now
    editMode = enabled;
}

function cancelEditing() {
    editMode = false;
    setInputsEnabled(false);
    loadSelectedMachineConfiguration();
    showMessage("");
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

    if (mode === "existing") {
        existingMachineGroup.style.display = "";
        newMachineGroup.style.display = "none";
    } else {
        existingMachineGroup.style.display = "none";
        newMachineGroup.style.display = "";
    }
    
    showMessage("");

    if (mode === "new") {
        machineNameInput.value = "";
        clearConfiguration();
        editMode = true;
        setInputsEnabled(true);
    } else {
        loadSelectedMachineConfiguration();
        editMode = false;
        setInputsEnabled(false);
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
    shiftFields.shift_a_start.value = data.shift_a_start || "";
    shiftFields.shift_a_end.value = data.shift_a_end || "";

    shiftFields.shift_b_start.value = data.shift_b_start || "";
    shiftFields.shift_b_end.value = data.shift_b_end || "";

    shiftFields.shift_c_start.value = data.shift_c_start || "";
    shiftFields.shift_c_end.value = data.shift_c_end || "";

    mealFields.breakfast_start.value = data.breakfast_time || "";
    mealFields.lunch_start.value = data.lunch_time || "";
    mealFields.dinner_start.value = data.dinner_time || "";
}

/* =========================================================
   LOAD CURRENT CONFIGURATION
========================================================= */

async function loadCurrentConfiguration() {
    try {
        const response = await fetch("/api/config");

        if (!response.ok) {
            throw new Error(`Configuration API returned ${response.status}`);
        }

        const data = await response.json();

        currentMachineId = data.machine_id || null;

        if (currentMachineId && machineSelect) {
            machineSelect.value = String(currentMachineId);
        }
        
        if (currentMachineId && assignmentMachine) {
            assignmentMachine.value = String(currentMachineId);
        }

        populateConfiguration(data);
        return data;

    } catch (error) {
        console.error("Failed to load current configuration:", error);
        clearConfiguration();
        showMessage("Unable to load current machine configuration.", "error");
        return null;
    }
}

/* =========================================================
   SELECTED MACHINE CONFIGURATION
========================================================= */

async function loadSelectedMachineConfiguration() {
    const selectedMachineId = Number(machineSelect.value);

    if (!selectedMachineId) {
        clearConfiguration();
        return;
    }

    try {
        const response = await fetch(`/api/machines/${selectedMachineId}/config`);

        if (!response.ok) {
            throw new Error();
        }

        const data = await response.json();
        populateConfiguration(data);
        showMessage("");

    } catch (error) {
        console.error(error);
        clearConfiguration();
        showMessage("Unable to load machine configuration.", "error");
    }
}

/* =========================================================
   LOAD MACHINE REGISTRY
========================================================= */

async function loadMachines() {
    try {
        const response = await fetch("/api/machines");

        if (!response.ok) {
            throw new Error(`Machine API returned ${response.status}`);
        }

        const data = await response.json();
        const machines = data.machines || [];

        currentMachineId = data.current_machine_id || null;

        machineSelect.innerHTML = "";
        assignmentMachine.innerHTML = "";

        if (!machines.length) {
            const noMachineHTML = `<option value="">No registered machines</option>`;
            machineSelect.innerHTML = noMachineHTML;
            assignmentMachine.innerHTML = noMachineHTML;
            setMode("new");
            return;
        }

        machines.forEach(machine => {
            const optionText = `${machine.name} [${machine.code}]`;
            
            const option1 = document.createElement("option");
            option1.value = String(machine.id);
            option1.textContent = optionText;
            machineSelect.appendChild(option1);
            
            const option2 = document.createElement("option");
            option2.value = String(machine.id);
            option2.textContent = optionText;
            assignmentMachine.appendChild(option2);
        });

        if (currentMachineId && machines.some(m => m.id === currentMachineId)) {
            machineSelect.value = String(currentMachineId);
            assignmentMachine.value = String(currentMachineId);
        } else {
            machineSelect.value = String(machines[0].id);
            assignmentMachine.value = String(machines[0].id);
        }

        await loadSelectedMachineConfiguration();

    } catch (error) {
        console.error("Failed to load machine registry:", error);
        
        const errorHTML = `<option value="">Failed to load machine registry</option>`;
        machineSelect.innerHTML = errorHTML;
        assignmentMachine.innerHTML = errorHTML;

        showMessage("Unable to retrieve registered machines.", "error");
    }
}

/* =========================================================
   BUILD PAYLOAD
========================================================= */

function buildPayload() {
    const payload = {
        shift_a_start: shiftFields.shift_a_start.value,
        shift_a_end: shiftFields.shift_a_end.value,

        shift_b_start: shiftFields.shift_b_start.value,
        shift_b_end: shiftFields.shift_b_end.value,

        shift_c_start: shiftFields.shift_c_start.value,
        shift_c_end: shiftFields.shift_c_end.value,

        breakfast_time: mealFields.breakfast_start.value || null,
        lunch_time: mealFields.lunch_start.value || null,
        dinner_time: mealFields.dinner_start.value || null
    };

    if (machineMode === "existing") {
        payload.machine_id = Number(machineSelect.value);
        payload.machine = null;
    } else {
        payload.machine_id = null;
        payload.machine = machineNameInput.value.trim();
    }

    return payload;
}

/* =========================================================
   VALIDATION
========================================================= */

function validateConfiguration(payload) {
    if (machineMode === "existing" && !payload.machine_id) {
        return "Select a registered machine.";
    }

    if (machineMode === "new" && !payload.machine) {
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

    if (requiredShiftFields.some(value => !value)) {
        return "Configure all shift start and end times.";
    }

    return null;
}

/* =========================================================
   SAVE CONFIGURATION
========================================================= */

async function saveConfiguration() {
    const payload = buildPayload();
    const validationError = validateConfiguration(payload);

    if (validationError) {
        showMessage(validationError, "error");
        return;
    }

    if (saveButton) {
        saveButton.disabled = true;
        saveButton.textContent = "SAVING...";
    }

    showMessage("Updating monitor configuration...");

    try {
        const response = await fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Configuration update failed");
        }

        showMessage("Monitor configuration applied successfully.", "success");

        if (machineMode === "new") {
            machineNameInput.value = "";
            setMode("existing");
        }
        
        editMode = false;
        setInputsEnabled(false);
        await loadMachines();

    } catch (error) {
        console.error("Configuration update failed:", error);
        showMessage(error.message, "error");
    } finally {
        if (saveButton) {
            saveButton.disabled = false;
            saveButton.textContent = "SAVE CONFIGURATION";
        }
    }
}

/* =========================================================
   ASSIGN MACHINE
========================================================= */

async function assignSelectedMachine() {
    const machineId = Number(assignmentMachine.value);

    if (!machineId) {
        showMessage("Select a machine.", "error");
        return;
    }

    try {
        const response = await fetch("/api/machines/assign", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                machine_id: machineId
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.message || "Assignment failed");
        }

        showMessage("Machine assigned successfully.", "success");

        await loadMachines();
        await loadCurrentConfiguration();

    } catch (error) {
        console.error(error);
        showMessage(error.message, "error");
    }
}

/* =========================================================
   EVENT LISTENERS
========================================================= */

if (existingModeButton) existingModeButton.addEventListener("click", () => setMode("existing"));
if (newModeButton) newModeButton.addEventListener("click", () => setMode("new"));
if (machineSelect) machineSelect.addEventListener("change", () => loadSelectedMachineConfiguration());
if (saveButton) saveButton.addEventListener("click", saveConfiguration);

if (editButton) {
    editButton.addEventListener("click", () => {
        editMode = true;
        setInputsEnabled(true);
    });
}

if (cancelButton) {
    cancelButton.addEventListener("click", cancelEditing);
}

if (assignButton) {
    assignButton.addEventListener("click", assignSelectedMachine);
}

/* =========================================================
   INITIALIZATION
========================================================= */

updateSystemClock();
setInterval(updateSystemClock, 1000);

loadMachines();
existingMachineGroup.style.display = "";
newMachineGroup.style.display = "none";
editMode = false;
setInputsEnabled(false);