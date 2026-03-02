# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-02

### Added

- Complete rewrite from Python to Rust
- System tray (optional `tray` feature): envelope icon, dynamic menu rebuild after import, disabled submenus without config
- System tray: export directory picker via folder browser dialog
- System tray: Thunderbird import with YesNoCancel dialog (import accounts / import with passwords / cancel)
- System tray: action-specific notification titles (Export terminé, Tri terminé, etc.)
- Thunderbird password extraction from NSS, written directly to `.env`
- Config split into three files: `accounts.yaml` (connection), `settings.yaml` (behaviour), `.env` (passwords)
- Platform-appropriate config directory: `%APPDATA%` (Windows), `~/.config` (Linux), `~/Library/Application Support` (macOS)

### Fixed

- System tray: silent notifications caused by `ControlFlow::Wait` (changed to `Poll`)
- System tray: Thunderbird profile detection now matches CLI logic (looks for `prefs.js`)
- `get_short_name()` incorrectly parsed `"Name <email>"` format (returned `JDJ` instead of `JD`)
- Two pre-existing test bugs: `get_short_name` assertion and `decode_imap_utf7` expected value

### Changed

- `accounts.yaml` no longer stores behaviour fields (moved to `settings.yaml`)
- Tray "Ouvrir config" menu item renamed to "Paramètres…"
- `ActionResult::Success` now carries `(title, message)` for per-action notification titles
