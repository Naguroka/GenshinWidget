# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.1.1] - 2025-09-13

- Fix Hoyolab auth: stop logging cookie values and switch default logs to INFO.
- Make real-time notes fetch auto-detect the correct UID.
- Accept optional cookies `account_id_v2` and `ltmid_v2` if present.
- Correct README: `ltuid_v2` is Hoyolab account ID, not in-game UID; improved cookie setup docs.

## [1.1.0] - 2025-09-13

- Add Linux support and docs.
- Resolve assets and config via paths relative to the script for cross‑platform launching (.desktop/systemd/terminal).
- Add `requirements.txt` for simpler installation.
- Add `run.sh` helper to run on Linux in background.
- Clean up README, clarify dependencies and cookie setup.

## [1.0.0] - 2024-xx-xx

- Initial release for Windows with PyQt5 widget and Hoyolab integration.
