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
from typing import List, Optional

from PyQt6.QtCore import pyqtSignal, Qt, QSize, QObject, QEvent
from PyQt6.QtGui import QIcon, QColor, QPainter, QPaintEvent, QBrush, QResizeEvent
from PyQt6.QtWidgets import QWidget, QLineEdit, QToolButton
from overrides import overrides
from qthandy import vbox, hbox, sp, incr_font, bold, \
    margins, clear_layout, vspacer
from qthandy.filter import VisibilityToggleEventFilter

from plotlyst.common import RELAXED_WHITE_COLOR, NEUTRAL_EMOTION_COLOR, \
    EMOTION_COLORS, PLOTLYST_SECONDARY_COLOR
from plotlyst.core.domain import BackstoryEvent
from plotlyst.view.common import tool_btn, frame, push_btn
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.confirm import confirmed
from plotlyst.view.widget.input import RemovalButton, AutoAdjustableTextEdit


@dataclass
class TimelineTheme:
    timeline_color: str = PLOTLYST_SECONDARY_COLOR
    card_bg_color: str = '#ffe8d6'


class BackstoryCard(QWidget):
    TYPE_SIZE: int = 36
    edited = pyqtSignal()
    deleteRequested = pyqtSignal(object)
    relationChanged = pyqtSignal()

    def __init__(self, backstory: BackstoryEvent, theme: TimelineTheme, parent=None):
        super().__init__(parent)
        self.backstory = backstory
        self._theme = theme

        vbox(self)
        margins(self, top=self.TYPE_SIZE // 2)

        self.cardFrame = frame()
        self.cardFrame.setObjectName('cardFrame')
        vbox(self.cardFrame, spacing=5)
        margins(self.cardFrame, left=5, bottom=15)

        self.btnType = tool_btn(QIcon(), parent=self)
        self.btnType.setIconSize(QSize(24, 24))

        self.btnRemove = RemovalButton()
        self.btnRemove.setVisible(False)
        self.btnRemove.clicked.connect(self._remove)

        self.lineKeyPhrase = QLineEdit()
        self.lineKeyPhrase.setPlaceholderText('Keyphrase')
        self.lineKeyPhrase.setProperty('transparent', True)
        self.lineKeyPhrase.textEdited.connect(self._keyphraseEdited)
        incr_font(self.lineKeyPhrase, 2)
        bold(self.lineKeyPhrase)

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
        wdgTop.layout().addWidget(self.btnRemove, alignment=Qt.AlignmentFlag.AlignTop)
        self.cardFrame.layout().addWidget(wdgTop)
        self.cardFrame.layout().addWidget(self.textSummary)
        self.layout().addWidget(self.cardFrame)

        self.cardFrame.installEventFilter(VisibilityToggleEventFilter(self.btnRemove, self.cardFrame))

        self.btnType.raise_()

        self.setMinimumWidth(200)
        sp(self).v_max()

    @overrides
    def resizeEvent(self, event: QResizeEvent) -> None:
        self.btnType.setGeometry(self.width() // 2 - self.TYPE_SIZE // 2, 2, self.TYPE_SIZE, self.TYPE_SIZE)

    def refresh(self):
        self._refreshStyle()
        self.lineKeyPhrase.setText(self.backstory.keyphrase)
        self.textSummary.setPlainText(self.backstory.synopsis)

    def _refreshStyle(self):
        frame_color = EMOTION_COLORS.get(self.backstory.emotion, NEUTRAL_EMOTION_COLOR)
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

    def _iconChanged(self, icon: str):
        self.backstory.type_icon = icon
        self.btnType.setIcon(IconRegistry.from_name(self.backstory.type_icon, EMOTION_COLORS[self.backstory.emotion]))
        self.edited.emit()

    def _remove(self):
        if self.backstory.synopsis and not confirmed('This action cannot be undone.',
                                                     f'Are you sure you want to remove the event "{self.backstory.keyphrase if self.backstory.keyphrase else "Untitled"}"?'):
            return
        self.deleteRequested.emit(self)


# class BackstoryCardPlaceholder(QWidget):
#     def __init__(self, card: BackstoryCard, alignment: int = Qt.AlignmentFlag.AlignRight, parent=None,
#                  compact: bool = True):
#         super().__init__(parent)
#         self.alignment = alignment
#         self.card = card
#
#         self._layout = hbox(self, 0, 3)
#         self.spacer = spacer()
#         self.spacer.setFixedWidth(self.width() // 2 + 3)
#         if self.alignment == Qt.AlignmentFlag.AlignRight:
#             self.layout().addWidget(self.spacer)
#             if compact:
#                 self._layout.addWidget(self.card, alignment=Qt.AlignmentFlag.AlignLeft)
#             else:
#                 self._layout.addWidget(self.card)
#         elif self.alignment == Qt.AlignmentFlag.AlignLeft:
#             if compact:
#                 self._layout.addWidget(self.card, alignment=Qt.AlignmentFlag.AlignRight)
#             else:
#                 self._layout.addWidget(self.card)
#             self.layout().addWidget(self.spacer)
#         else:
#             self.layout().addWidget(self.card)


#
#     def toggleAlignment(self):
#         if self.alignment == Qt.AlignmentFlag.AlignLeft:
#             self.alignment = Qt.AlignmentFlag.AlignRight
#             self._layout.takeAt(0)
#             self._layout.addWidget(self.spacer)
#             self._layout.setAlignment(self.card, Qt.AlignmentFlag.AlignRight)
#         else:
#             self.alignment = Qt.AlignmentFlag.AlignLeft
#             self._layout.takeAt(1)
#             self._layout.insertWidget(0, self.spacer)
#             self._layout.setAlignment(self.card, Qt.AlignmentFlag.AlignLeft)


class _ControlButtons(QWidget):

    def __init__(self, theme: TimelineTheme, parent=None):
        super().__init__(parent)
        vbox(self)

        self.btnPlaceholderCircle = QToolButton(self)
        self.btnPlus = tool_btn(IconRegistry.plus_icon(RELAXED_WHITE_COLOR), tooltip='Add new event')

        self.layout().addWidget(self.btnPlaceholderCircle)
        self.layout().addWidget(self.btnPlus)

        self.btnPlus.setHidden(True)

        for btn in [self.btnPlaceholderCircle, self.btnPlus]:
            btn.setStyleSheet(f'''
                QToolButton {{ background-color: {theme.timeline_color}; border: 1px;
                        border-radius: 13px; padding: 2px;}}
                QToolButton:pressed {{background-color: grey;}}
            ''')

        self.installEventFilter(self)

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Enter:
            self.btnPlaceholderCircle.setHidden(True)
            self.btnPlus.setVisible(True)
        elif event.type() == QEvent.Type.Leave:
            self.btnPlaceholderCircle.setVisible(True)
            self.btnPlus.setHidden(True)

        return super().eventFilter(watched, event)


class BackstoryCardPlaceholder(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        vbox(self, 0, 0)
        self.wdgTop = QWidget()
        hbox(self.wdgTop)

        self.btnLeft = push_btn(IconRegistry.plus_icon('grey'), text='Add event to the left', transparent_=True)
        sp(self.btnLeft).h_exp()
        self.btnRight = push_btn(IconRegistry.plus_icon('grey'), text='Add event to the right', transparent_=True)
        sp(self.btnRight).h_exp()
        self.wdgTop.layout().addWidget(self.btnLeft)
        self.wdgTop.layout().addWidget(self.btnRight)

        self.btnWhole = push_btn(IconRegistry.plus_icon('grey'), text='Add main event', transparent_=True)
        sp(self.btnWhole).h_exp()

        self.layout().addWidget(self.wdgTop)
        self.layout().addWidget(self.btnWhole)


class TimelineWidget(QWidget):
    changed = pyqtSignal()

    def __init__(self, theme: Optional[TimelineTheme] = None, parent=None):
        super().__init__(parent)
        self._theme = theme if theme else TimelineTheme()

        vbox(self, spacing=0)

    @abstractmethod
    def events(self) -> List[BackstoryEvent]:
        pass

    def cardClass(self):
        return BackstoryCard

    def refresh(self):
        clear_layout(self)

        placeholder = BackstoryCardPlaceholder()
        self.layout().addWidget(placeholder)

        self.layout().addWidget(vspacer())

    @overrides
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor(self._theme.timeline_color)))
        painter.drawRect(int(self.width() / 2) - 3, 0, 6, self.height())

# class TimelineWidget(QWidget):
#     changed = pyqtSignal()
#
#     def __init__(self, theme: Optional[TimelineTheme] = None, parent=None, compact: bool = True):
#         self._spacers: List[QWidget] = []
#         super().__init__(parent)
#         if theme is None:
#             theme = TimelineTheme()
#         self._theme = theme
#         self._compact = compact
#         self._layout = vbox(self, spacing=0)
#         self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
#         self._lineTopMargin: int = 0
#         self._endSpacerMinHeight: int = 45
#
#     @overrides
#     def resizeEvent(self, event: QResizeEvent) -> None:
#         for sp in self._spacers:
#             sp.setFixedWidth(self.width() // 2 + 3)
#
#     @abstractmethod
#     def events(self) -> List[BackstoryEvent]:
#         pass
#
#     def cardClass(self):
#         return BackstoryCard
#
#     def refresh(self):
#         self._spacers.clear()
#         clear_layout(self.layout())
#
#         prev_alignment = None
#         for i, backstory in enumerate(self.events()):
#             if prev_alignment is None:
#                 alignment = Qt.AlignmentFlag.AlignRight
#             elif backstory.follow_up and prev_alignment:
#                 alignment = prev_alignment
#             elif prev_alignment == Qt.AlignmentFlag.AlignLeft:
#                 alignment = Qt.AlignmentFlag.AlignRight
#             else:
#                 alignment = Qt.AlignmentFlag.AlignLeft
#             prev_alignment = alignment
#             event = BackstoryCardPlaceholder(self.cardClass()(backstory, self._theme), alignment, parent=self,
#                                              compact=self._compact)
#             event.card.deleteRequested.connect(self._remove)
#
#             self._spacers.append(event.spacer)
#             event.spacer.setFixedWidth(self.width() // 2 + 3)
#
#             self._addControlButtons(i)
#             self._layout.addWidget(event)
#
#             event.card.edited.connect(self.changed.emit)
#             event.card.relationChanged.connect(self.changed.emit)
#             event.card.relationChanged.connect(self.refresh)
#
#         self._addControlButtons(-1)
#         spacer_ = vspacer()
#         spacer_.setMinimumHeight(self._endSpacerMinHeight)
#         self.layout().addWidget(spacer_)
#
#     @overrides
#     def paintEvent(self, event: QPaintEvent) -> None:
#         painter = QPainter(self)
#         painter.setRenderHint(QPainter.RenderHint.Antialiasing)
#         painter.setBrush(QBrush(QColor(self._theme.timeline_color)))
#         painter.drawRect(int(self.width() / 2) - 3, self._lineTopMargin, 6, self.height() - self._lineTopMargin)
#
#         painter.end()
#
#     def add(self, pos: int = -1):
#         backstory = BackstoryEvent('', '', type_color=NEUTRAL_EMOTION_COLOR)
#         if pos >= 0:
#             self.events().insert(pos, backstory)
#         else:
#             self.events().append(backstory)
#         self.refresh()
#         self.changed.emit()
#
#     def _remove(self, card: BackstoryCard):
#         self.events().remove(card.backstory)
#
#         self.refresh()
#         self.changed.emit()
#
#     def _addControlButtons(self, pos: int):
#         control = _ControlButtons(self._theme, self)
#         control.btnPlus.clicked.connect(partial(self.add, pos))
#         self._layout.addWidget(control, alignment=Qt.AlignmentFlag.AlignHCenter)
