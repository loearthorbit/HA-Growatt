# Install the energy guard development app

This fork provides **HA Growatt (energy guard development)** for the Home
Assistant App Store. Version **0.9.1-dev.2** contains receiver package
**0.9.1.dev2**, including the energy filter and incomplete-field decoding fix.
It is a development build, not a hardware-qualified release. Images cover
**amd64** and **aarch64**.

This package is for the **app/add-on and MQTT route**. The native HACS
integration still downloads the original project's receiver wheel; adding this
fork in HACS does not install these receiver changes. An existing optional
companion can remain installed alongside the new app.

## Before changing anything

1. Make a Home Assistant backup that includes the current HA Growatt app and
   MQTT broker. Keep the original app installed so it can be restarted.
2. Save the app options, host port mapping and version privately. Include
   per-inverter profiles, discovery settings, MQTT broker settings and any
   advanced configuration. Do not post credentials or packet captures.
3. Note the existing inverter entity IDs and compare their current power, daily
   energy and lifetime energy with the inverter or a trustworthy reading.
   This filter does not repair statistics already recorded in Home Assistant.

The fork is a **separate app installation**, not an in-place update of the
original repository's app. Its protected options and restart cache are separate.
Do not assume the new app has inherited them. Without a saved baseline, its
first accepted energy reading establishes the comparison value.

## Install from the fork

1. Open **Settings → Apps → App store → Repositories**. Older Home Assistant
   versions call Apps **Add-ons**.
2. Add:

   ```text
   https://github.com/loearthorbit/HA-Growatt
   ```

3. Refresh the store and find **HA Growatt (energy guard development)** under
   **HA Growatt energy guard development builds**. Check that its version is
   **0.9.1-dev.2**, then install it. Do not start it yet.
4. Copy the existing app's effective options and host port mapping. Preserve
   the broker, discovery profile, inverter profiles and timestamp options.
   Leave datalogger destination settings unchanged if the new app will use
   the same Home Assistant address and port.
5. Disable automatic startup and the watchdog for the original app, then stop
   it. Only one receiver can own the datalogger port, normally **5279**.
6. Start the development app and open its web UI. Check that its receiver
   version is **0.9.1.dev2**, the MQTT broker connects and every inverter
   produces fresh readings. If an optional companion still points at the old
   app, update its app connection.

## Check the replacement

Before keeping this build in service, verify:

- Fresh readings from **every** inverter, with plausible power and energy.
- The same MQTT entity IDs, units and state classes, with existing history.
- The expected timestamp behaviour and no duplicated Energy Dashboard source.
- Continued Growatt cloud forwarding and ShinePhone updates when forwarding is
  enabled. Local filtering does not discard packets on the cloud connection.
- Recovery after an app restart and MQTT reconnection.
- Logs and downloaded diagnostics for `energy_jump_rejections`. A rejected
  decoded reading is withheld from all local outputs, not just its energy field.

The **25 kWh** limit applies in both directions and stays anchored to the last
accepted values. Daily energy can reset downwards on a later packet date;
buffered uploads have a separate baseline. A real increase of more than the
limit after a long outage can also be withheld. The value is defined once as
`ENERGY_JUMP_LIMIT_KWH` in [energy_guard.py](../src/ha_growatt/energy_guard.py).
Changing it requires rebuilding the image and increasing the development app
version so Home Assistant can recognise the new build.

## Roll back

Stop the development app and disable its automatic startup and watchdog.
Restart the original app with its saved settings and port mapping, then confirm
fresh readings and cloud forwarding. Do not run both receivers on the same
port. Restore the Home Assistant backup if configuration or history needs it.
Keep the original installation until the compatibility and installation checks
are complete; do not archive it just because this package installs successfully.

## Building and publishing

The root Dockerfile has an `addon` target that starts as root only to read
Supervisor's protected options; the application then drops privileges. The
default `standalone` target retains the unprivileged Docker entry point.

The **Development app image** workflow runs the README checks on Python 3.12,
3.13 and 3.14, plus installed-container probes on amd64, arm64 and arm/v7.
This fork does not build or qualify 32-bit x86 images.
The app targets also check Supervisor options and the privilege drop on amd64
and arm64. A development tag, for example `v0.9.1-dev.2`, publishes the app image
only after those checks pass. The tag must match the app configuration version.
Manual workflow runs on a branch check the build without publishing it.

Images are published to:

```text
ghcr.io/loearthorbit/ha-growatt:0.9.1-dev.2
```

GitHub may initially make a new container package private, even when its source
repository is public. Its owner must set the package visibility to **Public**
in GitHub Packages settings before Home Assistant can pull it without GitHub
credentials. Verify an anonymous image pull before advertising it as available.
Do not put registry credentials in the app options or repository.
