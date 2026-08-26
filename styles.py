"""
styles.py

Estilos visuales de AudioDrop.
"""

DARK_STYLE = """
QWidget {
    background-color: #07111D;
    color: #EAF4FF;
    font-family: Segoe UI, Arial;
    font-size: 10pt;
}

QFrame#HeaderFrame {
    background-color: #0D1D2D;
    border: 1px solid #17304A;
    border-radius: 14px;
}

QLabel#LogoBox {
    background-color: #112A42;
    border: 1px solid #24527D;
    border-radius: 13px;
    color: #7CCBFF;
    font-size: 22px;
    font-weight: bold;
}

QLabel#TitleLabel {
    color: #F4FBFF;
    font-size: 21px;
    font-weight: 700;
}

QLabel#SubtitleLabel, QLabel#MutedLabel {
    color: #93A9BE;
    font-size: 9pt;
}

QLabel#SectionTitle {
    color: #EAF4FF;
    font-size: 12pt;
    font-weight: 700;
}

QFrame#PanelFrame {
    background-color: #0B1A29;
    border: 1px solid #183550;
    border-radius: 12px;
}

QLabel#PreviewBox {
    background-color: #07111D;
    border: 1px solid #234B70;
    border-radius: 10px;
    color: #6F879D;
}

QLabel#PreviewTitle {
    color: #F2FAFF;
    font-weight: 600;
    font-size: 9.5pt;
}

QLineEdit, QComboBox {
    background-color: #0E2031;
    border: 1px solid #24415F;
    border-radius: 8px;
    padding: 7px 9px;
    color: #EAF4FF;
    selection-background-color: #2F80ED;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #3B82F6;
}

QComboBox::drop-down {
    border: none;
    width: 26px;
}

QPushButton {
    background-color: #14283B;
    border: 1px solid #26465F;
    border-radius: 9px;
    padding: 7px 12px;
    color: #EAF4FF;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #1A3550;
    border-color: #3B82F6;
}

QPushButton:pressed {
    background-color: #102237;
}

QPushButton:disabled {
    background-color: #101820;
    color: #657687;
    border-color: #1A2B3C;
}

QPushButton#PrimaryButton {
    background-color: #2563EB;
    border-color: #3B82F6;
    color: white;
}

QPushButton#PrimaryButton:hover {
    background-color: #1D72F3;
}

QPushButton#SuccessButton {
    background-color: #14935C;
    border-color: #19B975;
    color: white;
}

QPushButton#SuccessButton:hover {
    background-color: #18A96B;
}

QPushButton#DangerButton {
    background-color: #8D2430;
    border-color: #C44250;
    color: white;
}

QPushButton#DangerButton:hover {
    background-color: #A82C3A;
}

QPushButton#SecondaryButton {
    background-color: #122A42;
    border-color: #2B567C;
}

QFrame#PlayerBar {
    background-color: #0D1D2D;
    border: 1px solid #17304A;
    border-radius: 14px;
}

QFrame#PlayerInfoPill {
    background-color: #081724;
    border: 1px solid #203B57;
    border-radius: 12px;
}

QPushButton#PlayerButton {
    min-width: 34px;
    max-width: 38px;
    min-height: 30px;
    padding: 4px;
    border-radius: 15px;
    background-color: #132A40;
}

QPushButton#PlayMainButton {
    min-width: 44px;
    max-width: 48px;
    min-height: 36px;
    padding: 4px;
    border-radius: 18px;
    background-color: #2563EB;
    border-color: #60A5FA;
    color: white;
    font-weight: 800;
}

QTabWidget::pane {
    border: 1px solid #17304A;
    border-radius: 12px;
    top: -1px;
    background-color: #081522;
}

QTabBar::tab {
    background-color: #0E2031;
    color: #AFC2D4;
    border: 1px solid #17304A;
    border-bottom: none;
    padding: 8px 13px;
    margin-right: 3px;
    border-top-left-radius: 9px;
    border-top-right-radius: 9px;
}

QTabBar::tab:selected {
    background-color: #173550;
    color: #FFFFFF;
    border-color: #2F80ED;
}

QTabBar::tab:hover {
    background-color: #142A40;
}

QListWidget, QTableWidget, QScrollArea {
    background-color: #081522;
    border: 1px solid #183550;
    border-radius: 10px;
    alternate-background-color: #0B1A29;
}

QListWidget::item {
    padding: 7px;
    border-radius: 6px;
}

QListWidget::item:selected, QTableWidget::item:selected {
    background-color: #2457A6;
    color: white;
}

QHeaderView::section {
    background-color: #10253A;
    color: #DCEEFF;
    border: none;
    border-right: 1px solid #203B57;
    padding: 7px;
    font-weight: 700;
}

QProgressBar {
    background-color: #0B1A29;
    border: 1px solid #24415F;
    border-radius: 8px;
    text-align: center;
    color: #EAF4FF;
}

QProgressBar::chunk {
    background-color: #3B82F6;
    border-radius: 7px;
}

QMenu {
    background-color: #0D1D2D;
    color: #EAF4FF;
    border: 1px solid #24415F;
    border-radius: 8px;
    padding: 5px;
}

QMenu::item {
    padding: 7px 22px 7px 12px;
    border-radius: 6px;
}

QMenu::item:selected {
    background-color: #2457A6;
}

QSlider {
    background-color: transparent;
    border: none;
    min-height: 22px;
    max-height: 22px;
}

QSlider::groove:horizontal {
    height: 6px;
    background-color: #24415F;
    border: none;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background-color: #3B82F6;
    border: none;
    border-radius: 3px;
}

QSlider::add-page:horizontal {
    background-color: #24415F;
    border: none;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background-color: #DCEEFF;
    border: 1px solid #75B7FF;
    width: 13px;
    height: 13px;
    margin: -4px 0px;
    border-radius: 7px;
}
"""

