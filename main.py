import os
import re
import shutil
import zipfile
from bs4 import BeautifulSoup

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QFileDialog,
    QMessageBox,
    QPlainTextEdit,
    QTextEdit,
    QFrame,
)


STYLESHEET = """
/* =========================================================
   GLOBAL BASE
   ========================================================= */
QMainWindow, QWidget {
    background-color: #121212;
    color: #f5f5f5;
    font-size: 12px;
}

QLabel { color: #f5f5f5; }
QMessageBox QLabel { color: #f5f5f5; }

/* =========================================================
   TEXT EDITORS (DEFAULT)
   ========================================================= */
QPlainTextEdit, QTextEdit {
    background-color: #181818;
    color: #f5f5f5;
    border: 1px solid #3a3a3a;
    border-radius: 8px;
    padding: 10px;
    selection-background-color: #2d6cdf;
    selection-color: #ffffff;
}

/* READ-ONLY */
QPlainTextEdit:read-only, QTextEdit:read-only {
    background-color: #161616;
    color: #ffffff;
    border: 1px solid #444444;
}

/* DISABLED */
QPlainTextEdit:disabled, QTextEdit:disabled {
    background-color: #1a1a1a;
    color: #cccccc;
    border: 1px solid #2a2a2a;
}

/* =========================================================
   PREVIEW + MERGE SPECIAL (BY OBJECT NAME)
   ========================================================= */
QTextEdit#previewBox {
    background-color: #161616;
    color: #ffffff;
    border: 1px solid #444444;
    padding: 14px;
    font-size: 11pt;
}

/* IMPORTANT: force merge font size */
QPlainTextEdit#mergeBox {
    background-color: #1b1b1b;
    color: #ffffff;
    border: 1px solid #4a4a4a;
    font-size: 11pt;          /* <<< THIS FIXES "small" font */
}

QPlainTextEdit#mergeBox:disabled {
    background-color: #191919;
    color: #cfcfcf;
    border: 1px solid #2a2a2a;
    font-size: 11pt;
}

/* =========================================================
   BUTTONS
   ========================================================= */
QPushButton {
    background-color: #2a2a2a;
    color: #f5f5f5;
    border: 1px solid #3f3f3f;
    border-radius: 8px;
    padding: 8px 14px;
    min-height: 28px;
}
QPushButton:hover { background-color: #353535; }
QPushButton:pressed { background-color: #1f1f1f; }
QPushButton:disabled {
    background-color: #1c1c1c;
    color: #888888;
    border: 1px solid #2a2a2a;
}

/* =========================================================
   STATUS BAR
   ========================================================= */
QStatusBar {
    background: #101010;
    color: #dcdcdc;
    border-top: 1px solid #222;
}
QStatusBar QLabel {
    color: #dcdcdc;
    padding: 4px 8px;
}

/* =========================================================
   MESSAGE BOX
   ========================================================= */
QMessageBox { background-color: #121212; }
QMessageBox QPushButton { min-width: 90px; }

/* =========================================================
   FRAMES / SEPARATORS
   ========================================================= */
QFrame { color: #2c2c2c; }

/* =========================================================
   SCROLLBARS
   ========================================================= */
QScrollBar:vertical {
    background: #121212;
    width: 12px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #3a3a3a;
    border-radius: 6px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #4a4a4a; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QScrollBar:horizontal {
    background: #121212;
    height: 12px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #3a3a3a;
    border-radius: 6px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover { background: #4a4a4a; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""


class EPUBFixerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EPUB Sentence Fixer (PySide6)")
        self.resize(1100, 840)

        # -----------------------------
        # State
        # -----------------------------
        self.paragraphs = []
        self.suggestions = []
        self.tag_map = []
        self.current_suggestion_index = 0
        self.extracted_path = "_epub_working"
        self.loaded_epub_path = ""
        self.file_soups = {}
        self.applied_changes_log = []
        self.history_stack = []

        # Stats
        self.fixed_count = 0
        self.skipped_count = 0

        # Highlight settings
        self.boundary_words = 6

        # -----------------------------
        # Status bar
        # -----------------------------
        self.status_label = QLabel("Ready.")
        self.statusBar().addPermanentWidget(self.status_label, 1)

        # -----------------------------
        # UI
        # -----------------------------
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Top bar
        top = QHBoxLayout()
        self.btn_select = QPushButton("Select EPUB File")
        self.btn_select.clicked.connect(self.load_epub)

        self.lbl_status = QLabel("No file loaded.")
        self.lbl_status.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        top.addWidget(self.btn_select)
        top.addWidget(self.lbl_status, 1)
        root.addLayout(top)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        root.addWidget(sep)

        # Font: enforce 11pt for both preview windows
        preview_font = QFont("Segoe UI", 11)
        merge_font = QFont("Segoe UI", 11)

        # Rich preview
        self.text_display = QTextEdit()
        self.text_display.setObjectName("previewBox")
        self.text_display.setReadOnly(True)
        self.text_display.setPlaceholderText("Load an EPUB to begin.")
        self.text_display.setMinimumHeight(390)
        self.text_display.setFont(preview_font)
        root.addWidget(self.text_display, 2)

        # Merge editor (editable)
        self.merge_edit = QPlainTextEdit()
        self.merge_edit.setObjectName("mergeBox")
        self.merge_edit.setPlaceholderText("Proposed merge will appear here (editable).")
        self.merge_edit.setMinimumHeight(185)
        self.merge_edit.setFont(merge_font)  # keep this
        # Force document font too (extra robust)
        self.merge_edit.document().setDefaultFont(merge_font)
        root.addWidget(self.merge_edit, 1)

        # Buttons row
        buttons = QHBoxLayout()
        buttons.setSpacing(10)

        self.btn_back = QPushButton("Back")
        self.btn_skip = QPushButton("Skip")
        self.btn_fix = QPushButton("Fix")
        self.btn_save = QPushButton("Save Fixed EPUB")

        self.btn_back.clicked.connect(self.go_back)
        self.btn_skip.clicked.connect(self.skip_current)
        self.btn_fix.clicked.connect(self.fix_current)
        self.btn_save.clicked.connect(self.save_fixed_epub)

        buttons.addWidget(self.btn_back)
        buttons.addWidget(self.btn_skip)
        buttons.addWidget(self.btn_fix)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_save)

        root.addLayout(buttons)

        # Initial enabled state
        self.btn_back.setEnabled(False)
        self.btn_skip.setEnabled(False)
        self.btn_fix.setEnabled(False)
        self.btn_save.setEnabled(False)

        self._update_status_bar()

    # -----------------------------
    # Status bar updater
    # -----------------------------
    def _update_status_bar(self):
        if not self.loaded_epub_path:
            self.status_label.setText("Ready.")
            return

        total = len(self.suggestions)
        idx = min(self.current_suggestion_index + 1, total) if total else 0
        name = os.path.basename(self.loaded_epub_path)

        self.status_label.setText(
            f"Loaded: {name}   |   Suggestion: {idx}/{total}   |   Fixed: {self.fixed_count}   |   Skipped: {self.skipped_count}"
        )

    # -----------------------------
    # HTML helpers + boundary highlight
    # -----------------------------
    def _escape_html(self, text: str) -> str:
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
        )

    def _highlight_boundary(self, prev: str, curr: str, n_words: int = 6):
        prev = prev.strip()
        curr = curr.strip()

        prev_words = prev.split()
        curr_words = curr.split()

        if not prev_words or not curr_words:
            return self._escape_html(prev), self._escape_html(curr)

        prev_head = " ".join(prev_words[:-n_words]) if len(prev_words) > n_words else ""
        prev_tail = " ".join(prev_words[-n_words:])

        curr_head = " ".join(curr_words[:n_words])
        curr_tail = " ".join(curr_words[n_words:]) if len(curr_words) > n_words else ""

        prev_html = ""
        if prev_head:
            prev_html += self._escape_html(prev_head) + " "
        prev_html += f'<span class="hl1">{self._escape_html(prev_tail)}</span>'

        curr_html = f'<span class="hl2">{self._escape_html(curr_head)}</span>'
        if curr_tail:
            curr_html += " " + self._escape_html(curr_tail)

        # Seam heuristic
        try:
            last_prev_token = prev_words[-1]
            first_curr_token = curr_words[0]
            looks_like_split_word = (
                (prev.endswith("-") or last_prev_token.isalpha())
                and first_curr_token[:1].islower()
            )
            if looks_like_split_word:
                prev_html = prev_html.replace(
                    self._escape_html(last_prev_token),
                    f'<span class="seam">{self._escape_html(last_prev_token)}</span>',
                    1
                )
                curr_html = curr_html.replace(
                    self._escape_html(first_curr_token),
                    f'<span class="seam">{self._escape_html(first_curr_token)}</span>',
                    1
                )
        except Exception:
            pass

        return prev_html, curr_html

    def _render_preview_html(self, suggestion_idx: int, total: int, para_id: int, prev: str, curr: str) -> str:
        prev_h, curr_h = self._highlight_boundary(prev, curr, n_words=self.boundary_words)

        return f"""
