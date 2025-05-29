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
import calendar
from datetime import datetime
from functools import partial
from typing import Optional, Set

import qtanim
from PyQt6.QtCore import pyqtSignal, Qt, pyqtProperty, QTimer, QEvent, QSize, QPoint
from PyQt6.QtGui import QIcon, QMouseEvent, QEnterEvent, QAction, QColor, QPaintEvent, QPainter
from PyQt6.QtWidgets import QPushButton, QSizePolicy, QToolButton, QAbstractButton, QLabel, QButtonGroup, QMenu, \
    QWidget
from overrides import overrides
from qtanim import fade_in
from qthandy import hbox, translucent, bold, incr_font, transparent, retain_when_hidden, underline, vbox, decr_icon, \
    incr_icon, italic, pointy, sp, decr_font
from qthandy.filter import OpacityEventFilter
from qtmenu import MenuWidget, GridMenuWidget

from plotlyst.common import PLOTLYST_SECONDARY_COLOR, PLOTLYST_TERTIARY_COLOR, PLOTLYST_MAIN_COLOR, \
    LIGHTGREY_IDLE_COLOR, LIGHTGREY_ACTIVE_COLOR
from plotlyst.core.domain import SelectionItem, Novel, tag_characterization, tag_worldbuilding, \
    tag_brainstorming, tag_research, tag_writing, tag_plotting, tag_theme, tag_outlining, tag_revision, tag_drafting, \
    tag_editing, tag_collect_feedback, tag_publishing, tag_marketing, tag_book_cover_design, tag_formatting, \
    SnapshotType
from plotlyst.env import app_env
from plotlyst.event.core import emit_event, emit_global_event
from plotlyst.events import SocialSnapshotRequested, ShowRoadmapEvent
from plotlyst.service.importer import SyncImporter
from plotlyst.view.common import ButtonPressResizeEventFilter, tool_btn, spin, action, label, \
    ButtonIconSwitchEventFilter, push_btn
from plotlyst.view.icons import IconRegistry
from plotlyst.view.style.base import apply_white_menu


class SelectionItemPushButton(QPushButton):
    itemDoubleClicked = pyqtSignal(SelectionItem)

    def __init__(self, parent=None):
        super(SelectionItemPushButton, self).__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._item: Optional[SelectionItem] = None
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.clicked.connect(self._checkDoubleClick)

    def selectionItem(self) -> Optional[SelectionItem]:
        return self._item

    def setSelectionItem(self, item: SelectionItem):
        self.setText(item.text)
        if item.icon:
            self.setIcon(IconRegistry.from_name(item.icon, item.icon_color))

        if self._item is None:
            self._item = item
            self.toggled.connect(self._toggled)
        else:
            self._item = item

    def _toggled(self, checked: bool):
        bold(self, checked)

    def _checkDoubleClick(self):
        if not self._item:
            return
        if self.timer.isActive():
            self.itemDoubleClicked.emit(self._item)
            self.timer.stop()
        else:
            self.timer.start(250)


class _SecondaryActionButton(QAbstractButton):
    def __init__(self, parent=None):
        super(_SecondaryActionButton, self).__init__(parent)
        self._iconName: str = ''
        self._iconColor: str = 'black'
        self._checkedColor: str = 'black'
        self._padding: int = 4
        self.initStyleSheet()
        pointy(self)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum)
        self.installEventFilter(OpacityEventFilter(self, leaveOpacity=0.7, ignoreCheckedButton=True))

    def initStyleSheet(self, border_color: str = 'grey', border_style: str = 'solid', color: str = 'grey',
                       bg_color: Optional[str] = None, border_radius: int = 6):
        bg_style = ''
        if bg_color:
            bg_style = f'background: {bg_color};'
        self.setStyleSheet(f'''
                {self.__class__.__name__} {{
                    border: 1px {border_style} {border_color};
                    border-radius: {border_radius}px;
                    color: {color};
                    {bg_style}
                    padding: {self._padding}px;
                }}
                {self.__class__.__name__}:pressed {{
                    border: 2px solid {border_color};
                }}
                {self.__class__.__name__}:checked {{
                    border: 2px solid {self._checkedColor};
                }}
                {self.__class__.__name__}::menu-indicator {{width:0px;}}
            ''')

    def setBorderColor(self, color_name: str):
        self.initStyleSheet(color_name)
        self.update()

    def setPadding(self, value: int):
        if not value:
            return
        self._padding = value
        self.initStyleSheet()
        self.update()

    def _setIcon(self):
        if self._iconName:
            self.setIcon(IconRegistry.from_name(self._iconName, self._iconColor, color_on=self._checkedColor))


