from __future__ import annotations

import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import QObject, Qt, QTimer, Signal, QSettings
from PySide6.QtGui import QAction, QGuiApplication, QWheelEvent, QKeySequence, QShortcut
from app.version import __version__

from PySide6.QtWidgets import (
    QApplication, QAbstractItemView, QComboBox, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QProgressBar, QPushButton, QScrollArea, QSpinBox,
    QSplitter, QStackedWidget, QStatusBar, QTableWidget, QTableWidgetItem,
    QTextEdit, QToolButton, QVBoxLayout, QWidget
)


class Signals(QObject):
    progress = Signal(object, int, int, float)
    state = Signal(object, str, str)


class StatCard(QFrame):
    def __init__(self, eyebrow: str, value: str = "0", caption: str = ""):
        super().__init__()
        self.setObjectName("StatCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(3)
        self.eyebrow = QLabel(eyebrow.upper())
        self.eyebrow.setObjectName("CardEyebrow")
        self.value = QLabel(value)
        self.value.setObjectName("CardValue")
        self.caption = QLabel(caption)
        self.caption.setObjectName("CardCaption")
        layout.addWidget(self.eyebrow)
        layout.addWidget(self.value)
        layout.addWidget(self.caption)

    def setValue(self, value: str):
        self.value.setText(value)


class NavButton(QPushButton):
    def __init__(self, text: str):
        super().__init__(text)
        self.setCheckable(True)
        self.setObjectName("NavButton")
        self.setCursor(Qt.PointingHandCursor)


class NoWheelComboBox(QComboBox):
    """A combo box that does not change selection when the page is scrolled.

    This is intentional for forms inside scrollable panels. A mouse wheel over a
    field should scroll the panel, not silently change the selected source type.
    """

    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()


class MainWindow(QMainWindow):
    """South Park Downloader desktop UI.

    The source inspector deliberately keeps probe output compact. Long signed
    manifest URLs are never injected into a word-wrapped label, which prevents
    the source panel from expanding beyond the window and pushing its actions
    off-screen.
    """

    def __init__(self, service):
        super().__init__()
        self.service = service
        self.signals = Signals()
        self.current_episode = None
        self._season_numbers = []
        self._ui_settings = QSettings("SouthParkDownloader", "SouthParkDownloader")
        self._theme = str(self._ui_settings.value("theme", "dark")).lower()
        if self._theme not in {"dark", "light"}:
            self._theme = "dark"
        service.progress_callback = self.signals.progress.emit
        service.state_callback = self.signals.state.emit

        self.setWindowTitle("South Park Downloader")
        self.resize(1540, 930)
        self.setMinimumSize(1240, 780)
        self._build_menu()
        self._build_ui()
        self._connect()
        self._apply_style()
        self._apply_theme_popup()
        self.refresh()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_queue)
        self.timer.start(1200)

    # ---------- window / navigation ----------
    def _build_menu(self):
        file_menu = self.menuBar().addMenu("File")
        action = QAction("Open Downloads Folder", self)
        action.triggered.connect(self.open_downloads)
        file_menu.addAction(action)
        file_menu.addSeparator()
        action = QAction("Exit", self)
        action.triggered.connect(self.close)
        file_menu.addAction(action)

        tools = self.menuBar().addMenu("Tools")
        action = QAction("Sync Metadata", self)
        action.triggered.connect(self.sync)
        tools.addAction(action)
        action = QAction("Import Sources", self)
        action.triggered.connect(self.import_sources)
        tools.addAction(action)
        action = QAction("Scan Download Library", self)
        action.triggered.connect(self.scan)
        tools.addAction(action)

        help_menu = self.menuBar().addMenu("Help")
        action = QAction("Workflow", self)
        action.triggered.connect(lambda: self.navigate(3))
        help_menu.addAction(action)

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(224)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(16, 20, 16, 16)
        side.setSpacing(8)

        brand = QFrame()
        brand.setObjectName("Brand")
        brand_l = QVBoxLayout(brand)
        brand_l.setContentsMargins(10, 8, 10, 10)
        brand_l.setSpacing(2)
        title = QLabel("South Park")
        title.setObjectName("BrandTitle")
        sub = QLabel("Downloader")
        sub.setObjectName("BrandSub")
        brand_l.addWidget(title)
        brand_l.addWidget(sub)
        side.addWidget(brand)
        side.addSpacing(12)

        self.nav_library = NavButton("Library")
        self.nav_queue = NavButton("Download Queue")
        self.nav_settings = NavButton("Settings")
        self.nav_help = NavButton("Help & Workflow")
        for b in (self.nav_library, self.nav_queue, self.nav_settings, self.nav_help):
            side.addWidget(b)
        side.addStretch()

        version = QLabel(f"v{__version__}")
        version.setObjectName("SideVersion")
        version.setAlignment(Qt.AlignLeft)
        side.addStretch()
        side.addWidget(version)
        root_layout.addWidget(self.sidebar)

        content_wrap = QWidget()
        content = QVBoxLayout(content_wrap)
        content.setContentsMargins(24, 18, 24, 14)
        content.setSpacing(14)
        root_layout.addWidget(content_wrap, 1)

        header = QHBoxLayout()
        header.setSpacing(10)
        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        self.page_title = QLabel("Library")
        self.page_title.setObjectName("PageTitle")
        self.page_subtitle = QLabel("Browse seasons, configure sources, and manage downloads.")
        self.page_subtitle.setObjectName("PageSubtitle")
        title_box.addWidget(self.page_title)
        title_box.addWidget(self.page_subtitle)
        header.addLayout(title_box)
        header.addStretch()

        self.sync_btn = QPushButton("Sync Metadata")
        self.sync_btn.setObjectName("SecondaryButton")
        self.import_btn = QPushButton("Import Sources")
        self.import_btn.setObjectName("SecondaryButton")
        self.scan_btn = QPushButton("Scan Library")
        self.scan_btn.setObjectName("SecondaryButton")
        self.open_btn = QPushButton("Open Downloads")
        self.open_btn.setObjectName("SecondaryButton")
        for b in (self.sync_btn, self.import_btn, self.scan_btn, self.open_btn):
            b.setCursor(Qt.PointingHandCursor)
            header.addWidget(b)
        content.addLayout(header)

        cards = QHBoxLayout()
        cards.setSpacing(10)
        self.card_seasons = StatCard("Seasons", "0", "in library")
        self.card_episodes = StatCard("Episodes", "0", "metadata records")
        self.card_downloaded = StatCard("Downloaded", "0", "verified files")
        self.card_missing = StatCard("Missing", "0", "not downloaded")
        self.card_active = StatCard("Active", "0", "running jobs")
        for card in (self.card_seasons, self.card_episodes, self.card_downloaded, self.card_missing, self.card_active):
            cards.addWidget(card, 1)
        content.addLayout(cards)

        self.stack = QStackedWidget()
        content.addWidget(self.stack, 1)
        self.library_page = self._build_library_page()
        self.queue_page = self._build_queue_page()
        self.settings_page = self._build_settings_page()
        self.help_page = self._build_help_page()
        for page in (self.library_page, self.queue_page, self.settings_page, self.help_page):
            self.stack.addWidget(page)

        self.activity_progress = QProgressBar()
        self.activity_progress.setRange(0, 0)
        self.activity_progress.setFixedWidth(140)
        self.activity_progress.hide()
        self.setStatusBar(QStatusBar())
        self.statusBar().addPermanentWidget(self.activity_progress)
        self.statusBar().showMessage("Ready")

        self.navigate(0)
        self._install_shortcuts()

    def _build_library_page(self):
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        seasons = QFrame()
        seasons.setObjectName("Panel")
        seasons.setMinimumWidth(205)
        seasons.setMaximumWidth(235)
        sl = QVBoxLayout(seasons)
        sl.setContentsMargins(12, 12, 12, 12)
        sl.setSpacing(8)
        heading = QLabel("Seasons")
        heading.setObjectName("PanelTitle")
        sl.addWidget(heading)
        self.season_filter = QLineEdit()
        self.season_filter.setPlaceholderText("Search seasons")
        self.season_filter.setClearButtonEnabled(True)
        sl.addWidget(self.season_filter)
        self.seasons = QListWidget()
        self.seasons.setObjectName("SeasonList")
        sl.addWidget(self.seasons, 1)
        self.season_btn = QPushButton("Download Season")
        self.all_btn = QPushButton("Download All Missing")
        self.season_btn.setObjectName("PrimaryButton")
        self.all_btn.setObjectName("SecondaryButton")
        sl.addWidget(self.season_btn)
        sl.addWidget(self.all_btn)
        layout.addWidget(seasons)

        center = QFrame()
        center.setObjectName("Panel")
        cl = QVBoxLayout(center)
        cl.setContentsMargins(12, 12, 12, 12)
        cl.setSpacing(9)
        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search episodes by number, title, source or status")
        self.search.setClearButtonEnabled(True)
        toolbar.addWidget(self.search, 1)
        self.selected_btn = QPushButton("Download Selected")
        self.selected_btn.setObjectName("PrimaryButton")
        toolbar.addWidget(self.selected_btn)
        cl.addLayout(toolbar)

        self.table = QTableWidget(0, 6)
        self.table.setObjectName("EpisodeTable")
        self.table.setHorizontalHeaderLabels(["Episode", "Title", "Air date", "Source", "Status", "Progress"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        cl.addWidget(self.table, 1)
        layout.addWidget(center, 1)

        detail = self._build_detail_panel()
        layout.addWidget(detail)
        return page

    def _build_detail_panel(self):
        outer = QFrame()
        outer.setObjectName("Inspector")
        outer.setMinimumWidth(450)
        outer.setMaximumWidth(520)
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(12, 12, 12, 12)
        outer_layout.setSpacing(10)

        scroll = QScrollArea()
        scroll.setObjectName("InspectorScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        content = QWidget()
        content.setObjectName("InspectorContent")
        root = QVBoxLayout(content)
        root.setContentsMargins(2, 2, 2, 2)
        root.setSpacing(10)

        self.detail_title = QLabel("Select an episode")
        self.detail_title.setObjectName("InspectorTitle")
        self.detail_title.setWordWrap(True)
        root.addWidget(self.detail_title)

        self.summary = QLabel("Select an episode to see its metadata and configure its media source.")
        self.summary.setObjectName("Summary")
        self.summary.setWordWrap(True)
        self.summary.setMinimumHeight(44)
        self.summary.setMaximumHeight(92)
        root.addWidget(self.summary)

        meta = QFrame()
        meta.setObjectName("Inset")
        ml = QGridLayout(meta)
        ml.setContentsMargins(12, 10, 12, 10)
        ml.setHorizontalSpacing(14)
        ml.setVerticalSpacing(8)
        self.meta_air = QLabel("—")
        self.meta_runtime = QLabel("—")
        self.meta_status = QLabel("—")
        self.meta_source = QLabel("—")
        for label in (self.meta_air, self.meta_runtime, self.meta_status, self.meta_source):
            label.setObjectName("MetaValue")
        ml.addWidget(QLabel("Air date"), 0, 0)
        ml.addWidget(self.meta_air, 0, 1)
        ml.addWidget(QLabel("Runtime"), 1, 0)
        ml.addWidget(self.meta_runtime, 1, 1)
        ml.addWidget(QLabel("Status"), 0, 2)
        ml.addWidget(self.meta_status, 0, 3)
        ml.addWidget(QLabel("Source"), 1, 2)
        ml.addWidget(self.meta_source, 1, 3)
        root.addWidget(meta)

        source_card = QFrame()
        source_card.setObjectName("Inset")
        form = QGridLayout(source_card)
        form.setContentsMargins(12, 12, 12, 12)
        form.setVerticalSpacing(9)
        form.setHorizontalSpacing(10)
        form.setColumnMinimumWidth(0, 94)
        form.setColumnStretch(1, 1)

        label = QLabel("SOURCE CONFIGURATION")
        label.setObjectName("CardEyebrow")
        form.addWidget(label, 0, 0, 1, 2)

        form.addWidget(QLabel("Episode page"), 1, 0)
        self.page_url = QLineEdit()
        self.page_url.setPlaceholderText("Reference webpage only")
        self.page_url.setClearButtonEnabled(True)
        self.page_url.setMinimumHeight(38)
        self.page_url.setToolTip("The episode webpage. This is kept as a reference and is not the media download URL.")
        form.addWidget(self.page_url, 1, 1)

        form.addWidget(QLabel("Media source"), 2, 0)
        self.url = QLineEdit()
        self.url.setPlaceholderText("Direct media URL or HLS .m3u8")
        self.url.setClearButtonEnabled(True)
        self.url.setMinimumHeight(38)
        self.url.setToolTip("A direct media URL or an HLS .m3u8 manifest that you are authorized to access.")
        form.addWidget(self.url, 2, 1)

        form.addWidget(QLabel("Type"), 3, 0)
        self.kind = NoWheelComboBox()
        self.kind.addItem("Auto detect", "unknown")
        self.kind.addItem("Direct media", "direct")
        self.kind.addItem("HLS manifest (.m3u8)", "hls")
        self.kind.addItem("DASH manifest (.mpd)", "dash")
        self.kind.setMinimumHeight(38)
        self.kind.setToolTip("Source type. Probe Source can detect this automatically.")
        form.addWidget(self.kind, 3, 1)

        form.addWidget(QLabel("Extension"), 4, 0)
        self.ext = QLineEdit("mp4")
        self.ext.setMaxLength(8)
        self.ext.setMinimumHeight(38)
        form.addWidget(self.ext, 4, 1)

        form.addWidget(QLabel("SHA-256"), 5, 0)
        self.sha = QLineEdit()
        self.sha.setPlaceholderText("Optional verification hash")
        self.sha.setMinimumHeight(38)
        form.addWidget(self.sha, 5, 1)

        root.addWidget(source_card)

        probe_card = QFrame()
        probe_card.setObjectName("ProbeCard")
        pl = QVBoxLayout(probe_card)
        pl.setContentsMargins(12, 11, 12, 11)
        pl.setSpacing(7)
        row = QHBoxLayout()
        self.probe_badge = QLabel("NOT PROBED")
        self.probe_badge.setObjectName("ProbeBadge")
        row.addWidget(self.probe_badge)
        row.addStretch()
        self.copy_source = QPushButton("Copy URL")
        self.copy_source.setObjectName("TinyButton")
        row.addWidget(self.copy_source)
        pl.addLayout(row)
        self.source_hint = QLabel("Enter a media source and click Probe Source. Signed URLs are kept compact in this panel.")
        self.source_hint.setObjectName("ProbeText")
        self.source_hint.setWordWrap(True)
        self.source_hint.setMinimumHeight(42)
        self.source_hint.setMaximumHeight(72)
        pl.addWidget(self.source_hint)
        self.final_url = QLabel("")
        self.final_url.setObjectName("FinalUrl")
        self.final_url.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.final_url.setWordWrap(False)
        self.final_url.setMinimumHeight(24)
        self.final_url.setMaximumHeight(26)
        self.final_url.hide()
        pl.addWidget(self.final_url)
        root.addWidget(probe_card)
        root.addStretch(1)

        scroll.setWidget(content)
        outer_layout.addWidget(scroll, 1)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.open_page = QPushButton("Open Page")
        self.probe = QPushButton("Probe Source")
        self.save = QPushButton("Save Source")
        self.probe.setObjectName("SecondaryButton")
        self.save.setObjectName("PrimaryButton")
        self.open_page.setMinimumHeight(38)
        self.probe.setMinimumHeight(38)
        self.save.setMinimumHeight(38)
        actions.addWidget(self.open_page)
        actions.addWidget(self.probe)
        actions.addWidget(self.save)
        outer_layout.addLayout(actions)
        return outer

    def _build_queue_page(self):
        page = QFrame()
        page.setObjectName("Panel")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        controls = QHBoxLayout()
        self.pause_btn = QPushButton("Pause New Jobs")
        self.resume_btn = QPushButton("Resume New Jobs")
        self.retry_btn = QPushButton("Retry Failed")
        self.cancel_btn = QPushButton("Cancel Selected")
        self.clear_btn = QPushButton("Clear Completed")
        for b in (self.pause_btn, self.resume_btn, self.retry_btn, self.cancel_btn, self.clear_btn):
            b.setObjectName("SecondaryButton")
            controls.addWidget(b)
        controls.addStretch()
        controls.addWidget(QLabel("Workers"))
        self.worker_spin = QSpinBox()
        self.worker_spin.setRange(1, 8)
        self.worker_spin.setValue(self.service.settings.concurrency)
        controls.addWidget(self.worker_spin)
        layout.addLayout(controls)

        self.queue_note = QLabel("Jobs are persisted in SQLite. HLS downloads use FFmpeg and are validated before the final file appears in the library.")
        self.queue_note.setObjectName("InfoBanner")
        self.queue_note.setWordWrap(True)
        layout.addWidget(self.queue_note)

        self.qtable = QTableWidget(0, 8)
        self.qtable.setHorizontalHeaderLabels(["Episode", "Title", "Status", "Progress", "Speed", "Source", "Error", "File"])
        self.qtable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.qtable.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.qtable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.qtable.verticalHeader().setVisible(False)
        qh = self.qtable.horizontalHeader()
        qh.setSectionResizeMode(1, QHeaderView.Stretch)
        qh.setSectionResizeMode(6, QHeaderView.Stretch)
        qh.setSectionResizeMode(7, QHeaderView.Stretch)
        layout.addWidget(self.qtable, 1)
        return page

    def _build_settings_page(self):
        page = QFrame()
        page.setObjectName("Panel")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        title = QLabel("Settings")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)
        appearance = QFrame()
        appearance.setObjectName("Inset")
        al = QGridLayout(appearance)
        al.setContentsMargins(14, 14, 14, 14)
        al.addWidget(QLabel("Appearance"), 0, 0)
        self.theme_combo = NoWheelComboBox()
        self.theme_combo.setObjectName("ThemeCombo")
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.setCurrentText("Light" if self._theme == "light" else "Dark")
        self.theme_combo.setMinimumHeight(38)
        al.addWidget(self.theme_combo, 0, 1)
        al.addWidget(QLabel("Theme changes apply to the entire interface, including menus, fields, and the theme picker."), 1, 0, 1, 2)
        layout.addWidget(appearance)

        downloads = QFrame()
        downloads.setObjectName("Inset")
        dl = QGridLayout(downloads)
        dl.setContentsMargins(14, 14, 14, 14)
        dl.addWidget(QLabel("Download folder"), 0, 0)
        self.download_path = QLineEdit(str(self.service.settings.download_dir))
        self.download_path.setReadOnly(True)
        dl.addWidget(self.download_path, 0, 1)
        self.open_settings_downloads = QPushButton("Open Folder")
        self.open_settings_downloads.setObjectName("SecondaryButton")
        dl.addWidget(self.open_settings_downloads, 0, 2)
        layout.addWidget(downloads)
        layout.addStretch()
        return page

    def _build_help_page(self):
        page = QFrame()
        page.setObjectName("Panel")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("How it works")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setObjectName("HelpText")
        text.setHtml(
            "<h3>Episode page vs. media source</h3>"
            "<p>The episode page is stored as a reference. It is not the file being downloaded.</p>"
            "<p>For supported sources, the player may expose an HLS <code>master.m3u8</code> manifest. Put that manifest in <b>Media source</b>, then use <b>Probe Source</b> before saving it.</p>"
            "<h3>Source workflow</h3>"
            "<p><b>1.</b> Select an episode &nbsp; <b>2.</b> Configure the source &nbsp; <b>3.</b> Probe it &nbsp; <b>4.</b> Save it &nbsp; <b>5.</b> Queue the episode or season.</p>"
            "<p>The source inspector keeps long signed URLs compact, while the full value remains in the source field. Scrolling over the Type field will not change its selection.</p>"
            "<h3>Download lifecycle</h3>"
            "<p>Queued → downloading → validation → completed. HLS jobs are written to a temporary <code>.part.mp4</code> file and only become library files after validation succeeds.</p>"
            "<h3>Library organization</h3>"
            "<p>Downloads are grouped automatically into <code>Season XX</code> folders and named <code>SXXEXX - Episode Title.mp4</code>.</p>"
            "<h3>Troubleshooting</h3>"
            "<p>If a source probe fails, check that the URL is still valid and accessible. Signed streaming URLs can expire. A protected or DRM-only source is reported as unsupported rather than bypassed.</p>"
            "<h3>Access boundary</h3>"
            "<p>This project is intended for media sources you are authorized to access and download. It does not bypass DRM, authentication, geo restrictions, or other access controls.</p>"
        )
        layout.addWidget(text, 1)
        return page

    def _connect(self):
        self.sync_btn.clicked.connect(self.sync)
        self.import_btn.clicked.connect(self.import_sources)
        self.scan_btn.clicked.connect(self.scan)
        self.open_btn.clicked.connect(self.open_downloads)
        self.season_filter.textChanged.connect(self.filter_seasons)
        self.seasons.currentRowChanged.connect(self.load_season)
        self.table.itemSelectionChanged.connect(self.select_episode)
        self.table.cellDoubleClicked.connect(lambda row, _col: self._open_selected_episode_page(row))
        self.search.textChanged.connect(self.filter)
        self.selected_btn.clicked.connect(self.download_selected)
        self.season_btn.clicked.connect(self.download_season)
        self.all_btn.clicked.connect(self.download_all)
        self.pause_btn.clicked.connect(self.service.manager.pause)
        self.resume_btn.clicked.connect(self.service.manager.resume)
        self.retry_btn.clicked.connect(self.retry_failed)
        self.cancel_btn.clicked.connect(self.cancel_selected_jobs)
        self.clear_btn.clicked.connect(self.clear_completed)
        self.save.clicked.connect(self.save_source)
        self.probe.clicked.connect(self.probe_source)
        self.open_page.clicked.connect(self.open_episode_page)
        self.copy_source.clicked.connect(self.copy_source_url)
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        self.open_settings_downloads.clicked.connect(self.open_downloads)
        self.signals.progress.connect(self.on_progress)
        self.signals.state.connect(self.on_state)
        self.nav_library.clicked.connect(lambda: self.navigate(0))
        self.nav_queue.clicked.connect(lambda: self.navigate(1))
        self.nav_settings.clicked.connect(lambda: self.navigate(2))
        self.nav_help.clicked.connect(lambda: self.navigate(3))

    def _install_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+F"), self, self.search.setFocus)
        QShortcut(QKeySequence("Ctrl+L"), self, self.url.setFocus)
        QShortcut(QKeySequence("Ctrl+Shift+Q"), self, self.download_selected)
        QShortcut(QKeySequence("F5"), self, self.refresh)

    def navigate(self, index: int):
        self.stack.setCurrentIndex(index)
        buttons = (self.nav_library, self.nav_queue, self.nav_settings, self.nav_help)
        for i, button in enumerate(buttons):
            button.setChecked(i == index)
        titles = [
            ("Library", "Browse seasons, configure sources, and manage downloads."),
            ("Download Queue", "See exactly what is queued, running, completed, or failed."),
            ("Settings", "Appearance and local library options."),
            ("Help & Workflow", "Understand episode pages, manifests, FFmpeg, and validation."),
        ]
        self.page_title.setText(titles[index][0])
        self.page_subtitle.setText(titles[index][1])

    # ---------- style ----------
    def _apply_style(self):
        self.setStyleSheet(self._light_qss() if self._theme == "light" else self._dark_qss())

    def _dark_qss(self):
        return """
        /* Base: widgets stay transparent unless they are an actual surface. */
        QWidget {
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 13px;
            color: #f5f5f7;
            background: transparent;
        }
        QMainWindow { background: #0b0c0e; }
        QMenuBar {
            background: #0b0c0e;
            color: #d9d9df;
            border-bottom: 1px solid #25272b;
        }
        QMenuBar::item { padding: 6px 10px; background: transparent; border-radius: 7px; }
        QMenuBar::item:selected { background: #1c1e22; }
        QMenu {
            background: #17191c;
            color: #f5f5f7;
            border: 1px solid #2b2e33;
            padding: 5px;
        }
        QMenu::item { padding: 7px 24px 7px 10px; border-radius: 7px; }
        QMenu::item:selected { background: #292c31; }

        #Sidebar {
            background: #111214;
            border-right: 1px solid #25272b;
        }
        #Brand {
            background: #181a1d;
            border: 1px solid #2a2d32;
            border-radius: 14px;
        }
        #BrandTitle { font-size: 17px; font-weight: 700; }
        #BrandSub { color: #92959e; font-size: 12px; }
        #NavButton {
            text-align: left;
            padding: 10px 12px;
            border: 1px solid transparent;
            border-radius: 10px;
            background: transparent;
            color: #a9abb3;
            font-weight: 600;
        }
        #NavButton:hover { background: #191b1f; color: #f5f5f7; }
        #NavButton:checked {
            background: #25282d;
            border-color: #30343a;
            color: #ffffff;
        }
        #SideVersion { color: #666a73; font-size: 11px; padding: 4px 8px; }

        #PageTitle { font-size: 27px; font-weight: 750; }
        #PageSubtitle { color: #92959e; font-size: 13px; }

        /* One surface system throughout the application. */
        #StatCard, #Panel, #Inspector {
            background: #15171a;
            border: 1px solid #292c31;
            border-radius: 14px;
        }
        #Inspector { background: #15171a; }
        #InspectorScroll, #InspectorContent { background: transparent; border: 0; }
        #PanelTitle { font-size: 15px; font-weight: 700; }
        #SectionTitle { font-size: 22px; font-weight: 750; }
        #InspectorTitle { font-size: 19px; font-weight: 750; }
        #Summary { color: #a6a8b0; line-height: 1.3; }

        #CardEyebrow, #ProbeBadge {
            color: #8e919a;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 0.6px;
        }
        #CardValue { font-size: 24px; font-weight: 750; }
        #CardCaption { color: #7f828b; font-size: 11px; }

        #Inset, #ProbeCard, #InfoBanner {
            background: #1b1d21;
            border: 1px solid #2b2e34;
            border-radius: 11px;
        }
        #ProbeCard { background: #191b1f; }
        #ProbeText { color: #b7bac2; }
        #FinalUrl { color: #858891; font-size: 10px; }
        #MetaValue { color: #f1f1f3; font-weight: 600; }
        #InfoBanner { padding: 8px 10px; color: #a1a4ad; }

        QLineEdit, QComboBox, QSpinBox, QTextEdit, QTableWidget, QListWidget {
            min-height: 34px;
            background: #1b1d21;
            border: 1px solid #2d3036;
            border-radius: 9px;
            padding: 7px 9px;
            selection-background-color: #3a3e46;
            selection-color: #ffffff;
        }
        QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QTextEdit:hover { border-color: #393c43; }
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus { border-color: #6f747e; }
        QComboBox QAbstractItemView { background: #17191c; color: #f5f5f7; border: 1px solid #2b2e33; selection-background-color: #292c31; selection-color: #ffffff; }
        QComboBox::drop-down { border: 0; width: 28px; }
        QListWidget { padding: 5px; }
        QListWidget::item { padding: 9px 8px; border-radius: 8px; margin: 1px 0; }
        QListWidget::item:hover { background: #24272c; }
        QListWidget::item:selected { background: #30343a; color: #ffffff; }

        QTableWidget {
            gridline-color: #25282d;
            padding: 0;
            border-radius: 10px;
        }
        QHeaderView::section {
            background: #1b1d21;
            color: #8e919a;
            border: 0;
            border-bottom: 1px solid #2b2e34;
            padding: 9px 8px;
            font-size: 11px;
            font-weight: 700;
        }
        QTableWidget::item { padding: 7px 8px; border-bottom: 1px solid #24272c; }
        QTableWidget::item:selected { background: #30343a; }

        QPushButton {
            min-height: 34px;
            border: 1px solid #30333a;
            border-radius: 9px;
            padding: 7px 12px;
            background: #1d1f23;
            color: #f0f0f2;
            font-weight: 600;
        }
        QPushButton:hover { background: #25282d; border-color: #3a3d44; }
        QPushButton:pressed { background: #2b2e34; }
        QPushButton:disabled { color: #62656d; background: #17191c; border-color: #24262b; }
        #PrimaryButton {
            background: #f2f2f4;
            color: #161719;
            border-color: #f2f2f4;
        }
        #PrimaryButton:hover { background: #ffffff; border-color: #ffffff; }
        #SecondaryButton { background: #1d1f23; }
        #TinyButton { min-height: 26px; padding: 4px 8px; font-size: 11px; }

        QProgressBar {
            border: 0;
            border-radius: 4px;
            background: #292c31;
            text-align: center;
            height: 6px;
        }
        QProgressBar::chunk { background: #e6e6ea; border-radius: 4px; }
        QScrollBar:vertical { width: 9px; background: transparent; margin: 2px; }
        QScrollBar::handle:vertical { background: #3a3d44; border-radius: 4px; min-height: 30px; }
        QScrollBar::handle:vertical:hover { background: #4a4d55; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QStatusBar { background: #0b0c0e; color: #7f828b; border-top: 1px solid #25272b; }
        #StatusText { color: #92959e; }
        """

    def _light_qss(self):
        return """
        QWidget {
            font-family: "Segoe UI", Arial, sans-serif;
            font-size: 13px;
            color: #1c1c20;
            background: transparent;
        }
        QMainWindow { background: #f5f5f7; }
        QMenuBar { background: #f5f5f7; color: #25252a; border-bottom: 1px solid #dedee3; }
        QMenuBar::item { padding: 6px 10px; background: transparent; border-radius: 7px; }
        QMenuBar::item:selected { background: #e6e6eb; }
        QMenu { background: #ffffff; border: 1px solid #d8d8de; padding: 5px; }
        QMenu::item { padding: 7px 24px 7px 10px; border-radius: 7px; }
        QMenu::item:selected { background: #e4e4e9; }

        #Sidebar { background: #ededf0; border-right: 1px solid #d9d9df; }
        #Brand, #StatCard, #Panel, #Inspector {
            background: #ffffff;
            border: 1px solid #dedee3;
            border-radius: 14px;
        }
        #BrandTitle, #PageTitle, #InspectorTitle, #SectionTitle, #PanelTitle, #CardValue, #MetaValue { color: #17171a; }
        #InspectorScroll, #InspectorContent { background: transparent; border: 0; }
        #SideVersion { color: #9a9aa2; font-size: 11px; padding: 4px 8px; }
        #BrandSub, #PageSubtitle, #Summary, #CardCaption, #StatusText, #SideStatus, #ProbeText, #FinalUrl { color: #777780; }
        #NavButton { text-align: left; padding: 10px 12px; border: 1px solid transparent; border-radius: 10px; background: transparent; color: #676872; font-weight: 600; }
        #NavButton:hover { background: #e7e7eb; color: #222228; }
        #NavButton:checked { background: #dcdce2; border-color: #d3d3d9; color: #111114; }
        #CardEyebrow, #ProbeBadge { color: #777780; font-size: 10px; font-weight: 700; letter-spacing: 0.5px; }
        #CardValue { font-size: 24px; font-weight: 750; }
        #SectionTitle { font-size: 22px; font-weight: 750; }
        #InspectorTitle { font-size: 19px; font-weight: 750; }
        #Inset, #ProbeCard, #InfoBanner { background: #f9f9fb; border: 1px solid #dedee3; border-radius: 11px; }
        QLineEdit, QComboBox, QSpinBox, QTextEdit, QTableWidget, QListWidget { min-height: 34px; background: #ffffff; border: 1px solid #d7d7dd; border-radius: 9px; padding: 7px 9px; selection-background-color: #d7d7dd; selection-color: #17171a; }
        QLineEdit:hover, QComboBox:hover, QSpinBox:hover, QTextEdit:hover { border-color: #c4c4cb; }
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus { border-color: #8b8c95; }
        QComboBox QAbstractItemView { background: #ffffff; color: #222228; border: 1px solid #d7d7dd; selection-background-color: #e4e4e9; selection-color: #17171a; }
        QComboBox::drop-down { border: 0; width: 28px; }
        QListWidget { padding: 5px; }
        QListWidget::item { padding: 9px 8px; border-radius: 8px; margin: 1px 0; }
        QListWidget::item:hover { background: #f0f0f3; }
        QListWidget::item:selected { background: #dedee4; color: #111114; }
        QTableWidget { gridline-color: #ececf0; padding: 0; border-radius: 10px; }
        QHeaderView::section { background: #f9f9fb; color: #777780; border: 0; border-bottom: 1px solid #dedee3; padding: 9px 8px; font-size: 11px; font-weight: 700; }
        QTableWidget::item { padding: 7px 8px; border-bottom: 1px solid #eeeeF1; }
        QTableWidget::item:selected { background: #e2e2e7; }
        QPushButton { min-height: 34px; border: 1px solid #d6d6dc; border-radius: 9px; padding: 7px 12px; background: #ffffff; color: #222228; font-weight: 600; }
        QPushButton:hover { background: #f0f0f3; border-color: #c8c8cf; }
        QPushButton:pressed { background: #e7e7eb; }
        QPushButton:disabled { color: #aaaab1; background: #eeeeF1; }
        #PrimaryButton { background: #1d1d21; color: #ffffff; border-color: #1d1d21; }
        #PrimaryButton:hover { background: #101014; border-color: #101014; }
        #SecondaryButton { background: #ffffff; }
        #TinyButton { min-height: 26px; padding: 4px 8px; font-size: 11px; }
        QProgressBar { border: 0; border-radius: 4px; background: #e0e0e5; text-align: center; height: 6px; }
        QProgressBar::chunk { background: #2b2b30; border-radius: 4px; }
        QStatusBar { background: #f5f5f7; color: #777780; border-top: 1px solid #dedee3; }
        """

    def change_theme(self, value: str):
        self._theme = value.lower()
        self._ui_settings.setValue("theme", self._theme)
        qss = self._light_qss() if self._theme == "light" else self._dark_qss()
        self.setStyleSheet(qss)
        self._apply_theme_popup()

    def _apply_theme_popup(self):
        if not hasattr(self, "theme_combo"):
            return
        if self._theme == "light":
            self.theme_combo.view().setStyleSheet("""
                QAbstractItemView { background: #ffffff; color: #222228; border: 1px solid #d7d7dd; }
                QAbstractItemView::item { padding: 8px 10px; }
                QAbstractItemView::item:hover, QAbstractItemView::item:selected { background: #e4e4e9; color: #17171a; }
            """)
        else:
            self.theme_combo.view().setStyleSheet("""
                QAbstractItemView { background: #17191c; color: #f5f5f7; border: 1px solid #2b2e33; }
                QAbstractItemView::item { padding: 8px 10px; }
                QAbstractItemView::item:hover, QAbstractItemView::item:selected { background: #292c31; color: #ffffff; }
            """)


    # ---------- library ----------
    def refresh(self):
        old = self.current_season()
        self.seasons.blockSignals(True)
        self.seasons.clear()
        self._season_numbers.clear()
        total = done = 0
        for s in self.service.repo.list_seasons():
            total += s.episode_count
            done += s.downloaded_count
            self._season_numbers.append(s.number)
            item = QListWidgetItem(f"Season {s.number:02d}   {s.downloaded_count}/{s.episode_count}")
            item.setData(Qt.UserRole, s.number)
            self.seasons.addItem(item)
        self.seasons.blockSignals(False)
        self.filter_seasons(self.season_filter.text())
        if self.seasons.count():
            row = next((i for i in range(self.seasons.count()) if self.seasons.item(i).data(Qt.UserRole) == old), 0)
            self.seasons.setCurrentRow(row)
        self.card_seasons.setValue(str(len(self.service.repo.list_seasons())))
        self.card_episodes.setValue(str(total))
        self.card_downloaded.setValue(str(done))
        self.card_missing.setValue(str(total - done))
        self.refresh_queue()

    def current_season(self):
        item = self.seasons.currentItem()
        return item.data(Qt.UserRole) if item else None

    def filter_seasons(self, text):
        q = text.lower().strip()
        for i in range(self.seasons.count()):
            self.seasons.item(i).setHidden(bool(q and q not in self.seasons.item(i).text().lower()))

    def load_season(self, row):
        if row < 0 or self.current_season() is None:
            return
        episodes = self.service.repo.list_episodes(self.current_season())
        self.table.setRowCount(len(episodes))
        for r, e in enumerate(episodes):
            source = e.source_kind.upper() if e.source_url else "NONE"
            status = "Downloaded" if e.downloaded else ("Configured" if e.source_url else "Missing source")
            values = [f"S{e.season:02d}E{e.number:02d}", e.title, e.airdate or "—", source, status, ""]
            for c, v in enumerate(values):
                self.table.setItem(r, c, QTableWidgetItem(str(v)))
        self.filter(self.search.text())

    def filter(self, text):
        q = text.lower().strip()
        for r in range(self.table.rowCount()):
            hay = " ".join(self.table.item(r, c).text() for c in (0, 1, 3, 4)).lower()
            self.table.setRowHidden(r, bool(q and q not in hay))

    def select_episode(self):
        rows = self.table.selectionModel().selectedRows()
        if len(rows) != 1:
            self.current_episode = None
            self.detail_title.setText("Select an episode")
            self.summary.setText("Select an episode to see its metadata and configure its media source.")
            self.meta_air.setText("—")
            self.meta_runtime.setText("—")
            self.meta_status.setText("—")
            self.meta_source.setText("—")
            return
        code = self.table.item(rows[0].row(), 0).text()
        e = self.service.repo.get_episode(int(code[1:3]), int(code[4:6]))
        self.current_episode = e
        self.detail_title.setText(f"S{e.season:02d}E{e.number:02d} · {e.title}")
        self.summary.setText(e.summary or "No summary available.")
        self.meta_air.setText(e.airdate or "—")
        self.meta_runtime.setText(f"{e.runtime} min" if e.runtime else "—")
        self.meta_status.setText("Downloaded" if e.downloaded else ("Configured" if e.source_url else "Missing source"))
        self.meta_source.setText((e.source_kind or "unknown").upper() if e.source_url else "NONE")
        self.page_url.setText(e.page_url or "")
        self.url.setText(e.source_url or "")
        self.ext.setText(e.extension or "mp4")
        self.sha.setText(e.sha256 or "")
        idx = max(0, self.kind.findData(e.source_kind or "unknown"))
        self.kind.setCurrentIndex(idx)
        self.probe_badge.setText("CONFIGURED" if e.source_url else "NOT PROBED")
        self.final_url.hide()
        if e.source_url:
            self.source_hint.setText(f"Source configured as {e.source_kind}. Probe it to verify the current response before downloading.")
        else:
            self.source_hint.setText("No media source configured. The episode webpage is not itself a downloadable media source.")

    def _set_status(self, message: str):
        self.statusBar().showMessage(message)

    def _open_selected_episode_page(self, row: int):
        item = self.table.item(row, 0)
        if not item:
            return
        code = item.text()
        try:
            e = self.service.repo.get_episode(int(code[1:3]), int(code[4:6]))
        except (ValueError, IndexError):
            return
        if e and e.page_url:
            webbrowser.open(e.page_url)

    # ---------- source inspector ----------
    def copy_source_url(self):
        value = self.url.text().strip()
        if not value:
            return
        QGuiApplication.clipboard().setText(value)
        self._set_status("Media source copied to clipboard.")

    def _compact_url(self, value: str, limit: int = 72) -> str:
        if not value:
            return ""
        p = urlparse(value)
        base = f"{p.scheme}://{p.netloc}{p.path}"
        if p.query:
            base += "?…"
        if len(base) <= limit:
            return base
        return base[: limit - 1] + "…"

    def open_episode_page(self):
        url = self.page_url.text().strip()
        if not url:
            QMessageBox.information(self, "No episode page", "No episode webpage URL is configured.")
            return
        webbrowser.open(url)

    def open_downloads(self):
        folder = str(self.service.settings.download_dir)
        try:
            if os.name == "nt":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception as exc:
            QMessageBox.warning(self, "Open folder", str(exc))

    def probe_source(self):
        if not self.current_episode:
            QMessageBox.information(self, "Select an episode", "Select one episode first.")
            return
        url = self.url.text().strip()
        if not url:
            QMessageBox.warning(self, "No media source", "Enter a direct media URL or HLS .m3u8 manifest first.")
            return
        self.probe.setEnabled(False)
        self.probe_badge.setText("PROBING…")
        self.source_hint.setText("Checking the URL and response headers…")
        self.final_url.hide()
        self._set_status("Probing source…")
        self.activity_progress.show()
        QApplication.processEvents()
        try:
            result = self.service.probe_source(url)
            if result["valid"]:
                detected = result["kind"]
                idx = max(0, self.kind.findData(detected))
                self.kind.setCurrentIndex(idx)
                self.probe_badge.setText(f"VALID · {detected.upper()}")
                self.source_hint.setText(result["message"])
                final = result.get("final_url", "")
                if final:
                    self.final_url.setText(f"Final URL: {self._compact_url(final)}")
                    self.final_url.setToolTip(final)
                    self.final_url.show()
                self._set_status("Source probe complete.")
            else:
                self.probe_badge.setText("FAILED")
                self.source_hint.setText(result["message"])
                self._set_status("Source probe failed.")
        except Exception as exc:
            self.probe_badge.setText("ERROR")
            self.source_hint.setText(f"Probe error: {exc}")
            self._set_status("Source probe failed.")
        finally:
            self.activity_progress.hide()
            self.probe.setEnabled(True)

    def save_source(self):
        if not self.current_episode:
            QMessageBox.information(self, "Select an episode", "Select one episode first.")
            return
        e = self.current_episode
        try:
            self.service.save_source(e.season, e.number, self.url.text().strip(), self.ext.text().strip(),
                                     self.sha.text().strip(), self.page_url.text().strip(), self.kind.currentData())
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid source", str(exc))
            return
        self._set_status("Source saved.")
        self.refresh()

    # ---------- actions ----------
    def sync(self):
        self.sync_btn.setEnabled(False)
        self._set_status("Syncing TVmaze metadata…")
        self.activity_progress.show()
        try:
            count = self.service.sync_tvmaze()
            self._set_status(f"Synced {count} episodes.")
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Sync failed", str(exc))
        finally:
            self.activity_progress.hide()
            self.sync_btn.setEnabled(True)

    def import_sources(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Sources", "", "CSV/Text (*.csv *.txt)")
        if not path:
            return
        try:
            count = self.service.import_sources(path)
            self._set_status(f"Imported {count} source(s).")
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Import failed", str(exc))

    def scan(self):
        count = self.service.scan_library()
        self._set_status(f"Library scan found {count} matching file(s).")
        self.refresh()

    def selected_episodes(self):
        out = []
        for row in self.table.selectionModel().selectedRows():
            code = self.table.item(row.row(), 0).text()
            e = self.service.repo.get_episode(int(code[1:3]), int(code[4:6]))
            if e:
                out.append(e)
        return out

    def download_selected(self):
        count = 0
        errors = []
        for e in self.selected_episodes():
            try:
                if self.service.queue_episode(e.season, e.number):
                    count += 1
            except Exception as exc:
                errors.append(f"S{e.season:02d}E{e.number:02d}: {exc}")
        self._set_status(f"Queued {count} episode(s).")
        if errors:
            QMessageBox.warning(self, "Some episodes were not queued", "\n".join(errors[:12]))
        self.refresh_queue()
        self.navigate(1)

    def download_season(self):
        season = self.current_season()
        if season is None:
            return
        count = self.service.queue_season(season)
        self._set_status(f"Queued {count} episode(s) from Season {season:02d}.")
        self.refresh_queue()
        self.navigate(1)

    def download_all(self):
        count = self.service.queue_all()
        self._set_status(f"Queued {count} missing episode(s).")
        self.refresh_queue()
        self.navigate(1)

    def retry_failed(self):
        count = 0
        for job in self.service.repo.list_jobs():
            if job["status"] == "failed":
                e = self.service.repo.get_episode(job["season"], job["episode"])
                if e:
                    self.service.manager.retry(e)
                    count += 1
        self._set_status(f"Retried {count} failed job(s).")
        self.refresh_queue()

    def cancel_selected_jobs(self):
        rows = self.qtable.selectionModel().selectedRows()
        count = 0
        for row in rows:
            key = self.qtable.item(row.row(), 0).data(Qt.UserRole)
            if key:
                e = self.service.repo.get_episode(*key)
                if e:
                    self.service.manager.cancel(e)
                    count += 1
        self._set_status(f"Cancelled {count} job(s).")
        self.refresh_queue()

    def clear_completed(self):
        self.service.repo.clear_completed_jobs()
        self._set_status("Completed queue entries cleared.")
        self.refresh_queue()

    # ---------- live queue ----------
    def on_progress(self, e, done, total, speed):
        text = f"{done / total * 100:.0f}%" if total else "Working"
        self.update_episode_progress(e, text)

    def update_episode_progress(self, e, text):
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).text() == f"S{e.season:02d}E{e.number:02d}":
                self.table.setItem(row, 5, QTableWidgetItem(text))
                break

    def on_state(self, e, state, error):
        message = f"S{e.season:02d}E{e.number:02d}: {state}"
        if error:
            message += f" — {error}"
        self._set_status(message)
        self.statusBar().showMessage(message)
        self.refresh_queue()
        if state == "completed":
            self.refresh()

    def refresh_queue(self):
        jobs = self.service.repo.list_jobs()
        active = sum(j["status"] == "downloading" for j in jobs)
        self.card_active.setValue(str(active))
        self.qtable.setRowCount(len(jobs))
        for row, job in enumerate(jobs):
            e = self.service.repo.get_episode(job["season"], job["episode"])
            code = f"S{job['season']:02d}E{job['episode']:02d}"
            title = e.title if e else "Unknown episode"
            pct = f"{job['bytes_done'] / job['bytes_total'] * 100:.0f}%" if job["bytes_total"] else ("Working" if job["status"] == "downloading" else "")
            speed = f"{job['speed'] / 1024 / 1024:.2f} MB/s" if job["speed"] else ""
            source = e.source_kind.upper() if e else ""
            filename = e.filename if e else ""
            values = [code, title, job["status"].upper(), pct, speed, source, job["error"], filename]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value or ""))
                if col == 0:
                    item.setData(Qt.UserRole, (job["season"], job["episode"]))
                self.qtable.setItem(row, col, item)

    def show_help(self):
        self.navigate(3)

    def closeEvent(self, event):
        self.service.shutdown()
        event.accept()