<style>
  .hl1 {{
    background: rgba(138, 169, 255, 0.18);
    border: 1px solid rgba(138, 169, 255, 0.35);
    padding: 2px 4px;
    border-radius: 6px;
  }}
  .hl2 {{
    background: rgba(255, 212, 121, 0.16);
    border: 1px solid rgba(255, 212, 121, 0.35);
    padding: 2px 4px;
    border-radius: 6px;
  }}
  .seam {{
    background: rgba(166, 227, 161, 0.20);
    border: 1px solid rgba(166, 227, 161, 0.45);
    padding: 1px 3px;
    border-radius: 6px;
    font-weight: 600;
  }}
</style>

<div style="font-family: Segoe UI, sans-serif; font-size: 11pt; color: #f5f5f5;">

  <div style="margin-bottom:12px; color:#cfcfcf;">
    <b>Suggestion {suggestion_idx}</b> of {total}
    <span style="color:#8aa9ff;"> (ID: {para_id})</span>
  </div>

  <div style="border:1px solid #333; border-radius:10px; padding:12px; background:#141414; margin-bottom:10px;">
    <div style="color:#8aa9ff; font-weight:600; margin-bottom:6px;">Original 1</div>
    <div style="line-height:1.4;">{prev_h}</div>
  </div>

  <div style="border:1px solid #333; border-radius:10px; padding:12px; background:#141414; margin-bottom:10px;">
    <div style="color:#ffd479; font-weight:600; margin-bottom:6px;">Original 2</div>
    <div style="line-height:1.4;">{curr_h}</div>
  </div>

  <div style="margin-top:6px; color:#a6e3a1; font-weight:600;">
    Proposed Merge <span style="color:#cfcfcf; font-weight:400;">(editable below)</span>
  </div>

