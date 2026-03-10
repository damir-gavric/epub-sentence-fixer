import os
import re
import shutil
import zipfile

from bs4 import BeautifulSoup

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QKeySequence, QShortcut, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


STYLESHEET = """
QMainWindow, QWidget {
    background: #eef3f9;
    color: #233247;
    font-family: "Segoe UI";
    font-size: 12px;
}
QLabel { background: transparent; }
QFrame#headerBar, QFrame#sidebarCard, QFrame#contentCard, QFrame#infoCard, QFrame#editorCard, QFrame#previewCard, QFrame#actionCard {
    background: #f8fbff;
    border: 1px solid #d4deea;
    border-radius: 16px;
}
QFrame#headerBar {
    border-radius: 0;
    border-left: 0;
    border-right: 0;
    border-top: 0;
}
QLabel#titleLabel { font-size: 26px; font-weight: 700; color: #223248; }
QLabel#subtitleLabel, QLabel#sectionHint, QLabel#sidebarMeta { color: #6d7f96; }
QLabel#sectionHint { font-size: 14px; }
QLabel#subtitleLabel { font-size: 11px; }
QLabel#splitSummary { color: #4d617d; }
QLabel#fontControlIcon { color: #637892; padding: 0px 2px 0px 0px; min-width: 0px; font-size: 16px; font-weight: 700; }
QSpinBox#fontSizeSpin { background: #f8fbff; color: #233247; border: 1px solid #d4deea; border-radius: 10px; padding: 4px 8px; min-width: 56px; font-size: 15px; font-weight: 600; }
QSpinBox#fontSizeSpin:hover { background: #edf4fc; }
QSpinBox#fontSizeSpin::up-button, QSpinBox#fontSizeSpin::down-button { width: 16px; border: 0px; background: transparent; subcontrol-origin: border; }
QSpinBox#fontSizeSpin::up-button { subcontrol-position: top right; }
QSpinBox#fontSizeSpin::down-button { subcontrol-position: bottom right; }
QSpinBox#fontSizeSpin::up-arrow { image: none; width: 0px; height: 0px; border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 6px solid #637892; }
QSpinBox#fontSizeSpin::down-arrow { image: none; width: 0px; height: 0px; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 6px solid #637892; }
QLabel#sectionTitle { font-size: 16px; font-weight: 700; color: #2d3f57; }
QLabel#cardTitle { font-size: 13px; font-weight: 700; color: #4e617b; }
QLabel#badgeNeutral, QLabel#badgePending, QLabel#badgeFixed, QLabel#badgeSkipped, QLabel#viewBadge {
    border-radius: 10px;
    padding: 5px 10px;
    font-weight: 700;
}
QLabel#badgeNeutral { background: #e8eef6; color: #4e647f; }
QLabel#viewBadge { background: #eef4fb; color: #5c718d; padding: 4px 10px; }
QLabel#badgePending { background: #e7f0ff; color: #2f7cf6; }
QLabel#badgeFixed { background: #dff3ea; color: #1d7a58; }
QLabel#badgeSkipped { background: #e8eefc; color: #5873b8; }
QPushButton {
    background: #f8fbff;
    color: #233247;
    border: 1px solid #cfd9e6;
    border-radius: 12px;
    padding: 10px 16px;
    min-height: 24px;
    font-weight: 600;
}
QPushButton:hover { background: #edf4fc; }
QPushButton:pressed { background: #e4edf8; }
QPushButton:disabled { background: #e9eff6; color: #93a3b8; border: 1px solid #d8e1ec; }
QPushButton#primaryButton, QPushButton#saveButton {
    background: #3b82f6;
    color: #ffffff;
    border: 1px solid #2f73df;
}
QPushButton#headerSecondary {
    background: #f8fbff;
    color: #233247;
    border: 1px solid #bfd0e4;
}
QPushButton#headerSecondary:hover { background: #edf4fc; }
QPushButton#primaryButton:hover, QPushButton#saveButton:hover { background: #1f6be0; }
QListWidget { background: transparent; border: 0; outline: 0; }
QListWidget::item {
    background: #f8fbff;
    border: 1px solid #d9e3ef;
    border-radius: 12px;
    margin-bottom: 8px;
    padding: 0px;
}
QListWidget::item:selected { background: #eef5ff; border: 1px solid #a8c4eb; border-left: 4px solid #4f8ff7; color: #1f3552; }
QListWidget::item:hover { background: #eef4fb; }
QPlainTextEdit, QTextEdit {
    background: #ffffff;
    color: #243348;
    border: 1px solid #d3deea;
    border-radius: 14px;
    padding: 12px;
    selection-background-color: #bed7ff;
    selection-color: #16263f;
}
QPlainTextEdit:read-only, QTextEdit:read-only { background: #fbfdff; }
QPlainTextEdit:disabled, QTextEdit:disabled { background: #eef3f8; color: #8b9bae; }
QProgressBar {
    background: #e5edf7;
    border: 1px solid #d2ddeb;
    border-radius: 8px;
    text-align: center;
    min-height: 12px;
}
QProgressBar::chunk { background: #7ea8e8; border-radius: 7px; }
QStatusBar { background: #e9f0f8; color: #5a6f89; border-top: 1px solid #d2ddeb; }
QStatusBar QLabel { color: #5a6f89; padding: 4px 8px; }
"""

