# JD Smart for Home Assistant

Unofficial Home Assistant custom integration for devices connected through the
JD Smart / JD Xiaojia app. The current release supports air conditioners and a
tested subset of washing machines.

This project is not affiliated with JD.com, JD Smart, JD Xiaojia, or Home
Assistant.

[简体中文 README](README_zh-Hans.md)

## Features

### Air conditioners

- Power and HVAC modes.
- Target temperature and current temperature/humidity.
- Fan speed, vertical swing, horizontal direction, and sleep presets.
- Backlight, display, and powerful-mode switches when exposed by the device.

### Washing machines

- Power, start, pause, and child lock.
- Program selection and delayed start.
- State, remaining time, reservation time, completion, and error reporting.
- Programs discovered on the tested MiniJ washing machine, including standard,
  spin only, drum clean, quick wash, baby, boil 95 C, bra care, towel sanitize,
  sports, shirt collar, and new clothes.

Entities are created from streams actually reported by each device. Unsupported
controls are therefore omitted instead of appearing as unavailable entities.

### Authentication

- Home Assistant config flow with multi-device selection.
- Automatic WJLogin `tgt` and Cookie refresh while the JD account session is
  still valid.
- One-field JSON import for initial setup and reauthentication.
- Optional Android/ADB helper that captures only the minimum authentication
  fields and restores the phone's previous proxy automatically.

## Installation

### HACS

Add the following URL as a HACS custom repository with category `Integration`:

```text
https://github.com/tflins/ha-jd-smart
```

Install **JD Smart**, restart Home Assistant, then open:

```text
Settings -> Devices & services -> Add integration -> JD Smart
```

### Manual installation

Copy `custom_components/jd_smart` into the Home Assistant configuration
directory:

```text
config/custom_components/jd_smart
```

Restart Home Assistant and add the integration from **Settings -> Devices &
services**.

## Recommended Android setup

The helper supports macOS and Linux. It requires Python 3, ADB, an Android
phone with USB debugging enabled, and the JD Xiaojia app already signed in.

Clone this repository, connect the phone, and run:

```bash
tools/reauth.sh setup
```

Install the copied mitmproxy certificate as an Android user CA certificate.
This setup step is normally needed only once. Then capture a fresh session:

```bash
tools/reauth.sh capture
```

The helper temporarily configures the Android proxy, launches the JD Xiaojia
app, waits for an authenticated request, restores the previous proxy, saves a
private JSON file, and copies it to the clipboard when supported.

In Home Assistant, choose **JD Smart -> Add device -> Import capture JSON** and
paste the generated JSON. The same JSON field is available when Home Assistant
requests reauthentication.

The default local state directory is:

```text
~/.local/state/ha-jd-smart
```

Override it with `JD_SMART_STATE_DIR`. If automatic IP detection is unsuitable,
set `JD_SMART_PROXY_HOST` to the computer IP reachable by the phone.

When the helper is no longer needed, run:

```bash
tools/reauth.sh cleanup
```

This clears the Android proxy and removes the downloaded certificate file. The
installed user CA must still be removed separately in Android settings.

## Authentication lifecycle

The integration refreshes `tgt` and the associated Cookie automatically. The
refresh implementation matches WJLogin SDK 12.0.10 used by JD Xiaojia 2.3.0,
including application ID `1421` and application name `京东小家`.

Normal Home Assistant restarts do not require another capture. A new capture is
only needed when JD invalidates the underlying account session, the user signs
out, or the mobile app changes its private authentication protocol.

Manual entry remains available for captures made with Proxyman, Charles, HTTP
Toolkit, mitmproxy, or another HTTPS inspection tool. Use values from the same
authenticated request whenever possible.

## Security

The captured Cookie and `tgt` grant access to the user's JD Smart session.

- Never commit capture JSON, mitmproxy dumps, HAR files, Cookies, or tokens.
- The helper writes JSON with owner-only permissions and does not save complete
  HTTP flows.
- The helper state directory contains a mitmproxy CA private key. Protect it as
  sensitive data.
- Remove the Android user CA when packet inspection is no longer required.
- Use this integration only with an account and devices you own or administer.

See [SECURITY.md](SECURITY.md) for credential handling and vulnerability
reporting guidance.

## Supported and tested devices

Private JD device APIs vary by product and firmware. The integration currently
contains mappings validated against:

- JD Xiaojia-connected air conditioners using the existing JD Smart stream
  model.
- A MiniJ washing machine exposing `Power`, `Work`, `State`, `Error`, `Mode`,
  `BabyLock`, `RemainingTimeMin`, `ReserveTimeRemainingMinute`, and
  `ReserveTimeSetHour`.

Other devices may be discovered but will only receive entities for known
streams. Open an issue with sanitized stream names and values when requesting a
new device mapping. Do not post authentication data.

## Development

Validate source and JSON files locally:

```bash
python3 -m pip install --no-deps homeassistant==2025.3.4
python3 -m pip install -r requirements-test.txt
python3 -m unittest discover -s tests
python3 -m compileall -q custom_components/jd_smart tools tests
bash -n tools/reauth.sh
```

GitHub Actions also runs HACS and Hassfest validation.

## Acknowledgements

This repository builds on the original `ha-jd-smart` work by
[orangeboyChen](https://github.com/orangeboyChen/ha-jd-smart). The original MIT
license and attribution are preserved.

## Disclaimer

This integration uses undocumented private APIs that may change without
notice. Use may be subject to JD Smart / JD Xiaojia terms. Use it at your own
risk. See [DISCLAIMER.md](DISCLAIMER.md) for the full disclaimer.