</div>
"""

    # -----------------------------
    # Core logic
    # -----------------------------
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
            if not re.search(r'[.!?]["”\']?$|\)$', prev):
                if curr and curr[0].islower():
                    suggestions.append((i - 1, prev, curr))
        return suggestions

    def load_epub(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select EPUB File",
            "",
            "EPUB files (*.epub)",
        )
        if not file_path:
            return

        self.loaded_epub_path = file_path
        self.lbl_status.setText(f"Loaded: {os.path.basename(file_path)}")

        # reset counters
        self.fixed_count = 0
        self.skipped_count = 0

        self.cleanup_workspace()
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(self.extracted_path)

        self.paragraphs = []
        self.tag_map = []
        self.file_soups = {}
        self.applied_changes_log = []
        self.history_stack = []
        self.suggestions = []
        self.current_suggestion_index = 0

        for root_dir, _, files in os.walk(self.extracted_path):
            for file in files:
                if file.endswith(".xhtml") or file.endswith(".html"):
                    full_path = os.path.join(root_dir, file)
                    with open(full_path, encoding="utf-8") as f:
                        soup = BeautifulSoup(f, "html.parser")

                    self.file_soups[full_path] = soup
                    for tag in soup.find_all(True):
                        if tag.name in ["p", "div"] and tag.get_text(strip=True):
                            text = tag.get_text().strip()
                            self.paragraphs.append(text)
                            self.tag_map.append((full_path, tag))

        self.suggestions = self.detect_broken_sentences(self.paragraphs)
        self.current_suggestion_index = 0

        has_any = len(self.suggestions) > 0
        self.btn_skip.setEnabled(has_any)
        self.btn_fix.setEnabled(has_any)
        self.btn_back.setEnabled(False)
        self.btn_save.setEnabled(False)

        if not has_any:
            self.text_display.setHtml(
                "<div style='font-family: Segoe UI, sans-serif; font-size: 11pt; color:#f5f5f5;'>"
                "No suggestions found in this EPUB based on the current heuristic.</div>"
            )
            self.merge_edit.setPlainText("")
            self.merge_edit.setEnabled(False)
            self._update_status_bar()
            return

        self.display_next_suggestion()

    def display_next_suggestion(self):
        self.text_display.clear()
        self.merge_edit.clear()

        if not self.loaded_epub_path:
            self.text_display.setHtml(
                "<div style='font-family: Segoe UI, sans-serif; font-size: 11pt; color:#f5f5f5;'>"
                "Load an EPUB to begin.</div>"
            )
            self._update_status_bar()
            return

        # Keep merge editor active while working
        self.merge_edit.setEnabled(True)
        self.merge_edit.setReadOnly(False)

        if self.current_suggestion_index >= len(self.suggestions):
            self.text_display.setHtml(
                "<div style='font-family: Segoe UI, sans-serif; font-size: 11pt; color:#f5f5f5;'>"
                "✅ All suggestions processed.<br><br>"
                "Click <b>Save Fixed EPUB</b> to export the fixed book and a log file.</div>"
            )
            self.btn_fix.setEnabled(False)
            self.btn_skip.setEnabled(False)
            self.btn_back.setEnabled(len(self.history_stack) > 0)
            self.btn_save.setEnabled(True)

            self.merge_edit.setEnabled(False)
            self._update_status_bar()
            return

        total = len(self.suggestions)
        para_id, prev, curr = self.suggestions[self.current_suggestion_index]
        merged = f"{prev} {curr}"

        self.text_display.setHtml(
            self._render_preview_html(
                suggestion_idx=self.current_suggestion_index + 1,
                total=total,
                para_id=para_id,
                prev=prev,
                curr=curr,
            )
        )
        self.merge_edit.setPlainText(merged)

        self.btn_fix.setEnabled(True)
        self.btn_skip.setEnabled(True)
        self.btn_back.setEnabled(len(self.history_stack) > 0)
        self.btn_save.setEnabled(False)

        self._update_status_bar()

    def fix_current(self):
        if self.current_suggestion_index >= len(self.suggestions):
            return

        para_id, prev, curr = self.suggestions[self.current_suggestion_index]
        merged = self.merge_edit.toPlainText().strip()

        if not merged:
            QMessageBox.warning(self, "Empty merge", "Merged text is empty. Please edit it or click Skip.")
            return

        i = para_id

        self.history_stack.append(
            (self.current_suggestion_index, prev, curr, self.paragraphs[i], self.paragraphs[i + 1])
        )

        self.paragraphs[i] = merged
        self.paragraphs[i + 1] = ""

        file_path, tag = self.tag_map[i]
        _, tag_next = self.tag_map[i + 1]

        tag.string = merged
        tag_next.extract()

        self.applied_changes_log.append(
            f"[{file_path}]\nOriginal 1: {prev}\nOriginal 2: {curr}\nMerged: {merged}\n"
        )

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(str(self.file_soups[file_path]))

        self.fixed_count += 1
        self.current_suggestion_index += 1
        self.display_next_suggestion()

    def skip_current(self):
        self.history_stack.append((self.current_suggestion_index, None, None, None, None))
        self.skipped_count += 1
        self.current_suggestion_index += 1
        self.display_next_suggestion()

    def go_back(self):
        if not self.history_stack:
            return

        prev_index, prev, curr, old_p1, old_p2 = self.history_stack.pop()
        self.current_suggestion_index = prev_index

        # revert counters depending on last action
        if prev and curr:
            self.fixed_count = max(0, self.fixed_count - 1)
        else:
            self.skipped_count = max(0, self.skipped_count - 1)

        if prev and curr:
            para_id = self.suggestions[self.current_suggestion_index][0]
            i = para_id

            self.paragraphs[i] = old_p1
            self.paragraphs[i + 1] = old_p2

            file_path, tag = self.tag_map[i]
            _, tag_next = self.tag_map[i + 1]

            tag.string = old_p1
            new_tag = self.file_soups[file_path].new_tag(tag_next.name)
            new_tag.string = old_p2
            tag.insert_after(new_tag)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(str(self.file_soups[file_path]))

        self.display_next_suggestion()

    def save_fixed_epub(self):
        if not self.loaded_epub_path:
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Fixed EPUB",
            "",
            "EPUB files (*.epub)",
        )
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

        QMessageBox.information(
            self,
            "Success",
            f"Fixed EPUB saved to:\n{output_path}\n\nLog saved to:\n{log_path}",
        )


def main():
    app = QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)

    w = EPUBFixerWindow()
    w.show()
    app.exec()


if __name__ == "__main__":
    main()