class SecondaryActionToolButton(QToolButton, _SecondaryActionButton):
    @pyqtProperty(str)
    def iconName(self):
        return self._iconName

    @iconName.setter
    def iconName(self, value):
        self._iconName = value
        self._setIcon()

    @pyqtProperty(str)
    def iconColor(self):
        return self._iconColor

    @iconColor.setter
    def iconColor(self, value):
        self._iconColor = value
        self._setIcon()

    @pyqtProperty(str)
    def checkedColor(self):
        return self._checkedColor

    @checkedColor.setter
    def checkedColor(self, value):
        self._checkedColor = value
        self.initStyleSheet()
        self._setIcon()


class SecondaryActionPushButton(QPushButton, _SecondaryActionButton):
    @pyqtProperty(str)
    def iconName(self):
        return self._iconName

    @iconName.setter
    def iconName(self, value):
        self._iconName = value
        self._setIcon()

    @pyqtProperty(str)
    def iconColor(self):
        return self._iconColor

    @iconColor.setter
    def iconColor(self, value):
        self._iconColor = value
        self._setIcon()

    @pyqtProperty(str)
    def checkedColor(self):
        return self._checkedColor

    @checkedColor.setter
    def checkedColor(self, value):
        self._checkedColor = value
        self.initStyleSheet()
        self._setIcon()


class WordWrappedPushButton(QPushButton):
    def __init__(self, parent=None):
        super(WordWrappedPushButton, self).__init__(parent)
        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hbox(self, 0, 0).addWidget(self.label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum)

    @overrides
    def setText(self, text: str):
        self.label.setText(text)
        self.setFixedHeight(self.label.height() + 5)


class FadeOutButtonGroup(QButtonGroup):
    def __init__(self, parent=None):
        super(FadeOutButtonGroup, self).__init__(parent)
        self.buttonClicked.connect(self._clicked)
        self.setExclusive(False)
        self._opacity = 0.7
        self._fadeInDuration = 250
        self._secondaryLocked: bool = True
        self._secondaryButtons: Set[QAbstractButton] = set()

    def setButtonOpacity(self, opacity: float):
        self._opacity = opacity

    def setFadeInDuration(self, duration: int):
        self._fadeInDuration = duration

    def secondaryLocked(self) -> bool:
        return self._secondaryLocked

    def setSecondaryLocked(self, locked: bool):
        self._secondaryLocked = locked

    def setSecondaryButtons(self, *buttons):
        self._secondaryButtons.clear()
        for btn in buttons:
            self._secondaryButtons.add(btn)

    def toggle(self, btn: QAbstractButton):
        btn.setVisible(True)
        btn.setEnabled(True)
        btn.setChecked(not btn.isChecked())
        self._toggled(btn, animated=False)

    def setButtonChecked(self, btn: QAbstractButton, checked: bool):
        btn.setVisible(True)
        btn.setEnabled(True)
        btn.setChecked(checked)
        self._toggled(btn, animated=False)

    def reset(self):
        for btn in self.buttons():
            btn.setEnabled(True)
            btn.setChecked(False)
            btn.setVisible(True)
            translucent(btn, self._opacity)

    def _clicked(self, btn: QAbstractButton):
        self._toggled(btn)

    def _toggled(self, btn: QAbstractButton, animated: bool = True):
        for other_btn in self.buttons():
            if other_btn is btn:
                continue

            if btn.isChecked():
                other_btn.setChecked(False)
                other_btn.setDisabled(True)
                if animated:
                    qtanim.fade_out(other_btn)
                else:
                    other_btn.setHidden(True)
            else:
                other_btn.setEnabled(True)
                if self._secondaryLocked and other_btn in self._secondaryButtons:
                    continue
                if animated:
                    anim = qtanim.fade_in(other_btn, duration=self._fadeInDuration)
                    anim.finished.connect(partial(translucent, other_btn, self._opacity))
                else:
                    other_btn.setVisible(True)


