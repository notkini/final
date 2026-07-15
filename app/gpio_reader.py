"""
Reads the machine's UP/DOWN signal off GPIO17 (fed by the opto-isolated
input module, which converts the PLC's 24V signal down to a clean
3.3V/5V logic level -- no manual debounce needed in hardware, so we do it
here in software via gpiozero's bounce_time).

On a laptop with no real Pi/GPIO hardware, SIMULATION_MODE generates a
plausible UP/DOWN signal instead of crashing, so the rest of the stack
(monitor loop, DB writes, calculations) can be developed and tested
before the hardware is on-site.
"""
import logging
import random
import threading
import time as time_module
from datetime import datetime, timezone

from app.config import config

logger = logging.getLogger("weldomat.gpio_reader")


class GpioReader:
    """
    Calls on_state_change(state: str, event_time: datetime) exactly once
    per genuine transition (post-debounce). state is always 'UP' or 'DOWN'.
    """

    def __init__(self, on_state_change):
        self.on_state_change = on_state_change
        self._stop_event = threading.Event()
        self._thread = None
        self.current_state = None

    def start(self):
        if config.SIMULATION_MODE:
            logger.info(
                "SIMULATION_MODE enabled -- generating synthetic UP/DOWN "
                "signal instead of reading real GPIO"
            )
            self._thread = threading.Thread(
                target=self._run_simulation,
                daemon=True,
            )
        else:
            logger.info(
                "Reading real GPIO%s (bounce_time=%.3fs, active_high=%s)",
                config.GPIO_PIN,
                config.DEBOUNCE_SECONDS,
                config.ACTIVE_HIGH,
            )
            self._thread = threading.Thread(
                target=self._run_gpio,
                daemon=True,
            )

        self._thread.start()

    def stop(self):
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=5)

    # ---- Real hardware path ----
    def _run_gpio(self):
        try:
            from gpiozero import DigitalInputDevice
        except ImportError:
            logger.error(
                "gpiozero not available -- can't read real GPIO. "
                "Set SIMULATION_MODE=true in .env for laptop development."
            )
            return

        # The opto module actively drives the Pi input HIGH or LOW.
        # pull_up=False is correct for this external driven industrial input.
        pin = DigitalInputDevice(
            config.GPIO_PIN,
            pull_up=False,
            bounce_time=config.DEBOUNCE_SECONDS,
        )

        def _read_state():
            # ACTIVE_HIGH=True means GPIO HIGH represents machine UP.
            is_up = pin.is_active if config.ACTIVE_HIGH else not pin.is_active
            return "UP" if is_up else "DOWN"

        pin.when_activated = lambda: self._emit(_read_state())
        pin.when_deactivated = lambda: self._emit(_read_state())

        # Emit the initial state once at startup so the DB has a baseline.
        self._emit(_read_state())

        while not self._stop_event.is_set():
            time_module.sleep(0.5)

        pin.close()

    # ---- Simulation path (no hardware required) ----
    def _run_simulation(self):
        # Start DOWN, flip occasionally with randomized dwell times so the
        # rest of the system sees realistic-looking transitions.
        self._emit("DOWN")

        while not self._stop_event.is_set():
            dwell = random.uniform(20, 90)  # seconds in current state
            slept = 0.0

            while slept < dwell and not self._stop_event.is_set():
                step = min(0.5, dwell - slept)
                time_module.sleep(step)
                slept += step

            if self._stop_event.is_set():
                break

            next_state = "DOWN" if self.current_state == "UP" else "UP"
            self._emit(next_state)

    def _emit(self, state: str):
        if state == self.current_state:
            return  # not a real transition

        self.current_state = state
        event_time = datetime.now(timezone.utc)

        logger.info("Machine state changed -> %s @ %s", state, event_time)

        try:
            self.on_state_change(state, event_time)
        except Exception:
            logger.exception("on_state_change callback raised an exception")