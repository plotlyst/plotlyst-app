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
from typing import Optional, List, Dict, Iterable, Set, Any

import qtanim
from PyQt6 import QtGui
from PyQt6.QtCore import pyqtSignal, QSize, Qt, QEvent, QPoint, QMimeData, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDragMoveEvent, QColor, QAction, QIcon
from PyQt6.QtWidgets import QFrame, QApplication, QToolButton, QTextBrowser, QWidget
from overrides import overrides
from qthandy import clear_layout, retain_when_hidden, transparent, flow, translucent, gc, incr_icon, vbox, pointy, \
    incr_font, hbox, margins
from qthandy.filter import DragEventFilter, DropEventFilter, OpacityEventFilter
from qtmenu import MenuWidget

from plotlyst.common import PLOTLYST_SECONDARY_COLOR, RELAXED_WHITE_COLOR
from plotlyst.core.domain import Character, Scene, Novel, NovelSetting, CardSizeRatio, NovelDescriptor, LayoutType
from plotlyst.core.help import enneagram_help, mbti_help
from plotlyst.env import app_env
from plotlyst.service.cache import acts_registry
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import fade, fade_in, fade_out, tool_btn, push_btn, action
from plotlyst.view.generated.character_card_ui import Ui_CharacterCard
from plotlyst.view.generated.scene_card_ui import Ui_SceneCard
from plotlyst.view.icons import IconRegistry, set_avatar, avatars
from plotlyst.view.style.button import apply_button_palette_color
from plotlyst.view.widget.button import DotsMenuButton
from plotlyst.view.widget.display import Icon
from plotlyst.view.widget.labels import CharacterAvatarLabel


class CardMimeData(QMimeData):
    def __init__(self, card: 'Card'):
        super().__init__()
        self.card = card


class Card(QFrame):
    selected = pyqtSignal()
    doubleClicked = pyqtSignal()
    cursorEntered = pyqtSignal()
    cursorLeft = pyqtSignal()

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
        color = QColor(PLOTLYST_SECONDARY_COLOR)
        color.setAlpha(175)
        qtanim.glow(self, color=color, radius=12, reverseAnimation=False)

        self.cursorEntered.emit()

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        if self.isEnabled() and self.isVisible():  # protect against deletion
            color = QColor(PLOTLYST_SECONDARY_COLOR)
            color.setAlpha(175)
            qtanim.glow(self, color=color, radius=0, startRadius=12, reverseAnimation=False,
                        teardown=lambda: self.setGraphicsEffect(None))
            self.cursorLeft.emit()

    @overrides
    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        self.select()

    @overrides
    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        self.select()
        self.doubleClicked.emit()

    def select(self):
        self._setStyleSheet(selected=True)
        self.selected.emit()

    def clearSelection(self):
        self._setStyleSheet()

    def refresh(self):
        self.setGraphicsEffect(None)

    def quickRefresh(self):
        pass

    @abstractmethod
    def mimeType(self) -> str:
        pass

    @abstractmethod
    def data(self) -> Any:
        pass

    @abstractmethod
    def copy(self) -> 'Card':
        pass

    def _setStyleSheet(self, selected: bool = False):
        border_color = self._borderColor(selected)
        border_size = self._borderSize(selected)
        background_color = self._bgColor(selected)
        self.setStyleSheet(f'''
           Card {{
               border: {border_size}px solid {border_color};
               border-radius: 15px;
               background-color: {background_color};
           }}''')

    def _bgColor(self, selected: bool = False) -> str:
        return '#dec3c3' if selected else '#f3e8e8'

    def _borderSize(self, selected: bool = False) -> int:
        return 4 if selected else 2

    def _borderColor(self, selected: bool = False) -> str:
        return PLOTLYST_SECONDARY_COLOR if selected else 'lightgrey'