class ToolbarButton(QToolButton):
    def __init__(self, parent=None):
        super(ToolbarButton, self).__init__(parent)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.setCheckable(True)
        pointy(self)

        self.toggled.connect(lambda x: bold(self, x))

        self.setStyleSheet(f'''
            QToolButton {{
                border: 1px hidden lightgrey;
                padding: 3px;
            }}
            QToolButton:checked {{
                color: #240046;
                background: {PLOTLYST_TERTIARY_COLOR};
            }}
        ''')

        incr_font(self, 1)


class CollapseButton(QPushButton):
    def __init__(self, idle: Qt.Edge = Qt.Edge.BottomEdge, checked: Qt.Edge = Qt.Edge.RightEdge, parent=None):
        super(CollapseButton, self).__init__(parent)
        self._idleIcon = self._icon(idle)
        self._checkedIcon = self._icon(checked)
        self.setIcon(self._idleIcon)
        self.setCheckable(True)

        pointy(self)
        transparent(self)

        self.toggled.connect(self._toggled)

    def _toggled(self, checked: bool):
        if checked:
            self.setIcon(self._checkedIcon)
        else:
            self.setIcon(self._idleIcon)

    def _icon(self, direction: Qt.Edge) -> QIcon:
        if direction == Qt.Edge.TopEdge:
            return IconRegistry.from_name('fa5s.chevron-up')
        elif direction == Qt.Edge.LeftEdge:
            return IconRegistry.from_name('fa5s.chevron-left')
        elif direction == Qt.Edge.RightEdge:
            return IconRegistry.from_name('fa5s.chevron-right')
        else:
            return IconRegistry.from_name('fa5s.chevron-down')


class DotsMenuButton(QToolButton):
    def __init__(self, parent=None):
        super(DotsMenuButton, self).__init__(parent)
        transparent(self)
        retain_when_hidden(self)
        pointy(self)
        self.setIcon(IconRegistry.dots_icon('grey', vertical=True))
        self._pressFilter: Optional[ButtonPressResizeEventFilter] = None

    @overrides
    def setMenu(self, menu: QMenu):
        super(DotsMenuButton, self).setMenu(menu)
        if self._pressFilter is None:
            self._pressFilter = ButtonPressResizeEventFilter(self)
            self.installEventFilter(self._pressFilter)


class ReturnButton(QPushButton):
    def __init__(self, parent=None):
        super(ReturnButton, self).__init__(parent)
        self.setIcon(IconRegistry.return_icon())
        self.setText('Back')
        self.setProperty('return', True)
        underline(self)
        bold(self)
        self.installEventFilter(ButtonPressResizeEventFilter(self))

    @overrides
    def mousePressEvent(self, event: QMouseEvent) -> None:
        translucent(self, 0.8)
        super(ReturnButton, self).mousePressEvent(event)

    @overrides
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        translucent(self, 1)
        super(ReturnButton, self).mouseReleaseEvent(event)


