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
import os
import subprocess

import pypandoc
from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import QWidget
from jinja2 import Template
from overrides import overrides
from qthandy import hbox

from plotlyst.core.client import json_client
from plotlyst.core.domain import Novel
from plotlyst.env import app_env
from plotlyst.resources import resource_registry
from plotlyst.view._view import AbstractNovelView
from plotlyst.view.generated.formatting_view_ui import Ui_FormattingView
from plotlyst.view.widget.pdf import PdfView


def install_latex():
    parent_folder = os.path.join(os.path.expanduser('~'), '.cache', 'plotlyst')
    tinytex_dir = os.path.join(parent_folder, 'tinytex')
    os.makedirs(tinytex_dir, exist_ok=True)

    os.environ["TINYTEX_DIR"] = tinytex_dir

    install_script = "https://yihui.org/tinytex/install-bin-unix.sh"
    script_path = os.path.join(parent_folder, "install-bin-unix.sh")

    curl_command = ["curl", "-fsSL", install_script, "-o", script_path]
    subprocess.run(curl_command, check=True)

    install_command = ["sh", script_path]
    subprocess.run(install_command, check=True)

    packages = ['parskip', 'setspace', 'fancyhdr']
    for package in packages:
        subprocess.run([os.path.join(tinytex_dir, '.TinyTeX', 'bin', 'x86_64-linux', 'tlmgr'), 'install', package],
                       check=True)


class FormattingWidget(QWidget):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.novel = novel
        hbox(self, 10, 6)
        self._pdfView = PdfView()
        self._pdfView.setMaximumWidth(600)
        self.layout().addWidget(self._pdfView)

        with open(resource_registry.manuscript_template, "r", encoding="utf-8") as f:
            template_content = f.read()

        self._template = Template(template_content)
        self._novel_dir = os.path.join(app_env.cache_dir, str(self.novel.id))
        self._chapters_dir = os.path.join(self._novel_dir, 'chapters')
        os.makedirs(self._novel_dir, exist_ok=True)
        os.makedirs(self._chapters_dir, exist_ok=True)

        self._config = {
            "title": "The Picture of Dorian Gray",
            "author": "Oscar Wilde",
            "subtitle": "A novel about beauty, corruption, and consequence.",
            "font_size": "11pt",
            "line_spacing": "onehalf",
            "full_path": str(self._chapters_dir),
            "chapters": ["chapter1", "chapter2"]
        }
        self._output_tex_path = os.path.join(self._novel_dir, 'main.tex')

    @overrides
    def showEvent(self, event: QShowEvent) -> None:
        self._renderMain()
        self._generateChapters()
        self._generatePdf()

    def _renderMain(self):
        rendered_tex = self._template.render(self._config)
        with open(self._output_tex_path, "w", encoding="utf-8") as f:
            f.write(rendered_tex)

    def _generateChapters(self):
        json_client.load_manuscript(self.novel)
        if self.novel.prefs.is_scenes_organization():
            pass
        else:
            for i, scene in enumerate(self.novel.scenes):
                output = os.path.join(self._chapters_dir, f'chapter{i + 1}.tex')
                pypandoc.convert_text(scene.manuscript.content, to='latex', format='html', outputfile=output)

    def _generatePdf(self):
        subprocess.run(
            [os.path.join(app_env.cache_dir, 'tinytex/.TinyTeX/bin/x86_64-linux/pdflatex'), str(self._output_tex_path)])
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