LIGHT_STYLE = """
QWidget {
    background-color: #EEF5FC;
    color: #0C1B31;
    font-family: Segoe UI, Arial;
    font-size: 10pt;
}

QFrame#HeaderFrame {
    background-color: #FFFFFF;
    border: 1px solid #C7D8EA;
    border-radius: 14px;
}

QLabel#LogoBox {
    background-color: #E5F1FF;
    border: 1px solid #9DC4F0;
    border-radius: 13px;
    color: #2563EB;
    font-size: 22px;
    font-weight: bold;
}

QLabel#TitleLabel {
    color: #0C1B31;
    font-size: 21px;
    font-weight: 700;
}

QLabel#SubtitleLabel, QLabel#MutedLabel {
    color: #60758D;
    font-size: 9pt;
}

QLabel#SectionTitle {
    color: #0C1B31;
    font-size: 12pt;
    font-weight: 700;
}

QFrame#PanelFrame {
    background-color: #FFFFFF;
    border: 1px solid #C7D8EA;
    border-radius: 12px;
}

QLabel#PreviewBox {
    background-color: #F7FAFE;
    border: 1px solid #B8D0EA;
    border-radius: 10px;
    color: #60758D;
}

QLabel#PreviewTitle {
    color: #0C1B31;
    font-weight: 600;
    font-size: 9.5pt;
}

QLineEdit, QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #B8D0EA;
    border-radius: 8px;
    padding: 7px 9px;
    color: #0C1B31;
    selection-background-color: #2563EB;
}

QLineEdit:focus, QComboBox:focus {
    border: 1px solid #2563EB;
}

QComboBox::drop-down {
    border: none;
    width: 26px;
}

QPushButton {
    background-color: #E6F0FA;
    border: 1px solid #B8D0EA;
    border-radius: 9px;
    padding: 7px 12px;
    color: #0C1B31;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #D8EAFB;
    border-color: #2563EB;
}

QPushButton:disabled {
    background-color: #EEF2F7;
    color: #93A4B7;
    border-color: #D7E1EC;
}

QPushButton#PrimaryButton {
    background-color: #2563EB;
    border-color: #2563EB;
    color: white;
}

QPushButton#SuccessButton {
    background-color: #14935C;
    border-color: #14935C;
    color: white;
}

QPushButton#DangerButton {
    background-color: #C43E4B;
    border-color: #C43E4B;
    color: white;
}

QPushButton#SecondaryButton {
    background-color: #E6F0FA;
    border-color: #AFC9E7;
}

QFrame#PlayerBar {
    background-color: #FFFFFF;
    border: 1px solid #C7D8EA;
    border-radius: 14px;
}

QFrame#PlayerInfoPill {
    background-color: #F7FAFE;
    border: 1px solid #C7D8EA;
    border-radius: 12px;
}

QPushButton#PlayerButton {
    min-width: 34px;
    max-width: 38px;
    min-height: 30px;
    padding: 4px;
    border-radius: 15px;
}

QPushButton#PlayMainButton {
    min-width: 44px;
    max-width: 48px;
    min-height: 36px;
    padding: 4px;
    border-radius: 18px;
    background-color: #2563EB;
    border-color: #2563EB;
    color: white;
    font-weight: 800;
}

QTabWidget::pane {
    border: 1px solid #C7D8EA;
    border-radius: 12px;
    top: -1px;
    background-color: #F7FAFE;
}

QTabBar::tab {
    background-color: #E6F0FA;
    color: #425973;
    border: 1px solid #C7D8EA;
    border-bottom: none;
    padding: 8px 13px;
    margin-right: 3px;
    border-top-left-radius: 9px;
    border-top-right-radius: 9px;
}

QTabBar::tab:selected {
    background-color: #FFFFFF;
    color: #0C1B31;
    border-color: #2563EB;
}

QListWidget, QTableWidget, QScrollArea {
    background-color: #FFFFFF;
    border: 1px solid #C7D8EA;
    border-radius: 10px;
    alternate-background-color: #F3F8FD;
}

QListWidget::item {
    padding: 7px;
    border-radius: 6px;
}

QListWidget::item:selected, QTableWidget::item:selected {
    background-color: #2563EB;
    color: white;
}

QHeaderView::section {
    background-color: #E6F0FA;
    color: #0C1B31;
    border: none;
    border-right: 1px solid #C7D8EA;
    padding: 7px;
    font-weight: 700;
}

QProgressBar {
    background-color: #FFFFFF;
    border: 1px solid #B8D0EA;
    border-radius: 8px;
    text-align: center;
    color: #0C1B31;
}

QProgressBar::chunk {
    background-color: #2563EB;
    border-radius: 7px;
}

QMenu {
    background-color: #FFFFFF;
    color: #0C1B31;
    border: 1px solid #B8D0EA;
    border-radius: 8px;
    padding: 5px;
}

QMenu::item {
    padding: 7px 22px 7px 12px;
    border-radius: 6px;
}

QMenu::item:selected {
    background-color: #2563EB;
    color: white;
}

QSlider {
    background-color: transparent;
    border: none;
    min-height: 22px;
    max-height: 22px;
}

QSlider::groove:horizontal {
    height: 6px;
    background-color: #C4D7EF;
    border: none;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background-color: #2563EB;
    border: none;
    border-radius: 3px;
}

QSlider::add-page:horizontal {
    background-color: #C4D7EF;
    border: none;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background-color: #FFFFFF;
    border: 1px solid #2563EB;
    width: 13px;
    height: 13px;
    margin: -4px 0px;
    border-radius: 7px;
}
"""

APP_STYLE = DARK_STYLE


def obtener_estilo(tema: str = "oscuro") -> str:
    if tema == "claro":
        return LIGHT_STYLE
    return DARK_STYLE