class CharacterCard(Ui_CharacterCard, Card):

    def __init__(self, character: Character, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.character = character
        self.textName.setContentsMargins(0, 0, 0, 0)
        self.textName.document().setDocumentMargin(0)

        transparent(self.btnEnneagram)
        retain_when_hidden(self.iconRole)

        self._setStyleSheet()
        self.refresh()

    @overrides
    def mimeType(self) -> str:
        return 'application/character-card'

    @overrides
    def data(self) -> Any:
        return self.character

    @overrides
    def copy(self) -> 'Card':
        return CharacterCard(self.character)

    @overrides
    def refresh(self):
        super().refresh()
        self.textName.setText(self.character.displayed_name())
        self.textName.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_avatar(self.lblPic, self.character, size=118)

        enneagram = self.character.enneagram()
        if enneagram:
            self.btnEnneagram.setIcon(IconRegistry.from_name(enneagram.icon, enneagram.icon_color))
            self.btnEnneagram.setToolTip(enneagram_help[enneagram.text])
        mbti = self.character.mbti()
        if mbti:
            apply_button_palette_color(self.btnMbti, mbti.icon_color)
            self.btnMbti.setText(mbti.text)
            self.btnMbti.setIcon(IconRegistry.from_name(mbti.icon, mbti.icon_color))
            self.btnMbti.setToolTip(mbti_help[mbti.text])

        self.iconRole.setHidden(self.character.prefs.avatar.use_role)
        if self.character.role and not self.character.prefs.avatar.use_role:
            self.iconRole.setRole(self.character.role)
            self.iconRole.setToolTip(self.character.role.text)


class SceneCard(Ui_SceneCard, Card):
    def __init__(self, scene: Scene, novel: Novel, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.scene = scene
        self.novel = novel

        self.wdgCharacters.layout().setSpacing(1)

        self.textTitle.setFontPointSize(QApplication.font().pointSize() + 1)

        self.textSynopsis.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btnPov.clicked.connect(self.select)
        self.btnStage.clicked.connect(self.select)
        self.btnStage.setActiveColor('grey')

        self.btnBeat = QToolButton(self)
        self.btnBeat.setIconSize(QSize(28, 28))
        transparent(self.btnBeat)

        self._setStyleSheet()
        self.refresh()

        self._stageVisible = self.novel.prefs.toggled(NovelSetting.SCENE_CARD_STAGE)
        self.btnPov.setVisible(self.novel.prefs.toggled(NovelSetting.SCENE_CARD_POV))
        self.lblType.setVisible(
            self.novel.prefs.toggled(NovelSetting.SCENE_CARD_PURPOSE, default=False) and app_env.profile().get('scene-purpose', False))
        self.btnPlotProgress.setVisible(
            self.novel.prefs.toggled(NovelSetting.SCENE_CARD_PLOT_PROGRESS) and app_env.profile().get(
                'scene-progression', False))

        incr_icon(self.btnPlotProgress, 4)

        self.repo = RepositoryPersistenceManager.instance()

    @overrides
    def mimeType(self) -> str:
        return 'application/scene-card'

    @overrides
    def refresh(self):
        super().refresh()
        self.quickRefresh()
        self.textSynopsis.setText(self.scene.synopsis)

        self.refreshPov()
        self.wdgCharacters.setEnabled(False)
        self.refreshCharacters()
        self.refreshBeat()

        icon = IconRegistry.scene_type_icon(self.scene)
        if icon:
            self.lblType.setPixmap(icon.pixmap(QSize(24, 24)))
        else:
            self.lblType.clear()

        if self.scene.plot_pos_progress or self.scene.plot_neg_progress:
            self.btnPlotProgress.setIcon(
                IconRegistry.plot_charge_icon(self.scene.plot_pos_progress, self.scene.plot_neg_progress))
        elif self.scene.progress:
            self.btnPlotProgress.setIcon(IconRegistry.charge_icon(self.scene.progress))
        else:
            self.btnPlotProgress.setIcon(QIcon())

        self.btnStage.setScene(self.scene, self.novel)

    def refreshPov(self):
        if self.scene.pov:
            self.btnPov.setIcon(avatars.avatar(self.scene.pov))
        else:
            self.btnPov.setIcon(QIcon())

    def refreshCharacters(self):
        clear_layout(self.wdgCharacters)
        for char in self.scene.characters:
            self.wdgCharacters.addLabel(CharacterAvatarLabel(char, 20))

    def refreshBeat(self):
        beat = self.scene.beat(self.novel)
        if beat:
            icon = beat.icon if beat.icon else f'ri.number-{beat.seq}'
            self.btnBeat.setIcon(IconRegistry.scene_beat_badge_icon(icon, beat.icon_color, beat.icon_color))
            self.btnBeat.setToolTip(beat.text)
            self.btnBeat.setVisible(True)
        else:
            self.btnBeat.setHidden(True)

    @overrides
    def quickRefresh(self):
        self.textTitle.setText(self.scene.title_or_index(self.novel))
        self.textTitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

    @overrides
    def data(self) -> Any:
        return self.scene

    @overrides
    def copy(self) -> 'Card':
        return SceneCard(self.scene, self.novel)

    def setSetting(self, setting: NovelSetting, value: Any):
        if setting == NovelSetting.SCENE_CARD_POV:
            # self.btnPov.setVisible(value)
            fade(self.btnPov, value)
        elif setting == NovelSetting.SCENE_CARD_PURPOSE:
            fade(self.lblType, value)
        elif setting == NovelSetting.SCENE_CARD_PLOT_PROGRESS:
            fade(self.btnPlotProgress, value)
        elif setting == NovelSetting.SCENE_CARD_STAGE:
            self._stageVisible = value
            if self._stageVisible:
                if self.btnStage.stageOk():
                    fade_in(self.btnStage)
            else:
                fade_out(self.btnStage)

    @overrides
    def enterEvent(self, event: QEvent) -> None:
        super(SceneCard, self).enterEvent(event)
        if self._stageVisible:
            self.btnStage.setVisible(True)

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        super().leaveEvent(event)
        if not self._stageVisible:
            self.btnStage.setHidden(True)
        elif not self.btnStage.stageOk() and not self.btnStage.menu().isVisible():
            self.btnStage.setHidden(True)

    @overrides
    def showEvent(self, event: QtGui.QShowEvent) -> None:
        if self._stageVisible:
            self.btnStage.setVisible(self.btnStage.stageOk())
        else:
            self.btnStage.setHidden(True)

    @overrides
    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        w = event.size().width()
        self._adjustToWidth(w)

    @overrides
    def setFixedSize(self, w: int, h: int) -> None:
        super(SceneCard, self).setFixedSize(w, h)
        self._adjustToWidth(w)

    def _adjustToWidth(self, w: int):
        self.textSynopsis.setVisible(w > 170)
        self.lineAfterTitle.setVisible(w > 170)
        self.lineAfterTitle.setFixedWidth(w - 30)

        self.btnBeat.setGeometry(w - self.btnBeat.sizeHint().width(), 0, self.btnBeat.sizeHint().width(),
                                 self.btnBeat.sizeHint().height() + 5)


class NovelCard(Card):
    detach = pyqtSignal()

    def __init__(self, novel: NovelDescriptor, parent=None):
        super().__init__(parent)
        self.novel = novel

        self.btnSettings = DotsMenuButton(self)
        self.btnSettings.setGeometry(135, 5, 20, 20)

        menu = MenuWidget(self.btnSettings)
        menu.addAction(action('Detach novel from series', IconRegistry.from_name('fa5s.unlink'), slot=self.detach))

        self.textTitle = QTextBrowser()
        transparent(self.textTitle)
        incr_font(self.textTitle, 4)
        self.textTitle.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textTitle.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textTitle.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.textTitle.setContentsMargins(0, 0, 0, 0)
        self.textTitle.document().setDocumentMargin(0)

        self.icon = Icon()
        self.icon.setIconSize(QSize(32, 32))
        translucent(self.icon, 0.8)

        self.btnOpen = push_btn(IconRegistry.book_icon(RELAXED_WHITE_COLOR, RELAXED_WHITE_COLOR), 'Open',
                                properties=['positive', 'confirm'])

        vbox(self, margin=5)
        # self.layout().addWidget(self.btnSettings, alignment=Qt.AlignmentFlag.AlignRight)
        self.layout().addWidget(self.icon, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.textTitle)
        self.layout().addWidget(self.btnOpen, alignment=Qt.AlignmentFlag.AlignRight)

        self.btnSettings.setHidden(True)
        self.btnOpen.setHidden(True)

        self._setStyleSheet()
        self.refresh()

    @overrides
    def enterEvent(self, event: QEvent) -> None:
        super().enterEvent(event)
        fade_in(self.btnSettings)
        fade_in(self.btnOpen)

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        super().leaveEvent(event)
        self.btnSettings.setHidden(True)
        self.btnOpen.setHidden(True)

    @overrides
    def mimeType(self) -> str:
        return 'application/novel-card'

    @overrides
    def data(self) -> Any:
        return self.novel

    @overrides
    def copy(self) -> 'Card':
        return NovelCard(self.novel)

    @overrides
    def refresh(self):
        super().refresh()
        self.textTitle.setText(self.novel.title)
        self.textTitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.novel.icon:
            self.icon.setIcon(IconRegistry.from_name(self.novel.icon))
        else:
            self.icon.setIcon(IconRegistry.book_icon())


class PlaceholderCard(Card):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(False)
        self._dragEnabled = False
        vbox(self)
        pointy(self)

        self.btnPlus = tool_btn(IconRegistry.plus_icon('lightgrey'), transparent_=True)
        self.btnPlus.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.btnPlus.setIconSize(QSize(124, 124))
        self.btnPlus.clicked.connect(self.selected)

        self.layout().addWidget(self.btnPlus, alignment=Qt.AlignmentFlag.AlignCenter)
        self.installEventFilter(OpacityEventFilter(self, leaveOpacity=0.5, enterOpacity=0.6))

        self._setStyleSheet()

    @overrides
    def enterEvent(self, event: QEvent) -> None:
        pass

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        pass

    @overrides
    def mimeType(self) -> str:
        pass

    @overrides
    def data(self) -> Any:
        pass

    @overrides
    def copy(self) -> 'Card':
        pass

    @overrides
    def _setStyleSheet(self, selected: bool = False):
        self.setStyleSheet('''
                   Card {
                       border: 2px dotted grey;
                       border-radius: 15px;
                   }''')


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
        if not self._actsFilter.get(acts_registry.act(card.scene), True):
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

    def resetActsFilter(self):
        self._actsFilter.clear()


class CardsView(QFrame):
    cardSelected = pyqtSignal(Card)
    cardEntered = pyqtSignal(Card)
    cardLeft = pyqtSignal(Card)
    cardDoubleClicked = pyqtSignal(Card)
    cardCustomContextMenuRequested = pyqtSignal(Card, QPoint)
    orderChanged = pyqtSignal(list, Card)  # dropped Card
    selectionCleared = pyqtSignal()

    def __init__(self, parent=None, layoutType: LayoutType = LayoutType.FLOW, margin: int = 9, spacing: int = 15):
        super().__init__(parent)
        self._cards: Dict[Any, Card] = {}
        self._margin = margin
        self._spacing = spacing
        if layoutType == LayoutType.FLOW:
            self._layout = flow(self, self._margin, self._spacing)
            margins(self, left=15, top=15)
        elif layoutType == LayoutType.VERTICAL:
            self._layout = vbox(self, self._margin, self._spacing)
        elif layoutType == LayoutType.HORIZONTAL:
            self._layout = hbox(self, self._margin, self._spacing)

        self.setAcceptDrops(True)
        self._droppedTo: Optional[Card] = None
        self._selected: Optional[Card] = None
        self._cardsWidth: int = 135
        self._cardsRatio = CardSizeRatio.RATIO_3_4
        self._dragPlaceholder: Optional[Card] = None
        self._dragged: Optional[Card] = None
        self._wasDropped = False

    @overrides
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        event.acceptProposedAction()
        super(CardsView, self).dragEnterEvent(event)

    @overrides
    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        event.acceptProposedAction()

    @overrides
    def mouseReleaseEvent(self, a0: QtGui.QMouseEvent) -> None:
        self.clearSelection()

    def clearSelection(self):
        if self._selected:
            self._selected.clearSelection()
            self._selected = None
            self.selectionCleared.emit()

    def clear(self):
        self._selected = None
        self._cards.clear()
        clear_layout(self._layout)

    def addCard(self, card: Card, alignment=None):
        self._initCardWidget(card)
        if alignment:
            self._layout.addWidget(card, alignment=alignment)
        else:
            self._layout.addWidget(card)

    def insertAfter(self, ref: Card, card: Card):
        self._initCardWidget(card)
        i = self._layout.indexOf(ref)
        self._layout.insertWidget(i + 1, card)

    def insertAt(self, index: int, card: Card):
        self._initCardWidget(card)
        self._layout.insertWidget(index, card)

    def remove(self, obj: Any):
        self._selected = None
        card = self._cards.pop(obj, None)
        if card:
            card.setDisabled(True)
            card.setVisible(False)
            self._layout.removeWidget(card)
            gc(card)

        for card in self._cards.values():
            card.quickRefresh()

    def reorderCards(self, data: List[Any]):
        self._selected = None
        clear_layout(self._layout, auto_delete=False)

        for obj in data:
            card = self._cards.get(obj)
            if card:
                self._layout.addWidget(card)
                card.quickRefresh()

    def selectCard(self, ref: Any):
        card = self._cards.get(ref, None)
        if card is not None:
            card.select()

    def cardAt(self, pos: int) -> Optional[Card]:
        item = self._layout.itemAt(pos)
        if item and item.widget():
            return item.widget()

    def card(self, item: Any) -> Optional[Card]:
        return self._cards.get(item, None)

    def cards(self) -> Iterable[Card]:
        return self._cards.values()

    def setCardsWidth(self, value: int):
        self._cardsWidth = value
        self._resizeAllCards()

    def setCardsSizeRatio(self, ratio: CardSizeRatio):
        self._cardsRatio = ratio
        self._resizeAllCards()

    def swapLayout(self, layoutType: LayoutType, alignment=None):
        cards = []
        for i in range(self._layout.count()):
            item = self._layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), Card):
                cards.append(item.widget())
        clear_layout(self._layout, auto_delete=False)
        QWidget().setLayout(self.layout())

        if layoutType == LayoutType.FLOW:
            self._layout = flow(self, self._margin, self._spacing)
        elif layoutType == LayoutType.VERTICAL:
            self._layout = vbox(self, self._margin, self._spacing)
        elif layoutType == LayoutType.HORIZONTAL:
            self._layout = hbox(self, self._margin, self._spacing)

        for card in cards:
            if alignment:
                self._layout.addWidget(card, alignment=alignment)
            else:
                self._layout.addWidget(card)

    def setSetting(self, setting: NovelSetting, value: Any):
        for card in self._cards.values():
            card.setSetting(setting, value)

    def applyFilter(self, cardFilter: CardFilter):
        for card in self._cards.values():
            card.setVisible(cardFilter.filter(card))

    def _initCardWidget(self, card: Card):
        card.setAcceptDrops(True)
        if card.isDragEnabled():
            card.installEventFilter(DragEventFilter(card, card.mimeType(), lambda x: card.data(),
                                                    startedSlot=partial(self._dragStarted, card),
                                                    finishedSlot=partial(self._dragFinished, card)))
        card.selected.connect(lambda: self._cardSelected(card))
        card.doubleClicked.connect(lambda: self.cardDoubleClicked.emit(card))
        card.cursorEntered.connect(lambda: self.cardEntered.emit(card))
        card.cursorLeft.connect(lambda: self.cardLeft.emit(card))
        card.customContextMenuRequested.connect(partial(self.cardCustomContextMenuRequested.emit, card))
        card.installEventFilter(DropEventFilter(card, [card.mimeType()], motionDetection=Qt.Orientation.Horizontal,
                                                motionSlot=partial(self._dragMoved, card),
                                                droppedSlot=self._dropped))
        self._cards[card.data()] = card
        self._resizeCard(card)

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
        if not isinstance(card, PlaceholderCard):
            self._selected = card
        self.cardSelected.emit(card)

    def _dragStarted(self, card: Card):
        card.setHidden(True)
        self._dragged = card
        self._dragPlaceholder = card.copy()
        self._resizeCard(self._dragPlaceholder)
        translucent(self._dragPlaceholder)
        self._dragPlaceholder.setHidden(True)
        self._dragPlaceholder.setParent(self)
        self._dragPlaceholder.setAcceptDrops(True)
        self._dragPlaceholder.installEventFilter(
            DropEventFilter(self._dragPlaceholder, mimeTypes=[card.mimeType()], droppedSlot=self._dropped))

    def _dragMoved(self, card: Card, edge: Qt.Edge, _: QPoint):
        i = self._layout.indexOf(card)
        if edge == Qt.Edge.LeftEdge:
            self._layout.insertWidget(i, self._dragPlaceholder)
        else:
            self._layout.insertWidget(i + 1, self._dragPlaceholder)
        self._dragPlaceholder.setVisible(True)

    def _dropped(self, _: QMimeData):
        self.clearSelection()
        droppedCard = self._dragged.copy()
        self._initCardWidget(droppedCard)

        i = self._layout.indexOf(self._dragPlaceholder)
        self._layout.insertWidget(i, droppedCard)

        data = []
        for i in range(self._layout.count()):
            card: Card = self._layout.itemAt(i).widget()
            if card is self._dragPlaceholder or card is self._dragged:
                continue
            if isinstance(card, PlaceholderCard):
                continue
            data.append(card.data())

        QTimer.singleShot(10, lambda: self.orderChanged.emit(data, droppedCard))
        gc(self._dragPlaceholder)
        self._dragPlaceholder = None

        self._wasDropped = True

    def _dragFinished(self, card: Card):
        if self._dragPlaceholder:
            gc(self._dragPlaceholder)
            self._dragPlaceholder = None
        if self._wasDropped:
            self._layout.removeWidget(card)
            gc(card)
        else:
            card.setVisible(True)
        self._dragged = None

        self._wasDropped = False
