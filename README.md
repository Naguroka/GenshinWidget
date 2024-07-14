# Genshin Widget

This repository contains a PyQt5 application that uses the `genshin.py` library to display information from Genshin Impact. The app can be customized using settings from a `settings.ini` file.

## Description

The Genshin App is a fully customizable desktop application that displays various pieces of information from Genshin Impact. It allows for extensive customization through the `settings.ini` file, which includes options for the display settings, authentication details, and window properties.

![Preview Image](https://raw.githubusercontent.com/Naguroka/GenshinWidget/main/Preview.png)

## Functionality

- **Customizable UI**: The application allows you to customize the font size, font color, background color, or image, and whether the window is draggable or always on top.
- **Authentication**: Requires authentication details to access Genshin Impact's API.
- **Periodic Updates**: The application fetches and displays updated information periodically.
- **Real-Time Information**: Shows real-time data such as Resin count, Daily Reward status, and Realm Currency.

## Running the Application

To run the application with an invisible console, use the provided `run_invisible.bat` file.


###run_invisible.bat

```bat
@echo off
start "" /b pythonw.exe main.py
exit

## Configuration

The application reads settings from `settings.ini` to customize its behavior and appearance. Ensure you have this file in the same directory as `main.py`.

### Settings Example

```ini
[Display]
word_wrap = 1
fit_window_to_text = 0
show_background = 1
background_color = #FFFFFF
background_image = path/to/your/image.png
font_size = 12
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

## Dependencies

Make sure you have the following dependencies installed:

```bash
pip install PyQt5 genshin qasync asyncio logging configparser
```

## Detailed Instructions

1. **Install Python**: Ensure you have Python installed on your system. (This app is made with Python 3.12.2)
2. **Install Dependencies**: Use the provided `pip` command to install necessary libraries.
3. **Configure Settings**: Modify the `settings.ini` file with your specific preferences and authentication details.
4. **Run the Application**: Use the `run_invisible.bat` file to start the application without showing the console.

### run_invisible.bat

```bat
@echo off
start "" /b pythonw.exe main.py
exit
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

If you would like to contribute to this project, please fork the repository and use a feature branch. Pull requests are welcome.

## Support

For any issues or questions, please open an issue in the repository. I don't check Github often so no promises.