class _NovelSyncWidget(QWidget):
    def __init__(self, parent=None):
        super(_NovelSyncWidget, self).__init__(parent)
        self.setProperty('relaxed-white-bg', True)

        self._wdgTop = QWidget()
        hbox(self._wdgTop)
        self._wdgCenter = QWidget()
        hbox(self._wdgCenter)
        self._wdgBottom = QWidget()
        hbox(self._wdgBottom)

        self.lblTitle = QLabel('Novel synchronization')
        underline(self.lblTitle)
        bold(self.lblTitle)

        self.btnChangeLocation = tool_btn(IconRegistry.from_name('fa5.folder-open'))
        transparent(self.btnChangeLocation)
        decr_icon(self.btnChangeLocation, 4)
        retain_when_hidden(self.btnChangeLocation)
        self.btnChangeLocation.installEventFilter(OpacityEventFilter(self.btnChangeLocation))
        self._wdgTop.layout().addWidget(self.lblTitle, alignment=Qt.AlignmentFlag.AlignCenter)
        self._wdgTop.layout().addWidget(self.btnChangeLocation, alignment=Qt.AlignmentFlag.AlignRight)
        self.btnChangeLocation.setHidden(True)

        self.lblUpdateMessage = QLabel()
        self.lblUpdateMessage.setProperty('description', True)
        self.lblUpdateMessage.setMinimumWidth(200)
        self._wdgCenter.layout().addWidget(self.lblUpdateMessage, alignment=Qt.AlignmentFlag.AlignCenter)

        self.lblErrorNotFoundMessage = QLabel('Project not found.')
        self.lblErrorNotFoundMessage.setProperty('error', True)
        self.lblErrorNotFoundMessage.setHidden(True)
        self._wdgCenter.layout().addWidget(self.lblErrorNotFoundMessage, alignment=Qt.AlignmentFlag.AlignCenter)

        self.btnCheck = QPushButton('Check for updates')
        self.btnCheck.setProperty('base', True)
        pointy(self.btnCheck)
        self.btnCheck.setIcon(IconRegistry.refresh_icon('black'))
        self.btnCheck.installEventFilter(ButtonPressResizeEventFilter(self.btnCheck))

        self.btnSync = QPushButton('Synchronize')
        pointy(self.btnSync)
        self.btnSync.setProperty('base', True)
        self.btnSync.setProperty('positive', True)
        self.btnSync.setIcon(IconRegistry.refresh_icon('white'))
        self.btnSync.installEventFilter(ButtonPressResizeEventFilter(self.btnSync))

        self._wdgBottom.layout().addWidget(self.btnCheck, alignment=Qt.AlignmentFlag.AlignCenter)
        self._wdgBottom.layout().addWidget(self.btnSync, alignment=Qt.AlignmentFlag.AlignCenter)

        # self.installEventFilter(VisibilityToggleEventFilter(self.btnChangeLocation, self))

        vbox(self, 5)
        self.layout().addWidget(self._wdgTop)
        self.layout().addWidget(self._wdgCenter)
        self.layout().addWidget(self._wdgBottom)


class NovelSyncButton(QPushButton):
    UP_TO_DATE_MSG: str = 'Up-to-date'
    UPDATES_AVAILABLE_MSG: str = 'New updates are available'

    def __init__(self, parent=None):
        super(NovelSyncButton, self).__init__(parent)
        self.setProperty('importer-sync', True)
        self.installEventFilter(ButtonPressResizeEventFilter(self))
        self.installEventFilter(OpacityEventFilter(self, leaveOpacity=0.7))
        pointy(self)

        self._icon = QIcon()
        self._importer: Optional[SyncImporter] = None
        self._novel: Optional[Novel] = None

        self._menu = MenuWidget(self)
        self._wdgSync = _NovelSyncWidget()
        self._menu.addWidget(self._wdgSync)
        apply_white_menu(self._menu)

        self._wdgSync.btnCheck.clicked.connect(self._checkForUpdates)
        self._wdgSync.btnSync.clicked.connect(self._sync)

    def setImporter(self, importer: SyncImporter, novel: Novel):
        self._importer = importer
        self._novel = novel
        self._icon = self._importer.icon()
        self.setIcon(self._icon)
        self.setText(self._importer.name())

        location = self._importer.location(self._novel)
        self._wdgSync.lblTitle.setText(location)
        self._wdgSync.lblTitle.setToolTip(self._novel.import_origin.source)

        self._toggleUpToDate(True)

    def clear(self):
        self._novel = None
        self._importer = None

    def _checkForUpdates(self):
        prev_icon = self._wdgSync.btnCheck.icon()
        spin(self._wdgSync.btnCheck)
        if self._importer.location_exists(self._novel):
            self._wdgSync.lblErrorNotFoundMessage.setHidden(True)
            self.setIcon(self._icon)

            if self._importer.is_updated(self._novel):
                fade_in(self._wdgSync.lblUpdateMessage)
            else:
                self._toggleUpToDate(False)
                fade_in(self._wdgSync.lblUpdateMessage)
                fade_in(self._wdgSync.btnSync)
        else:
            self.setIcon(IconRegistry.from_name('ri.error-warning-fill', '#e76f51'))
            self._wdgSync.lblUpdateMessage.setHidden(True)
            self._wdgSync.lblErrorNotFoundMessage.setVisible(True)

        QTimer.singleShot(100, lambda: self._wdgSync.btnCheck.setIcon(prev_icon))

    def _sync(self):
        self._importer.sync(self._novel)

        self._toggleUpToDate(True)
        self.menu().close()

    def _toggleUpToDate(self, updated: bool):
        # hide all first to avoid layout problems
        self._wdgSync.btnCheck.setHidden(True)
        self._wdgSync.btnSync.setHidden(True)

        self._wdgSync.btnCheck.setVisible(updated)
        self._wdgSync.btnSync.setHidden(updated)

        self._wdgSync.lblUpdateMessage.setText(self.UP_TO_DATE_MSG if updated else self.UPDATES_AVAILABLE_MSG)


