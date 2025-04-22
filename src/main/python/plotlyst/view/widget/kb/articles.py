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
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QWidget
from overrides import overrides
from qthandy import vbox, incr_icon, vspacer, line

from plotlyst.env import app_env
from plotlyst.view.common import wrap
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.display import IconText
from plotlyst.view.widget.input import AutoAdjustableTextEdit


class AbstractArticleWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        vbox(self, 40)

        self.titlePointSize = 28
        self.titleIconSize = 38
        self.subheadingPointSize = 22 if app_env.is_mac() else 20
        if app_env.is_mac():
            self.textFontPointSize = 18
        elif app_env.is_linux():
            self.textFontPointSize = 14
        else:
            self.textFontPointSize = 16

        self.textFontFamily = app_env.sans_serif_font()

    def setTitle(self, name: str, icon: str = ''):
        title = IconText()
        title.setText(name)
        font = title.font()
        font.setPointSize(self.titlePointSize)
        title.setFont(font)
        if icon:
            title.setIcon(IconRegistry.from_name(icon))
            title.setIconSize(QSize(self.titleIconSize, self.titleIconSize))

        self.layout().addWidget(wrap(title, margin_bottom=35), alignment=Qt.AlignmentFlag.AlignCenter)

    def addSeparator(self):
        self.layout().addWidget(line())

    def addSubheading(self, heading: str, icon: str = ''):
        subheading = IconText()

        subheading.setText(heading)
        font = subheading.font()
        font.setPointSize(self.subheadingPointSize)
        subheading.setFont(font)
        if icon:
            subheading.setIcon(IconRegistry.from_name(icon))
            incr_icon(subheading, 2)

        self.layout().addWidget(wrap(subheading, margin_bottom=8, margin_top=8), alignment=Qt.AlignmentFlag.AlignLeft)

    def addText(self, text: str, textIndent: int = 20, marginLeft: int = 0):
        textedit = AutoAdjustableTextEdit()
        textedit.setProperty('transparent', True)
        textedit.setAcceptRichText(True)
        textedit.setReadOnly(True)

        font = textedit.font()
        font.setPointSize(self.textFontPointSize)
        font.setFamily(self.textFontFamily)
        textedit.setFont(font)

        textedit.setBlockFormat(lineSpacing=130, textIndent=textIndent, margin_bottom=10, margin_top=10,
                                margin_left=marginLeft)
        textedit.setMarkdown(text)
        textedit.applyBlockFormat()

        self.layout().addWidget(textedit)

    def finish(self):
        self.layout().addWidget(vspacer())


class PlotlystArticleWidget(AbstractArticleWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle('Plotlyst Knowledge Base')
        self.addText(
            '''Welcome to Plotlyst Knowledge Base! On this panel you will find different articles and reference guides about Plotlyst, writing, and storytelling.
            
Currently this panel is still work-in-progress but you can anticipate new articles in every new release.
            ''')
        self.finish()


class FAQArticleWidget(AbstractArticleWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setTitle('Frequently Asked Questions', 'ei.question')
        self.addSeparator()
        self.addSubheading("Where is all of my data stored?", 'fa5s.database')
        self.addText(
            '''Your library, including all your novels, characters, manuscripts, etc., are in a separate folder that you can find under the menu option `File > Project > Open in explorer`.

You can sync this folder through any 3rd party cloud service to have a backup.
You can also change this location under the same menu, `Change project directory`.''',
        )
        self.addSubheading("Is there any AI in the app?", 'mdi.robot-angry')
        self.addText(
            "No, there isn't, and I plan to keep it that way. An AI-based spellchecker could be an argument later on, but otherwise there won't be any AI support for writing.")
        self.finish()

    @overrides
    def addText(self, text: str):
        super().addText(text, textIndent=0, marginLeft=20)
