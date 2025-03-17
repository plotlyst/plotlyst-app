"""
Plotlyst
Copyright (C) 2021-2025  Zsolt Kovari

This file is part of Plotlyst.

Plotlyst is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Plotlyst is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import subprocess

from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import QWidget
from jinja2 import Template
from overrides import overrides
from qthandy import hbox

from plotlyst.core.domain import Novel
from plotlyst.resources import resource_registry
from plotlyst.view._view import AbstractNovelView
from plotlyst.view.generated.formatting_view_ui import Ui_FormattingView
from plotlyst.view.widget.pdf import PdfView


class FormattingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        hbox(self, 10, 6)
        self._pdfView = PdfView()
        self._pdfView.setMaximumWidth(600)
        self.layout().addWidget(self._pdfView)

        self._config = {
            "title": "The Picture of Dorian Gray",
            "author": "Oscar Wilde",
            "subtitle": "A novel about beauty, corruption, and consequence.",
            "font_size": "11pt",
            "line_spacing": "onehalf",
            "chapters": ["chapter1", "chapter2"]
        }

    @overrides
    def showEvent(self, event: QShowEvent) -> None:
        with open(resource_registry.manuscript_template, "r", encoding="utf-8") as f:
            template_content = f.read()

        template = Template(template_content)
        rendered_tex = template.render(self._config)

        # Write the generated content to main.tex
        with open("main.tex", "w", encoding="utf-8") as f:
            f.write(rendered_tex)

        subprocess.run(['pdflatex', 'main.tex'])
        self._pdfView.load('main.pdf')


class FormattingView(AbstractNovelView):
    DOWNLOAD_THRESHOLD_SECONDS = 60 * 60 * 8  # 8 hours in seconds

    def __init__(self, novel: Novel):
        super().__init__(novel)
        self.ui = Ui_FormattingView()
        self.ui.setupUi(self.widget)

        # self.wdgFormatting = FormattingWidget()
        # sp(self.wdgFormatting).v_exp().h_exp()
        # self.widget.layout().addWidget(self.wdgFormatting)