class EyeToggle(QToolButton):
    def __init__(self, parent=None):
        super(EyeToggle, self).__init__(parent)
        self.setCheckable(True)
        pointy(self)
        transparent(self)
        self.toggled.connect(self._toggled)

        self._toggled(False)

    def _toggled(self, toggled: bool):
        if toggled:
            self.setIcon(IconRegistry.from_name('ei.eye-open', PLOTLYST_SECONDARY_COLOR))
            translucent(self, 1)
        else:
            self.setIcon(IconRegistry.from_name('ei.eye-close'))
            translucent(self)


class TaskTagSelector(QToolButton):
    tagSelected = pyqtSignal(SelectionItem)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected = False
        pointy(self)
        self._reset()

        tagsMenu = GridMenuWidget(self)

        tagsMenu.addAction(self._action(tag_characterization), 0, 0)
        tagsMenu.addAction(self._action(tag_worldbuilding), 0, 2)
        tagsMenu.addAction(self._action(tag_brainstorming), 1, 0)
        tagsMenu.addAction(self._action(tag_writing), 2, 0)
        tagsMenu.addAction(self._action(tag_research), 1, 2)
        tagsMenu.addAction(self._action(tag_plotting), 2, 2)
        tagsMenu.addAction(self._action(tag_theme), 3, 0)
        tagsMenu.addSeparator(4, 0, colSpan=3)

        tagsMenu.addAction(self._action(tag_outlining), 5, 0)
        tagsMenu.addAction(self._action(tag_revision), 6, 0)
        tagsMenu.addAction(self._action(tag_drafting), 7, 0)
        tagsMenu.addAction(self._action(tag_editing), 8, 0)
        tagsMenu.addAction(self._action(tag_formatting), 9, 0)
        tagsMenu.addSeparator(5, 1, rowSpan=5, vertical=True)

        tagsMenu.addAction(self._action(tag_collect_feedback), 5, 2)
        tagsMenu.addAction(self._action(tag_book_cover_design), 6, 2)
        tagsMenu.addAction(self._action(tag_publishing), 7, 2)
        tagsMenu.addAction(self._action(tag_marketing), 8, 2)

        tagsMenu.addSeparator(10, 0, colSpan=3)
        self._actionRemove = action('Remove', IconRegistry.trash_can_icon(), slot=self._reset)
        italic(self._actionRemove)
        tagsMenu.addAction(self._actionRemove, 12, 0)
        transparent(self)
        translucent(self, 0.9)
        self.installEventFilter(ButtonPressResizeEventFilter(self))

    @overrides
    def enterEvent(self, event: QEnterEvent) -> None:
        if not self._selected:
            self.setIcon(IconRegistry.from_name('ei.tag', 'grey'))

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        if not self._selected:
            self.setIcon(IconRegistry.from_name('ei.tag', '#adb5bd'))

    def select(self, tag: SelectionItem):
        self.__updateTag(tag)

    def _tagSelected(self, tag: SelectionItem):
        self.__updateTag(tag)
        self.tagSelected.emit(tag)

    def _reset(self):
        self.setIcon(IconRegistry.from_name('ei.tag', '#adb5bd'))
        self.setToolTip('Ling a tag')
        self._selected = False
        decr_icon(self)

    def _action(self, tag: SelectionItem) -> QAction:
        return action(tag.text, IconRegistry.from_selection_item(tag),
                      slot=partial(self._tagSelected, tag))

    def __updateTag(self, tag: SelectionItem):
        if not self._selected:
            incr_icon(self)
        self.setIcon(IconRegistry.from_selection_item(tag))
        self.setToolTip(tag.text)
        self._selected = True


class ChargeButton(SecondaryActionToolButton):
    def __init__(self, positive: bool, parent=None):
        super().__init__(parent)
        if positive:
            self.setIcon(IconRegistry.plus_circle_icon('grey'))
        else:
            self.setIcon(IconRegistry.minus_icon('grey'))
        decr_icon(self, 4)
        transparent(self)
        retain_when_hidden(self)


