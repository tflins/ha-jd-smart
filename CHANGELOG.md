# Changelog

All notable changes to this project are documented in this file.

## 0.3.5

- Use Home Assistant's IPv4 HTTP connector for JD endpoints to avoid persistent
  dual-stack DNS resolver failures in Home Assistant Container installations.
- Route initial connection failures through the coordinator's standard update
  failure handling instead of logging them as unexpected exceptions.
- Include the underlying connection reason in terminal update failure logs.

## 0.3.4

- Distinguish transient WJLogin failures from rejected credentials so temporary
  network or server errors no longer trigger unnecessary reauthentication.
- Serialize shared token refreshes and Wangyin requests across multiple devices.
- Preserve the latest full state when control or snapshot responses contain no
  streams, and merge partial control responses into the current snapshot.
- Add explicit cloud request timeouts and reject malformed or offline snapshots.
- Generate per-installation request device IDs and prevent credentials from a
  different JD account from overwriting an existing entry.
- Advertise optional climate controls only when their streams are available,
  and improve unknown switch and washer error states.
- Run integration unit tests in GitHub Actions.

## 0.3.3

- Keep the last successful device snapshot for up to five minutes during
  transient JD cloud or network failures before marking entities unavailable.
- Reduce repeated update warnings and include the request path and underlying
  exception details in connection errors.

## 0.3.2

- Only request Home Assistant reauthentication for explicit authentication
  failures. Temporary device, cloud, or network failures now keep the entity
  unavailable without incorrectly invalidating a working JD account session.
- Keep washer settings available while the appliance is powered off, and hide
  stale cycle duration values when the washer is idle.

## 0.3.1

- Clear Android legacy global proxy fields during capture restoration and
  cleanup so the phone does not retain an unreachable proxy after the helper
  exits.

## 0.3.0

- Add MiniJ washing-machine entities for power, program selection, start,
  pause, child lock, reservation, state, remaining time, completion, and
  diagnostics.
- Create device entities dynamically from reported streams.
- Add multi-device discovery and selection.
- Fix WJLogin refresh for JD Xiaojia 2.3.0 by using application ID 1421,
  application name `京东小家`, and the matching WJLogin protocol.
- Add one-field capture JSON import for setup and reauthentication.
- Add an optional Android/ADB reauthentication helper with automatic proxy
  restoration and private credential storage.
- Add API, config-flow, and capture-helper tests.

## 0.2.0

- Add Home Assistant config flow and JD Smart air-conditioner entities.