APP_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ICON_PATH = os.path.join(APP_DIR, "assets", "epub-sentence-fixer-icon.svg")

STATUS_PENDING = "Pending"
STATUS_FIXED = "Fixed"
STATUS_SKIPPED = "Skipped"


class EPUBFixerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EPUB Sentence Fixer")
        if os.path.exists(APP_ICON_PATH):
            self.setWindowIcon(QIcon(APP_ICON_PATH))
        self.resize(1500, 980)

        self.paragraphs = []
        self.suggestions = []
        self.tag_map = []
        self.suggestion_statuses = []
        self.suggestion_merged_texts = []
        self.current_suggestion_index = -1
        self.extracted_path = "_epub_working"
        self.loaded_epub_path = ""
        self.file_soups = {}
        self.applied_changes_log = []
        self.history_stack = []
        self.fixed_count = 0
        self.skipped_count = 0
        self.boundary_words = 6
        self.unsaved_changes = False
        self.sidebar_sync_locked = False
        self.current_prev_focus = ""
        self.current_curr_focus = ""
        self.merge_highlight_sync = False
        self.content_font_size = 11

        self.status_label = QLabel("Ready.")
        self.statusBar().addPermanentWidget(self.status_label, 1)

        self._build_ui()
        self._bind_shortcuts()
        self._apply_content_font_size()
        self._refresh_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame()
        header.setObjectName("headerBar")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(28, 20, 28, 20)
        header_layout.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        self.title_label = QLabel("EPUB Sentence Fixer")
        self.title_label.setObjectName("titleLabel")
        self.subtitle_label = QLabel("Detect and repair broken sentences from PDF-to-EPUB conversions")
        self.subtitle_label.setObjectName("subtitleLabel")
        title_col.addWidget(self.title_label)
        title_col.addWidget(self.subtitle_label)
        header_layout.addLayout(title_col, 1)

        header_actions = QHBoxLayout()
        header_actions.setContentsMargins(0, 0, 0, 0)
        header_actions.setSpacing(10)
        header_actions.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.font_control_icon = QLabel("Aa")
        self.font_control_icon.setObjectName("fontControlIcon")
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setObjectName("fontSizeSpin")
        self.font_size_spin.setRange(6, 15)
        self.font_size_spin.setValue(self.content_font_size)
        self.font_size_spin.setButtonSymbols(QSpinBox.UpDownArrows)
        self.font_size_spin.valueChanged.connect(self._on_content_font_size_changed)
        self.btn_select = QPushButton("Open EPUB")
        self.btn_select.setObjectName("headerSecondary")
        self.btn_select.setMinimumWidth(122)
        self.btn_select.clicked.connect(self.load_epub)
        self.btn_save = QPushButton("Save Fixed EPUB")
        self.btn_save.setObjectName("saveButton")
        self.btn_save.setMinimumWidth(160)
        self.btn_save.clicked.connect(self.save_fixed_epub)
        header_actions.addWidget(self.font_control_icon)
        header_actions.addWidget(self.font_size_spin)
        header_actions.addWidget(self.btn_select)
        header_actions.addWidget(self.btn_save)
        header_layout.addLayout(header_actions)
        root.addWidget(header)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(16, 16, 16, 16)
        body_layout.setSpacing(16)
        root.addWidget(body, 1)

        sidebar = QFrame()
        sidebar.setObjectName("sidebarCard")
        sidebar.setMinimumWidth(320)
        sidebar.setMaximumWidth(360)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(12)

        sidebar_header = QHBoxLayout()
        self.sidebar_title = QLabel("Suggestions")
        self.sidebar_title.setObjectName("sectionTitle")
        self.current_status_badge = self._make_badge("Pending", "badgePending")
        sidebar_header.addWidget(self.sidebar_title)
        sidebar_header.addStretch(1)
        sidebar_header.addWidget(self.current_status_badge)
        sidebar_layout.addLayout(sidebar_header)

        self.sidebar_meta = QLabel("Load an EPUB to review detected sentence splits.")
        self.sidebar_meta.setObjectName("sidebarMeta")
        self.sidebar_meta.setWordWrap(True)
        self.suggestion_list = QListWidget()
        self.suggestion_list.currentRowChanged.connect(self._on_sidebar_row_changed)
        sidebar_layout.addWidget(self.sidebar_meta)
        sidebar_layout.addWidget(self.suggestion_list, 1)

        sidebar_footer = QFrame()
        sidebar_footer.setObjectName("infoCard")
        sidebar_footer_layout = QVBoxLayout(sidebar_footer)
        sidebar_footer_layout.setContentsMargins(14, 14, 14, 14)
        self.sidebar_stats = QLabel("Fixed: 0  |  Skipped: 0")
        self.sidebar_stats.setObjectName("sectionHint")
        self.sidebar_progress = QProgressBar()
        self.sidebar_progress.setRange(0, 100)
        sidebar_footer_layout.addWidget(self.sidebar_stats)
        sidebar_footer_layout.addWidget(self.sidebar_progress)
        sidebar_layout.addWidget(sidebar_footer)
        body_layout.addWidget(sidebar)
        content = QFrame()
        content.setObjectName("contentCard")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(18, 18, 18, 18)
        content_layout.setSpacing(16)

        review_header = QHBoxLayout()
        self.review_title = QLabel("Detected Split")
        self.review_title.setObjectName("sectionTitle")
        self.viewing_label = QLabel("Viewing 0 of 0")
        self.viewing_label.setObjectName("viewBadge")
        review_header.addWidget(self.review_title)
        review_header.addStretch(1)
        review_header.addWidget(self.viewing_label)
        content_layout.addLayout(review_header)

        original_grid = QGridLayout()
        original_grid.setHorizontalSpacing(16)
        original_grid.setVerticalSpacing(12)
        self.orig1_title = QLabel("Original paragraph 1")
        self.orig1_title.setObjectName("cardTitle")
        self.orig2_title = QLabel("Original paragraph 2")
        self.orig2_title.setObjectName("cardTitle")
        self.orig1_text = QTextEdit()
        self.orig1_text.setReadOnly(True)
        self.orig1_text.setMinimumHeight(210)
        self.orig2_text = QTextEdit()
        self.orig2_text.setReadOnly(True)
        self.orig2_text.setMinimumHeight(210)
        original_grid.addWidget(self.orig1_title, 0, 0)
        original_grid.addWidget(self.orig2_title, 0, 1)
        original_grid.addWidget(self.orig1_text, 1, 0)
        original_grid.addWidget(self.orig2_text, 1, 1)
        content_layout.addLayout(original_grid)

        split_card = QFrame()
        split_card.setObjectName("infoCard")
        split_layout = QVBoxLayout(split_card)
        split_layout.setContentsMargins(16, 10, 16, 10)
        split_layout.setSpacing(6)
        self.split_title = QLabel("Split detected")
        self.split_title.setObjectName("sectionTitle")
        self.split_summary = QLabel("No active suggestion.")
        self.split_summary.setObjectName("splitSummary")
        self.split_summary.setTextFormat(Qt.RichText)
        self.split_summary.setWordWrap(True)
        split_layout.addWidget(self.split_title)
        split_layout.addWidget(self.split_summary)
        content_layout.addWidget(split_card)

        editor_card = QFrame()
        editor_card.setObjectName("editorCard")
        editor_layout = QVBoxLayout(editor_card)
        editor_layout.setContentsMargins(16, 16, 16, 16)
        self.editor_title = QLabel("Proposed corrected paragraph")
        self.editor_title.setObjectName("sectionTitle")
        self.merge_edit = QPlainTextEdit()
        self.merge_edit.setMinimumHeight(170)
        self.merge_edit.textChanged.connect(self._handle_merge_text_changed)
        editor_layout.addWidget(self.editor_title)
        editor_layout.addWidget(self.merge_edit)
        content_layout.addWidget(editor_card)

        action_card = QFrame()
        action_card.setObjectName("actionCard")
        action_layout = QHBoxLayout(action_card)
        action_layout.setContentsMargins(16, 14, 16, 14)
        action_layout.setSpacing(12)
        self.btn_undo = QPushButton("Undo")
        self.btn_previous = QPushButton("Previous")
        self.btn_skip = QPushButton("Skip")
        self.btn_fix = QPushButton("Accept Fix")
        self.btn_fix.setObjectName("primaryButton")
        self.btn_next = QPushButton("Next")
        self.btn_undo.clicked.connect(self.undo_last_action)
        self.btn_previous.clicked.connect(self.previous_suggestion)
        self.btn_skip.clicked.connect(self.skip_current)
        self.btn_fix.clicked.connect(self.fix_current)
        self.btn_next.clicked.connect(self.next_suggestion)
        action_layout.addWidget(self.btn_undo)
        action_layout.addWidget(self.btn_previous)
        action_layout.addStretch(1)
        action_layout.addWidget(self.btn_skip)
        action_layout.addWidget(self.btn_fix)
        action_layout.addWidget(self.btn_next)
        content_layout.addWidget(action_card)
        body_layout.addWidget(content, 1)

    def _bind_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key_Return), self, activated=self.fix_current)
        QShortcut(QKeySequence(Qt.Key_Enter), self, activated=self.fix_current)
        QShortcut(QKeySequence("S"), self, activated=self.skip_current)
        QShortcut(QKeySequence(Qt.Key_Left), self, activated=self.previous_suggestion)
        QShortcut(QKeySequence(Qt.Key_Right), self, activated=self.next_suggestion)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_fixed_epub)
        QShortcut(QKeySequence("Ctrl+Z"), self, activated=self.undo_last_action)

    def _make_badge(self, text: str, object_name: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName(object_name)
        return label

    def _status_badge_style(self, status: str) -> str:
        if status == STATUS_FIXED:
            return "badgeFixed"
        if status == STATUS_SKIPPED:
            return "badgeSkipped"
        return "badgePending"

    def _status_dot_color(self, status: str) -> str:
        if status == STATUS_FIXED:
            return "#1d7a58"
        if status == STATUS_SKIPPED:
            return "#5873b8"
        return "#3b82f6"

    def _apply_content_font_size(self):
        content_font = QFont("Segoe UI", self.content_font_size)
        self.orig1_text.setFont(content_font)
        self.orig2_text.setFont(content_font)
        self.merge_edit.setFont(content_font)
        self.merge_edit.document().setDefaultFont(content_font)

        split_font = QFont("Segoe UI", self.content_font_size)
        self.split_summary.setFont(split_font)

    def _on_content_font_size_changed(self, value: int):
        self.content_font_size = int(value)
        self._apply_content_font_size()
        if self.loaded_epub_path or self.suggestions:
            self._refresh_ui()

    def _build_sidebar_item_widget(self, index: int, status: str, file_name: str) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(8)

        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(f"background:{self._status_dot_color(status)}; border-radius:5px;")

        title = QLabel(f"Suggestion {index + 1}")
        title.setStyleSheet("color:#2c3f58; font-weight:600;")

        top.addWidget(dot, 0, Qt.AlignVCenter)
        top.addWidget(title, 1)

        meta = QLabel(file_name)
        meta.setStyleSheet("color:#6d7f96;")

        layout.addLayout(top)
        layout.addWidget(meta)
        return widget

    def _processed_count(self) -> int:
        return self.fixed_count + self.skipped_count

    def _refresh_status_bar(self):
        if not self.loaded_epub_path:
            self.status_label.setText("Ready.")
            return
        total = len(self.suggestions)
        if total and 0 <= self.current_suggestion_index < total:
            view_text = f"Viewing {self.current_suggestion_index + 1}/{total}"
        elif total:
            view_text = f"Summary {total}/{total}"
        else:
            view_text = "Viewing 0/0"
        self.status_label.setText(
            f"Current file: {os.path.basename(self.loaded_epub_path)}   |   {view_text}   |   Fixed: {self.fixed_count}   |   Skipped: {self.skipped_count}"
        )

    def _escape_html(self, text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    def _highlight_boundary(self, prev: str, curr: str, n_words: int = 6):
        prev_words = prev.strip().split()
        curr_words = curr.strip().split()
        if not prev_words or not curr_words:
            return self._escape_html(prev), self._escape_html(curr)
        prev_head = " ".join(prev_words[:-n_words]) if len(prev_words) > n_words else ""
        prev_tail = " ".join(prev_words[-n_words:])
        curr_head = " ".join(curr_words[:n_words])
        curr_tail = " ".join(curr_words[n_words:]) if len(curr_words) > n_words else ""
        prev_html = (self._escape_html(prev_head) + " ") if prev_head else ""
        prev_html += f'<span class="hl1">{self._escape_html(prev_tail)}</span>'
        curr_html = f'<span class="hl2">{self._escape_html(curr_head)}</span>'
        if curr_tail:
            curr_html += " " + self._escape_html(curr_tail)
        return prev_html, curr_html

    def _seam_tokens(self, prev: str, curr: str):
        prev_words = prev.split()
        curr_words = curr.split()
        return (prev_words[-1] if prev_words else "", curr_words[0] if curr_words else "")

    def _leading_focus_phrase(self, text: str, max_words: int = 4) -> str:
        words = text.strip().split()
        if not words:
            return ""
        chosen = []
        for word in words[:max_words]:
            chosen.append(word)
            if word.endswith((",", ";", ":", ".")):
                break
        return " ".join(chosen)

    def _trailing_focus_phrase(self, text: str, max_words: int = 2) -> str:
        words = text.strip().split()
        if not words:
            return ""
        return " ".join(words[-max_words:])

    def _clear_merge_highlights(self):
        self.merge_edit.setExtraSelections([])

    def _original_paragraph_html(self, text: str, target: str, background: str, foreground: str) -> str:
        display_text = text.replace(" ", " ")
        escaped = self._escape_html(display_text)
        if target:
            start = display_text.find(target)
            if start != -1:
                before = self._escape_html(display_text[:start])
                middle = self._escape_html(display_text[start:start + len(target)])
                after = self._escape_html(display_text[start + len(target):])
                escaped = (
                    before
                    + f"<span style='background:{background}; color:{foreground}; padding:0 1px; border-radius:2px;'>{middle}</span>"
                    + after
                )
        escaped = escaped.replace("\n", "<br>")
        return (
            f'<div style="font-family:Segoe UI,sans-serif; font-size:{self.content_font_size}pt; line-height:1.55; color:#243348;">'
            f"{escaped}"
            f"</div>"
        )

    def _clear_original_highlights(self):
        self.orig1_text.clear()
        self.orig2_text.clear()

    def _apply_original_highlights(self, prev: str, prev_focus: str, curr: str, curr_focus: str):
        self.orig1_text.setHtml(self._original_paragraph_html(prev, prev_focus, "#d9e8ff", "#27496b"))
        self.orig2_text.setHtml(self._original_paragraph_html(curr, curr_focus, "#f2e4bf", "#5a4526"))

    def _merge_selection(self, start: int, length: int, background: str, foreground: str):
        selection = QTextEdit.ExtraSelection()
        cursor = self.merge_edit.textCursor()
        cursor.setPosition(start)
        cursor.setPosition(start + length, QTextCursor.KeepAnchor)
        selection.cursor = cursor
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(background))
        fmt.setForeground(QColor(foreground))
        fmt.setProperty(QTextCharFormat.FullWidthSelection, False)
        selection.format = fmt
        return selection

    def _apply_merge_highlights(self):
        if self.merge_highlight_sync:
            return

        merged = self.merge_edit.toPlainText()
        selections = []

        prev_focus = self.current_prev_focus.strip()
        curr_focus = self.current_curr_focus.strip()

        if prev_focus:
            start = merged.find(prev_focus)
            if start != -1:
                selections.append(self._merge_selection(start, len(prev_focus), "#d9e8ff", "#27496b"))

        if curr_focus:
            search_from = 0
            if prev_focus:
                prev_start = merged.find(prev_focus)
                if prev_start != -1:
                    search_from = prev_start + len(prev_focus)
            start = merged.find(curr_focus, search_from)
            if start == -1:
                start = merged.find(curr_focus)
            if start != -1:
                selections.append(self._merge_selection(start, len(curr_focus), "#f2e4bf", "#5a4526"))

        self.merge_edit.setExtraSelections(selections)

    def _handle_merge_text_changed(self):
        self._apply_merge_highlights()

    def _summary_html(self) -> str:
        total = len(self.suggestions)
        return f"""
<div style="font-family:'Segoe UI',sans-serif;color:#233247;">
  <div style="font-size:18pt;font-weight:700;margin-bottom:12px;">Review complete</div>
  <div style="background:#ffffff;border:1px solid #d5dfeb;border-radius:14px;padding:16px;">
    <div style="margin-bottom:8px;">Total suggestions: <b>{total}</b></div>
    <div style="margin-bottom:8px;">Fixed: <b>{self.fixed_count}</b></div>
    <div style="margin-bottom:8px;">Skipped: <b>{self.skipped_count}</b></div>
    <div>Output is ready. Save the corrected EPUB when you are done reviewing.</div>
  </div>
</div>
"""

    def _refresh_sidebar(self):
        self.sidebar_sync_locked = True
        self.suggestion_list.clear()
        for index, suggestion in enumerate(self.suggestions):
            file_path, _ = self.tag_map[suggestion[0]]
            file_name = os.path.basename(file_path)
            status = self.suggestion_statuses[index]
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 64))
            self.suggestion_list.addItem(item)
            self.suggestion_list.setItemWidget(item, self._build_sidebar_item_widget(index, status, file_name))
        if self.suggestions and 0 <= self.current_suggestion_index < len(self.suggestions):
            self.suggestion_list.setCurrentRow(self.current_suggestion_index)
        else:
            self.suggestion_list.clearSelection()
        self.sidebar_sync_locked = False

    def _refresh_counts(self):
        total = len(self.suggestions)
        processed = self._processed_count()
        self.sidebar_progress.setValue(int((processed / total) * 100) if total else 0)
        self.sidebar_stats.setText(f"Fixed: {self.fixed_count}  |  Skipped: {self.skipped_count}")
        self.viewing_label.setText(
            f"Viewing {self.current_suggestion_index + 1} of {total}" if total and 0 <= self.current_suggestion_index < total else (f"Summary {total} of {total}" if total else "Viewing 0 of 0")
        )
        self.sidebar_meta.setText(
            f"{processed} processed of {total}. Select any suggestion from the list to review it." if total else "Load an EPUB to review detected sentence splits."
        )

    def _refresh_action_state(self):
        total = len(self.suggestions)
        has_current = total and 0 <= self.current_suggestion_index < total
        on_summary = total and self.current_suggestion_index == total
        current_status = self.suggestion_statuses[self.current_suggestion_index] if has_current else STATUS_PENDING
        self.current_status_badge.setObjectName(self._status_badge_style(current_status))
        self.current_status_badge.setText(current_status if has_current else "Pending")
        self.current_status_badge.style().unpolish(self.current_status_badge)
        self.current_status_badge.style().polish(self.current_status_badge)
        self.btn_undo.setEnabled(bool(self.history_stack))
        self.btn_previous.setEnabled(total > 0 and self.current_suggestion_index > 0)
        self.btn_next.setEnabled(total > 0 and self.current_suggestion_index < total)
        self.btn_skip.setEnabled(has_current and current_status != STATUS_FIXED)
        self.btn_fix.setEnabled(has_current and current_status != STATUS_FIXED)
        self.btn_save.setEnabled(bool(self.loaded_epub_path) and (self.fixed_count > 0 or on_summary))
        self.merge_edit.setEnabled(has_current)
        self.merge_edit.setReadOnly(not has_current or current_status == STATUS_FIXED)

    def _populate_summary_state(self):
        self.review_title.setText("Review summary")
        self.orig1_text.setEnabled(False)
        self.orig2_text.setEnabled(False)
        self.orig1_text.setPlainText("")
        self.orig2_text.setPlainText("")
        self._clear_original_highlights()
        self.current_prev_focus = ""
        self.current_curr_focus = ""
        self.merge_edit.setEnabled(False)
        self.merge_edit.setPlainText("")
        self._clear_merge_highlights()
        self.split_summary.setText("All suggestions have been reviewed.")

    def _populate_empty_state(self):
        self.review_title.setText("Detected Split")
        self.orig1_text.setEnabled(False)
        self.orig2_text.setEnabled(False)
        self.orig1_text.setPlainText("Load an EPUB to begin.")
        self.orig2_text.setPlainText("Detected sentence splits will appear here.")
        self._clear_original_highlights()
        self.current_prev_focus = ""
        self.current_curr_focus = ""
        self.merge_edit.setEnabled(False)
        self.merge_edit.setPlainText("")
        self._clear_merge_highlights()
        self.split_summary.setText("No active suggestion.")

    def _populate_current_suggestion(self):
        para_id, prev, curr = self.suggestions[self.current_suggestion_index]
        merged = self.suggestion_merged_texts[self.current_suggestion_index]
        status = self.suggestion_statuses[self.current_suggestion_index]
        seam_prev, seam_curr = self._seam_tokens(prev, curr)
        prev_focus = self._trailing_focus_phrase(prev)
        curr_focus = self._leading_focus_phrase(curr)
        self.current_prev_focus = prev_focus
        self.current_curr_focus = curr_focus
        self.review_title.setText("Detected Split")
        self.orig1_text.setEnabled(True)
        self.orig2_text.setEnabled(True)
        self._apply_original_highlights(prev, prev_focus, curr, curr_focus)
        self.merge_highlight_sync = True
        self.merge_edit.setPlainText(merged)
        self.merge_highlight_sync = False
        self._apply_merge_highlights()
        self.split_summary.setText(
            f"Split detected between <span style='background:#dce9fb; color:#24415f; border-radius:4px; padding:1px 4px;'><b>{self._escape_html(prev_focus)}</b></span> "
            f"and <span style='background:#efe3c8; color:#4d4030; border-radius:4px; padding:1px 4px;'><b>{self._escape_html(curr_focus)}</b></span>."
        )
        if status != STATUS_FIXED:
            self.merge_edit.setFocus()

    def _refresh_ui(self):
        self._refresh_sidebar()
        self._refresh_counts()
        if not self.loaded_epub_path or not self.suggestions:
            self._populate_empty_state()
        elif self.current_suggestion_index == len(self.suggestions):
            self._populate_summary_state()
        elif 0 <= self.current_suggestion_index < len(self.suggestions):
            self._populate_current_suggestion()
        else:
            self._populate_empty_state()
        self._refresh_action_state()
        self._refresh_status_bar()

    def cleanup_workspace(self):
        if os.path.exists(self.extracted_path):
            shutil.rmtree(self.extracted_path)

    def detect_broken_sentences(self, paragraphs):
        suggestions = []
        for i in range(1, len(paragraphs)):
            prev = paragraphs[i - 1].strip()
            curr = paragraphs[i].strip()
            if not prev or not curr:
                continue
            if not re.search(r'[.!?]["â€\']?$|\)$', prev) and curr[0].islower():
                suggestions.append((i - 1, prev, curr))
        return suggestions
    def load_epub(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open EPUB", "", "EPUB files (*.epub)")
        if not file_path:
            return
        self.loaded_epub_path = file_path
        self.fixed_count = 0
        self.skipped_count = 0
        self.unsaved_changes = False
        self.cleanup_workspace()
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(self.extracted_path)

        self.paragraphs = []
        self.tag_map = []
        self.file_soups = {}
        self.applied_changes_log = []
        self.history_stack = []
        self.suggestions = []
        self.suggestion_statuses = []
        self.suggestion_merged_texts = []
        self.current_suggestion_index = -1

        for root_dir, _, files in os.walk(self.extracted_path):
            for file in files:
                if file.endswith(".xhtml") or file.endswith(".html"):
                    full_path = os.path.join(root_dir, file)
                    with open(full_path, encoding="utf-8") as handle:
                        soup = BeautifulSoup(handle, "html.parser")
                    self.file_soups[full_path] = soup
                    for tag in soup.find_all(True):
                        if tag.name in ["p", "div"] and tag.get_text(strip=True):
                            self.paragraphs.append(tag.get_text().strip())
                            self.tag_map.append((full_path, tag))

        self.suggestions = self.detect_broken_sentences(self.paragraphs)
        self.suggestion_statuses = [STATUS_PENDING for _ in self.suggestions]
        self.suggestion_merged_texts = [f"{prev} {curr}" for _, prev, curr in self.suggestions]
        self.current_suggestion_index = 0 if self.suggestions else -1
        self.statusBar().showMessage(
            f"Loaded {len(self.suggestions)} suggestions for review." if self.suggestions else "No likely sentence splits were found in this EPUB.",
            3000,
        )
        self._apply_content_font_size()
        self._refresh_ui()

    def _on_sidebar_row_changed(self, row: int):
        if not self.sidebar_sync_locked and 0 <= row < len(self.suggestions):
            self.current_suggestion_index = row
            self._refresh_ui()

    def previous_suggestion(self):
        if not self.suggestions:
            return
        if self.current_suggestion_index == len(self.suggestions):
            self.current_suggestion_index = len(self.suggestions) - 1
        elif self.current_suggestion_index > 0:
            self.current_suggestion_index -= 1
        self._refresh_ui()

    def next_suggestion(self):
        if not self.suggestions:
            return
        if self.current_suggestion_index < len(self.suggestions) - 1:
            self.current_suggestion_index += 1
        elif self.current_suggestion_index == len(self.suggestions) - 1:
            self.current_suggestion_index = len(self.suggestions)
        self._refresh_ui()

    def _write_soup(self, file_path: str):
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(str(self.file_soups[file_path]))

    def fix_current(self):
        if not (0 <= self.current_suggestion_index < len(self.suggestions)):
            return
        if self.suggestion_statuses[self.current_suggestion_index] == STATUS_FIXED:
            self.statusBar().showMessage("This suggestion is already accepted.", 2000)
            return
        merged = self.merge_edit.toPlainText().strip()
        if not merged:
            QMessageBox.warning(self, "Empty correction", "Proposed corrected paragraph is empty.")
            return

        para_id, prev, curr = self.suggestions[self.current_suggestion_index]
        previous_status = self.suggestion_statuses[self.current_suggestion_index]
        previous_merged = self.suggestion_merged_texts[self.current_suggestion_index]
        file_path, tag = self.tag_map[para_id]
        _, tag_next = self.tag_map[para_id + 1]

        self.history_stack.append({
            "action": "fix",
            "index": self.current_suggestion_index,
            "previous_status": previous_status,
            "previous_merged": previous_merged,
            "old_p1": self.paragraphs[para_id],
            "old_p2": self.paragraphs[para_id + 1],
        })

        self.paragraphs[para_id] = merged
        self.paragraphs[para_id + 1] = ""
        tag.string = merged
        tag_next.extract()
        self._write_soup(file_path)

        if previous_status == STATUS_SKIPPED:
            self.skipped_count = max(0, self.skipped_count - 1)
        self.fixed_count += 1
        self.suggestion_statuses[self.current_suggestion_index] = STATUS_FIXED
        self.suggestion_merged_texts[self.current_suggestion_index] = merged
        self.applied_changes_log.append(
            f"[{file_path}]\nOriginal paragraph 1: {prev}\nOriginal paragraph 2: {curr}\nMerged: {merged}\n"
        )
        self.unsaved_changes = True
        self.statusBar().showMessage("Fix accepted.", 2500)
        self.next_suggestion()

    def skip_current(self):
        if not (0 <= self.current_suggestion_index < len(self.suggestions)):
            return
        current_status = self.suggestion_statuses[self.current_suggestion_index]
        if current_status == STATUS_FIXED:
            self.statusBar().showMessage("Accepted fixes cannot be skipped. Use Undo to revert the last action.", 2500)
            return
        if current_status == STATUS_SKIPPED:
            self.next_suggestion()
            return
        self.history_stack.append({"action": "skip", "index": self.current_suggestion_index, "previous_status": current_status})
        self.suggestion_statuses[self.current_suggestion_index] = STATUS_SKIPPED
        self.skipped_count += 1
        self.statusBar().showMessage("Suggestion skipped.", 2500)
        self.next_suggestion()
    def undo_last_action(self):
        if not self.history_stack:
            return
        entry = self.history_stack.pop()
        index = entry["index"]
        self.current_suggestion_index = index
        if entry["action"] == "skip":
            if self.suggestion_statuses[index] == STATUS_SKIPPED:
                self.skipped_count = max(0, self.skipped_count - 1)
            self.suggestion_statuses[index] = entry["previous_status"]
        elif entry["action"] == "fix":
            para_id = self.suggestions[index][0]
            file_path, tag = self.tag_map[para_id]
            _, tag_next = self.tag_map[para_id + 1]
            self.paragraphs[para_id] = entry["old_p1"]
            self.paragraphs[para_id + 1] = entry["old_p2"]
            tag.string = entry["old_p1"]
            new_tag = self.file_soups[file_path].new_tag(tag_next.name)
            new_tag.string = entry["old_p2"]
            tag.insert_after(new_tag)
            self._write_soup(file_path)
            self.fixed_count = max(0, self.fixed_count - 1)
            if entry["previous_status"] == STATUS_SKIPPED:
                self.skipped_count += 1
            self.suggestion_statuses[index] = entry["previous_status"]
            self.suggestion_merged_texts[index] = entry["previous_merged"]
        self.statusBar().showMessage("Last action reverted.", 2500)
        self._refresh_ui()

    def save_fixed_epub(self):
        if not self.loaded_epub_path:
            return
        output_path, _ = QFileDialog.getSaveFileName(self, "Save Fixed EPUB", "", "EPUB files (*.epub)")
        if not output_path:
            return
        if not output_path.lower().endswith(".epub"):
            output_path += ".epub"

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as epub_zip:
            mimetype_path = os.path.join(self.extracted_path, "mimetype")
            if os.path.exists(mimetype_path):
                epub_zip.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)
            for root_dir, _, files in os.walk(self.extracted_path):
                for file in files:
                    full_path = os.path.join(root_dir, file)
                    arcname = os.path.relpath(full_path, self.extracted_path)
                    if arcname != "mimetype":
                        epub_zip.write(full_path, arcname)

        log_path = os.path.splitext(output_path)[0] + "_log.txt"
        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write("\n\n".join(self.applied_changes_log))

        self.unsaved_changes = False
        QMessageBox.information(self, "Saved", f"Fixed EPUB saved to:\n{output_path}\n\nLog saved to:\n{log_path}")

    def closeEvent(self, event):
        if self.unsaved_changes and self.fixed_count > 0:
            answer = QMessageBox.question(
                self,
                "Unsaved fixes",
                "You have unsaved fixes. Do you want to close without saving?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer == QMessageBox.No:
                event.ignore()
                return
        super().closeEvent(event)


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    if os.path.exists(APP_ICON_PATH):
        app.setWindowIcon(QIcon(APP_ICON_PATH))
    window = EPUBFixerWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
