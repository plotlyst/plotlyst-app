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

from abc import abstractmethod
from functools import partial
from typing import Optional, Any

from PyQt6.QtCore import Qt, pyqtSignal, QRect
from PyQt6.QtGui import QPainter, QPen, QColor, QIcon, QPaintEvent, QKeySequence, QShowEvent, QFont, QUndoStack
from PyQt6.QtWidgets import QFrame, \
    QToolButton, QWidget, \
    QAbstractButton, QSlider, QButtonGroup, QPushButton, QLabel, QLineEdit
from overrides import overrides
from qthandy import hbox, margins, sp, vbox, grid, pointy, vline, decr_icon, transparent
from qtmenu import MenuWidget
from qttextedit.ops import Heading2Operation, Heading3Operation, Heading1Operation

from plotlyst.common import PLOTLYST_SECONDARY_COLOR
from plotlyst.core.domain import GraphicsItemType, NODE_SUBTYPE_DISTURBANCE, NODE_SUBTYPE_CONFLICT, \
    NODE_SUBTYPE_GOAL, NODE_SUBTYPE_BACKSTORY, \
    NODE_SUBTYPE_INTERNAL_CONFLICT
from plotlyst.view.common import shadow, tool_btn, ExclusiveOptionalButtonGroup
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.widget.graphics.commands import GraphicsItemCommand, TextEditingCommand, SizeEditingCommand, \
    NoteEditorCommand
from plotlyst.view.widget.graphics.items import EventItem, ConnectorItem, NoteItem, CharacterItem, IconItem
from plotlyst.view.widget.input import FontSizeSpinBox, AutoAdjustableLineEdit, AutoAdjustableTextEdit
from plotlyst.view.widget.utility import ColorPicker, IconSelectorDialog


class ZoomBar(QFrame):
    zoomed = pyqtSignal(float)
    reset = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setProperty('relaxed-white-bg', True)
        self.setProperty('rounded', True)

        shadow(self)
        hbox(self, 2, spacing=6)
        margins(self, left=10, right=10)

        self._btnZoomIn = tool_btn(IconRegistry.plus_circle_icon('lightgrey'), 'Zoom in', transparent_=True,
                                   parent=self)
        self._btnZoomIn.setShortcut(QKeySequence.StandardKey.ZoomIn)

        self._btnScaledFactor = QPushButton()
        self._btnScaledFactor.setStyleSheet('border: 0px; color: lightgrey;')
        # pointy(self._btnScaledFactor)
        # self._btnScaledFactor.installEventFilter(ButtonPressResizeEventFilter(self._btnScaledFactor))
        # self._btnScaledFactor.clicked.connect(self.reset.emit)
        self.updateScaledFactor(1.0)

        self._btnZoomOut = tool_btn(IconRegistry.minus_icon('lightgrey'), 'Zoom out', transparent_=True,
                                    parent=self)
        self._btnZoomOut.setShortcut(QKeySequence.StandardKey.ZoomOut)
        self._btnZoomIn.clicked.connect(lambda: self.zoomed.emit(0.1))
        self._btnZoomOut.clicked.connect(lambda: self.zoomed.emit(-0.1))

        self.layout().addWidget(self._btnZoomOut)
        self.layout().addWidget(self._btnScaledFactor)
        self.layout().addWidget(self._btnZoomIn)

    def updateScaledFactor(self, scale: float):
        self._btnScaledFactor.setText(f'{int(scale * 100)}%')


