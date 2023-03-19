"""
Plotlyst
Copyright (C) 2021-2023  Zsolt Kovari

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
from enum import Enum
from functools import partial
from typing import Optional, List, Dict, Iterable, Set, Any

import qtanim
from PyQt6 import QtGui
from PyQt6.QtCore import pyqtSignal, QSize, Qt, QEvent, QPoint, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QColor, QAction
from PyQt6.QtWidgets import QFrame, QApplication, QToolButton
from overrides import overrides
from qtframes import Frame
from qthandy import clear_layout, retain_when_hidden, transparent, margins, flow
from qthandy.filter import DragEventFilter, DropEventFilter

from src.main.python.plotlyst.common import act_color
from src.main.python.plotlyst.core.domain import NovelDescriptor, Character, Scene, Novel
from src.main.python.plotlyst.core.help import enneagram_help, mbti_help
from src.main.python.plotlyst.service.cache import acts_registry
from src.main.python.plotlyst.service.persistence import RepositoryPersistenceManager
from src.main.python.plotlyst.view.generated.character_card_ui import Ui_CharacterCard
from src.main.python.plotlyst.view.generated.novel_card_ui import Ui_NovelCard
from src.main.python.plotlyst.view.generated.scene_card_ui import Ui_SceneCard
from src.main.python.plotlyst.view.icons import IconRegistry, set_avatar, avatars
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
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.select)
        self.dragStartPosition: Optional[QPoint] = None
        self._dragEnabled: bool = True
        self._popup_actions: List[QAction] = []

    def isDragEnabled(self) -> bool:
        return self._dragEnabled

    def setDragEnabled(self, enabled: bool):
        self._dragEnabled = enabled

    @overrides
    def enterEvent(self, event: QEvent) -> None:
        qtanim.glow(self, color=QColor('#0096c7'))

    @overrides
    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        self.select()

    @overrides
    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        self.select()
        self.doubleClicked.emit(self)

    def select(self):
        self._setStyleSheet(selected=True)
        self.selected.emit(self)

    def clearSelection(self):
        self._setStyleSheet()

    @abstractmethod
    def mimeType(self) -> str:
        pass

    @abstractmethod
    def data(self) -> Any:
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


class NovelCard(Ui_NovelCard, Card):

    def __init__(self, novel: NovelDescriptor, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.novel = novel
        self._setStyleSheet()
        self.refresh()

    def refresh(self):
        self.textName.setText(self.novel.title)
        self.textName.setAlignment(Qt.AlignmentFlag.AlignCenter)

    @overrides
    def mimeType(self) -> str:
        return 'application/novel-card'

    @overrides
    def data(self) -> Any:
        return self.novel


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

        transparent(self.btnEnneagram)
        enneagram = self.character.enneagram()
        if enneagram:
            self.btnEnneagram.setIcon(IconRegistry.from_name(enneagram.icon, enneagram.icon_color))
            self.btnEnneagram.setToolTip(enneagram_help[enneagram.text])
        mbti = self.character.mbti()
        if mbti:
            self.btnMbti.setStyleSheet(f'color: {mbti.icon_color};border:0px;')
            self.btnMbti.setText(mbti.text)
            self.btnMbti.setIcon(IconRegistry.from_name(mbti.icon, mbti.icon_color))
            self.btnMbti.setToolTip(mbti_help[mbti.text])

        retain_when_hidden(self.iconRole)
        self.iconRole.setHidden(self.character.prefs.avatar.use_role)
        if self.character.role and not self.character.prefs.avatar.use_role:
            self.iconRole.setRole(self.character.role)
            self.iconRole.setToolTip(self.character.role.text)
        self._setStyleSheet()

    @overrides
    def mimeType(self) -> str:
        return 'application/character-card'

    @overrides
    def data(self) -> Any:
        return self.character


class SceneCard(Ui_SceneCard, Card):
    cursorEntered = pyqtSignal()

    def __init__(self, scene: Scene, novel: Novel, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.scene = scene
        self.novel = novel

        self.wdgCharacters.layout().setSpacing(1)

        self.textTitle.setFontPointSize(QApplication.font().pointSize() + 1)
        self.textTitle.setText(self.scene.title_or_index(self.novel))
        self.textTitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.textSynopsis.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.textSynopsis.setText(scene.synopsis)

        self.btnPov.clicked.connect(self.select)
        self.btnStage.clicked.connect(self.select)

        if scene.pov:
            self.btnPov.setIcon(avatars.avatar(scene.pov))
        for char in scene.characters:
            self.wdgCharacters.addLabel(CharacterAvatarLabel(char, 20))

        self._beatFrame = Frame(self)
        self.btnBeat = QToolButton()
        transparent(self.btnBeat)
        self.btnBeat.setIconSize(QSize(24, 24))
        self._beatFrame.setWidget(self.btnBeat)
        self._beatFrame.setGeometry(self.width() - 30, 0, self._beatFrame.width(), self._beatFrame.height())

        beat = self.scene.beat(self.novel)
        if beat and beat.icon:
            self.btnBeat.setIcon(IconRegistry.from_name(beat.icon, beat.icon_color))
            self._beatFrame.setFrameColor(QColor(act_color(beat.act)))
            self._beatFrame.setBackgroundColor(Qt.GlobalColor.white)
            margins(self._beatFrame, 0, 0, 0, 0)
        else:
            self._beatFrame.setHidden(True)

        icon = IconRegistry.scene_type_icon(self.scene)
        if icon:
            self.lblType.setPixmap(icon.pixmap(QSize(24, 24)))
        else:
            self.lblType.clear()

        self.btnStage.setScene(self.scene)

        self._setStyleSheet()

        self.repo = RepositoryPersistenceManager.instance()

    @overrides
    def mimeType(self) -> str:
        return 'application/scene-card'

    @overrides
    def data(self) -> Any:
        return self.scene

    @overrides
    def enterEvent(self, event: QEvent) -> None:
        super(SceneCard, self).enterEvent(event)
        self.wdgCharacters.setEnabled(True)
        if not self.btnStage.stageOk():
            self.btnStage.setVisible(True)
        self.cursorEntered.emit()

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        self.wdgCharacters.setEnabled(False)
        if not self.btnStage.stageOk() and not self.btnStage.menu().isVisible():
            self.btnStage.setHidden(True)

    @overrides
    def showEvent(self, event: QtGui.QShowEvent) -> None:
        self.btnStage.setVisible(self.btnStage.stageOk())

    @overrides
    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        w = event.size().width()
        self._adjustToWidth(w)

    @overrides
    def setFixedSize(self, w: int, h: int) -> None:
        super(SceneCard, self).setFixedSize(w, h)
        self._adjustToWidth(w)

    def _adjustToWidth(self, w):
        self.textSynopsis.setVisible(w > 170)
        self.lineAfterTitle.setVisible(w > 170)
        self.lineAfterTitle.setFixedWidth(w - 30)

        self._beatFrame.setGeometry(w - 40, 0, 40, 50)


class CardSizeRatio(Enum):
    RATIO_2_3 = 0
    RATIO_3_4 = 1


class CardFilter:
    def filter(self, card: Card) -> bool:
        return True


class SceneCardFilter(CardFilter):

    def __init__(self):
        super(SceneCardFilter, self).__init__()
        self._actsFilter: Dict[int, bool] = {}
        self._povs: Set[Character] = set()

    @overrides
    def filter(self, card: SceneCard) -> bool:
        if not self._actsFilter[acts_registry.act(card.scene)]:
            return False

        if card.scene.pov and card.scene.pov not in self._povs:
            return False

        return True

    def setActsFilter(self, actsFilter: Dict[int, bool]):
        self._actsFilter.clear()
        self._actsFilter.update(actsFilter)

    def setActivePovs(self, characters: Iterable[Character]):
        self._povs.clear()
        self._povs.update(set(characters))


class CardsView(QFrame):
    swapped = pyqtSignal(object, object)
    selectionCleared = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cards: Dict[Any, Card] = {}
        self._layout = flow(self, 9, 15)
        self.setAcceptDrops(True)
        self._droppedTo: Optional[Card] = None
        self._selected: Optional[Card] = None
        self._cardsWidth: int = 135
        self._cardsRatio = CardSizeRatio.RATIO_3_4

    @overrides
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        event.acceptProposedAction()
        super(CardsView, self).dragEnterEvent(event)

    @overrides
    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        event.acceptProposedAction()

    @overrides
    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        if self._selected:
            self._selected.clearSelection()
            self._selected = None
            self.selectionCleared.emit()

    def clear(self):
        self._selected = None
        self._cards.clear()
        clear_layout(self._layout)

    def addCard(self, card: Card):
        card.setAcceptDrops(True)
        if card.isDragEnabled():
            card.installEventFilter(DragEventFilter(card, card.mimeType(), lambda x: card.data(), hideTarget=True,
                                                    finishedSlot=partial(self._dragFinished, card)))
        card.selected.connect(self._cardSelected)
        card.installEventFilter(DropEventFilter(card, [card.mimeType()], droppedSlot=partial(self._dropped, card)))
        card.dropped.connect(self.swapped.emit)

        self._layout.addWidget(card)
        self._cards[card.data()] = card
        self._resizeCard(card)

    def cardAt(self, pos: int) -> Optional[Card]:
        item = self._layout.itemAt(pos)
        if item and item.widget():
            return item.widget()

    def setCardsWidth(self, value: int):
        self._cardsWidth = value
        self._resizeAllCards()

    def setCardsSizeRatio(self, ratio: CardSizeRatio):
        self._cardsRatio = ratio
        self._resizeAllCards()

    def applyFilter(self, cardFilter: CardFilter):
        for card in self._cards.values():
            card.setVisible(cardFilter.filter(card))

    def _resizeAllCards(self):
        for card in self._cards.values():
            self._resizeCard(card)

    def _resizeCard(self, card: Card):
        if self._cardsRatio == CardSizeRatio.RATIO_3_4:
            height = self._cardsWidth * 1.3
        else:
            height = self._cardsWidth / 2 * 3
        card.setFixedSize(self._cardsWidth, int(height))

    def _cardSelected(self, card: Card):
        self._selected = card

    def _dropped(self, card: Card, _: QMimeData):
        self._droppedTo = card

    def _dragFinished(self, card: Card):
        if self._droppedTo is not None:
            card.setHidden(True)
            self.swapped.emit(card, self._droppedTo)
            self._droppedTo = None
