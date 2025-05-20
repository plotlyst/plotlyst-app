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
from dataclasses import dataclass
from functools import partial
from typing import List, Optional, Any, Dict

import qtanim
from PyQt6.QtCore import pyqtSignal, Qt, QSize, QEvent, QTimer
from PyQt6.QtGui import QIcon, QColor, QPainter, QPaintEvent, QBrush, QResizeEvent, QShowEvent, QEnterEvent, \
    QDragEnterEvent, QDragLeaveEvent, QDropEvent
from PyQt6.QtWidgets import QWidget, QSizePolicy, \
    QLineEdit, QFrame
from overrides import overrides
from qthandy import vbox, hbox, sp, vspacer, clear_layout, spacer, incr_font, margins, gc, retain_when_hidden, \
    translucent, decr_icon
from qthandy.filter import VisibilityToggleEventFilter, DragEventFilter, DropEventFilter, OpacityEventFilter
from qtmenu import MenuWidget

from plotlyst.common import RELAXED_WHITE_COLOR, NEUTRAL_EMOTION_COLOR, \
    EMOTION_COLORS, PLOTLYST_SECONDARY_COLOR, ALT_BACKGROUND_COLOR
from plotlyst.core.domain import BackstoryEvent, Position
from plotlyst.env import app_env
from plotlyst.view.common import tool_btn, frame, columns, rows, scroll_area, fade_in, insert_before_the_end, shadow, \
    fade_out_and_gc, action, remove_and_gc
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.confirm import confirmed
from plotlyst.view.widget.display import DotsDragIcon
from plotlyst.view.widget.input import AutoAdjustableTextEdit
from plotlyst.view.widget.utility import IconSelectorDialog


@dataclass
class TimelineTheme:
    timeline_color: str = PLOTLYST_SECONDARY_COLOR
    timeline_opacity: float = 1.0
    card_bg_color: str = '#ffe8d6'


