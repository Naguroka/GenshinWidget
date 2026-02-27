import sys
import os
import asyncio
import logging
import signal
import atexit
import ctypes
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QMessageBox, QHBoxLayout, QFrame
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QTimer, QUrl
from PyQt5.QtGui import QFontDatabase, QFont, QPixmap, QPainter, QBrush, QDesktopServices, QMouseEvent
import configparser
import genshin
from qasync import QEventLoop, asyncSlot

# Resolve paths relative to this file to be cross-platform friendly
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def resource_path(*parts: str) -> str:
    """Return an absolute path for a resource located next to the script.

    If a provided path is already absolute, it's returned unchanged.
    """
    if parts and os.path.isabs(parts[0]):
        return os.path.join(*parts)
    return os.path.join(BASE_DIR, *parts)

# Setup logging
log_file = resource_path('debug.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def apply_process_metadata(process_name="Genshin Widget"):
    if sys.platform.startswith("win") and hasattr(ctypes, 'windll'):
        try:
            ctypes.windll.kernel32.SetConsoleTitleW(process_name)
        except Exception as exc:
            logging.debug("Unable to set console title: %s", exc)
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(process_name)
        except Exception as exc:
            logging.debug("Unable to set AppUserModelID: %s", exc)


class ClickableLabel(QLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = None

    def setUrl(self, url):
        self.url = QUrl(url)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.url:
            QDesktopServices.openUrl(self.url)
        else:
            super().mousePressEvent(event)

class BackgroundFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.background_image = None

    def setBackgroundImage(self, image_path):
        if image_path and os.path.exists(image_path):
            self.background_image = QPixmap(image_path)
        else:
            self.background_image = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.background_image and not self.background_image.isNull():
            painter.drawPixmap(self.rect(), self.background_image)
        else:
            painter.fillRect(self.rect(), QBrush(self.palette().color(self.backgroundRole())))
        super().paintEvent(event)

class GenshinApp(QWidget):
    update_ui_signal = pyqtSignal(str, str, str)  # Signal to update the UI

    def __init__(self, loop=None):
        super().__init__()
        self.loop = loop or asyncio.get_event_loop()
        self.tasks = []
        self._is_shutting_down = False
        self.initUI()

    def initUI(self):
        self.config = configparser.ConfigParser()
        self.settings_path = resource_path('settings.ini')
        self.config.read(self.settings_path)

        display_config = self.config['Display']
        auth_config = self.config['Auth']
        window_config = self.config['Window']

        logging.debug(f"display_config: {list(display_config.items())}")
        # Do NOT log raw auth values; they are sensitive.
        logging.debug(f"auth_config keys: {[k for k in auth_config.keys()]}")
        logging.debug(f"window_config: {list(window_config.items())}")

        # Check for auth details
        if not auth_config.get('ltuid_v2') or not auth_config.get('ltoken_v2') or not auth_config.get('cookie_token_v2') or not auth_config.get('account_mid_v2'):
            self.show_warning("Authentication details are missing in settings.ini")
            sys.exit()

        # Convert 1/0 to True/False
        def bool_from_str(value):
            return value == '1'

        # Ensure only one of word_wrap and fit_window_to_text is enabled
        word_wrap = bool_from_str(display_config['word_wrap'])
        fit_window_to_text = bool_from_str(display_config['fit_window_to_text'])
        if word_wrap and fit_window_to_text:
            self.show_warning("Both 'word_wrap' and 'fit_window_to_text' cannot be enabled simultaneously.")
            sys.exit()

        # Setup window properties
        self.setWindowFlags(Qt.FramelessWindowHint if not bool_from_str(display_config['show_in_taskbar']) else Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(float(display_config['transparency']))
        if bool_from_str(display_config['always_on_top']): 
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        if not bool_from_str(display_config['show_in_taskbar']):
            self.setWindowFlags(self.windowFlags() | Qt.Tool)
        self.setWindowTitle("Genshin Widget")

        # Restore last window position
        last_x = window_config.getint('last_x', 100)
        last_y = window_config.getint('last_y', 100)

        # Screen bounds check
        if QApplication.desktop():
            screen_geo = QApplication.desktop().availableGeometry()
            if not screen_geo.contains(last_x, last_y):
                logging.warning(f"Restored position ({last_x}, {last_y}) is off-screen. Resetting to (100, 100).")
                last_x, last_y = 100, 100
        
        self.move(last_x, last_y)

        # Setup layout
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)

        # Create a background frame
        self.background_frame = BackgroundFrame(self)
        self.main_layout.addWidget(self.background_frame)

        # Setup content layout
        self.content_layout = QVBoxLayout(self.background_frame)

        # Apply margins
        self.margins = display_config.getint('margins', 10)
        logging.debug(f"Applying margins: {self.margins}")
        self.content_layout.setContentsMargins(self.margins, self.margins, self.margins, self.margins)

        # Load and apply custom font
        font_id = QFontDatabase.addApplicationFont(resource_path("zh-cn.ttf"))
        if font_id == -1:
            logging.error("Failed to load custom font.")
            self.custom_font = QFont()
        else:
            custom_font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            self.custom_font = QFont(custom_font_family)
            logging.debug(f"Custom font loaded: {custom_font_family}")

        # Setup Genshin API client
        self.client = genshin.Client()
        self.set_cookies(auth_config)
        # Silence overly chatty third‑party debug logs by default.
        try:
            import logging as _logging
            _logging.getLogger("genshin").setLevel(_logging.WARNING)
        except Exception:
            pass

        # Set font size and color for the entire window
        self.font_size = display_config.getint('font_size')
        self.font_color = display_config['font_color']
        logging.debug(f"Applying font size: {self.font_size}, font color: {self.font_color}")

        # Set background color or image
        self.show_background = bool_from_str(display_config['show_background'])
        self.background_color = display_config['background_color']
        bg_from_cfg = display_config.get('background_image', '')
        # If the configured path is absolute, use it; otherwise resolve relative to BASE_DIR
        self.background_image = bg_from_cfg if os.path.isabs(bg_from_cfg) else resource_path(bg_from_cfg) if bg_from_cfg else ''

        # Apply styles
        self.apply_styles()

        # Allow window resizing
        self.setFixedSize(400, 300) if not bool_from_str(display_config['allow_resizing']) else self.resize(400, 300)

        # Make window draggable
        if bool_from_str(display_config['draggable']):
            self.mousePressEvent = self.startMove

        self.update_ui_signal.connect(self.update_ui)
        logging.debug("Connected update_ui_signal to update_ui slot")

        # Handle word wrapping
        self.word_wrap = word_wrap

        # Handle fit to text
        self.fit_window_to_text = fit_window_to_text

        # Trigger an initial data refresh once the UI is ready.
        initial_load = self.loop.create_task(self.refresh_notes())
        self.tasks.append(initial_load)

        # Setup timer for periodic updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_info)
        self.timer.start(60000)  # 60000 ms = 1 minute

    def apply_styles(self):
        corner_radius = self.config['Display'].getint('corner_radius', 0)
        self.setStyleSheet(f"""
            QWidget {{
                font-size: {self.font_size}px;
                color: {self.font_color};
            }}
            QFrame {{
                border-radius: {corner_radius}px;
                background-clip: padding-box;
            }}
            QLabel {{
                background-color: transparent;
            }}
        """)

        if self.show_background and self.background_image:
            self.background_frame.setBackgroundImage(self.background_image)
        else:
            self.background_frame.setBackgroundImage(None)
            self.background_frame.setStyleSheet(f"background-color: {self.background_color};")

    def _load_scaled_pixmap(self, filename):
        path = resource_path(filename)
        pixmap = QPixmap(path)
        if pixmap.isNull():
            logging.warning(f"Failed to load pixmap from {path}")
            return QPixmap()
        target_height = max(1, self.font_size)
        return pixmap.scaledToHeight(target_height)

    def prepare_shutdown(self):
        if getattr(self, '_is_shutting_down', False):
            return
        self._is_shutting_down = True

        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()

        for task in list(getattr(self, 'tasks', [])):
            if not task.done():
                task.cancel()
        if hasattr(self, 'tasks'):
            self.tasks.clear()

        if self.loop and self.loop.is_running():
            try:
                self.loop.call_soon_threadsafe(self.loop.stop)
            except RuntimeError:
                # Loop may already be closed or stopping; ignore.
                pass

    def bool_from_str(self, value):
        return value == '1'

    def set_cookies(self, auth_config):
        # Use required cookies; include optional ones if present.
        cookie_kwargs = {
            'ltuid_v2': auth_config['ltuid_v2'],
            'ltoken_v2': auth_config['ltoken_v2'],
            'cookie_token_v2': auth_config['cookie_token_v2'],
            'account_mid_v2': auth_config['account_mid_v2'],
        }
        # Optional extras that can help some endpoints
        for optional_key in ('account_id_v2', 'ltmid_v2'):
            if auth_config.get(optional_key):
                cookie_kwargs[optional_key] = auth_config[optional_key]

        self.client.set_cookies(**cookie_kwargs)
        # Do not log cookie values; confirm only that required keys are present.
        logging.info("Authentication cookies set (ltuid_v2, ltoken_v2, cookie_token_v2, account_mid_v2)")

    async def refresh_notes(self):
        try:
            # Let the genshin client auto-detect the correct UID from cookies.
            logging.debug("Fetching notes (auto-detected UID)")

            show_notes = self.config['Display'].get('show_notes', '0')  # Default to '0' if 'show_notes' is not found

            if self.bool_from_str(show_notes):
                try:
                    # Passing no UID lets the client resolve the correct account automatically.
                    notes = await self.client.get_notes()
                    logging.debug(f"Notes: {notes}")
                    resin_info = f"Resin: {notes.current_resin}/{notes.max_resin}"
                    checkin_info = f"Daily Reward Claimed: {notes.claimed_commission_reward}"
                    realm_currency_info = f"Realm Currency: {notes.current_realm_currency}/2400"
                    self.update_ui_signal.emit(resin_info, checkin_info, realm_currency_info)
                except genshin.errors.GenshinException as e:
                    logging.error(f"Error fetching notes: {str(e)} - Response: {e.response}")
                    self.update_ui_signal.emit(f"Error fetching notes: {str(e)}", "", "")

        except Exception as e:
            logging.error(f"Error fetching data: {str(e)}")
            self.update_ui_signal.emit(f"Error fetching data: {str(e)}", "", "")

    @asyncSlot()
    async def update_info(self):
        await self.refresh_notes()

    def update_ui(self, resin_info, checkin_info, realm_currency_info):
        logging.debug(f"Updating UI with resin info: {resin_info}, checkin info: {checkin_info}, realm currency info: {realm_currency_info}")

        # Clear previous widgets
        while self.content_layout.count() > 0:
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                # Recursively delete layouts
                self.clear_layout(item.layout())

        # Create resin info row
        resin_row = QHBoxLayout()
        resin_icon = QLabel()
        resin_pixmap = self._load_scaled_pixmap("resin.png")
        if not resin_pixmap.isNull():
            resin_icon.setPixmap(resin_pixmap)
        else:
            resin_icon.setVisible(False)
        resin_label = QLabel(resin_info)
        resin_label.setFont(self.custom_font)
        resin_row.addWidget(resin_icon)
        resin_row.addWidget(resin_label, 1)  # Add stretch factor
        resin_row.setAlignment(Qt.AlignLeft)

        # Create checkin info row
        checkin_row = QHBoxLayout()
        checkin_icon = ClickableLabel()
        checkin_pixmap = self._load_scaled_pixmap("checkin.png")
        if not checkin_pixmap.isNull():
            checkin_icon.setPixmap(checkin_pixmap)
        else:
            checkin_icon.setVisible(False)
        checkin_icon.setUrl("https://act.hoyolab.com/ys/event/signin-sea-v3/index.html?act_id=e202102251931481")
        checkin_label = QLabel(checkin_info)
        checkin_label.setFont(self.custom_font)
        checkin_row.addWidget(checkin_icon)
        checkin_row.addWidget(checkin_label, 1)  # Add stretch factor
        checkin_row.setAlignment(Qt.AlignLeft)

        # Create realm currency info row
        realm_currency_row = QHBoxLayout()
        realm_currency_icon = QLabel()
        realm_currency_pixmap = self._load_scaled_pixmap("realmCurr.png")
        if not realm_currency_pixmap.isNull():
            realm_currency_icon.setPixmap(realm_currency_pixmap)
        else:
            realm_currency_icon.setVisible(False)
        realm_currency_label = QLabel(realm_currency_info)
        realm_currency_label.setFont(self.custom_font)
        realm_currency_row.addWidget(realm_currency_icon)
        realm_currency_row.addWidget(realm_currency_label, 1)  # Add stretch factor
        realm_currency_row.setAlignment(Qt.AlignLeft)

        # Add rows to content layout
        self.content_layout.addLayout(resin_row)
        self.content_layout.addLayout(checkin_row)
        self.content_layout.addLayout(realm_currency_row)

        if self.fit_window_to_text:
            self.adjustSize()

    def clear_layout(self, layout):
        """Recursively clear all items from the layout"""
        while layout.count() > 0:
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
            else:
                self.clear_layout(item.layout())

    def show_warning(self, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText(message)
        msg.setWindowTitle("Warning")
        msg.exec_()

    def startMove(self, event):
        if event.button() == Qt.LeftButton:
            self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.oldPos = event.globalPos()

        # Save the current window position to settings.ini
        self.config.set('Window', 'last_x', str(self.x()))
        self.config.set('Window', 'last_y', str(self.y()))
        with open(self.settings_path, 'w') as configfile:
            self.config.write(configfile)

    def closeEvent(self, event):
        # Save the current window position to settings.ini
        self.config.set('Window', 'last_x', str(self.x()))
        self.config.set('Window', 'last_y', str(self.y()))
        with open(self.settings_path, 'w') as configfile:
            self.config.write(configfile)

        self.prepare_shutdown()

        app = QApplication.instance()
        if app is not None:
            closing_down_attr = getattr(app, 'closingDown', None)
            if callable(closing_down_attr):
                is_closing = closing_down_attr()
            elif closing_down_attr is None:
                is_closing = False
            else:
                is_closing = bool(closing_down_attr)
            if not is_closing:
                app.quit()

        event.accept()
        super().closeEvent(event)

if __name__ == '__main__':
    apply_process_metadata("Genshin Widget")
    app = QApplication(sys.argv)
    app.setApplicationName("Genshin Widget")
    app.setApplicationDisplayName("Genshin Widget")

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    def _stop_loop():
        if loop.is_running():
            loop.call_soon_threadsafe(loop.stop)

    app.aboutToQuit.connect(_stop_loop)

    window_ref = {}

    def _handle_shutdown_signal(signum, frame):
        logging.info("Received shutdown signal %s", signum)
        window_instance = window_ref.get('window')
        if window_instance is not None:
            try:
                loop.call_soon_threadsafe(window_instance.prepare_shutdown)
            except RuntimeError:
                window_instance.prepare_shutdown()
        try:
            if loop.is_running():
                loop.call_soon_threadsafe(loop.stop)
        except RuntimeError:
            pass
        app_instance = QApplication.instance()
        if app_instance is not None:
            try:
                if loop.is_running():
                    loop.call_soon_threadsafe(app_instance.quit)
                else:
                    app_instance.quit()
            except RuntimeError:
                app_instance.quit()

    shutdown_signals = [signal.SIGINT, signal.SIGTERM]
    for optional in ('SIGBREAK', 'SIGHUP'):
        maybe_signal = getattr(signal, optional, None)
        if maybe_signal is not None:
            shutdown_signals.append(maybe_signal)

    for sig in shutdown_signals:
        try:
            signal.signal(sig, _handle_shutdown_signal)
        except (ValueError, OSError) as exc:
            logging.debug("Unable to register handler for signal %s: %s", sig, exc)

    def _atexit_cleanup():
        window_instance = window_ref.get('window')
        if window_instance is not None:
            window_instance.prepare_shutdown()
        try:
            if loop.is_running():
                loop.call_soon_threadsafe(loop.stop)
        except RuntimeError:
            pass

    atexit.register(_atexit_cleanup)

    try:
        with loop:
            window = GenshinApp(loop=loop)
            window_ref['window'] = window
            app.aboutToQuit.connect(window.prepare_shutdown)
            window.show()
            loop.run_forever()
    except Exception as e:
        logging.critical("Unhandled exception in main loop", exc_info=True)
        # Use ctypes to show a message box in case PyQt fails or window is hidden
        if sys.platform == 'win32':
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, f"Critical Error:\n{str(e)}", "Genshin Widget Error", 0x10)
        sys.exit(1)
