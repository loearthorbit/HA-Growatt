# HA Growatt energy guard development

This fork's **0.9.1-dev.1** app contains the 25 kWh energy safeguard and the
incomplete numeric-field decoding fix. It uses the fork's receiver image, not
the original project's image. It is a development build, not a hardware-qualified
release. See [installation and rollback](../../docs/fork-installation.md) before
replacing a working receiver. MQTT identifiers and cloud forwarding are retained.

The app also provides cloud-failure fallback, connection diagnostics and supported
inverter settings. See the [feature guide](https://github.com/Herbertmt978/HA-Growatt/blob/main/docs/home-assistant-features.md)
for the available controls and their limits.

Receive Growatt inverter readings in Home Assistant through MQTT while
forwarding datalogger traffic to Growatt.

See [installation](../../docs/installation.md) and
[configuration](../../docs/configuration.md) before replacing an existing service.

## Disclaimer

By using HA Growatt, you accept responsibility for the security of the data you
extract. Neither HA Growatt nor Growatt can be held responsible for data breaches
stemming from the extraction of data outside of the Growatt ecosystem.
