# Changelog

All notable changes to this project are documented in this file.

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