class SelectorToggleButton(QToolButton):
    displayHint = pyqtSignal(str)
    hideHint = pyqtSignal()

    def __init__(self, button_style: Qt.ToolButtonStyle = Qt.ToolButtonStyle.ToolButtonTextUnderIcon,
                 minWidth: int = 100, animated: bool = True, checkedColor: str = '#D4B8E0', hoverColor: str = '#FCF5FE',
                 parent=None):
        super().__init__(parent)
        self._animated = animated

        if minWidth:
            self.setMinimumWidth(minWidth)
        self.installEventFilter(ButtonPressResizeEventFilter(self))
        self.setCheckable(True)
        self.setToolButtonStyle(button_style)

        pointy(self)
        incr_icon(self, 4)
        if app_env.is_mac() and button_style == Qt.ToolButtonStyle.ToolButtonTextUnderIcon:
            incr_font(self)

        if button_style == Qt.ToolButtonStyle.ToolButtonTextBesideIcon:
            radius = 6
            padding = 6
        else:
            radius = 10
            padding = 2

        self.setStyleSheet(f'''
                    QToolButton {{
                        border: 1px hidden lightgrey;
                        border-radius: {radius}px;
                        padding: {padding}px;
                    }}
                    QToolButton:hover:!checked {{
                        background: {hoverColor};
                    }}
                    QToolButton:checked {{
                        background: {checkedColor};
                    }}
                    ''')

        if self._animated:
            self.toggled.connect(self._toggled)

    def _toggled(self, toggled: bool):
        if toggled:
            color = QColor(PLOTLYST_MAIN_COLOR)
            color.setAlpha(175)
            qtanim.glow(self, radius=8, color=color, reverseAnimation=False,
                        teardown=lambda: self.setGraphicsEffect(None))
        else:
            qtanim.glow(self, radius=0, startRadius=8, color=QColor('grey'), reverseAnimation=False,
                        teardown=lambda: self.setGraphicsEffect(None))


