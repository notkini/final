function isMachineAssigned(data) {
    return data && data.assigned === true;
}


function isUnassignedMachine(data) {
    return !isMachineAssigned(data);
}