"""
Plotlyst
Copyright (C) 2021-2024  Zsolt Kovari

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
from enum import Enum
from functools import partial
from typing import Optional, Dict, List

import qtanim
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QMimeData, QPointF, QEvent
from PyQt6.QtGui import QFont, QResizeEvent, QMouseEvent, QColor, QIcon, QImage, \
    QShowEvent, QPixmap, QCursor, QEnterEvent
from PyQt6.QtWidgets import QWidget, QSplitter, QLineEdit, QDialog, QGridLayout, QSlider, QToolButton, QButtonGroup, \
    QLabel, QToolTip, QSpacerItem, QSizePolicy, QTextEdit
from overrides import overrides
from qthandy import vspacer, clear_layout, vbox, margins, hbox, sp, retain_when_hidden, decr_icon, pointy, \
    grid, flow, spacer, line, gc, translucent, incr_font, vline, bold
from qthandy.filter import OpacityEventFilter, VisibilityToggleEventFilter, DisabledClickEventFilter, DragEventFilter, \
    DropEventFilter
from qtmenu import MenuWidget, ActionTooltipDisplayMode
from qttextedit.ops import Heading3Operation, InsertListOperation, InsertNumberedListOperation, \
    InsertDividerOperation

from plotlyst.core.domain import Novel, WorldBuildingEntity, WorldBuildingEntityElement, WorldBuildingEntityElementType, \
    BackstoryEvent, Variable, VariableType, \
    Topic, Location, WorldConceitType, WorldConceit
from plotlyst.env import app_env
from plotlyst.service.image import upload_image, load_image
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import action, push_btn, frame, insert_before_the_end, fade_out_and_gc, \
    tool_btn, label, wrap, calculate_resized_dimensions, fade_in
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.style.text import apply_text_color
from plotlyst.view.widget.button import DotsMenuButton
from plotlyst.view.widget.display import Icon, PopupDialog, DotsDragIcon
from plotlyst.view.widget.input import AutoAdjustableTextEdit, AutoAdjustableLineEdit, MarkdownPopupTextEditorToolbar
from plotlyst.view.widget.timeline import TimelineWidget, BackstoryCard, TimelineTheme
from plotlyst.view.widget.topic import TopicSelectionDialog
from plotlyst.view.widget.utility import IconSelectorDialog, ColorSelectorButton
from plotlyst.view.widget.world._topics import ecological_topics, cultural_topics, historical_topics, \
    linguistic_topics, technological_topics, economic_topics, infrastructural_topics, religious_topics, \
    fantastic_topics, nefarious_topics, environmental_topics, ecology_topic, culture_topic, history_topic, \
    language_topic, technology_topic, economy_topic, infrastructure_topic, religion_topic, fantasy_topic, \
    villainy_topic, environment_topic, magic_topics, magic_topic
from plotlyst.view.widget.world.conceit import ConceitsTreeView, ConceitBubble
from plotlyst.view.widget.world.glossary import GlossaryTextBlockHighlighter, GlossaryTextBlockData
from plotlyst.view.widget.world.milieu import LocationsTreeView
from plotlyst.view.widget.world.theme import WorldBuildingPalette


class WorldBuildingTextEdit(AutoAdjustableTextEdit):
    def __init__(self, novel: Novel, palette: WorldBuildingPalette, parent=None):
        super().__init__(parent)
        self.setProperty('transparent', True)
        self.setCommandsEnabled(True)
        self.setAcceptRichText(True)
        self.setCommandOperations([Heading3Operation, InsertListOperation,
                                   InsertNumberedListOperation, InsertDividerOperation])
        self.setBlockPlaceholderEnabled(True)
        self.setAutoFormatting(QTextEdit.AutoFormattingFlag.AutoAll)

        self._glossaryHighlighter = GlossaryTextBlockHighlighter(novel.world.glossary, self.document(), palette)
        toolbar = MarkdownPopupTextEditorToolbar()
        toolbar.activate(self)
        self.setPopupWidget(toolbar)

    @overrides
    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.Type.ToolTip:
            cursor = self.cursorForPosition(event.pos())
            block = cursor.block()
            block_data: GlossaryTextBlockData = block.userData()

            if block_data:
                cursor_pos = cursor.positionInBlock()
                for ref in block_data.refs:
                    if ref.start <= cursor_pos <= ref.start + ref.length:
                        QToolTip.showText(event.globalPos(), ref.glossary.text)
                        return True

        return super().event(event)


class WorldBuildingEntityElementWidget(QWidget):
    removed = pyqtSignal()

    def __init__(self, novel: Novel, element: WorldBuildingEntityElement, parent=None,
                 cornerBtnEnabled: bool = True):
        super().__init__(parent)
        self.novel = novel
        self.element = element
        self._cornerBtnEnabled = cornerBtnEnabled and self.element.type not in [WorldBuildingEntityElementType.Section,
                                                                                WorldBuildingEntityElementType.Main_Section,
                                                                                WorldBuildingEntityElementType.Variables,
                                                                                WorldBuildingEntityElementType.Highlight]

        vbox(self, 0)
        if self._underSection():
            margins(self, left=15)

        self.btnAdd = tool_btn(IconRegistry.plus_icon('grey'), transparent_=True, tooltip='Insert new block')
        self.btnAdd.installEventFilter(OpacityEventFilter(self.btnAdd))
        decr_icon(self.btnAdd, 4)
        self.btnAdd.setHidden(True)
        retain_when_hidden(self.btnAdd)

        self.btnDrag = DotsDragIcon(self)
        self.btnDrag.setToolTip('''<html><b>Drag</b> to move<p/>
        <b>Click</b> to display menu
        ''')
        self.btnDrag.setHidden(True)

        self.btnMenu = DotsMenuButton(self)
        self.btnMenu.setHidden(True)
        self.menu = MenuWidget()
        self.actionRemove = action('Remove', IconRegistry.trash_can_icon(), slot=self.removed)
        self.menu.addAction(self.actionRemove)
        self.btnDrag.clicked.connect(lambda: self.menu.exec(QCursor.pos()))
        self.btnMenu.clicked.connect(lambda: self.menu.exec(QCursor.pos()))
        self._dotsMenuEnabled = self.element.type in [WorldBuildingEntityElementType.Variables,
                                                      WorldBuildingEntityElementType.Highlight]
        if self._dotsMenuEnabled:
            self.installEventFilter(VisibilityToggleEventFilter(self.btnMenu, self))

        self._btnCornerButtonOffsetY = 1
        self._btnCornerButtonOffsetX = 20

        sp(self).v_max()

    def save(self):
        RepositoryPersistenceManager.instance().update_world(self.novel)

    @overrides
    def enterEvent(self, event: QEnterEvent) -> None:
        if self._cornerBtnEnabled:
            fade_in(self.btnDrag)

    @overrides
    def leaveEvent(self, _: QEvent) -> None:
        self.btnDrag.setHidden(True)

    @overrides
    def resizeEvent(self, event: QResizeEvent) -> None:
        if self._cornerBtnEnabled:
            self.btnDrag.setGeometry(event.size().width() - self._btnCornerButtonOffsetX,
                                     self._btnCornerButtonOffsetY, 20, 20)
        if self._dotsMenuEnabled:
            self.btnMenu.setGeometry(event.size().width() - self._btnCornerButtonOffsetX, self._btnCornerButtonOffsetY,
                                     20, 20)

        super().resizeEvent(event)

    def activate(self):
        pass

    @staticmethod
    def newWidget(novel: Novel, element: WorldBuildingEntityElement, palette: WorldBuildingPalette,
                  parent: Optional[QWidget] = None,
                  editor: Optional['WorldBuildingEntityEditor'] = None) -> 'WorldBuildingEntityElementWidget':
        if element.type == WorldBuildingEntityElementType.Text:
            return TextElementEditor(novel, element, palette, parent)
        elif element.type == WorldBuildingEntityElementType.Section:
            return SectionElementEditor(novel, element, palette, parent, editor)
        elif element.type == WorldBuildingEntityElementType.Main_Section:
            return MainSectionElementEditor(novel, element, palette, parent, editor)
        elif element.type == WorldBuildingEntityElementType.Header:
            return HeaderElementEditor(novel, element, palette, parent)
        elif element.type == WorldBuildingEntityElementType.Quote:
            return QuoteElementEditor(novel, element, palette, parent)
        elif element.type == WorldBuildingEntityElementType.Image:
            return ImageElementEditor(novel, element, palette, parent)
        elif element.type == WorldBuildingEntityElementType.Variables:
            return VariablesElementEditor(novel, element, palette, parent)
        elif element.type == WorldBuildingEntityElementType.Highlight:
            return HighlightedTextElementEditor(novel, element, palette, parent)
        elif element.type == WorldBuildingEntityElementType.Timeline:
            return TimelineElementEditor(novel, element, palette, parent)
        elif element.type == WorldBuildingEntityElementType.Conceits:
            return ConceitsElementEditor(novel, element, palette, parent)
        else:
            raise ValueError(f'Unsupported WorldBuildingEntityElement type {element.type}')

    def _underSection(self) -> bool:
        if self.element.type == WorldBuildingEntityElementType.Section or self.element.type == WorldBuildingEntityElementType.Header:
            return False
        return self.parent() and not isinstance(
            self.parent(), (MainSectionElementEditor, WorldBuildingEntityEditor))


class TextElementEditor(WorldBuildingEntityElementWidget):
    def __init__(self, novel: Novel, element: WorldBuildingEntityElement, palette: WorldBuildingPalette, parent=None):
        super().__init__(novel, element, parent)
        self._palette = palette
        self._capitalizedChecked = False
        self._isProcessingTextChanged = False

        self.textEdit = WorldBuildingTextEdit(novel, self._palette)
        if self._underSection():
            margins(self, left=0)
            self.textEdit.setViewportMargins(20, 0, 0, 0)

        font = self.textEdit.font()
        if app_env.is_mac():
            self._fontPointSize = 18
        else:
            self._fontPointSize = 16
        font.setPointSize(self._fontPointSize)
        font.setFamily(app_env.sans_serif_font())
        self.textEdit.setFont(font)

        self.textEdit.textChanged.connect(self._textChanged)
        self.textEdit.setMarkdown(element.text)
        self.textEdit.setBlockFormat(margin_bottom=10, margin_top=10)

        self.layout().addWidget(self.textEdit)
        self.layout().addWidget(self.btnAdd, alignment=Qt.AlignmentFlag.AlignCenter)
        self.installEventFilter(VisibilityToggleEventFilter(self.btnAdd, self))
        self.btnDrag.raise_()

    def _textChanged(self):
        self.element.text = self.textEdit.toMarkdown()
        self.save()

        # if self._isProcessingTextChanged:
        #     return
        # self._isProcessingTextChanged = True
        #
        # cursor = QTextCursor(self.textEdit.document())
        # text = self.textEdit.toPlainText()
        # if not text or len(text) == 1:
        #     self._capitalizedChecked = False
        #     self._isProcessingTextChanged = False
        #     return
        #
        # cursor.movePosition(QTextCursor.MoveOperation.Start)
        # cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
        #
        # if cursor.block().textList():
        #     self._capitalizedChecked = True
        #     self._isProcessingTextChanged = False
        #     return
        # if cursor.blockFormat().headingLevel() > 0:
        #     self._capitalizedChecked = True
        #     self._isProcessingTextChanged = False
        #     return
        #
        # if self.textEdit.textCursor().position() == 1 and self._capitalizedChecked:
        #     print('pos 1 and cap checked already')
        #     self._capitalizedChecked = False
        #     format_normal = QTextCharFormat()
        #     format_normal.setFontPointSize(self._fontPointSize)
        #     resetCursor = QTextCursor(self.textEdit.document())
        #     resetCursor.select(QTextCursor.SelectionType.Document)
        #     resetCursor.mergeCharFormat(format_normal)
        # elif self.textEdit.textCursor().position() == 2 and self._capitalizedChecked:
        #     print('reset at pos 2')
        #     resetCursor = self.textEdit.textCursor()
        #     select_previous_character(resetCursor)
        #     format_normal = QTextCharFormat()
        #     format_normal.setFontPointSize(self._fontPointSize)
        #     resetCursor.mergeCharFormat(format_normal)
        #
        # if self._capitalizedChecked:
        #     self._isProcessingTextChanged = False
        #     return
        #
        # if not self._capitalizedChecked and cursor.hasSelection():
        #     print('capitalize')
        #     self._capitalizedChecked = True
        #     format_first_letter = QTextCharFormat()
        #     format_first_letter.setFontPointSize(32)
        #     cursor.setCharFormat(format_first_letter)
        #
        # self._isProcessingTextChanged = False


class HeaderElementEditor(WorldBuildingEntityElementWidget):
    def __init__(self, novel: Novel, element: WorldBuildingEntityElement, palette: WorldBuildingPalette, parent=None):
        super().__init__(novel, element, parent,
                         cornerBtnEnabled=False if isinstance(parent, MainSectionElementEditor) else True)
        self._palette = palette

        if isinstance(parent, MainSectionElementEditor):
            self.layout().setSpacing(0)

        self.icon = Icon()
        self.icon.setIconSize(QSize(32, 32))
        if self.element.icon:
            self.icon.setIcon(IconRegistry.from_name(self.element.icon, self._palette.primary_color))
        self.lineTitle = AutoAdjustableLineEdit(defaultWidth=50)
        self.lineTitle.setProperty('transparent', True)
        self.lineTitle.setPlaceholderText('New section')
        font = self.lineTitle.font()
        font.setPointSize(24)
        font.setFamily(app_env.serif_font())
        self.lineTitle.setFont(font)

        apply_text_color(self.lineTitle, QColor(self._palette.primary_color))
        self.lineTitle.setText(self.element.title)
        self.lineTitle.textEdited.connect(self._titleEdited)

        self.frame = frame()
        vbox(self.frame).addWidget(group(spacer(), self.icon, self.lineTitle, spacer(), margin=0, spacing=0))
        self.layout().addWidget(self.frame)
        self.frame.setStyleSheet(f'''
        .QFrame {{
            border-top: 1px outset {self._palette.primary_color};
            border-bottom: 1px outset {self._palette.primary_color};
            border-radius: 6px;
            background: {self._palette.secondary_color};
        }}''')

        self.layout().addWidget(self.btnAdd, alignment=Qt.AlignmentFlag.AlignCenter)
        self.installEventFilter(VisibilityToggleEventFilter(self.btnAdd, self))

        self._btnCornerButtonOffsetY = 7

        self.menu.clear()
        self.menu.addAction(action('Change icon', IconRegistry.icons_icon(), self._changeIcon))
        self.menu.addSeparator()
        self.menu.addAction(self.actionRemove)

        self.btnDrag.raise_()

    def _titleEdited(self, title: str):
        self.element.title = title
        self.save()

    def _changeIcon(self):
        result = IconSelectorDialog.popup(pickColor=False)
        if result:
            self.icon.setIcon(IconRegistry.from_name(result[0], self._palette.primary_color))
            self.element.icon = result[0]
            self.save()


class QuoteElementEditor(WorldBuildingEntityElementWidget):
    def __init__(self, novel: Novel, element: WorldBuildingEntityElement, palette: WorldBuildingPalette, parent=None):
        super().__init__(novel, element, parent)
        self._palette = palette

        if self._underSection():
            margins(self, left=15, right=15, top=5, bottom=5)
        self.textEdit = AutoAdjustableTextEdit()
        self.textEdit.setStyleSheet(f'''
                border: 0px;
                background-color: rgba(0, 0, 0, 0);
                color: #343a40;
        ''')
        self.textEdit.setPlaceholderText('Edit quote')
        font: QFont = self.textEdit.font()
        font.setPointSize(16)
        font.setFamily(app_env.cursive_font())
        font.setItalic(True)
        self.textEdit.setFont(font)
        self.textEdit.setMarkdown(self.element.text)
        self.textEdit.textChanged.connect(self._quoteChanged)

        self.lineEditRef = AutoAdjustableLineEdit()
        self.lineEditRef.setFont(font)
        self.lineEditRef.setStyleSheet(f'''
                QLineEdit {{
                    border: 0px;
                    background-color: rgba(0, 0, 0, 0);
                    color: {self._palette.primary_color};
                }}''')
        self.lineEditRef.setPlaceholderText('Source')
        self.lineEditRef.setText(self.element.ref)
        self.lineEditRef.textEdited.connect(self._quoteRefEdited)
        self.wdgQuoteRef = QWidget()
        hbox(self.wdgQuoteRef, 2, 0)
        iconDash = Icon()
        iconDash.setIcon(IconRegistry.from_name('msc.dash', self._palette.primary_color, scale=2.0))
        self.wdgQuoteRef.layout().addWidget(iconDash)
        self.wdgQuoteRef.layout().addWidget(self.lineEditRef)

        self.frame = frame()
        vbox(self.frame, 5)
        margins(self.frame, left=20, right=15)
        self.frame.layout().addWidget(self.textEdit)
        self.frame.layout().addWidget(self.wdgQuoteRef, alignment=Qt.AlignmentFlag.AlignRight)
        self.layout().addWidget(self.frame)
        self.frame.setStyleSheet(f'''
                .QFrame {{
                    border-left: 3px outset {self._palette.primary_color};
                    border-radius: 2px;
                    background: {self._palette.tertiary_color};
                }}''')

        self.layout().addWidget(self.btnAdd, alignment=Qt.AlignmentFlag.AlignCenter)
        self.installEventFilter(VisibilityToggleEventFilter(self.btnAdd, self))

        self.btnDrag.raise_()

    def _quoteChanged(self):
        self.element.text = self.textEdit.toMarkdown()
        self.save()

    def _quoteRefEdited(self, text: str):
        self.element.ref = text
        self.save()


class ImageElementEditor(WorldBuildingEntityElementWidget):
    def __init__(self, novel: Novel, element: WorldBuildingEntityElement, palette: WorldBuildingPalette, parent=None):
        super().__init__(novel, element, parent)
        margins(self, left=10, right=10)
        self._palette = palette

        self.lblImage = QLabel('')
        self.lblImage.setScaledContents(True)
        self._image: Optional[QImage] = None
        if self.element.image_ref is None:
            self.lblImage.setPixmap(IconRegistry.image_icon(color='grey').pixmap(256, 256))
            pointy(self)
            self._opacityFilter = OpacityEventFilter(self)
            self.installEventFilter(self._opacityFilter)
        else:
            image = QImage(256, 256, QImage.Format.Format_RGB32)
            image.fill(Qt.GlobalColor.gray)
            self.lblImage.setPixmap(QPixmap.fromImage(image))

        self.layout().addWidget(self.lblImage, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.btnAdd, alignment=Qt.AlignmentFlag.AlignCenter)
        self.installEventFilter(VisibilityToggleEventFilter(self.btnAdd, self))

        self.btnDrag.raise_()

    @overrides
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.element.image_ref is None:
            self.lblImage.setPixmap(IconRegistry.image_icon(color='grey').pixmap(248, 248))

    @overrides
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self.element.image_ref is None:
            self.lblImage.setPixmap(IconRegistry.image_icon(color='grey').pixmap(256, 256))
            self._uploadImage()

    @overrides
    def resizeEvent(self, event: QResizeEvent) -> None:
        if self._image:
            w, h = calculate_resized_dimensions(self._image.width(), self._image.height(), self.parent().width() - 20)
            self.lblImage.setMinimumSize(int(w * 0.98), int(h * 0.98))
            self.lblImage.setMaximumSize(w, h)
        else:
            super().resizeEvent(event)

    @overrides
    def showEvent(self, a0: QShowEvent) -> None:
        if self.element.image_ref and self._image is None:
            self._image = load_image(self.novel, self.element.image_ref)
            self._setImage()

    def _uploadImage(self):
        loaded_image = upload_image(self.novel)
        if loaded_image:
            self.element.image_ref = loaded_image.ref
            self._image = loaded_image.image
            self._setImage()

            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.removeEventFilter(self._opacityFilter)
            translucent(self, 1.0)

            self.save()

    def _setImage(self):
        if self._image:
            w, h = calculate_resized_dimensions(self._image.width(), self._image.height(), self.parent().width() - 20)
            self.lblImage.setPixmap(
                QPixmap.fromImage(self._image).scaled(w, h,
                                                      Qt.AspectRatioMode.KeepAspectRatio,
                                                      Qt.TransformationMode.SmoothTransformation))


class VariableEditorDialog(PopupDialog):
    def __init__(self, variable: Optional[Variable] = None, parent=None):
        super().__init__(parent)
        self._variable: Optional[Variable] = variable

        self.lineKey = QLineEdit()
        self.lineKey.setProperty('white-bg', True)
        self.lineKey.setProperty('rounded', True)
        self.lineKey.setPlaceholderText('Key')
        self.lineKey.textChanged.connect(self._keyChanged)

        self.lineValue = QLineEdit()
        self.lineValue.setProperty('white-bg', True)
        self.lineValue.setProperty('rounded', True)
        self.lineValue.setPlaceholderText('Value')

        self.wdgTitle = QWidget()
        hbox(self.wdgTitle)
        self.wdgTitle.layout().addWidget(self.btnReset, alignment=Qt.AlignmentFlag.AlignRight)

        self.btnConfirm = push_btn(text='Confirm', properties=['confirm', 'positive'])
        self.btnConfirm.clicked.connect(self.accept)
        self.btnConfirm.setDisabled(True)
        self.btnConfirm.installEventFilter(
            DisabledClickEventFilter(self.btnConfirm, lambda: qtanim.shake(self.lineKey)))

        self.btnCancel = push_btn(text='Cancel', properties=['confirm', 'cancel'])
        self.btnCancel.clicked.connect(self.reject)

        if self._variable:
            self.lineKey.setText(self._variable.key)
            self.lineValue.setText(self._variable.value)

        self.frame.layout().addWidget(self.wdgTitle)
        self.frame.layout().addWidget(self.lineKey)
        self.frame.layout().addWidget(self.lineValue)
        self.frame.layout().addWidget(group(self.btnCancel, self.btnConfirm), alignment=Qt.AlignmentFlag.AlignRight)

    def display(self) -> Optional[Variable]:
        result = self.exec()

        if result == QDialog.DialogCode.Accepted:
            if self._variable is None:
                self._variable = Variable(self.lineKey.text(), VariableType.Text, '')
            self._variable.key = self.lineKey.text()
            self._variable.value = self.lineValue.text()

            return self._variable

    @classmethod
    def edit(cls, variable: Optional[Variable] = None) -> Optional[Variable]:
        return cls.popup(variable)

    def _keyChanged(self, key: str):
        self.btnConfirm.setEnabled(len(key) > 0)


class VariableWidget(QWidget):
    def __init__(self, variable: Variable, parent=None):
        super().__init__(parent)
        self.variable = variable
        vbox(self)
        self.lblKey = label(variable.key, bold=True)
        self.valueField = label(variable.value)
        self.layout().addWidget(self.lblKey, alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(self.valueField, alignment=Qt.AlignmentFlag.AlignLeft)

        self.installEventFilter(OpacityEventFilter(self, 0.7, 1.0))
        pointy(self)

    @overrides
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self.edit()

    def edit(self):
        edited = VariableEditorDialog.edit(self.variable)
        if edited:
            self.lblKey.setText(self.variable.key)
            self.valueField.setText(self.variable.value)


class VariablesElementEditor(WorldBuildingEntityElementWidget):
    def __init__(self, novel: Novel, element: WorldBuildingEntityElement, palette: WorldBuildingPalette, parent=None):
        super().__init__(novel, element, parent)
        margins(self, right=15)
        self._palette = palette

        self._btnCornerButtonOffsetY = 7

        self.frame = frame()
        vbox(self.frame, 10)
        self.frame.setStyleSheet(f'''
        .QFrame {{
            border: 1px outset {self._palette.primary_color};
            border-radius: 6px;
            background: {self._palette.secondary_color};
        }}
        ''')

        self.btnAdd = tool_btn(IconRegistry.plus_icon('grey'), transparent_=True)
        self.btnAdd.installEventFilter(OpacityEventFilter(self.btnAdd, enterOpacity=0.8))
        self.btnAdd.clicked.connect(self._addNew)
        self._variables: Dict[Variable, VariableWidget] = {}
        for variable in self.element.variables:
            wdg = VariableWidget(variable)
            self._variables[variable] = wdg
            self.frame.layout().addWidget(wdg)

        self.frame.layout().addWidget(self.btnAdd)

        self.layout().addWidget(self.frame)

        self.btnMenu.raise_()
        self.menu.aboutToShow.connect(self._fillMenu)

    def _addNew(self):
        variable = VariableEditorDialog.edit()
        if variable:
            self.element.variables.append(variable)
            wdg = VariableWidget(variable)
            self._variables[variable] = wdg
            insert_before_the_end(self.frame, wdg)
            qtanim.fade_in(wdg, teardown=lambda: wdg.setGraphicsEffect(None))
            self.save()

    def _edit(self, variable: Variable):
        self._variables[variable].edit()

    def _remove(self, variable: Variable):
        if self.menu.isVisible():
            self.menu.close()
        wdg = self._variables.pop(variable)
        fade_out_and_gc(self.frame, wdg)
        self.element.variables.remove(variable)
        self.save()

    def _fillMenu(self):
        self.menu.clear()
        wdg = QWidget()
        grid_layout: QGridLayout = grid(wdg)
        for i, variable in enumerate(self.element.variables):
            grid_layout.addWidget(label(variable.key), i, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignLeft)

            edit_btn = tool_btn(IconRegistry.edit_icon(), tooltip=f'Edit {variable.key}', transparent_=True)
            edit_btn.clicked.connect(partial(self._edit, variable))
            grid_layout.addWidget(edit_btn, i, 2)

            remove_btn = tool_btn(IconRegistry.trash_can_icon(), transparent_=True, tooltip=f'Remove {variable.key}')
            remove_btn.clicked.connect(partial(self._remove, variable))
            grid_layout.addWidget(remove_btn, i, 3)
        self.menu.addWidget(wdg)
        self.menu.addSeparator()
        self.menu.addAction(action('Remove all variables', IconRegistry.trash_can_icon(), slot=self.removed))


class HighlightedTextElementEditor(WorldBuildingEntityElementWidget):
    def __init__(self, novel: Novel, element: WorldBuildingEntityElement, palette: WorldBuildingPalette, parent=None):
        super().__init__(novel, element, parent)
        margins(self, right=15)
        self._palette = palette

        self.frame = frame()
        sp(self.frame).v_max()
        self.frame.setStyleSheet(f'''
                        .QFrame {{
                            border: 1px outset {self._palette.primary_color};
                            border-left: 3px outset {self._palette.primary_color};
                            border-radius: 4px;
                            background: {self._palette.tertiary_color};
                        }}''')

        self.textEdit = WorldBuildingTextEdit(novel, self._palette)
        font: QFont = self.textEdit.font()
        font.setPointSize(14)
        self.textEdit.setFont(font)
        self.textEdit.setBlockPlaceholderEnabled(False)
        self.textEdit.setPlaceholderText('Begin writing...')
        self.textEdit.setMarkdown(self.element.text)
        self.textEdit.textChanged.connect(self._textChanged)
        vbox(self.frame, 10).addWidget(self.textEdit)

        self.layout().addWidget(self.frame)
        self.btnDrag.raise_()

    @overrides
    def activate(self):
        self.textEdit.setFocus()

    def _textChanged(self):
        self.element.text = self.textEdit.toMarkdown()
        self.save()


class EntityTimelineCard(BackstoryCard):
    def __init__(self, backstory: BackstoryEvent, parent=None):
        super().__init__(backstory, parent)
        self.refresh()

        self.setMinimumWidth(250)
        self.setMaximumWidth(450)


class EntityTimelineWidget(TimelineWidget):
    def __init__(self, element: WorldBuildingEntityElement, palette: WorldBuildingPalette, parent=None):
        super().__init__(TimelineTheme(timeline_color=palette.primary_color, card_bg_color=palette.tertiary_color),
                         parent=parent)
        self.element = element
        self.refresh()

    @overrides
    def events(self) -> List[BackstoryEvent]:
        return self.element.events

    @overrides
    def cardClass(self):
        return EntityTimelineCard


class TimelineElementEditor(WorldBuildingEntityElementWidget):
    def __init__(self, novel: Novel, element: WorldBuildingEntityElement, palette: WorldBuildingPalette, parent=None):
        super().__init__(novel, element, parent)
        self._palette = palette

        self.timeline = EntityTimelineWidget(element, self._palette)
        self.layout().addWidget(self.timeline)
        self.timeline.changed.connect(self.save)

        self.layout().addWidget(self.btnAdd, alignment=Qt.AlignmentFlag.AlignCenter)
        self.installEventFilter(VisibilityToggleEventFilter(self.btnAdd, self))

        self.btnDrag.raise_()


class ConceitsElementEditor(WorldBuildingEntityElementWidget):
    def __init__(self, novel: Novel, element: WorldBuildingEntityElement, palette: WorldBuildingPalette, parent=None):
        super().__init__(novel, element, parent)
        self._palette = palette

        self._wdgToolbar = QWidget()
        hbox(self._wdgToolbar)
        self._wdgEditor = frame(self)
        vbox(self._wdgEditor)
        self._splitter = QSplitter(self._wdgEditor)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.setHandleWidth(10)
        self._splitter.setProperty('framed', True)
        self._splitter.setSizes([100, 500])
        self._wdgEditor.layout().addWidget(self._splitter)

        self._wdgTree = ConceitsTreeView(novel, self._palette)
        self._wdgTree.rootSelected.connect(self.refresh)
        self._wdgTree.conceitSelected.connect(self._conceitSelected)
        self._wdgTree.conceitTypeSelected.connect(self._conceitTypeSelected)
        self._wdgTree.conceitDeleted.connect(self._conceitNodeDeleted)
        self._wdgDisplay = QWidget()
        flow(self._wdgDisplay, 10, 8)
        self._splitter.addWidget(self._wdgTree)
        self._splitter.addWidget(self._wdgDisplay)

        self._btnToggleTree = tool_btn(IconRegistry.from_name('mdi.file-tree-outline', self._palette.primary_color),
                                       transparent_=True,
                                       checkable=True)
        self._btnToggleTree.installEventFilter(
            OpacityEventFilter(self._btnToggleTree, enterOpacity=0.6, ignoreCheckedButton=True))
        self._btnToggleTree.clicked.connect(lambda x: qtanim.toggle_expansion(self._wdgTree, x))
        self._btnAddConceit = tool_btn(IconRegistry.plus_icon(self._palette.primary_color), tooltip='Add conceit',
                                       transparent_=True)
        self._btnAddConceit.clicked.connect(self._showMenu)
        self._btnTitle = push_btn(text='Fantasy conceits', pointy_=False, icon_resize=False)
        self._btnTitle.setStyleSheet(
            f'color: #343a40; background-color: rgba(0, 0, 0, 0); border: 0px;font-family: {app_env.serif_font()};')
        bold(self._btnTitle)

        self._wdgToolbar.layout().addWidget(self._btnToggleTree)
        self._wdgToolbar.layout().addWidget(vline())
        self._wdgToolbar.layout().addWidget(self._btnAddConceit)
        self._wdgToolbar.layout().addWidget(spacer())
        self._wdgToolbar.layout().addWidget(self._btnTitle)
        self._wdgToolbar.layout().addWidget(spacer())

        self.layout().addWidget(self._wdgToolbar)
        self.layout().addWidget(self._wdgEditor)

        self.layout().addWidget(self.btnAdd, alignment=Qt.AlignmentFlag.AlignCenter)
        self.installEventFilter(VisibilityToggleEventFilter(self.btnAdd, self))

        self._wdgToolbar.setStyleSheet(f'''
                        .QWidget {{
                            border: 0px;
                            background: {self._palette.secondary_color};
                        }}''')
        self._wdgEditor.setStyleSheet(f'''
                        .QFrame {{
                            border: 1px solid {self._palette.tertiary_color};
                            border-top-left-radius: 0px;
                            border-top-right-radius: 0px;
                            border-bottom-left-radius: 15px;
                            border-bottom-right-radius: 15px;
                        }}''')

        self.btnDrag.raise_()
        self._wdgTree.setVisible(self._btnToggleTree.isChecked())

        self.refresh()

    @overrides
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._wdgDisplay.updateGeometry()

    def refresh(self):
        clear_layout(self._wdgDisplay)
        for conceit in self.novel.world.conceits:
            bubble = self._initBubble(conceit)
            self._wdgDisplay.layout().addWidget(bubble)

    def _showMenu(self):
        menu = MenuWidget()
        for conceitType in WorldConceitType:
            action_ = action(conceitType.name, IconRegistry.from_name(conceitType.icon()),
                             slot=partial(self._addNewConceit, conceitType))
            incr_font(action_, 2)
            menu.addAction(action_)

        menu.exec()

    def _addNewConceit(self, conceitType: WorldConceitType):
        conceit = WorldConceit('Conceit', type=conceitType)
        bubble = self._initBubble(conceit)
        self._wdgDisplay.layout().addWidget(bubble)
        fade_in(bubble)

        self.novel.world.conceits.append(conceit)
        self.save()
        self._wdgTree.refresh()

    def _initBubble(self, conceit: WorldConceit) -> ConceitBubble:
        bubble = ConceitBubble(conceit, self._palette)
        bubble.nameEdited.connect(partial(self._conceitChanged, conceit))
        bubble.iconChanged.connect(partial(self._conceitChanged, conceit))
        bubble.textChanged.connect(self.save)
        bubble.removed.connect(partial(self._conceitRemoved, bubble))
        return bubble

    def _conceitChanged(self, conceit: WorldConceit):
        self._wdgTree.updateItem(conceit)
        self.save()

    def _conceitRemoved(self, bubble: ConceitBubble):
        self.novel.world.conceits.remove(bubble.conceit)
        fade_out_and_gc(self._wdgDisplay, bubble)

        self._wdgTree.refresh()
        self.save()

    def _conceitSelected(self, conceit: WorldConceit):
        clear_layout(self._wdgDisplay)

        bubble = self._initBubble(conceit)
        self._wdgDisplay.layout().addWidget(bubble)
        self._wdgDisplay.layout().addItem(QSpacerItem(0, 5, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum))
        if conceit.children:
            lbl = label('Subtypes', underline=True)
            self._wdgDisplay.layout().addWidget(lbl)
            self._wdgDisplay.layout().addItem(
                QSpacerItem(0, 5, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum))

        for conceit in conceit.children:
            bubble = self._initBubble(conceit)
            self._wdgDisplay.layout().addWidget(bubble)

    def _conceitTypeSelected(self, conceitType: WorldConceitType):
        clear_layout(self._wdgDisplay)
        for conceit in self.novel.world.conceits:
            if conceit.type == conceitType:
                bubble = self._initBubble(conceit)
                self._wdgDisplay.layout().addWidget(bubble)

    def _conceitNodeDeleted(self, conceit: WorldConceit):
        for i in range(self._wdgDisplay.layout().count()):
            wdg = self._wdgDisplay.layout().itemAt(i).widget()
            if wdg and isinstance(wdg, ConceitBubble):
                if wdg.conceit == conceit:
                    fade_out_and_gc(self._wdgDisplay, wdg)
                    return


class SectionElementEditor(WorldBuildingEntityElementWidget):
    WORLD_BLOCK_MIMETYPE = 'application/world-block'
    WORLD_SECTION_MIMETYPE = 'application/world-section'
    removed = pyqtSignal()

    def __init__(self, novel: Novel, element: WorldBuildingEntityElement, palette: WorldBuildingPalette, parent,
                 editor: 'WorldBuildingEntityEditor'):
        super().__init__(novel, element, parent, cornerBtnEnabled=False)
        self._editor = editor
        self._palette = palette
        for element in self.element.blocks:
            wdg = self.__initBlockWidget(element)
            self.layout().addWidget(wdg)

        self.setAcceptDrops(True)
        self.installEventFilter(
            DropEventFilter(self, [self.WORLD_SECTION_MIMETYPE],
                            motionDetection=Qt.Orientation.Vertical,
                            motionSlot=partial(self.editor().dragMoved, self),
                            droppedSlot=self.editor().drop
                            ))

    def editor(self) -> 'WorldBuildingEntityEditor':
        return self._editor

    def insertElement(self, i: int, element: WorldBuildingEntityElement):
        wdg = self.__initBlockWidget(element)
        self.layout().insertWidget(i, wdg)

    def _addClicked(self, wdg: WorldBuildingEntityElementWidget):
        menu = MainBlockAdditionMenu()
        menu.newBlockSelected.connect(partial(self._addBlock, wdg))
        menu.exec(QCursor.pos())

    def _addBlock(self, wdg: WorldBuildingEntityElementWidget, type_: WorldBuildingEntityElementType):
        element = WorldBuildingEntityElement(type_)
        newBlockWdg = self.__initBlockWidget(element)

        index = self.element.blocks.index(wdg.element)
        if index == len(self.element.blocks) - 1:
            self.element.blocks.append(element)
            self.layout().addWidget(newBlockWdg)
        else:
            self.element.blocks.insert(index + 1, element)
            self.layout().insertWidget(index + 1, newBlockWdg)
        qtanim.fade_in(newBlockWdg, teardown=lambda: newBlockWdg.setGraphicsEffect(None))

    def _removeBlock(self, widget: WorldBuildingEntityElementWidget):
        if isinstance(widget, HeaderElementEditor):
            self.removed.emit()
            return

        self.element.blocks.remove(widget.element)
        self.save()
        fade_out_and_gc(self, widget)

    def __initBlockWidget(self, element: WorldBuildingEntityElement) -> WorldBuildingEntityElementWidget:
        wdg = WorldBuildingEntityElementWidget.newWidget(self.novel, element, self._palette, self)
        wdg.btnAdd.clicked.connect(partial(self._addClicked, wdg))
        wdg.removed.connect(partial(self._removeBlock, wdg))

        mimeType = self.WORLD_SECTION_MIMETYPE if element.type == WorldBuildingEntityElementType.Header else self.WORLD_BLOCK_MIMETYPE

        wdg.btnDrag.installEventFilter(
            DragEventFilter(wdg, mimeType,
                            dataFunc=lambda x: wdg.element,
                            grabbed=wdg,
                            startedSlot=partial(self.editor().dragStarted, wdg),
                            finishedSlot=partial(self.editor().dragStopped, wdg)))
        wdg.setAcceptDrops(True)
        wdg.installEventFilter(
            DropEventFilter(wdg, [self.WORLD_BLOCK_MIMETYPE],
                            motionDetection=Qt.Orientation.Vertical,
                            motionSlot=partial(self.editor().dragMoved, wdg),
                            droppedSlot=self.editor().drop
                            )
        )

        return wdg


class MainSectionElementEditor(SectionElementEditor):
    def __init__(self, novel: Novel, element: WorldBuildingEntityElement, palette: WorldBuildingPalette, parent=None,
                 editor=None):
        super().__init__(novel, element, palette, parent, editor)
        self._palette = palette
        item = self.layout().itemAt(0)
        if item and item.widget():
            item.widget().frame.setHidden(True)


class SectionAdditionMenu(MenuWidget):
    newSectionSelected = pyqtSignal()
    topicSectionSelected = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.addAction(action('New section', IconRegistry.plus_icon('grey'), slot=self.newSectionSelected))
        self.addSeparator()
        self.addAction(
            action('Select topics...', IconRegistry.from_name('mdi.card-text-outline', 'grey'),
                   slot=self.topicSectionSelected))


class MainBlockAdditionMenu(MenuWidget):
    newBlockSelected = pyqtSignal(WorldBuildingEntityElementType)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.addAction(action('Text', IconRegistry.from_name('mdi.text'),
                              slot=lambda: self.newBlockSelected.emit(WorldBuildingEntityElementType.Text)))
        self.addAction(action('Quote', IconRegistry.from_name('ei.quote-right-alt'),
                              slot=lambda: self.newBlockSelected.emit(WorldBuildingEntityElementType.Quote)))
        self.addAction(action('Image', IconRegistry.image_icon(),
                              slot=lambda: self.newBlockSelected.emit(WorldBuildingEntityElementType.Image)))
        self.addAction(action('Timeline', IconRegistry.from_name('mdi.timeline'),
                              slot=lambda: self.newBlockSelected.emit(WorldBuildingEntityElementType.Timeline)))

        if app_env.is_plus():
            otherMenu = MenuWidget()
            otherMenu.setTooltipDisplayMode(ActionTooltipDisplayMode.DISPLAY_UNDER)
            tooltip = "Track fantasy elements that deviate from our world, introducing a sense of wonder into the story"
            otherMenu.addAction(action('Fantasy conceits', IconRegistry.from_name('ei.magic'), tooltip=tooltip,
                                       slot=lambda: self.newBlockSelected.emit(
                                           WorldBuildingEntityElementType.Conceits)))
            otherMenu.setTitle('Other')
            self.addSeparator()
            self.addMenu(otherMenu)


class SideBlockAdditionMenu(MenuWidget):
    newSideBlockSelected = pyqtSignal(WorldBuildingEntityElementType)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.addAction(action('Variables', IconRegistry.from_name('mdi.alpha-v-box-outline'),
                              slot=lambda: self.newSideBlockSelected.emit(WorldBuildingEntityElementType.Variables)))
        self.addAction(action('Highlighted text', IconRegistry.from_name('mdi6.card-text'),
                              slot=lambda: self.newSideBlockSelected.emit(WorldBuildingEntityElementType.Highlight)))


class WorldBuildingTopicSelectionDialog(TopicSelectionDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._title.setText('Common worldbuilding topics')

        self._addSection(ecology_topic, ecological_topics)
        self._addSection(culture_topic, cultural_topics)
        self._addSection(history_topic, historical_topics)
        self._addSection(language_topic, linguistic_topics)
        self._addSection(technology_topic, technological_topics)
        self._addSection(economy_topic, economic_topics)
        self._addSection(infrastructure_topic, infrastructural_topics)
        self._addSection(religion_topic, religious_topics)
        self._addSection(fantasy_topic, fantastic_topics)
        self._addSection(magic_topic, magic_topics)
        self._addSection(villainy_topic, nefarious_topics)
        self._addSection(environment_topic, environmental_topics)

        self._wdgCenter.layout().addWidget(vspacer())
        self.frame.layout().addWidget(group(self.btnCancel, self.btnSelect), alignment=Qt.AlignmentFlag.AlignRight)


class WorldBuildingEntityEditor(QWidget):
    WORLD_BLOCK_MIMETYPE = 'application/world-block'
    WORLD_SECTION_MIMETYPE = 'application/world-section'

    def __init__(self, novel: Novel, palette: WorldBuildingPalette, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._palette = palette
        self._entity: Optional[WorldBuildingEntity] = None

        self.wdgEditorMiddle = QWidget()
        vbox(self.wdgEditorMiddle, spacing=10)
        margins(self.wdgEditorMiddle, left=40, bottom=40)
        self.wdgEditorSide = QWidget()
        vbox(self.wdgEditorSide, 7, spacing=10)
        margins(self.wdgEditorSide, left=15, right=15)

        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self.wdgEditorMiddle)
        splitter.addWidget(self.wdgEditorSide)
        splitter.setSizes([500, 170])

        vbox(self, 0, 0).addWidget(splitter)

        self._placeholderWidget: Optional[QWidget] = None
        self._dragged: Optional[QWidget] = None
        self._toBeRemoved: Optional[QWidget] = None
        self._lastMovedWdg = None
        self._lastMovedDirection = None

        self.repo = RepositoryPersistenceManager.instance()

    def setEntity(self, entity: WorldBuildingEntity):
        self._entity = entity

        clear_layout(self.wdgEditorMiddle)
        clear_layout(self.wdgEditorSide)

        for element in self._entity.elements:
            self._addElement(element)

        for element in self._entity.side_elements:
            self._addElement(element, False)

        self._addPlaceholder()
        self._addPlaceholder(False)
        self.wdgEditorMiddle.layout().addWidget(vspacer())
        self.wdgEditorSide.layout().addWidget(vspacer())

        self.layoutChangedEvent()

    def layoutChangedEvent(self):
        self.wdgEditorSide.setVisible(self._entity.side_visible)
        margins(self.wdgEditorMiddle, right=2 if self._entity.side_visible else 40)

    def _addPlaceholder(self, middle: bool = True):
        wdg = push_btn(IconRegistry.plus_icon('grey'), 'Add section' if middle else 'Add block', transparent_=True)
        if middle:
            menu = SectionAdditionMenu(wdg)
            menu.newSectionSelected.connect(self._addNewSection)
            menu.topicSectionSelected.connect(self._selectNewTopic)
        else:
            menu = SideBlockAdditionMenu(wdg)
            menu.newSideBlockSelected.connect(self._addNewSideBlock)
        wdg.installEventFilter(OpacityEventFilter(wdg, enterOpacity=0.8))
        if middle:
            self.wdgEditorMiddle.layout().addWidget(wdg, alignment=Qt.AlignmentFlag.AlignLeft)
        else:
            self.wdgEditorSide.layout().addWidget(wdg, alignment=Qt.AlignmentFlag.AlignCenter)

    def _addElement(self, element: WorldBuildingEntityElement, middle: bool = True):
        wdg = self.__initElementWidget(element, middle, self._palette)

        if middle:
            self.wdgEditorMiddle.layout().addWidget(wdg)
        else:
            self.wdgEditorSide.layout().addWidget(wdg)

    def _addNewSection(self, topic: Optional[Topic] = None):
        header = WorldBuildingEntityElement(WorldBuildingEntityElementType.Header)
        element = WorldBuildingEntityElement(WorldBuildingEntityElementType.Section, blocks=[
            header,
            WorldBuildingEntityElement(WorldBuildingEntityElementType.Text)
        ])
        if topic:
            element.ref = topic.id
            element.title = topic.text
            header.title = topic.text
            header.icon = topic.icon
        wdg = self.__initElementWidget(element, True, self._palette)
        insert_before_the_end(self.wdgEditorMiddle, wdg, 2)
        qtanim.fade_in(wdg, teardown=lambda: wdg.setGraphicsEffect(None))

        self._entity.elements.append(element)
        self.repo.update_world(self._novel)

    def _selectNewTopic(self):
        topics = WorldBuildingTopicSelectionDialog.popup()
        if topics:
            for topic in topics:
                self._addNewSection(topic)

    def _removeSection(self, wdg: WorldBuildingEntityElementWidget):
        self._entity.elements.remove(wdg.element)
        fade_out_and_gc(self.wdgEditorMiddle, wdg)
        self.repo.update_world(self._novel)

    def _addNewSideBlock(self, type_: WorldBuildingEntityElementType):
        element = WorldBuildingEntityElement(type_)
        wdg = self.__initElementWidget(element, False, self._palette)

        insert_before_the_end(self.wdgEditorSide, wdg, 2)
        qtanim.fade_in(wdg, teardown=lambda: wdg.setGraphicsEffect(None))
        wdg.activate()

        self._entity.side_elements.append(element)
        self.repo.update_world(self._novel)

    def _removeSideBlock(self, wdg: WorldBuildingEntityElementWidget):
        self._entity.side_elements.remove(wdg.element)
        fade_out_and_gc(self.wdgEditorSide, wdg)
        self.repo.update_world(self._novel)

    def dragStarted(self, wdg: WorldBuildingEntityElementWidget):
        if isinstance(wdg, HeaderElementEditor):
            self._dragged = wdg.parent()
        else:
            self._dragged = wdg
        self._placeholderWidget = line(parent=self, color=self._palette.primary_color)
        self._placeholderWidget.setHidden(True)
        self._placeholderWidget.setAcceptDrops(True)
        self._placeholderWidget.installEventFilter(
            DropEventFilter(self._placeholderWidget, [self.WORLD_BLOCK_MIMETYPE, self.WORLD_SECTION_MIMETYPE],
                            droppedSlot=self.drop))
        if isinstance(wdg, HeaderElementEditor):
            wdg.parent().setHidden(True)
        else:
            wdg.setHidden(True)

    def dragStopped(self, wdg: WorldBuildingEntityElementWidget):
        if self._placeholderWidget:
            gc(self._placeholderWidget)
            self._placeholderWidget = None
        self._dragged = None

        if self._toBeRemoved:
            gc(self._toBeRemoved)
            self._toBeRemoved = None
        else:
            if isinstance(wdg, HeaderElementEditor):
                wdg.parent().setVisible(True)
            else:
                wdg.setVisible(True)

    def dragMoved(self, wdg: WorldBuildingEntityElementWidget, edge: Qt.Edge, point: QPointF):
        if wdg is self._lastMovedWdg and edge == self._lastMovedDirection:
            return

        if self._placeholderWidget.parent() is wdg.parent():
            wdg.parent().layout().removeWidget(self._placeholderWidget)
            self._placeholderWidget.setHidden(True)

        i = wdg.parent().layout().indexOf(wdg)
        if edge == Qt.Edge.TopEdge:
            if isinstance(wdg, (HeaderElementEditor, MainSectionElementEditor)):
                return
            wdg.parent().layout().insertWidget(i, self._placeholderWidget)
        else:
            wdg.parent().layout().insertWidget(i + 1, self._placeholderWidget)

        self._lastMovedWdg = wdg
        self._lastMovedDirection = edge
        qtanim.fade_in(self._placeholderWidget, 150)

    def drop(self, mimeData: QMimeData):
        if self._placeholderWidget.isHidden():
            return
        # ref: WorldBuildingEntityElement = mimeData.reference()

        new_index = self._placeholderWidget.parent().layout().indexOf(self._placeholderWidget)
        if isinstance(self._dragged, SectionElementEditor):
            self._dropSection(self._dragged.element, new_index)
        else:
            self._dropBlock(self._dragged.element, new_index)

        self._placeholderWidget.setHidden(True)
        self._toBeRemoved = self._dragged

        self.repo.update_world(self._novel)

    def _dropBlock(self, ref: WorldBuildingEntityElement, new_index: int):
        if self._dragged.parent() is self._placeholderWidget.parent():
            old_index = self._dragged.parent().layout().indexOf(self._dragged)
            self._dragged.parent().element.blocks.remove(ref)

            if old_index < new_index:
                self._placeholderWidget.parent().element.blocks.insert(new_index - 1, ref)
            else:
                self._placeholderWidget.parent().element.blocks.insert(new_index, ref)
        else:
            self._dragged.parent().element.blocks.remove(ref)
            self._placeholderWidget.parent().element.blocks.insert(new_index, ref)

        self._placeholderWidget.parent().insertElement(new_index, ref)

    def _dropSection(self, ref: WorldBuildingEntityElement, new_index: int):
        old_index = self.wdgEditorMiddle.layout().indexOf(self._dragged)
        self._entity.elements.remove(ref)

        if old_index < new_index:
            self._entity.elements.insert(new_index - 1, ref)
        else:
            self._entity.elements.insert(new_index, ref)

        wdg = self.__initElementWidget(ref, True, self._palette)
        self.wdgEditorMiddle.layout().insertWidget(new_index, wdg)

    def __initElementWidget(self, element: WorldBuildingEntityElement, middle: bool,
                            palette: WorldBuildingPalette) -> WorldBuildingEntityElementWidget:
        wdg = WorldBuildingEntityElementWidget.newWidget(self._novel, element, palette, self, editor=self)
        if middle and isinstance(wdg, SectionElementEditor):
            wdg.removed.connect(partial(self._removeSection, wdg))
        elif not middle:
            wdg.removed.connect(partial(self._removeSideBlock, wdg))

        return wdg


class EntityLayoutType(Enum):
    CENTER = 0
    SIDE = 1


class EntityLayoutSettings(QWidget):
    layoutChanged = pyqtSignal(EntityLayoutType)

    def __init__(self, parent=None):
        super().__init__(parent)
        hbox(self)

        self.btnCentral = self._btn(IconRegistry.from_name('ri.layout-top-fill'))
        self.btnCentral.setToolTip('Content is at the center')
        self.btnSide = self._btn(IconRegistry.from_name('ri.layout-fill'))
        self.btnSide.setToolTip('Content is also available on the side')
        self.layout().addWidget(spacer())
        self.layout().addWidget(self.btnCentral)
        self.layout().addWidget(self.btnSide)
        self.layout().addWidget(spacer())

        self.btnGroup = QButtonGroup()
        self.btnGroup.setExclusive(True)
        self.btnGroup.addButton(self.btnCentral)
        self.btnGroup.addButton(self.btnSide)
        self.btnGroup.buttonClicked.connect(self._clicked)

    def setEntity(self, entity: WorldBuildingEntity):
        if entity.side_visible:
            self.btnSide.setChecked(True)
        else:
            self.btnCentral.setChecked(True)

    def _clicked(self):
        if self.btnCentral.isChecked():
            self.layoutChanged.emit(EntityLayoutType.CENTER)
        elif self.btnSide.isChecked():
            self.layoutChanged.emit(EntityLayoutType.SIDE)

    def _btn(self, icon: QIcon) -> QToolButton:
        btn = tool_btn(icon, checkable=True)
        btn.installEventFilter(OpacityEventFilter(btn, ignoreCheckedButton=True))
        btn.setIconSize(QSize(32, 32))
        btn.setStyleSheet('''
                            QToolButton {
                                border: 1px hidden lightgrey;
                                padding: 8px;
                                border-radius: 25px;
                            }
                            QToolButton:hover:!checked {
                                background: #FCF5FE;
                            }
                            QToolButton:checked {
                                background: #D4B8E0;
                            }
                            ''')
        return btn


class PaletteSettings(QWidget):
    paletteChanged = pyqtSignal()

    def __init__(self, palette: WorldBuildingPalette, parent=None):
        super().__init__(parent)
        self.palette = palette
        flow(self)

        self.btnBgColor = ColorSelectorButton(self.palette.bg_color)
        self.btnBgColor.colorChanged.connect(self._updateBgColor)

        self.btnPrimaryColor = ColorSelectorButton(self.palette.primary_color)
        self.btnPrimaryColor.colorChanged.connect(self._updatePrimaryColor)

        self.btnSecondaryColor = ColorSelectorButton(self.palette.secondary_color)
        self.btnSecondaryColor.colorChanged.connect(self._updateSecondaryColor)

        self.btnTertiaryColor = ColorSelectorButton(self.palette.tertiary_color)
        self.btnTertiaryColor.colorChanged.connect(self._updateTertiaryColor)

        self.layout().addWidget(self.btnBgColor)
        self.layout().addWidget(self.btnPrimaryColor)
        self.layout().addWidget(self.btnSecondaryColor)
        self.layout().addWidget(self.btnTertiaryColor)

    def _updateBgColor(self, color: str):
        self.palette.bg_color = color
        self.paletteChanged.emit()

    def _updatePrimaryColor(self, color: str):
        self.palette.primary_color = color
        self.paletteChanged.emit()

    def _updateSecondaryColor(self, color: str):
        self.palette.secondary_color = color
        self.paletteChanged.emit()

    def _updateTertiaryColor(self, color: str):
        self.palette.tertiary_color = color
        self.paletteChanged.emit()


class WorldBuildingEditorSettingsWidget(QWidget):
    widthChanged = pyqtSignal(int)
    layoutChanged = pyqtSignal(EntityLayoutType)
    paletteChanged = pyqtSignal()

    def __init__(self, defaultWidth: int, palette: WorldBuildingPalette, parent=None):
        super().__init__(parent)
        self._palette = palette
        vbox(self)
        margins(self, top=15, left=5, right=15)
        self.layout().addWidget(label('Entity settings', bold=True, underline=True))
        self.layout().addWidget(wrap(label('Layout'), margin_left=5))
        self.layoutSettings = EntityLayoutSettings()
        self.layoutSettings.layoutChanged.connect(self.layoutChanged)
        self.layout().addWidget(self.layoutSettings)

        self.layout().addWidget(line())

        self.layout().addWidget(label('Global settings', bold=True, underline=True))
        self.layout().addWidget(wrap(label('Editor max width'), margin_left=5))
        self._widthSlider = QSlider(Qt.Orientation.Horizontal)
        self._widthSlider.setMinimum(800)
        self._widthSlider.setMaximum(1200)
        self._widthSlider.setValue(defaultWidth)
        self._widthSlider.valueChanged.connect(self.widthChanged)
        self.layout().addWidget(wrap(self._widthSlider, margin_left=15))

        # self.palette = PaletteSettings(self._palette)
        # self.palette.paletteChanged.connect(self.paletteChanged)
        # self.layout().addWidget(line())
        # self.layout().addWidget(self.palette)

        self.layout().addWidget(vspacer())

    def setEntity(self, entity: WorldBuildingEntity):
        self.layoutSettings.setEntity(entity)


class MilieuSelectorPopup(PopupDialog):
    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._selectedElement: Optional[Location] = None

        self.treeView = LocationsTreeView()
        self.treeView.locationSelected.connect(self._selected)
        self.treeView.setNovel(novel, readOnly=True)
        self.treeView.setMinimumSize(300, 400)
        self.treeView.setMaximumSize(500, 500)
        sp(self.treeView).v_exp().h_exp()

        self.btnSelect = push_btn(text='Select', properties=['confirm', 'positive'])
        self.btnSelect.clicked.connect(self.accept)
        self.btnClose = push_btn(text='Cancel', properties=['confirm', 'cancel'])
        self.btnClose.clicked.connect(self.reject)

        self.frame.layout().addWidget(self.btnReset, alignment=Qt.AlignmentFlag.AlignRight)
        self.frame.layout().addWidget(label('Select a location', h4=True), alignment=Qt.AlignmentFlag.AlignCenter)
        self.frame.layout().addWidget(self.treeView)
        self.frame.layout().addWidget(group(self.btnClose, self.btnSelect), alignment=Qt.AlignmentFlag.AlignRight)

    def display(self) -> Optional[Location]:
        result = self.exec()
        if result == QDialog.DialogCode.Accepted:
            return self._selectedElement

    def _selected(self, location: Location):
        self._selectedElement = location