class SecondarySelectorWidget(QFrame):
    selected = pyqtSignal(GraphicsItemType, str)

    def __init__(self, parent=None, optional: bool = False):
        super().__init__(parent)
        self.setProperty('relaxed-white-bg', True)
        self.setProperty('rounded', True)
        shadow(self)
        self._grid = grid(self, h_spacing=5, v_spacing=3)
        margins(self, left=5, right=5)

        if optional:
            self._btnGroup = ExclusiveOptionalButtonGroup()
        else:
            self._btnGroup = QButtonGroup()

    def addWidget(self, widget: QWidget, row: int, col: int):
        self._grid.layout().addWidget(widget, row, col)

    def addButton(self, icon: QIcon, tooltip: str, row: int,
                  col: int) -> QToolButton:
        btn = tool_btn(icon, tooltip,
                       True, icon_resize=False,
                       properties=['transparent-rounded-bg-on-hover', 'top-selector'],
                       parent=self)
        self._btnGroup.addButton(btn)
        self._grid.layout().addWidget(btn, row, col)

        return btn

    def addItemTypeButton(self, itemType: GraphicsItemType, icon: QIcon, tooltip: str, row: int,
                          col: int, subType: str = '') -> QToolButton:
        def clicked(toggled: bool):
            if toggled:
                self.selected.emit(itemType, subType)

        btn = self.addButton(icon, tooltip, row, col)
        btn.clicked.connect(clicked)

        return btn


class BaseItemToolbar(QWidget):
    def __init__(self, undoStack: QUndoStack, parent=None):
        super().__init__(parent)
        self.undoStack = undoStack
        vbox(self, spacing=5)
        self._toolbar = QFrame(self)
        self._toolbar.setProperty('relaxed-white-bg', True)
        self._toolbar.setProperty('rounded', True)
        shadow(self._toolbar)

        hbox(self._toolbar, 5, spacing=6)
        self.layout().addWidget(self._toolbar)

        self._secondaryWidgets = []

    def addSecondaryWidget(self, btn: QAbstractButton, widget: QWidget, alignment=Qt.AlignmentFlag.AlignLeft):
        self._secondaryWidgets.append(widget)
        sp(widget).h_max()
        self.layout().addWidget(widget, alignment)
        btn.clicked.connect(partial(self._toggleSecondarySelector, widget))
        widget.setVisible(False)

    def _toggleSecondarySelector(self, secondary: QWidget):
        secondary.setVisible(not secondary.isVisible())
        if secondary.isVisible():
            self.setFixedHeight(self._toolbar.sizeHint().height() + secondary.sizeHint().height())
        else:
            self.setFixedHeight(self._toolbar.sizeHint().height())

    def _hideSecondarySelectors(self):
        for wdg in self._secondaryWidgets:
            wdg.setVisible(False)
        self.setFixedHeight(self._toolbar.sizeHint().height())


class TextLineEditorPopup(MenuWidget):

    def __init__(self, text: str, rect: QRect, parent=None, placeholder: str = 'Event'):
        super().__init__(parent)
        transparent(self)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._lineEdit = AutoAdjustableLineEdit(defaultWidth=rect.width())
        self._lineEdit.setPlaceholderText(placeholder)
        self._lineEdit.setText(text)
        self.addWidget(self._lineEdit)

        self._lineEdit.editingFinished.connect(self.hide)

    @overrides
    def showEvent(self, QShowEvent):
        self._lineEdit.setFocus()

    @overrides
    def setFont(self, font: QFont):
        self._lineEdit.setFont(font)

    def text(self) -> str:
        return self._lineEdit.text()


class TextNoteEditorPopup(MenuWidget):

    def __init__(self, undoStack: QUndoStack, item: NoteItem, parent=None, placeholder: str = 'Begin typing'):
        super().__init__(parent)
        self.undoStack = undoStack
        self._item = item
        transparent(self)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._textEdit = AutoAdjustableTextEdit()
        self._textEdit.setProperty('white-bg', True)
        self._textEdit.setProperty('rounded', True)
        self._textEdit.setAcceptRichText(True)
        self._textEdit.setCommandsEnabled(True)
        self._textEdit.setCommandOperations([Heading1Operation, Heading2Operation, Heading3Operation])
        self._textEdit.setFixedWidth(item.textRect().width())
        self._textEdit.setPlaceholderText(placeholder)
        self._textEdit.setMarkdown(item.text())
        self._textEdit.textChanged.connect(self._textChanged)
        self._textEdit.resizedOnShow.connect(self._resized)

        self.addWidget(self._textEdit)

    @overrides
    def setFont(self, font: QFont):
        self._textEdit.setFont(font)

    @overrides
    def showEvent(self, QShowEvent):
        self._textEdit.setFocus()

    def text(self) -> str:
        return self._textEdit.toMarkdown()

    def _textChanged(self):
        self._resized()
        self.undoStack.push(
            NoteEditorCommand(self._item, self._item.text(), self._item.height(), self.text(), self._textEdit.height()))
        # self._item.setText(self.text(), self._textEdit.height())

    def _resized(self):
        self.setFixedHeight(self._textEdit.height() + 5)


