# Genshin Widget

This is a small PyQt5 widget that displays Genshin Impact account info using the `genshin.py` library. The app is customizable via `settings.ini` and now supports both Windows and Linux.

![Preview Image](https://raw.githubusercontent.com/Naguroka/GenshinWidget/main/Preview.png)

## Features

- **Customizable UI**: Font size/color, background color/image, margins, rounded corners, transparency, draggable, always-on-top.
- **Realtime info**: Resin, Daily Reward status, and Realm Currency (via Hoyolab).
- **Periodic refresh**: Updates every minute.
- **Cross-platform**: Works on Windows and Linux.

## Requirements

- Python 3.9+
- PyQt5
- genshin
- qasync

Install dependencies with:

```bash
pip install -r requirements.txt
```

Note: `asyncio`, `logging`, and `configparser` are part of Python’s standard library; no need to install them via pip.

## Configuration

Copy `settings.ini` next to `main.py` and fill in your details. The app will resolve all asset and config paths relative to the script, so launching from a different working directory works on both Windows and Linux.

Example:

```ini
[Display]
word_wrap = 1
fit_window_to_text = 0
show_background = 1
background_color = #FFFFFF
background_image = bg.png
font_size = 14
font_color = #000000
margins = 10
corner_radius = 15
always_on_top = 1
transparency = 0.9
show_in_taskbar = 1
allow_resizing = 1
draggable = 1

[Auth]
ltuid_v2 = your_ltuid_v2
ltoken_v2 = your_ltoken_v2
cookie_token_v2 = your_cookie_token_v2
account_mid_v2 = your_account_mid_v2

[Window]
last_x = 100
last_y = 100
```

## Running

### Windows

- Double-click `run_invisible.bat` to run without a console window.

`run_invisible.bat`:

```bat
@echo off
start "" /b pythonw.exe main.py
exit
```

### Linux

- Run from a terminal:

```bash
python3 main.py
```

- Or run in the background with the included helper script:

```bash
./run.sh
```

- Optional: create a `.desktop` file for launching from your desktop environment:

```
[Desktop Entry]
Type=Application
Name=Genshin Widget
Exec=/usr/bin/python3 /path/to/GenshinWidget/main.py
Icon=/path/to/GenshinWidget/resin.png
Terminal=false
Categories=Utility;
```

Notes for Linux:
- For transparency/rounded corners, a compositor (e.g., picom) is recommended.
- When `show_in_taskbar = 0`, the app uses a tool window hint; behavior can vary by desktop environment.

## Getting Cookies

1. Log into Hoyolab in your browser.
2. Open Developer Tools → Application/Storage → Cookies for the Hoyolab domain.
3. Copy values for `ltuid_v2`, `ltoken_v2`, `cookie_token_v2`, and `account_mid_v2` into `settings.ini`.
4. Use your in-game UID for `ltuid_v2` if applicable.

## Fonts

The app loads a bundled font `zh-cn.ttf` placed next to `main.py`. If it fails to load, system default fonts will be used.

## Changelog

See `CHANGELOG.md` for recent changes.

## License

MIT — see `LICENSE`.

## Contributing

Issues and PRs are welcome.
