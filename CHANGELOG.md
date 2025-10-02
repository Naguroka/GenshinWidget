# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [1.2.0] - 2025-10-02

- Replace the initial async task setup with `refresh_notes()` to avoid qasync type errors and keep updates flowing.
- Guard icon pixmap loading to prevent null pixmap warnings and hide missing assets gracefully.
- Add centralized shutdown handling plus signal/atexit hooks so closing the widget or console fully stops the asyncio loop and background tasks.
- Set the application/process metadata to "Genshin Widget" for clearer window titles and taskbar grouping on Windows.

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