class _RoleFilterButton(QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        transparent(self)
        pointy(self)
        self.installEventFilter(ButtonPressResizeEventFilter(self))
        self.installEventFilter(OpacityEventFilter(self))


class MajorRoleFilterButton(_RoleFilterButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(IconRegistry.major_character_icon())
        self.setToolTip('Filter for Major characters')


class SecondaryRoleFilterButton(_RoleFilterButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(IconRegistry.secondary_character_icon())
        self.setToolTip('Filter for Secondary characters')


class MinorRoleFilterButton(_RoleFilterButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(IconRegistry.minor_character_icon())
        self.setToolTip('Filter for Minor characters')


class SmallToggleButton(QToolButton):
    def __init__(self, parent=None, translucent: bool = True):
        super().__init__(parent)
        self.setIcon(IconRegistry.from_name('ph.toggle-left-thin'))
        self.setCheckable(True)
        pointy(self)
        transparent(self)
        self.setIconSize(QSize(28, 28))

        if translucent:
            self.installEventFilter(OpacityEventFilter(self, leaveOpacity=0.7, ignoreCheckedButton=True))
        self.installEventFilter(ButtonPressResizeEventFilter(self))

        self.toggled.connect(self._toggled)

    def _toggled(self, toggled: bool):
        if toggled:
            self.setIcon(
                IconRegistry.from_name('ph.toggle-right-fill', PLOTLYST_SECONDARY_COLOR, PLOTLYST_SECONDARY_COLOR))
        else:
            self.setIcon(IconRegistry.from_name('ph.toggle-left-thin'))


class ToggleAllOnAndOff(QWidget):
    on = pyqtSignal()
    off = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        hbox(self, 0, 0)

        sp(self).h_max()
        self.btnOn = tool_btn(IconRegistry.from_name('mdi6.check-all'), transparent_=True)
        self.btnOn.installEventFilter(OpacityEventFilter(self.btnOn))
        self.btnOff = tool_btn(IconRegistry.from_name('ei.remove'), transparent_=True)
        self.btnOff.installEventFilter(OpacityEventFilter(self.btnOff))
        decr_icon(self.btnOn, 4)
        decr_icon(self.btnOff, 4)

        self.btnOn.clicked.connect(self.on)
        self.btnOff.clicked.connect(self.off)

        self.layout().addWidget(label('Toggle all:', color='grey', decr_font_diff=1))
        self.layout().addWidget(self.btnOn)
        self.layout().addWidget(label('/'))
        self.layout().addWidget(self.btnOff)


class TopSelectorButton(QPushButton):
    def __init__(self, icon: str = '', text: str = '', parent=None):
        super().__init__(parent)
        self.setText(text)
        if icon:
            self.setIcon(IconRegistry.from_name(icon, color_on=PLOTLYST_SECONDARY_COLOR))
        self.setCheckable(True)
        pointy(self)
        self.setProperty('transparent-rounded-bg-on-hover', True)
        self.setProperty('secondary-selector', True)

        incr_icon(self, 4)
        incr_font(self, 2)


class SnapshotButton(QPushButton):

    def __init__(self, novel: Novel, snapshotType: SnapshotType, parent=None):
        super().__init__(parent)
        self.setToolTip('Take a snapshot for social media')
        transparent(self)
        self.installEventFilter(ButtonPressResizeEventFilter(self))
        self.installEventFilter(
            ButtonIconSwitchEventFilter(self, IconRegistry.from_name('mdi.camera', LIGHTGREY_IDLE_COLOR),
                                        IconRegistry.from_name('mdi.camera', LIGHTGREY_ACTIVE_COLOR)))
        pointy(self)

        incr_icon(self, 6)
        self.clicked.connect(lambda: emit_event(novel, SocialSnapshotRequested(self, snapshotType)))


def premium_button_notice_small(parent) -> QPushButton:
    btn = push_btn(icon=IconRegistry.from_name('mdi.certificate'), text='Plotlyst Premium Feature', transparent_=True,
                   parent=parent)
    decr_font(btn)
    btn.installEventFilter(OpacityEventFilter(btn, leaveOpacity=0.6))
    btn.clicked.connect(lambda: emit_global_event(ShowRoadmapEvent(parent)))

    return btn


class YearSelectorButton(QPushButton):
    selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        current_year = datetime.today().year
        self.setText(str(current_year))
        self.setIcon(IconRegistry.from_name('mdi.calendar-blank'))
        self.installEventFilter(ButtonPressResizeEventFilter(self))
        pointy(self)
        incr_font(self, 4)
        incr_icon(self, 2)

        self._dropDownIcon = IconRegistry.from_name('ri.arrow-down-s-fill')
        self._dropDownIconSize: int = 15
        self.setStyleSheet(
            f'border: 0px; background-color: rgba(0, 0, 0, 0); padding-right: {self._dropDownIconSize}px;')

        self.clicked.connect(self._showSelector)

    @overrides
    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._dropDownIcon.paint(painter, self.width() - self._dropDownIconSize,
                                 (self.height() - self._dropDownIconSize) // 2,
                                 self._dropDownIconSize, self._dropDownIconSize)

    def _showSelector(self):
        menu = MenuWidget()
        for year in range(datetime.today().year, 2023, -1):
            menu.addAction(action(str(year), slot=partial(self._selected, year)))

        menu.exec(self.mapToGlobal(QPoint(0, self.sizeHint().height() + 10)))

    def _selected(self, year: int):
        self.setText(str(year))
        self.selected.emit(year)


class MonthSelectorButton(QPushButton):
    selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        current_month = datetime.today().month
        self.setText(calendar.month_name[current_month])
        self.setIcon(IconRegistry.from_name('mdi.calendar-month'))
        self.installEventFilter(ButtonPressResizeEventFilter(self))
        pointy(self)
        incr_font(self, 4)
        incr_icon(self, 2)

        self._dropDownIcon = IconRegistry.from_name('ri.arrow-down-s-fill')
        self._dropDownIconSize: int = 15
        self.setStyleSheet(
            f'border: 0px; background-color: rgba(0, 0, 0, 0); padding-right: {self._dropDownIconSize}px;')

        self.clicked.connect(self._showSelector)

    @overrides
    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._dropDownIcon.paint(painter, self.width() - self._dropDownIconSize,
                                 (self.height() - self._dropDownIconSize) // 2,
                                 self._dropDownIconSize, self._dropDownIconSize)

    def _showSelector(self):
        menu = MenuWidget()
        for month in range(1, 13):
            month_name = calendar.month_name[month]
            menu.addAction(action(month_name, slot=partial(self._selected, month)))

        menu.exec(self.mapToGlobal(QPoint(0, self.sizeHint().height() + 10)))

    def _selected(self, month: int):
        self.setText(calendar.month_name[month])
        self.selected.emit(month)
