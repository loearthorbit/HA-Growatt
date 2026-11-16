"""Reject energy jumps before decoded readings reach local outputs."""

from __future__ import annotations

import logging
from datetime import datetime
from math import isfinite

from .profiles import wire_profiles
from .recovery import MAX_DEVICES
from .telemetry import Telemetry

# Maximum change between accepted readings, in either direction. Change this
# one value to tune the safeguard for both Shine receivers and all local outputs.
ENERGY_JUMP_LIMIT_KWH = 25

_LOG = logging.getLogger(__name__)


class EnergyGuard:
    """Compare each counter with its last accepted value, in kWh.

    Live and buffered uploads have separate baselines. Missing fields do not
    erase earlier counters, and rejecting a packet never moves the baseline.
    """

    def __init__(self) -> None:
        self.rejected = 0
        self._counters: dict[tuple[str, bool], dict[str, tuple[float, datetime | None]]] = {}

    def _energy_values(self, telemetry):
        metadata = telemetry.sensor_metadata
        if metadata is None:
            metadata = wire_profiles().get(telemetry.profile, {}).get("sensors", {})
        for key, sensor in metadata.items():
            if sensor.get("device_class") != "energy":
                continue
            unit = sensor.get("unit")
            if unit not in {"Wh", "kWh", "MWh"}:
                continue
            source = sensor.get("source", key)
            raw = telemetry.values.get(source)
            if raw is None:
                continue
            try:
                value = float(raw) / sensor.get("divisor", 1)
                value *= {"Wh": 0.001, "kWh": 1, "MWh": 1000}[unit]
            except (TypeError, ValueError, OverflowError, ZeroDivisionError):
                value = float("nan")
            yield source, value

    def accept(self, telemetry: Telemetry) -> bool:
        identity = telemetry.device_id or telemetry.values.get("pvserial")
        if not isinstance(identity, str):
            return True
        key = (identity, telemetry.buffered)
        previous = self._counters.get(key, {})
        current = dict(self._energy_values(telemetry))
        for source, value in current.items():
            old = previous.get(source)
            daily_reset = False
            if old is not None:
                old_value, old_stamp = old
                stamp = telemetry.recorded_at
                daily_reset = (
                    source.lower().endswith(("today", "_tod"))
                    and old_stamp is not None
                    and stamp is not None
                    and stamp.date() > old_stamp.date()
                    and 0 <= value < old_value
                )
            if not isfinite(value) or (
                old is not None and abs(value - old[0]) > ENERGY_JUMP_LIMIT_KWH and not daily_reset
            ):
                self.rejected += 1
                # Leave identities, exact readings and packet bytes out of logs.
                _LOG.warning(
                    "Discarded decoded reading: energy field %s exceeds the "
                    "%s kWh jump limit or is not finite",
                    source,
                    ENERGY_JUMP_LIMIT_KWH,
                )
                return False
        if current and (key in self._counters or len(self._counters) < MAX_DEVICES * 2):
            self._counters.setdefault(key, {}).update(
                {source: (value, telemetry.recorded_at) for source, value in current.items()}
            )
        return True
