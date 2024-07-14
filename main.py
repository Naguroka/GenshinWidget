import sys
import os
import asyncio
import logging
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QMessageBox, QHBoxLayout, QFrame
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QTimer, QUrl
from PyQt5.QtGui import QFontDatabase, QFont, QPixmap, QPainter, QBrush, QDesktopServices, QMouseEvent
import configparser
import genshin
from qasync import QEventLoop, asyncSlot

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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

    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.config = configparser.ConfigParser()
        self.config.read('settings.ini')

        display_config = self.config['Display']
        auth_config = self.config['Auth']
        window_config = self.config['Window']

        logging.debug(f"display_config: {list(display_config.items())}")
        logging.debug(f"auth_config: {list(auth_config.items())}")
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

        # Restore last window position
        self.move(window_config.getint('last_x', 100), window_config.getint('last_y', 100))

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
        font_id = QFontDatabase.addApplicationFont("zh-cn.ttf")
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
        logging.debug(f"Using cookies: {{'ltuid_v2': '{auth_config['ltuid_v2']}', 'ltoken_v2': '{auth_config['ltoken_v2']}', 'cookie_token_v2': '{auth_config['cookie_token_v2']}', 'account_mid_v2': '{auth_config['account_mid_v2']}'}}")

        # Set font size and color for the entire window
        self.font_size = display_config.getint('font_size')
        self.font_color = display_config['font_color']
        logging.debug(f"Applying font size: {self.font_size}, font color: {self.font_color}")

        # Set background color or image
        self.show_background = bool_from_str(display_config['show_background'])
        self.background_color = display_config['background_color']
        self.background_image = display_config.get('background_image', '')

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

        # Add info labels asynchronously
        asyncio.ensure_future(self.add_info_labels(display_config))

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

    def bool_from_str(self, value):
        return value == '1'

    def set_cookies(self, auth_config):
        # Use ltuid_v2, ltoken_v2, cookie_token_v2, and account_mid_v2
        self.client.set_cookies(ltuid_v2=auth_config['ltuid_v2'], ltoken_v2=auth_config['ltoken_v2'], cookie_token_v2=auth_config['cookie_token_v2'], account_mid_v2=auth_config['account_mid_v2'])
        logging.debug(f"Set cookies: ltuid_v2={auth_config['ltuid_v2']}, ltoken_v2={auth_config['ltoken_v2']}, cookie_token_v2={auth_config['cookie_token_v2']}, account_mid_v2={auth_config['account_mid_v2']}")

    @asyncSlot()
    async def add_info_labels(self, display_config):
        await self.update_info()

    @asyncSlot()
    async def update_info(self):
        try:
            uid = int(self.config['Auth']['ltuid_v2'])
            logging.debug(f"Fetching notes for UID: {uid}")

            show_notes = self.config['Display'].get('show_notes', '0')  # Default to '0' if 'show_notes' is not found

            if self.bool_from_str(show_notes):
                try:
                    notes = await self.client.get_notes(uid)
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
        resin_pixmap = QPixmap("resin.png").scaledToHeight(self.font_size)
        resin_icon.setPixmap(resin_pixmap)
        resin_label = QLabel(resin_info)
        resin_label.setFont(self.custom_font)
        resin_row.addWidget(resin_icon)
        resin_row.addWidget(resin_label, 1)  # Add stretch factor
        resin_row.setAlignment(Qt.AlignLeft)

        # Create checkin info row
        checkin_row = QHBoxLayout()
        checkin_icon = ClickableLabel()
        checkin_pixmap = QPixmap("checkin.png").scaledToHeight(self.font_size)
        checkin_icon.setPixmap(checkin_pixmap)
        checkin_icon.setUrl("https://act.hoyolab.com/ys/event/signin-sea-v3/index.html?act_id=e202102251931481")
        checkin_label = QLabel(checkin_info)
        checkin_label.setFont(self.custom_font)
        checkin_row.addWidget(checkin_icon)
        checkin_row.addWidget(checkin_label, 1)  # Add stretch factor
        checkin_row.setAlignment(Qt.AlignLeft)

        # Create realm currency info row
        realm_currency_row = QHBoxLayout()
        realm_currency_icon = QLabel()
        realm_currency_pixmap = QPixmap("realmCurr.png").scaledToHeight(self.font_size)
        realm_currency_icon.setPixmap(realm_currency_pixmap)
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
        with open('settings.ini', 'w') as configfile:
            self.config.write(configfile)

    def closeEvent(self, event):
        # Save the current window position to settings.ini
        self.config.set('Window', 'last_x', str(self.x()))
        self.config.set('Window', 'last_y', str(self.y()))
        with open('settings.ini', 'w') as configfile:
            self.config.write(configfile)
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    with loop:
        window = GenshinApp()
        window.show()
        loop.run_forever()
