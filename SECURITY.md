# Security Policy

## Supported versions

Security fixes are applied to the latest release on the default branch.

## Credential handling

JD Smart Cookies, `tgt` values, capture JSON files, and mitmproxy CA keys are
secrets. Do not include them in issues, pull requests, logs, screenshots, or
example files.

The Android capture helper stores its state under
`~/.local/state/ha-jd-smart` by default. The directory is owner-only, and the
generated JSON is written with mode `0600`. Users remain responsible for
protecting and deleting that directory when it is no longer needed.

The helper installs no certificate automatically. Users explicitly install the
generated user CA on Android and must remove that CA from Android settings when
packet inspection is no longer required.

## Reporting a vulnerability

Do not open a public issue containing an exploit or credentials. Use GitHub's
private vulnerability reporting feature for this repository. Include affected
versions, reproduction steps with sanitized data, and the expected impact.

Device compatibility bugs without sensitive data may be reported as normal
issues.