class BackstoryCard(QWidget):
    TYPE_SIZE: int = 36
    edited = pyqtSignal()
    deleteRequested = pyqtSignal(object)

    def __init__(self, backstory: BackstoryEvent, theme: TimelineTheme, parent=None, iconPicker: bool = True):
        super().__init__(parent)
        self.backstory = backstory
        self._theme = theme

        vbox(self, 0)
        margins(self, left=5, right=5, top=self.TYPE_SIZE // 2, bottom=3)

        self.cardFrame = frame()
        self.cardFrame.setObjectName('cardFrame')
        vbox(self.cardFrame, spacing=5)
        margins(self.cardFrame, left=5, bottom=15)

        self.btnType = tool_btn(QIcon(), parent=self)
        self.btnType.setIconSize(QSize(24, 24))
        if iconPicker:
            self.btnType.clicked.connect(self._selectIcon)

        self.btnDrag = DotsDragIcon()
        self.btnDrag.setVisible(False)
        decr_icon(self.btnDrag, 2)
        self.btnDrag.clicked.connect(self._showContextMenu)
        # self.btnDrag.clicked.connect(self._remove)

        self.lineKeyPhrase = QLineEdit()
        self.lineKeyPhrase.setPlaceholderText('Keyphrase')
        self.lineKeyPhrase.setProperty('transparent', True)
        self.lineKeyPhrase.textEdited.connect(self._keyphraseEdited)
        font = self.lineKeyPhrase.font()
        font.setPointSize(font.pointSize() + 2)
        font.setFamily(app_env.serif_font())
        self.lineKeyPhrase.setFont(font)

        self.textSummary = AutoAdjustableTextEdit(height=40)
        self.textSummary.setPlaceholderText("Summarize this event")
        self.textSummary.setBlockFormat(lineSpacing=120)
        self.textSummary.setViewportMargins(3, 0, 3, 0)
        self.textSummary.setProperty('transparent', True)
        self.textSummary.textChanged.connect(self._synopsisChanged)
        incr_font(self.textSummary)

        wdgTop = QWidget()
        hbox(wdgTop, 0, 0)
        margins(wdgTop, top=5)
        wdgTop.layout().addWidget(self.lineKeyPhrase)
        wdgTop.layout().addWidget(self.btnDrag, alignment=Qt.AlignmentFlag.AlignTop)
        self.cardFrame.layout().addWidget(wdgTop)
        self.cardFrame.layout().addWidget(self.textSummary)
        self.layout().addWidget(self.cardFrame)

        self.cardFrame.installEventFilter(VisibilityToggleEventFilter(self.btnDrag, self.cardFrame))
        self.installEventFilter(VisibilityToggleEventFilter(self.btnDrag, self))

        self.btnType.raise_()

        self.setMinimumWidth(200)
        sp(self).v_max()

        shadow(self, color=Qt.GlobalColor.gray)

    @overrides
    def resizeEvent(self, event: QResizeEvent) -> None:
        self.btnType.setGeometry(self.width() // 2 - self.TYPE_SIZE // 2, 2, self.TYPE_SIZE, self.TYPE_SIZE)

    def refresh(self):
        self._refreshStyle()
        self.lineKeyPhrase.setText(self.backstory.keyphrase)
        self.textSummary.setPlainText(self.backstory.synopsis)

    def _refreshStyle(self):
        frame_color = self._frameColor()
        self.cardFrame.setStyleSheet(f'''
                            #cardFrame {{
                                border-top: 8px solid {frame_color};
                                border-bottom-left-radius: 12px;
                                border-bottom-right-radius: 12px;
                                background-color: {self._theme.card_bg_color};
                                }}
                            ''')
        self.btnType.setStyleSheet(
            f'''
                    QToolButton {{
                            background-color: {RELAXED_WHITE_COLOR}; border: 3px solid {frame_color};
                            border-radius: 18px;
                            padding: 4px;
                        }}
                    QToolButton:hover {{
                        padding: 2px;
                    }}
                    ''')

        self.btnType.setIcon(IconRegistry.from_name(self.backstory.type_icon, frame_color))

    def _synopsisChanged(self):
        self.backstory.synopsis = self.textSummary.toPlainText()
        self.edited.emit()

    def _keyphraseEdited(self):
        self.backstory.keyphrase = self.lineKeyPhrase.text()
        self.edited.emit()

    def _selectIcon(self):
        result = IconSelectorDialog.popup(pickColor=False)
        if result:
            self._iconChanged(result[0])

    def _iconChanged(self, icon: str):
        self.backstory.type_icon = icon
        self.btnType.setIcon(IconRegistry.from_name(self.backstory.type_icon, EMOTION_COLORS[self.backstory.emotion]))
        self.edited.emit()

    def _showContextMenu(self):
        menu = MenuWidget()
        menu.addAction(action('Remove', IconRegistry.trash_can_icon(), slot=self._remove))
        menu.exec()

    def _remove(self):
        if self.backstory.synopsis and not confirmed('This action cannot be undone.',
                                                     f'Are you sure you want to remove the event "{self.backstory.keyphrase if self.backstory.keyphrase else "Untitled"}"?'):
            return
        self.deleteRequested.emit(self)

    def _frameColor(self) -> str:
        return EMOTION_COLORS.get(self.backstory.emotion, NEUTRAL_EMOTION_COLOR)


class PlaceholderWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        self.btnPlus = tool_btn(IconRegistry.plus_icon('grey'), transparent_=True)
        self.btnPlus.setIconSize(QSize(22, 22))
        sp(self.btnPlus).h_exp()
        vbox(self, 0, 0).addWidget(self.btnPlus)
        translucent(self)
        retain_when_hidden(self.btnPlus)
        self.setMinimumWidth(150)
        self.setMaximumWidth(200)
        self.deactivate()

        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.timeout.connect(self._applyHoverStyle)

    def activate(self):
        self.btnPlus.setVisible(True)

    def deactivate(self):
        self.btnPlus.setHidden(True)

    @overrides
    def enterEvent(self, event: QEnterEvent) -> None:
        self._hover_timer.start(100)

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        self._hover_timer.stop()
        self.setStyleSheet('')

    @overrides
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        self.setStyleSheet(f'background: {PLOTLYST_SECONDARY_COLOR};')
        event.accept()

    @overrides
    def dragLeaveEvent(self, event: QDragLeaveEvent) -> None:
        self.setStyleSheet('')

    @overrides
    def dropEvent(self, event: QDropEvent) -> None:
        self.setStyleSheet('')

    def _applyHoverStyle(self):
        self.setStyleSheet(f'background: {ALT_BACKGROUND_COLOR};')


class PlaceholdersRow(QWidget):
    dropped = pyqtSignal(Position)

    def __init__(self, mimeType: str, parent=None, centerOnly: bool = False):
        super().__init__(parent)
        self._mimeType = mimeType
        self._centerOnly = centerOnly
        hbox(self, 0, 0)

        self.placeholderLeft = PlaceholderWidget()
        self.placeholderCenter = PlaceholderWidget()
        self.placeholderRight = PlaceholderWidget()
        self.layout().addWidget(spacer())
        self.layout().addWidget(self.placeholderLeft)
        self.layout().addWidget(self.placeholderCenter)
        self.layout().addWidget(self.placeholderRight)
        self.layout().addWidget(spacer())

        if self._centerOnly:
            self.placeholderCenter.setMinimumWidth(self.placeholderCenter.minimumWidth() * 3)
            self.placeholderCenter.setMaximumWidth(self.placeholderCenter.maximumWidth() * 3)
            self.placeholderLeft.setFixedWidth(1)
            self.placeholderRight.setFixedWidth(1)

        self.placeholderLeft.installEventFilter(
            DropEventFilter(self, [mimeType], droppedSlot=lambda x: self.dropped.emit(Position.LEFT)))
        self.placeholderRight.installEventFilter(
            DropEventFilter(self, [mimeType], droppedSlot=lambda x: self.dropped.emit(Position.RIGHT)))
        self.placeholderCenter.installEventFilter(
            DropEventFilter(self, [mimeType], droppedSlot=lambda x: self.dropped.emit(Position.CENTER)))

    @overrides
    def enterEvent(self, event: QEnterEvent) -> None:
        if not self._centerOnly:
            self.placeholderLeft.activate()
            self.placeholderCenter.activate()
            self.placeholderRight.activate()
        else:
            self.placeholderCenter.activate()

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        if not self._centerOnly:
            self.placeholderLeft.deactivate()
            self.placeholderCenter.deactivate()
            self.placeholderRight.deactivate()
        else:
            self.placeholderCenter.deactivate()


class TimelineEntityRow(QWidget):
    insert = pyqtSignal(Position)
    dropped = pyqtSignal(Position)

    def __init__(self, card: BackstoryCard, parent: 'TimelineLinearWidget', centerOnly: bool = False):
        super().__init__(parent)
        self.card = card

        self._margin: int = 2

        vbox(self, self._margin, 0)
        self.wdgPlaceholders = PlaceholdersRow(parent.mimeType(), centerOnly=centerOnly)
        self.wdgPlaceholders.placeholderLeft.btnPlus.clicked.connect(lambda: self.insert.emit(Position.LEFT))
        self.wdgPlaceholders.placeholderCenter.btnPlus.clicked.connect(lambda: self.insert.emit(Position.CENTER))
        self.wdgPlaceholders.placeholderRight.btnPlus.clicked.connect(lambda: self.insert.emit(Position.RIGHT))

        self.wdgPlaceholders.dropped.connect(self.dropped)

        self.wdgCardParent = columns(0, 0)

        self._spacer = None

        if self.card.backstory.position == Position.RIGHT:
            self._spacer = spacer()
            self.wdgCardParent.layout().addWidget(self._spacer)
            self.wdgCardParent.layout().addWidget(self.card, alignment=Qt.AlignmentFlag.AlignLeft)
        elif self.card.backstory.position == Position.LEFT:
            self.wdgCardParent.layout().addWidget(self.card, alignment=Qt.AlignmentFlag.AlignRight)
            self._spacer = spacer()
            self.wdgCardParent.layout().addWidget(self._spacer)
        else:
            self.wdgCardParent.layout().addWidget(self.card, alignment=Qt.AlignmentFlag.AlignCenter)

        self.layout().addWidget(self.wdgPlaceholders)
        self.layout().addWidget(self.wdgCardParent)

        self.card.btnDrag.installEventFilter(
            DragEventFilter(self.card, mimeType=parent.mimeType(), dataFunc=lambda x: card.backstory,
                            grabbed=self.card, startedSlot=partial(parent.dragStartedEvent, self),
                            finishedSlot=partial(parent.dragFinishedEvent, self)))

        self.setAcceptDrops(True)

    @overrides
    def resizeEvent(self, event: QResizeEvent) -> None:
        if self._spacer is not None:
            self._spacer.setFixedWidth(self.width() // 2 + self._margin * 2)

    @overrides
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().formats()[0].startswith(self.parent().mimeType()):
            event.accept()
        else:
            event.ignore()


class TimelineLinearWidget(QWidget):
    changed = pyqtSignal()
    addedToTheEnd = pyqtSignal()

    def __init__(self, theme: Optional[TimelineTheme] = None, parent=None, centerOnly: bool = False):
        super().__init__(parent)
        self._centerOnly = centerOnly
        self._dragged: Optional[TimelineEntityRow] = None

        if theme is None:
            theme = TimelineTheme()
        self._theme = theme
        vbox(self, spacing=0)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._endSpacerMinHeight: int = 45

    @abstractmethod
    def events(self) -> List[BackstoryEvent]:
        pass

    def mimeType(self) -> str:
        return 'application/timeline-event'

    def cardClass(self):
        return BackstoryCard

    def setAddButtonEnabled(self, color: str = 'grey'):
        btnAdd = tool_btn(IconRegistry.plus_icon(color), transparent_=True, parent=self)
        btnAdd.installEventFilter(OpacityEventFilter(btnAdd))
        btnAdd.setIconSize(QSize(32, 32))
        btnAdd.clicked.connect(lambda: self.add(Position.CENTER))

        btnAdd.setGeometry(0, 0, btnAdd.sizeHint().width(), btnAdd.sizeHint().height())
        margins(self, top=btnAdd.sizeHint().height())
        btnAdd.raise_()

    def refresh(self):
        clear_layout(self)

        auto_pos = Position.RIGHT
        for i, backstory in enumerate(self.events()):
            if backstory.position is None:
                backstory.position = auto_pos
                auto_pos = auto_pos.toggle()

            row = self.__initEntityRow(backstory)
            self.layout().addWidget(row)

        wdgPlaceholders = PlaceholdersRow(self.mimeType(), centerOnly=self._centerOnly)
        wdgPlaceholders.placeholderLeft.btnPlus.clicked.connect(lambda: self.add(Position.LEFT))
        wdgPlaceholders.placeholderRight.btnPlus.clicked.connect(lambda: self.add(Position.RIGHT))
        wdgPlaceholders.placeholderCenter.btnPlus.clicked.connect(lambda: self.add(Position.CENTER))
        wdgPlaceholders.dropped.connect(partial(self._dropped, wdgPlaceholders))
        self.layout().addWidget(wdgPlaceholders)

        spacer_ = vspacer()
        spacer_.setMinimumHeight(self._endSpacerMinHeight)
        self.layout().addWidget(spacer_)

    @overrides
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(self._theme.timeline_color)))
        painter.setOpacity(self._theme.timeline_opacity)
        painter.drawRect(int(self.width() / 2) - 3, 0, 6, self.height())

        painter.end()

    def add(self, position: Position = Position.CENTER):
        backstory = BackstoryEvent('', '', type_color=NEUTRAL_EMOTION_COLOR, position=position)
        self.events().append(backstory)

        row = self.__initEntityRow(backstory)
        insert_before_the_end(self, row, 2)
        fade_in(row)

        self.changed.emit()
        QTimer.singleShot(45, lambda: self.addedToTheEnd.emit())

    def dragStartedEvent(self, row: TimelineEntityRow):
        self._dragged = row
        self._dragged.setHidden(True)

    def dragFinishedEvent(self, row: TimelineEntityRow):
        if self._dragged is not None:
            row.setVisible(True)

    def _insert(self, event: TimelineEntityRow, position: Position):
        i = self.layout().indexOf(event)
        backstory = BackstoryEvent('', '', type_color=NEUTRAL_EMOTION_COLOR, position=position)
        self.events().insert(i, backstory)

        row = self.__initEntityRow(backstory)
        self.layout().insertWidget(i, row)
        fade_in(row)

        self.changed.emit()

    def _dropped(self, row: TimelineEntityRow, position: Position):
        event = self._dragged.card.backstory
        event.position = position

        newRow = self.__initEntityRow(event)
        i = self.layout().indexOf(row)
        self.layout().insertWidget(i, newRow)

        new_events: List[BackstoryEvent] = []
        for i in range(self.layout().count()):
            item = self.layout().itemAt(i)
            if item.widget() and item.widget() is not self._dragged and isinstance(item.widget(), TimelineEntityRow):
                new_events.append(item.widget().card.backstory)

        self.events()[:] = new_events

        remove_and_gc(self, self._dragged)
        self._dragged = None

        self.changed.emit()

    def _remove(self, row: TimelineEntityRow, card: BackstoryCard):
        self.events().remove(card.backstory)
        fade_out_and_gc(self, row)

        self.changed.emit()

    def __initEntityRow(self, event: BackstoryEvent) -> TimelineEntityRow:
        row = TimelineEntityRow(self.cardClass()(event, self._theme), parent=self, centerOnly=self._centerOnly)
        row.insert.connect(partial(self._insert, row))
        row.dropped.connect(partial(self._dropped, row))
        row.card.deleteRequested.connect(partial(self._remove, row))
        row.card.edited.connect(self.changed)

        return row


class TimelineGridPlaceholder(QWidget):
    def __init__(self, ref: Any, parent: 'TimelineGridLine'):
        super().__init__(parent)
        self.ref = ref
        vbox(self, 0, 0)
        self.btn = tool_btn(IconRegistry.plus_circle_icon(parent.ref.icon_color, RELAXED_WHITE_COLOR),
                            transparent_=True)
        self.btn.setIconSize(QSize(32, 32))
        self.layout().addWidget(self.btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.btn.setHidden(True)

    @overrides
    def enterEvent(self, event: QEnterEvent) -> None:
        self.btn.setIcon(IconRegistry.plus_circle_icon(self.parent().ref.icon_color, RELAXED_WHITE_COLOR))
        qtanim.fade_in(self.btn, duration=150, teardown=lambda: translucent(self.btn, 0.5))

    @overrides
    def leaveEvent(self, a0: QEvent) -> None:
        self.btn.setHidden(True)


class TimelineGridLine(QWidget):
    def __init__(self, ref: Any, vertical: bool = False):
        super().__init__()
        self.ref = ref
        self._vertical = vertical
        if vertical:
            hbox(self, 0, 0)
        else:
            vbox(self, 0, 0)

        if vertical:
            sp(self).v_max()
        else:
            sp(self).h_max()

    @overrides
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        color = self.ref.icon_color if self.ref.icon_color else 'lightgrey'
        painter.setPen(QColor(color))
        painter.setBrush(QColor(color))
        painter.setOpacity(0.25)

        if self._vertical:
            painter.drawRect(5, self.rect().height() // 2 - 4, self.rect().width(), 8)
        else:
            painter.drawRect(self.rect().width() // 2 - 4, 5, 8, self.rect().height())


class TimelineGridWidget(QFrame):
    def __init__(self, parent=None, vertical: bool = False):
        super().__init__(parent)
        self._vertical = vertical

        self._columnWidth: int = 150
        self._rowHeight: int = 50
        self._headerHeight: int = 40
        self._verticalHeaderWidth: int = 200
        self._spacing: int = 10
        self._margins: int = 15

        self._rows: Dict[Any, QWidget] = {}
        self._columns: Dict[Any, TimelineGridLine] = {}

        self.wdgColumns = columns(0, self._spacing)
        self.scrollColumns = scroll_area(False, False, frameless=True)
        self.scrollColumns.setWidget(self.wdgColumns)
        # sp(self.scrollColumns).v_max()
        # self.scrollColumns.setFixedHeight(self._headerHeight)
        self.scrollColumns.setFixedHeight(self._headerHeight)
        self.scrollColumns.horizontalScrollBar().setEnabled(False)

        self.wdgRows = rows(0, self._spacing)
        # self.wdgRows.setStyleSheet('background: green;')
        margins(self.wdgRows, top=self._headerHeight, right=self._spacing)
        self.scrollRows = scroll_area(False, False, frameless=True)
        self.scrollRows.setWidget(self.wdgRows)
        sp(self.scrollRows).h_max()
        self.scrollRows.verticalScrollBar().setEnabled(False)

        if self._vertical:
            self.wdgEditor = rows(0, self._spacing)
        else:
            self.wdgEditor = columns(0, self._spacing)

        margins(self.wdgEditor, left=self._margins, top=self._margins)
        margins(self.wdgColumns, left=self._margins)
        margins(self.wdgRows, top=self._headerHeight)

        sp(self.wdgEditor).v_exp().h_exp()
        self.scrollEditor = scroll_area(frameless=True)
        self.scrollEditor.setWidget(self.wdgEditor)
        self.scrollEditor.horizontalScrollBar().valueChanged.connect(self._horizontalScrolled)
        self.scrollEditor.verticalScrollBar().valueChanged.connect(self._verticalScrolled)
        self.scrollEditor.verticalScrollBar().rangeChanged.connect(self._editorRangeChanged)

        self.wdgCenter = rows(0, 0)
        self.wdgCenter.layout().addWidget(self.scrollColumns)
        self.wdgCenter.layout().addWidget(self.scrollEditor)

        self.wdgRows.layout().addWidget(vspacer())
        self.wdgColumns.layout().addWidget(spacer())
        if self._vertical:
            self.wdgEditor.layout().addWidget(vspacer())
        else:
            self.wdgEditor.layout().addWidget(spacer())

        hbox(self, 0, 0)
        self.layout().addWidget(self.scrollRows)
        self.layout().addWidget(self.wdgCenter)

        self._emptyPlaceholder = QWidget(self)
        self._emptyPlaceholder.setProperty('bg', True)
        self._emptyPlaceholder.setGeometry(0, 0, self._verticalHeaderWidth, self._headerHeight)

    def setColumnWidth(self, width: int):
        self._columnWidth = width

    def setRowHeight(self, height: int):
        self._rowHeight = height

    # def addColumn(self, ref: Any, title: str = '', icon: Optional[QIcon] = None):
    #     lblColumn = push_btn(text=title, transparent_=True)
    #     if icon:
    #         lblColumn.setIcon(icon)
    #     incr_font(lblColumn, 1)
    #     lblColumn.setFixedSize(self._columnWidth, self._headerHeight)
    #     insert_before_the_end(self.wdgColumns, lblColumn, alignment=Qt.AlignmentFlag.AlignCenter)
    #
    #     column = TimelineGridLine(ref, vertical=self._vertical)
    #     if not self._vertical:
    #         column.setFixedWidth(self._columnWidth)
    #     column.layout().setSpacing(self._spacing)
    #     spacer_wdg = spacer() if self._vertical else vspacer()
    #     # spacer_wdg.setProperty('relaxed-white-bg', True)
    #     column.layout().addWidget(spacer_wdg)
    #
    #     self._columns[ref] = column
    #     for j in range(self.wdgRows.layout().count() - 1):
    #         self._addPlaceholders(column)
    #
    #     insert_before_the_end(self.wdgEditor, column)

    # def addRow(self, ref: Any, title: str = '', icon: Optional[QIcon] = None):
    #     lblRow = push_btn(text=title, transparent_=True)
    #     if icon:
    #         lblRow.setIcon(icon)
    #     incr_font(lblRow, 2)
    #     self.addRowWidget(ref, lblRow)

    # def addRowWidget(self, ref: Any, wdg: QWidget):
    #     self._rows[ref] = wdg
    #     wdg.setFixedHeight(self._rowHeight)
    #     insert_before_the_end(self.wdgRows, wdg, alignment=Qt.AlignmentFlag.AlignCenter)
    #
    #     for line in self._columns.values():
    #         self._addPlaceholders(line)

    # def setRowWidget(self, ref: Any, wdg: QWidget):
    #     self._rows[ref] = wdg
    #     wdg.setFixedHeight(self._rowHeight)
    #     for line in self._columns.values():
    #         self._addPlaceholders(line)

    # def addItem(self, source: Any, index: int, ref: Any, text: str):
    #     wdg = QTextEdit()
    #     wdg.setTabChangesFocus(True)
    #     wdg.setPlaceholderText('How does the story move forward')
    #     wdg.setStyleSheet(f'''
    #      QTextEdit {{
    #         border-radius: 6px;
    #         padding: 4px;
    #         background-color: {RELAXED_WHITE_COLOR};
    #         border: 1px solid lightgrey;
    #     }}
    #
    #     QTextEdit:focus {{
    #         border: 1px solid {source.icon_color};
    #     }}
    #     ''')
    #     shadow(wdg, color=QColor(source.icon_color))
    #     wdg.setText(text)
    #     wdg.setAlignment(Qt.AlignmentFlag.AlignCenter)
    #     wdg.setFixedSize(self._columnWidth - 2 * self._spacing, self._rowHeight)
    #     if self._vertical:
    #         line = self._rows[source]
    #     else:
    #         line = self._columns[source]
    #     placeholder = line.layout().itemAt(index).widget()
    #     line.layout().replaceWidget(placeholder, wdg)

    @overrides
    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        self._editorRangeChanged()

    def _addPlaceholder(self, line: TimelineGridLine, ref: Any):
        placeholder = self._initPlaceholder(line, ref)

        insert_before_the_end(line, placeholder)

    def _insertPlaceholder(self, index: int, line: TimelineGridLine, ref: Any):
        placeholder = self._initPlaceholder(line, ref)
        line.layout().insertWidget(index, placeholder)

    def _replaceWithPlaceholder(self, index: int, line: TimelineGridLine, ref: Any):
        placeholder = self._initPlaceholder(line, ref)

        wdg = line.layout().itemAt(index).widget()
        line.layout().removeWidget(wdg)
        gc(wdg)
        line.layout().insertWidget(index, placeholder)

    def _removeWidget(self, line: TimelineGridLine, index: int):
        wdg = line.layout().itemAt(index).widget()
        line.layout().removeWidget(wdg)
        gc(wdg)

    def _horizontalScrolled(self, value: int):
        self.scrollColumns.horizontalScrollBar().setValue(value)

    def _verticalScrolled(self, value: int):
        self.scrollRows.verticalScrollBar().setValue(value)

    def _editorRangeChanged(self):
        if self.scrollEditor.verticalScrollBar().isVisible():
            margins(self.wdgRows, bottom=self.scrollEditor.verticalScrollBar().sizeHint().height())
        else:
            margins(self.wdgRows, bottom=0)

        if self.scrollEditor.horizontalScrollBar().isVisible():
            margins(self.wdgColumns, right=self.scrollEditor.horizontalScrollBar().sizeHint().width())
        else:
            margins(self.wdgColumns, right=0)

    def _initPlaceholder(self, line: TimelineGridLine, ref: Any) -> TimelineGridPlaceholder:
        placeholder = TimelineGridPlaceholder(ref, parent=line)
        placeholder.btn.clicked.connect(partial(self._placeholderClicked, line, placeholder))
        placeholder.setFixedSize(self._columnWidth, self._rowHeight)

        return placeholder

    def _placeholderClicked(self, line: TimelineGridLine, placeholder: TimelineGridPlaceholder):
        pass
