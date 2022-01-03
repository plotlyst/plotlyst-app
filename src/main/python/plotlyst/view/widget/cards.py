"""
Plotlyst
Copyright (C) 2021-2022  Zsolt Kovari

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
import pickle
from abc import abstractmethod
from typing import Optional, List

import emoji
from PyQt6 import QtGui
from PyQt6.QtCore import pyqtSignal, QSize, Qt, QEvent, QPoint, QMimeData, QByteArray
from PyQt6.QtGui import QIcon, QMouseEvent, QDrag, QDragEnterEvent, QDragMoveEvent, QDropEvent, QAction
from PyQt6.QtWidgets import QFrame, QApplication
from fbs_runtime import platform
from overrides import overrides

from src.main.python.plotlyst.common import PIVOTAL_COLOR
from src.main.python.plotlyst.core.domain import NovelDescriptor, Character, Scene, SceneType, Document
from src.main.python.plotlyst.view.common import emoji_font, PopupMenuBuilder
from src.main.python.plotlyst.view.generated.character_card_ui import Ui_CharacterCard
from src.main.python.plotlyst.view.generated.journal_card_ui import Ui_JournalCard
from src.main.python.plotlyst.view.generated.novel_card_ui import Ui_NovelCard
from src.main.python.plotlyst.view.generated.scene_card_ui import Ui_SceneCard
from src.main.python.plotlyst.view.icons import IconRegistry, set_avatar, avatars
from src.main.python.plotlyst.view.layout import FlowLayout
from src.main.python.plotlyst.view.widget.labels import CharacterAvatarLabel


class CardMimeData(QMimeData):
    def __init__(self, card: 'Card'):
        super().__init__()
        self.card = card


class Card(QFrame):
    selected = pyqtSignal(object)
    doubleClicked = pyqtSignal(object)
    dropped = pyqtSignal(object, object)

    def __init__(self, parent):
        super().__init__(parent)
        self.dragStartPosition: Optional[QPoint] = None
        self._dragEnabled: bool = True
        self._popup_actions: List[QAction] = []

    def isDragEnabled(self) -> bool:
        return self._dragEnabled

    def setDragEnabled(self, enabled: bool):
        self._dragEnabled = enabled

    @overrides
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._dragEnabled and event.button() == Qt.MouseButton.LeftButton:
            self.dragStartPosition = event.pos()
        else:
            self.dragStartPosition = None
        super(Card, self).mousePressEvent(event)

    @overrides
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._dragEnabled:
            return
        if not event.buttons() & Qt.MouseButton.LeftButton:
            return
        if not self.dragStartPosition:
            return
        if (event.pos() - self.dragStartPosition).manhattanLength() < QApplication.startDragDistance():
            return

        drag = QDrag(self)
        mimeData = CardMimeData(self)
        mimeData.setData(self.mimeType(), QByteArray(pickle.dumps(self.objectName())))
        drag.setPixmap(self.grab())
        drag.setMimeData(mimeData)
        drag.exec(Qt.DropAction.MoveAction)

    @overrides
    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        self.select()

    @overrides
    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        self.select()
        self.doubleClicked.emit(self)

    @overrides
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        event.acceptProposedAction()

    @overrides
    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if event.mimeData().hasFormat(self.mimeType()):
            event.acceptProposedAction()
        else:
            event.ignore()

    @overrides
    def dropEvent(self, event: QDropEvent) -> None:
        if isinstance(event.mimeData(), CardMimeData):
            if event.mimeData().card is self:
                event.ignore()
                return

            self.dropped.emit(event.mimeData().card, self)
            event.acceptProposedAction()
        else:
            event.ignore()

    def setPopupMenuActions(self, actions: List[QAction]):
        self._popup_actions = actions
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._contextMenuRequested)

    def select(self):
        self._setStyleSheet(selected=True)
        self.selected.emit(self)

    def clearSelection(self):
        self._setStyleSheet()

    @abstractmethod
    def mimeType(self) -> str:
        pass

    def _setStyleSheet(self, selected: bool = False):
        border_color = self._borderColor(selected)
        border_size = self._borderSize(selected)
        background_color = self._bgColor(selected)
        self.setStyleSheet(f'''
           QFrame[mainFrame=true] {{
               border: {border_size}px solid {border_color};
               border-radius: 15px;
               background-color: {background_color};
           }}''')

    def _bgColor(self, selected: bool = False) -> str:
        return '#dec3c3' if selected else '#f9f4f4'

    def _borderSize(self, selected: bool = False) -> int:
        return 4 if selected else 2

    def _borderColor(self, selected: bool = False) -> str:
        return '#2a4d69' if selected else '#adcbe3'

    def _contextMenuRequested(self, pos: QPoint):
        self.select()
        builder = PopupMenuBuilder.from_widget_position(self, pos)
        for action in self._popup_actions:
            action.setParent(builder.menu)
            builder.menu.addAction(action)
        builder.popup()


class NovelCard(Ui_NovelCard, Card):

    def __init__(self, novel: NovelDescriptor, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.novel = novel
        self.textName.setText(self.novel.title)
        self.textName.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._setStyleSheet()

    def refresh(self):
        self.textName.setText(self.novel.title)

    @overrides
    def mimeType(self) -> str:
        return 'application/novel-card'


class CharacterCard(Ui_CharacterCard, Card):

    def __init__(self, character: Character, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.character = character
        self.textName.setContentsMargins(0, 0, 0, 0)
        self.textName.document().setDocumentMargin(0)
        self.textName.setText(self.character.name)
        self.textName.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_avatar(self.lblPic, self.character, size=118)

        enneagram = self.character.enneagram()
        if enneagram:
            self.lblEnneagram.setPixmap(
                IconRegistry.from_name(enneagram.icon, enneagram.icon_color).pixmap(QSize(28, 28)))
        role = self.character.role()
        if role:
            self.lblRole.setPixmap(IconRegistry.from_name(role.icon, role.icon_color).pixmap(QSize(24, 24)))
        self._setStyleSheet()

    @overrides
    def mimeType(self) -> str:
        return 'application/character-card'


class JournalCard(Card, Ui_JournalCard):

    def __init__(self, journal: Document, parent=None):
        super(JournalCard, self).__init__(parent)
        self.setupUi(self)
        self.journal = journal

        self.refresh()
        self.textTitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._setStyleSheet()
        self.setDragEnabled(False)

    @overrides
    def mimeType(self) -> str:
        return 'application/journal-card'

    def refresh(self):
        self.textTitle.setText(self.journal.title)


class SceneCard(Ui_SceneCard, Card):
    def __init__(self, scene: Scene, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.scene = scene

        self.wdgCharacters.layout().setSpacing(1)

        self.textTitle.setFontPointSize(QApplication.font().pointSize() + 1)
        self.textTitle.setText(self.scene.title)
        self.textTitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btnPov.clicked.connect(self.select)
        self.btnComments.clicked.connect(self.select)

        if scene.pov:
            self.btnPov.setIcon(QIcon(avatars.pixmap(scene.pov)))
        for char in scene.characters:
            self.wdgCharacters.addLabel(CharacterAvatarLabel(char, 20))

        if self.scene.beat:
            if self.scene.beat.icon:
                self.lblBeatEmoji.setPixmap(
                    IconRegistry.from_name(self.scene.beat.icon, self.scene.beat.icon_color).pixmap(24, 24))
            else:
                if platform.is_windows():
                    self._emoji_font = emoji_font(14)
                else:
                    self._emoji_font = emoji_font(20)
                self.lblBeatEmoji.setFont(self._emoji_font)
                self.lblBeatEmoji.setText(emoji.emojize(':performing_arts:'))
        else:
            self.lblBeatEmoji.clear()
            self.lblBeatEmoji.setHidden(True)

        if any([x.major for x in scene.comments]):
            self.btnComments.setIcon(IconRegistry.from_name('fa5s.comment', color='#fb8b24'))
        else:
            self.btnComments.setHidden(True)

        if self.scene.type == SceneType.ACTION:
            self.lblType.setPixmap(
                IconRegistry.action_scene_icon(self.scene.outcome_resolution(), self.scene.outcome_trade_off()).pixmap(
                    QSize(24, 24, )))
        elif self.scene.type == SceneType.REACTION:
            self.lblType.setPixmap(IconRegistry.reaction_scene_icon().pixmap(QSize(24, 24, )))
        else:
            self.lblType.clear()

        self._setStyleSheet()

    @overrides
    def mimeType(self) -> str:
        return 'application/scene-card'

    @overrides
    def enterEvent(self, event: QEvent) -> None:
        self.wdgCharacters.setEnabled(True)

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        self.wdgCharacters.setEnabled(False)

    @overrides
    def _borderSize(self, selected: bool = False) -> int:
        if self.scene.beat:
            return 7 if selected else 5
        return super(SceneCard, self)._borderSize(selected)

    @overrides
    def _borderColor(self, selected: bool = False) -> str:
        if self.scene.beat:
            return '#6b7d7d' if selected else PIVOTAL_COLOR
        return super(SceneCard, self)._borderColor(selected)


class CardsView(QFrame):
    swapped = pyqtSignal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = FlowLayout(spacing=9)
        self.setLayout(self._layout)
        self.setAcceptDrops(True)

    @overrides
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        event.acceptProposedAction()
        super(CardsView, self).dragEnterEvent(event)

    @overrides
    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        event.acceptProposedAction()

    def clear(self):
        self._layout.clear()

    def addCard(self, card: Card):
        card.setAcceptDrops(True)
        card.dropped.connect(self.swapped.emit)
        self._layout.addWidget(card)

    def cardAt(self, pos: int) -> Optional[Card]:
        item = self._layout.itemAt(pos)
        if item and item.widget():
            return item.widget()