class EventSelectorWidget(SecondarySelectorWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._grid.addWidget(QLabel('Events'), 0, 0, 1, 3)

        self._btnGeneral = self.addItemTypeButton(GraphicsItemType.EVENT,
                                                  IconRegistry.from_name('mdi.square-rounded-outline'),
                                                  'General event', 1, 0)
        self._btnGoal = self.addItemTypeButton(GraphicsItemType.EVENT, IconRegistry.goal_icon('black', 'black'),
                                               'Goal or action',
                                               1, 1, subType=NODE_SUBTYPE_GOAL)
        self._btnConflict = self.addItemTypeButton(GraphicsItemType.EVENT,
                                                   IconRegistry.conflict_icon('black', 'black'),
                                                   'Conflict', 1, 2, subType=NODE_SUBTYPE_CONFLICT)
        self._btnDisturbance = self.addItemTypeButton(GraphicsItemType.EVENT,
                                                      IconRegistry.inciting_incident_icon('black'),
                                                      'Inciting incident', 2,
                                                      0, subType=NODE_SUBTYPE_DISTURBANCE)

        self._grid.addWidget(QLabel('Internal'), 3, 0, 1, 3)
        self._btnInternalConflict = self.addItemTypeButton(GraphicsItemType.EVENT,
                                                           IconRegistry.conflict_self_icon('black', 'black'),
                                                           'Internal conflict', 4, 0,
                                                           subType=NODE_SUBTYPE_INTERNAL_CONFLICT)
        self._btnBackstory = self.addItemTypeButton(GraphicsItemType.EVENT,
                                                    IconRegistry.backstory_icon('black', 'black'),
                                                    'Backstory', 4, 1, subType=NODE_SUBTYPE_BACKSTORY)

        # self._grid.addWidget(QLabel('Narrative'), 5, 0, 1, 3)
        # self._btnQuestion = self.addItemTypeButton(DiagramNodeType.SETUP, IconRegistry.from_name('ei.question-sign'),
        #                                            "Reader's question", 6,
        #                                            0, subType=NODE_SUBTYPE_QUESTION)
        # self._btnSetup = self.addItemTypeButton(DiagramNodeType.SETUP, IconRegistry.from_name('ri.seedling-fill'),
        #                                         'Setup and payoff', 6, 1)
        # self._btnForeshadowing = self.addItemTypeButton(DiagramNodeType.SETUP,
        #                                                 IconRegistry.from_name('mdi6.crystal-ball'),
        #                                                 'Foreshadowing',
        #                                                 6, 2, subType=NODE_SUBTYPE_FORESHADOWING)

        self._btnGeneral.setChecked(True)

    @overrides
    def showEvent(self, event: QShowEvent) -> None:
        self._btnGeneral.setChecked(True)


class CharacterToolbar(BaseItemToolbar):
    changeCharacter = pyqtSignal(CharacterItem)

    def __init__(self, undoStack: QUndoStack, parent=None):
        super().__init__(undoStack, parent)
        self._item: Optional[CharacterItem] = None

        self._btnCharacter = tool_btn(IconRegistry.character_icon(), 'Change character', transparent_=True)
        self._btnCharacter.clicked.connect(self._characterClicked)
        self._btnText = tool_btn(IconRegistry.from_name('mdi.format-text'), 'Change displayed text', transparent_=True)
        self._menuText = MenuWidget(self._btnText)
        self._textLineEdit = QLineEdit()
        self._textLineEdit.setPlaceholderText('Character')
        self._textLineEdit.setClearButtonEnabled(True)
        self._textLineEdit.textEdited.connect(self._textEdited)
        self._menuText.addWidget(self._textLineEdit)
        self._menuText.aboutToShow.connect(self._textLineEdit.setFocus)

        self._sbSize = AvatarSizeEditor()
        self._sbSize.valueChanged.connect(self._sizeChanged)

        self._toolbar.layout().addWidget(self._btnCharacter)
        self._toolbar.layout().addWidget(self._btnText)
        self._toolbar.layout().addWidget(vline())
        self._toolbar.layout().addWidget(self._sbSize)

    def setItem(self, item: CharacterItem):
        self._item = None
        self._hideSecondarySelectors()

        self._sbSize.setValue(item.node().size)
        self._textLineEdit.setPlaceholderText(item.character().name)
        self._textLineEdit.setText(item.node().text)
        self._item = item

    def _sizeChanged(self, value: int):
        if self._item:
            self.undoStack.push(SizeEditingCommand(self._item, value))

    def _characterClicked(self):
        if self._item:
            self.changeCharacter.emit(self._item)

    def _textEdited(self):
        if self._item:
            self.undoStack.push(TextEditingCommand(self._item, self._textLineEdit.text()))


class PaintedItemBasedToolbar(BaseItemToolbar):
    def __init__(self, undoStack: QUndoStack, parent=None):
        super().__init__(undoStack, parent)
        self._item: Optional[Any] = None

        self._btnColor = tool_btn(IconRegistry.from_name('fa5s.circle', color='darkBlue'), 'Change style',
                                  transparent_=True)
        self._colorPicker = ColorPicker(self, maxColumn=5)
        self._colorPicker.colorPicked.connect(self._colorChanged)
        self._colorSecondaryWidget = SecondarySelectorWidget(self)
        self._colorSecondaryWidget.addWidget(self._colorPicker, 0, 0)
        self.addSecondaryWidget(self._btnColor, self._colorSecondaryWidget)
        self._btnIcon = tool_btn(IconRegistry.from_name('mdi.emoticon-outline'), 'Change icon', transparent_=True)
        self._btnIcon.clicked.connect(self._showIconSelector)

    def setItem(self, item: Any):
        self._item = None
        self._hideSecondarySelectors()

        icon: str = item.icon()
        self._updateColor(item.color().name())
        if icon:
            self._updateIcon(icon)
        else:
            self._resetIcon()

        self._item = item

    def _showIconSelector(self):
        result = IconSelectorDialog.popup(pickColor=False)
        if result and self._item:
            command = GraphicsItemCommand(self._item, self._item.setIcon,
                                          self._item.icon(), result[0])
            self.undoStack.push(command)
            self._updateIcon(result[0])

    def _colorChanged(self, color: QColor):
        if self._item:
            command = GraphicsItemCommand(self._item, self._item.setColor,
                                          self._item.color(), color)
            self.undoStack.push(command)
            self._updateColor(color.name())
            pass

    def _updateIcon(self, icon: str):
        self._btnIcon.setIcon(IconRegistry.from_name(icon))

    def _resetIcon(self):
        self._btnIcon.setIcon(IconRegistry.from_name('mdi.emoticon-outline'))

    def _updateColor(self, color: str):
        self._btnColor.setIcon(IconRegistry.from_name('fa5s.circle', color))


class ConnectorToolbar(PaintedItemBasedToolbar):
    def __init__(self, undoStack: QUndoStack, parent=None):
        super().__init__(undoStack, parent)

        self._btnText = tool_btn(IconRegistry.from_name('mdi.format-text'), 'Change displayed text', transparent_=True)
        self._menuText = MenuWidget(self._btnText)
        self._textLineEdit = QLineEdit()
        self._textLineEdit.setPlaceholderText('Connector text...')
        self._textLineEdit.setClearButtonEnabled(True)
        self._textLineEdit.textEdited.connect(self._textEdited)
        self._menuText.addWidget(self._textLineEdit)
        self._menuText.aboutToShow.connect(self._textLineEdit.setFocus)

        self._arrowStart = tool_btn(
            IconRegistry.from_name('mdi.arrow-left-thick', 'lightgrey', color_on=PLOTLYST_SECONDARY_COLOR),
            tooltip='Arrow at the start', checkable=True, transparent_=True)
        self._arrowEnd = tool_btn(
            IconRegistry.from_name('mdi.arrow-right-thick', 'lightgrey', color_on=PLOTLYST_SECONDARY_COLOR),
            tooltip='Arrow at the start', checkable=True, transparent_=True)
        self._arrowStart.clicked.connect(self._arrowStartClicked)
        self._arrowEnd.clicked.connect(self._arrowEndClicked)

        self._solidLine = SolidPenStyleSelector()
        self._dashLine = DashPenStyleSelector()
        self._dotLine = DotPenStyleSelector()
        self._lineBtnGroup = QButtonGroup()
        self._lineBtnGroup.addButton(self._solidLine)
        self._lineBtnGroup.addButton(self._dashLine)
        self._lineBtnGroup.addButton(self._dotLine)
        self._lineBtnGroup.buttonClicked.connect(self._penStyleChanged)

        self._sbWidth = PenWidthEditor()
        self._sbWidth.valueChanged.connect(self._widthChanged)

        self._toolbar.layout().addWidget(self._btnColor)
        self._toolbar.layout().addWidget(self._btnIcon)
        self._toolbar.layout().addWidget(self._btnText)
        self._toolbar.layout().addWidget(vline())
        self._toolbar.layout().addWidget(self._arrowStart)
        self._toolbar.layout().addWidget(self._arrowEnd)
        self._toolbar.layout().addWidget(vline())
        self._toolbar.layout().addWidget(self._solidLine)
        self._toolbar.layout().addWidget(self._dashLine)
        self._toolbar.layout().addWidget(self._dotLine)
        self._toolbar.layout().addWidget(vline())
        self._toolbar.layout().addWidget(self._sbWidth)

    @overrides
    def setItem(self, connector: ConnectorItem):
        super().setItem(connector)
        self._item = None

        self._sbWidth.setValue(connector.size())
        self._textLineEdit.setText(connector.text())
        self._arrowStart.setChecked(connector.startArrowEnabled())
        self._arrowEnd.setChecked(connector.endArrowEnabled())

        penStyle = connector.penStyle()
        for line in [self._solidLine, self._dashLine, self._dotLine]:
            if penStyle == line.penStyle():
                line.setChecked(True)
                break
        self._item = connector

    def _textEdited(self):
        if self._item:
            self.undoStack.push(TextEditingCommand(self._item, self._textLineEdit.text()))

    def _penStyleChanged(self):
        btn = self._lineBtnGroup.checkedButton()
        if btn and self._item:
            command = GraphicsItemCommand(self._item, self._item.setPenStyle,
                                          self._item.penStyle(), btn.penStyle())
            self.undoStack.push(command)

    def _widthChanged(self, value: int):
        if self._item:
            self.undoStack.push(SizeEditingCommand(self._item, value))

    def _arrowStartClicked(self, toggled: bool):
        if self._item:
            command = GraphicsItemCommand(self._item, self._item.setStartArrowEnabled,
                                          self._item.startArrowEnabled(), toggled)
            self.undoStack.push(command)

    def _arrowEndClicked(self, toggled: bool):
        if self._item:
            command = GraphicsItemCommand(self._item, self._item.setEndArrowEnabled,
                                          self._item.endArrowEnabled(), toggled)
            self.undoStack.push(command)


class NoteToolbar(PaintedItemBasedToolbar):
    def __init__(self, undoStack: QUndoStack, parent=None):
        super().__init__(undoStack, parent)

        # self._btnColor.setToolTip('Background color')
        # self._btnTopFrame = tool_btn(IconRegistry.from_name('ri.layout-top-line'), tooltip='Top frame color',
        #                              transparent_=True)
        # self._btnSticker = tool_btn(IconRegistry.from_name('mdi6.sticker-emoji'), tooltip='Add sticker',
        #                             transparent_=True)
        self._btnTransparent = tool_btn(IconRegistry.transparent_background(), 'Toggle transparent background',
                                        transparent_=True, checkable=True)
        self._btnTransparent.clicked.connect(self._transparentClicked)

        # self._toolbar.layout().addWidget(self._btnColor)
        # self._toolbar.layout().addWidget(self._btnIcon)
        # self._toolbar.layout().addWidget(self._btnTopFrame)
        # self._toolbar.layout().addWidget(vline())
        # self._toolbar.layout().addWidget(self._btnSticker)
        # self._toolbar.layout().addWidget(vline())
        self._toolbar.layout().addWidget(self._btnTransparent)

    @overrides
    def setItem(self, item: NoteItem):
        super().setItem(item)
        self._item = None

        self._btnTransparent.setChecked(item.node().transparent)

        self._item = item

    def _transparentClicked(self, toggled: bool):
        if self._item:
            command = GraphicsItemCommand(self._item, self._item.setTransparent,
                                          self._item.transparent(), toggled)
            self.undoStack.push(command)


class IconItemToolbar(PaintedItemBasedToolbar):
    def __init__(self, undoStack: QUndoStack, parent=None):
        super().__init__(undoStack, parent)

        self._sbSize = AvatarSizeEditor()
        self._sbSize.valueChanged.connect(self._sizeChanged)

        self._toolbar.layout().addWidget(self._btnColor)
        self._toolbar.layout().addWidget(self._btnIcon)
        self._toolbar.layout().addWidget(vline())
        self._toolbar.layout().addWidget(self._sbSize)

    @overrides
    def setItem(self, item: IconItem):
        super().setItem(item)
        self._item = None

        self._sbSize.setValue(item.node().size)
        self._item = item

    def _sizeChanged(self, value: int):
        if self._item:
            self.undoStack.push(SizeEditingCommand(self._item, value))


class EventItemToolbar(PaintedItemBasedToolbar):
    def __init__(self, undoStack: QUndoStack, parent=None):
        super().__init__(undoStack, parent)
        self._btnType = tool_btn(IconRegistry.from_name('mdi.square-rounded-outline'), 'Change type', transparent_=True)
        self._sbFont = FontSizeSpinBox()
        self._sbFont.fontChanged.connect(self._fontChanged)
        self._btnBold = tool_btn(IconRegistry.from_name('fa5s.bold'), 'Bold', checkable=True, icon_resize=False,
                                 properties=['transparent-rounded-bg-on-hover', 'top-selector'])
        decr_icon(self._btnBold)
        self._btnItalic = tool_btn(IconRegistry.from_name('fa5s.italic'), 'Italic',
                                   checkable=True, icon_resize=False,
                                   properties=['transparent-rounded-bg-on-hover', 'top-selector'])
        decr_icon(self._btnItalic)
        self._btnUnderline = tool_btn(IconRegistry.from_name('fa5s.underline'), 'Underline',
                                      checkable=True, icon_resize=False,
                                      properties=['transparent-rounded-bg-on-hover', 'top-selector'])
        decr_icon(self._btnUnderline)
        self._btnBold.clicked.connect(self._textStyleChanged)
        self._btnItalic.clicked.connect(self._textStyleChanged)
        self._btnUnderline.clicked.connect(self._textStyleChanged)

        self._eventSelector = EventSelectorWidget(self)
        self.addSecondaryWidget(self._btnType, self._eventSelector)
        self._eventSelector.selected.connect(self._typeChanged)

        self._toolbar.layout().addWidget(self._btnType)
        self._toolbar.layout().addWidget(vline())
        self._toolbar.layout().addWidget(self._btnColor)
        self._toolbar.layout().addWidget(self._btnIcon)
        self._toolbar.layout().addWidget(vline())
        self._toolbar.layout().addWidget(self._sbFont)
        self._toolbar.layout().addWidget(vline())
        self._toolbar.layout().addWidget(group(self._btnBold, self._btnItalic, self._btnUnderline, margin=0, spacing=2))

    @overrides
    def setItem(self, item: EventItem):
        super().setItem(item)
        self._item = None

        self._sbFont.setValue(item.fontSize())
        self._btnBold.setChecked(item.bold())
        self._btnItalic.setChecked(item.italic())
        self._btnUnderline.setChecked(item.underline())

        self._item = item

    def _fontChanged(self, size: int):
        self._hideSecondarySelectors()
        if self._item:
            self._item.setFontSettings(size=size)

    def _textStyleChanged(self):
        self._hideSecondarySelectors()
        if self._item:
            self._item.setFontSettings(bold=self._btnBold.isChecked(), italic=self._btnItalic.isChecked(),
                                       underline=self._btnUnderline.isChecked())

    def _typeChanged(self, itemType: GraphicsItemType, subtype: str):
        if self._item:
            self._item.setItemType(itemType, subtype)


class PenStyleSelector(QAbstractButton):
    penStyleToggled = pyqtSignal(Qt.PenStyle, bool)

    def __init__(self, penWidth: int = 2, color=Qt.GlobalColor.lightGray, colorOn=PLOTLYST_SECONDARY_COLOR,
                 parent=None):
        super().__init__(parent)
        self._penWidth = penWidth
        self._color = color
        self._colorOn = colorOn
        self._penStyle = self.penStyle()
        self.setFixedSize(20, 20)

        self.setCheckable(True)

        self._pen = QPen(QColor(self._color), self._penWidth, self._penStyle)
        self._penToggled = QPen(QColor(self._colorOn), self._penWidth, self._penStyle)
        pointy(self)

    @abstractmethod
    def penStyle(self) -> Qt.PenStyle:
        pass

    @overrides
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.isChecked():
            painter.setPen(self._penToggled)
        else:
            painter.setPen(self._pen)
        painter.drawLine(0, self.rect().height() // 2, self.rect().width(), self.rect().height() // 2)


class SolidPenStyleSelector(PenStyleSelector):

    @overrides
    def penStyle(self) -> Qt.PenStyle:
        return Qt.PenStyle.SolidLine


class DashPenStyleSelector(PenStyleSelector):

    @overrides
    def penStyle(self) -> Qt.PenStyle:
        return Qt.PenStyle.DashLine


class DotPenStyleSelector(PenStyleSelector):

    @overrides
    def penStyle(self) -> Qt.PenStyle:
        return Qt.PenStyle.DotLine


class PenWidthEditor(QSlider):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimum(1)
        self.setMaximum(10)
        self.setOrientation(Qt.Orientation.Horizontal)


class AvatarSizeEditor(QSlider):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimum(48)
        self.setMaximum(255)
        self.setOrientation(Qt.Orientation.Horizontal)


class RelationsButton(QAbstractButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._icon = IconRegistry.character_icon()
        self.setFixedSize(40, 20)
        pointy(self)

    @overrides
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(Qt.GlobalColor.black, 1))

        x = 5
        y = 2
        painter.drawEllipse(x, y, self.rect().width() - x * 2, self.rect().height() - y * 2)

        self._icon.paint(painter, 0, y, 15, 15)
        self._icon.paint(painter, self.rect().width() - 15, y, 15, 15)
