"""Energy jumps must not poison the baseline or another inverter's readings."""

from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from ha_growatt.energy_guard import ENERGY_JUMP_LIMIT_KWH, EnergyGuard
from ha_growatt.telemetry import Telemetry

RAW_LIMIT = ENERGY_JUMP_LIMIT_KWH * 10


def reading(values, *, identity="INVERT0001", stamp=datetime(2026, 11, 16, 12)):
    return Telemetry({"pvserial": identity} | values, stamp, "classic-6")


@pytest.mark.parametrize("change", [RAW_LIMIT + 1, -RAW_LIMIT - 1, 4294967295])
def test_whole_packet_rejected_and_last_good_baseline_kept(change):
    guard = EnergyGuard()
    assert guard.accept(reading({"pvenergytotal": 500, "epv1total": 300}))
    assert not guard.accept(reading({"pvenergytotal": 550, "epv1total": 300 + change}))
    # The other counter from the rejected packet must not become the baseline.
    assert not guard.accept(reading({"pvenergytotal": 500 + RAW_LIMIT + 1}))
    assert guard.accept(reading({"pvenergytotal": 501, "epv1total": 301}))
    assert guard.rejected == 2


@pytest.mark.parametrize("change", [RAW_LIMIT, -RAW_LIMIT, 0])
def test_exactly_the_limit_is_allowed(change):
    guard = EnergyGuard()
    assert guard.accept(reading({"pvenergytotal": 500}))
    assert guard.accept(reading({"pvenergytotal": 500 + change}))


def test_devices_and_missing_counters_are_independent():
    guard = EnergyGuard()
    assert guard.accept(reading({"pvenergytotal": 500}))
    assert guard.accept(reading({"pvenergytotal": 999999}, identity="INVERT0002"))
    assert guard.accept(reading({"pvpowerout": 1200}))
    assert not guard.accept(reading({"pvenergytotal": 500 + RAW_LIMIT + 1}))


def test_daily_reset_requires_a_later_date_and_never_resets_lifetime_totals():
    guard = EnergyGuard()
    first = reading({"pvenergytoday": RAW_LIMIT + 50, "pvenergytotal": 5000})
    assert guard.accept(first)
    assert not guard.accept(reading({"pvenergytoday": 0}))
    assert not guard.accept(reading({"pvenergytoday": 0}, stamp=None))
    next_day = first.recorded_at + timedelta(days=1)
    assert not guard.accept(reading({"pvenergytotal": 0}, stamp=next_day))
    assert guard.accept(reading({"pvenergytoday": 0, "pvenergytotal": 5001}, stamp=next_day))
    assert not guard.accept(reading({"pvenergytoday": RAW_LIMIT + 1}, stamp=next_day))


def test_buffered_records_have_their_own_last_good_baseline():
    guard = EnergyGuard()
    assert guard.accept(reading({"pvenergytotal": 5000}))
    historical = replace(reading({"pvenergytotal": 50}), buffered=True)
    assert guard.accept(historical)
    assert not guard.accept(
        replace(historical, values=historical.values | {"pvenergytotal": 50 + RAW_LIMIT + 1})
    )
    assert guard.accept(reading({"pvenergytotal": 5001}))
    assert guard.accept(replace(historical, values=historical.values | {"pvenergytotal": 51}))


@pytest.mark.parametrize(
    "unit,divisor,units_per_kwh", [("Wh", 10, 1000), ("kWh", 100, 1), ("MWh", 1000, 0.001)]
)
def test_custom_metadata_sources_and_units_define_the_limit(unit, divisor, units_per_kwh):
    guard = EnergyGuard()
    custom = Telemetry(
        {"pvserial": "INVERT0001", "raw_energy": "1000000"},
        None,
        "custom:test",
        sensor_metadata={
            "energy": {
                "source": "raw_energy",
                "divisor": divisor,
                "unit": unit,
                "device_class": "energy",
            }
        },
    )
    assert guard.accept(custom)
    jump = int(ENERGY_JUMP_LIMIT_KWH * divisor * units_per_kwh) + 1
    assert not guard.accept(
        replace(custom, values=custom.values | {"raw_energy": str(1000000 + jump)})
    )


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "not a number"])
def test_non_finite_energy_is_rejected_even_without_a_baseline(value):
    guard = EnergyGuard()
    assert not guard.accept(reading({"pvenergytotal": value}))
    assert guard.accept(reading({"pvenergytotal": 10}))


def test_device_id_and_profile_change_do_not_bypass_the_baseline():
    guard = EnergyGuard()
    first = replace(reading({"pvenergytotal": 500}), device_id="device")
    assert guard.accept(first)
    assert not guard.accept(
        replace(first, profile="mod-6", values={"pvenergytotal": 500 + RAW_LIMIT + 1})
    )


def test_changing_the_shared_constant_changes_validation_and_warning(monkeypatch, caplog):
    monkeypatch.setattr("ha_growatt.energy_guard.ENERGY_JUMP_LIMIT_KWH", 1)
    guard = EnergyGuard()
    assert guard.accept(reading({"pvenergytotal": 500}))
    assert guard.accept(reading({"pvenergytotal": 510}))
    assert not guard.accept(reading({"pvenergytotal": 521}))
    assert "1 kWh jump limit" in caplog.text
