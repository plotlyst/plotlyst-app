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
import string
from dataclasses import dataclass
from functools import partial
from typing import Iterable, List, Optional, Dict, Union

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QByteArray, QBuffer, QIODevice
from PyQt6.QtGui import QIcon, QColor, QImageReader, QImage, QPixmap, \
    QShowEvent
from PyQt6.QtWidgets import QWidget, QToolButton, QButtonGroup, QSizePolicy, QLabel, QPushButton, \
    QFileDialog, QMessageBox, QGridLayout, QFrame
from overrides import overrides
from qthandy import vspacer, transparent, gc, line, spacer, clear_layout, hbox, flow, translucent, margins, pointy, \
    vbox, retain_when_hidden, incr_icon
from qthandy.filter import OpacityEventFilter
from qtmenu import MenuWidget, ScrollableMenuWidget

from plotlyst.common import RELAXED_WHITE_COLOR
from plotlyst.core.domain import Novel, Character, CharacterProfileSectionType, NovelSetting, CharacterMultiAttribute
from plotlyst.core.template import SelectionItem, TemplateField, RoleImportance
from plotlyst.env import app_env
from plotlyst.event.core import EventListener, Event
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import CharacterSummaryChangedEvent, CharacterBackstoryChangedEvent
from plotlyst.resources import resource_registry
from plotlyst.settings import CHARACTER_INITIAL_AVATAR_COLOR_CODES
from plotlyst.view.common import action, ButtonPressResizeEventFilter, tool_btn, label, push_btn, scroll_area
from plotlyst.view.generated.characters_progress_widget_ui import Ui_CharactersProgressWidget
from plotlyst.view.icons import avatars, IconRegistry
from plotlyst.view.style.base import apply_border_image, transparent_menu
from plotlyst.view.widget.display import IconText, Icon, OverlayWidget
from plotlyst.view.widget.labels import CharacterLabel
from plotlyst.view.widget.progress import CircularProgressBar, ProgressTooltipMode, \
    CharacterRoleProgressChart
from plotlyst.view.widget.utility import ColorPicker, IconSelectorDialog, ImageCropDialog


class CharacterToolButton(QToolButton):
    def __init__(self, character: Character, parent=None):
        super(CharacterToolButton, self).__init__(parent)
        self.character = character
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        pointy(self)
        self.refresh()

    def refresh(self):
        self.setToolTip(self.character.name)
        self.setIcon(avatars.avatar(self.character))


class CharacterSelectorButtons(QWidget):
    characterToggled = pyqtSignal(Character, bool)
    characterClicked = pyqtSignal(Character)

    def __init__(self, parent=None, exclusive: bool = True):
        super(CharacterSelectorButtons, self).__init__(parent)
        hbox(self)
        self.container = QWidget()
        self.container.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Maximum)

        self._layout = flow(self.container)

        self.layout().addWidget(self.container)

        self._btn_group = QButtonGroup()
        self._buttons: List[CharacterToolButton] = []
        self._buttonsPerCharacters: Dict[Character, CharacterToolButton] = {}
        self.setExclusive(exclusive)

    def exclusive(self) -> bool:
        return self._btn_group.exclusive()

    def setExclusive(self, exclusive: bool):
        self._btn_group.setExclusive(exclusive)

    def characters(self, all: bool = True) -> Iterable[Character]:
        return [x.character for x in self._buttons if all or x.isChecked()]

    def setCharacters(self, characters: Iterable[Character], checkAll: bool = True):
        self.clear()

        for char in characters:
            self.addCharacter(char, checked=checkAll)

        if not self._buttons:
            return
        if self._btn_group.exclusive():
            self._buttons[0].setChecked(True)

    def updateCharacters(self, characters: Iterable[Character], checkAll: bool = True):
        if not self._buttons:
            return self.setCharacters(characters, checkAll)

        current_characters = set(x for x in self._buttonsPerCharacters.keys())

        for c in characters:
            if c in self._buttonsPerCharacters.keys():
                current_characters.remove(c)
            else:
                self.addCharacter(c, checkAll)

        for c in current_characters:
            self.removeCharacter(c)

        for btn in self._buttons:
            btn.refresh()

    def addCharacter(self, character: Character, checked: bool = True):
        tool_btn = CharacterToolButton(character)

        self._buttons.append(tool_btn)
        self._buttonsPerCharacters[character] = tool_btn
        self._btn_group.addButton(tool_btn)
        self._layout.addWidget(tool_btn)

        tool_btn.setChecked(checked)

        tool_btn.toggled.connect(partial(self.characterToggled.emit, character))
        tool_btn.clicked.connect(partial(self.characterClicked.emit, character))
        tool_btn.installEventFilter(OpacityEventFilter(parent=tool_btn, ignoreCheckedButton=True))

    def removeCharacter(self, character: Character):
        if character not in self._buttonsPerCharacters:
            return

        btn = self._buttonsPerCharacters.pop(character)
        if btn.isChecked():
            btn.setChecked(False)

        self._btn_group.removeButton(btn)
        self._buttons.remove(btn)
        self._layout.removeWidget(btn)
        gc(btn)

    def clear(self):
        clear_layout(self._layout)

        for btn in self._buttons:
            self._btn_group.removeButton(btn)
            self._layout.removeWidget(btn)
            gc(btn)

        self._buttons.clear()
        self._buttonsPerCharacters.clear()


class CharacterSelectorMenu(ScrollableMenuWidget):
    selected = pyqtSignal(Character)

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self._novel = novel
        self._characters: Optional[List[Character]] = None
        self.aboutToShow.connect(self._beforeShow)

    @overrides
    def sizeHint(self) -> QSize:
        hint: QSize = super().sizeHint()

        has_characters = len(self.characters()) > 0
        if has_characters:
            hint.setHeight(20)
        for i in range(self._frame.layout().count()):
            widget: QWidget = self._frame.layout().itemAt(i).widget()
            if not isinstance(widget, QFrame):
                hint = hint.expandedTo(QSize(widget.width(), hint.height()))

            if has_characters and i < 11:
                hint = hint.expandedTo(QSize(hint.width(), hint.height() + widget.sizeHint().height()))

        return hint

    def setCharacters(self, character: List[Character]):
        self._characters = character
        self._fillUpMenu()

    def characters(self) -> List[Character]:
        if self._characters is not None:
            return self._characters
        else:
            return self._novel.characters

    def refresh(self):
        self._fillUpMenu()

    def _beforeShow(self):
        if self._characters is None:
            self._fillUpMenu()

    def _fillUpMenu(self):
        self.clear()

        for char in self.characters():
            charAction = action(char.displayed_name(), avatars.avatar(char), slot=partial(self.selected.emit, char),
                                parent=self)
            font = charAction.font()
            if not char.name:
                charAction.setText('Character')
                font.setItalic(True)
            charAction.setFont(font)
            self.addAction(charAction)

        if not self.actions():
            self.addSection('No characters were found')
            self.addSeparator()
            self.addSection('Go to the Characters panel to create your first character')

        self._frame.updateGeometry()


class CharacterSelectorButton(QToolButton):
    characterSelected = pyqtSignal(Character)

    def __init__(self, novel: Novel, parent=None, opacityEffectEnabled: bool = True, iconSize: int = 32):
        super().__init__(parent)
        self._novel = novel
        self._iconSize = iconSize
        self._setIconSize = self._iconSize + 4
        pointy(self)
        self._opacityEffectEnabled = opacityEffectEnabled
        if self._opacityEffectEnabled:
            self._opacityFilter = OpacityEventFilter(self)
        else:
            self._opacityFilter = None
        self.installEventFilter(ButtonPressResizeEventFilter(self))
        self._menu = CharacterSelectorMenu(self._novel, self)
        self._menu.selected.connect(self._selected)
        self.clear()

    def characterSelectorMenu(self) -> CharacterSelectorMenu:
        return self._menu

    def setCharacter(self, character: Character):
        self.setIcon(avatars.avatar(character))
        transparent(self)
        if self._opacityEffectEnabled:
            self.removeEventFilter(self._opacityFilter)
            translucent(self, 1.0)
        self.setIconSize(QSize(self._setIconSize, self._setIconSize))

    def clear(self):
        self.setStyleSheet('''
                QToolButton {
                    border: 2px dotted grey;
                    border-radius: 6px;
                }
                QToolButton:hover {
                    border: 2px dotted black;
                }
        ''')
        self.setIcon(IconRegistry.character_icon('grey'))
        self.setIconSize(QSize(self._iconSize, self._iconSize))
        if self._opacityEffectEnabled:
            self.installEventFilter(self._opacityFilter)

    def _selected(self, character: Character):
        self.setCharacter(character)
        self.characterSelected.emit(character)


class CharacterLinkWidget(QWidget):
    characterSelected = pyqtSignal(Character)

    def __init__(self, parent=None):
        super(CharacterLinkWidget, self).__init__(parent)
        hbox(self)
        self.novel = app_env.novel
        self.character: Optional[Character] = None
        self.label: Optional[CharacterLabel] = None

        self.btnLinkCharacter = QPushButton(self)
        self.layout().addWidget(self.btnLinkCharacter)
        self.btnLinkCharacter.setIcon(IconRegistry.character_icon())
        self.btnLinkCharacter.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btnLinkCharacter.setStyleSheet('''
                QPushButton {
                    border: 2px dotted grey;
                    border-radius: 6px;
                    font: italic;
                }
                QPushButton:hover {
                    border: 2px dotted darkBlue;
                }
            ''')

        self._menu = ScrollableMenuWidget(self.btnLinkCharacter)

    def setDefaultText(self, value: str):
        self.btnLinkCharacter.setText(value)

    def setCharacter(self, character: Character):
        if self.character and character.id == self.character.id:
            return
        self.character = character

        self._clearLabel()
        self.label = CharacterLabel(self.character)
        self.label.setToolTip(f'<html>Agenda character: <b>{character.name}</b>')
        self.label.installEventFilter(OpacityEventFilter(self.label, enterOpacity=0.7, leaveOpacity=1.0))
        pointy(self.label)
        self.label.clicked.connect(lambda: self._menu.exec())
        self.layout().addWidget(self.label)
        self.btnLinkCharacter.setHidden(True)

    def reset(self):
        self._clearLabel()
        self.btnLinkCharacter.setVisible(True)

    def setAvailableCharacters(self, characters: List[Character]):
        self._menu.clear()
        for character in characters:
            self._menu.addAction(
                action(character.displayed_name(), avatars.avatar(character),
                       partial(self._characterClicked, character)))

    def _clearLabel(self):
        if self.label is not None:
            self.layout().removeWidget(self.label)
            gc(self.label)
            self.label = None

    def _characterClicked(self, character: Character):
        self.btnLinkCharacter.menu().hide()
        self.setCharacter(character)
        self.characterSelected.emit(character)


class AvatarSelectors(QWidget):
    updated = pyqtSignal()
    selectorChanged = pyqtSignal()

    def __init__(self, character: Character, parent=None):
        super(AvatarSelectors, self).__init__(parent)
        self.character = character
        hbox(self, spacing=0)
        self.wdgLeftSide = QWidget()
        self.wdgLeftSide.setStyleSheet(f'''
        .QWidget {{
            background: {RELAXED_WHITE_COLOR};
            border-top-left-radius: 15px;
            border-top-right-radius: 15px;
            border-bottom-left-radius: 15px;
        }}
        ''')
        vbox(self.wdgLeftSide, 8, 5)
        self.wdgRightSide = QWidget()
        retain_when_hidden(self.wdgRightSide)
        vbox(self.wdgRightSide, 0, 5)
        margins(self.wdgRightSide, top=40)
        self.wdgRightSide.setFixedWidth(200)
        self.wdgIconVariants = QWidget()
        vbox(self.wdgIconVariants)
        self.wdgIconVariants.setStyleSheet(f'''
                .QWidget {{
                    background: {RELAXED_WHITE_COLOR};
                    border-top-right-radius: 15px;
                    border-bottom-right-radius: 15px;
                }}
                ''')
        self.wdgRightSide.layout().addWidget(self.wdgIconVariants)

        self.colorSelector = tool_btn(IconRegistry.from_name('fa5s.circle', self.character.prefs.avatar.icon_color))
        self.colorSelector.installEventFilter(OpacityEventFilter(self.colorSelector, 0.7, 1.0))
        incr_icon(self.colorSelector, 8)
        menu = MenuWidget(self.colorSelector)
        colorPicker = ColorPicker(maxColumn=5, colors=CHARACTER_INITIAL_AVATAR_COLOR_CODES)
        colorPicker.colorPicked.connect(self._colorChanged)
        menu.addWidget(colorPicker)

        scroll = scroll_area(False, False, True)
        self.wdgFirstLetterVariants = QWidget()
        self.wdgFirstLetterVariants.setProperty('relaxed-white-bg', True)
        scroll.setWidget(self.wdgFirstLetterVariants)
        flow(self.wdgFirstLetterVariants, 0, 0)

        self.btnCustomIcon = push_btn(IconRegistry.icons_icon(), 'Custom icon', transparent_=True)
        self.btnCustomIcon.clicked.connect(self._selectCustomIcon)
        self.btnCustomIcon.installEventFilter(OpacityEventFilter(self.btnCustomIcon))

        self.wdgIconVariants.layout().addWidget(self.colorSelector, alignment=Qt.AlignmentFlag.AlignRight)
        self.wdgIconVariants.layout().addWidget(scroll)
        self.wdgIconVariants.layout().addWidget(self.btnCustomIcon,
                                                alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)

        self.layout().addWidget(self.wdgLeftSide)
        self.layout().addWidget(self.wdgRightSide)

        self.wdgSelectors = QWidget()
        vbox(self.wdgSelectors, spacing=0)

        self.btnImage = push_btn(text='Image', checkable=True, properties=['main-side-nav'])
        self.btnInitial = push_btn(IconRegistry.from_name('mdi.alpha-a-circle', color_on=RELAXED_WHITE_COLOR),
                                   text='Icon',
                                   checkable=True, properties=['main-side-nav'])
        self.btnRole = push_btn(IconRegistry.from_name('fa5s.chess-bishop', color_on=RELAXED_WHITE_COLOR),
                                text='Role icon',
                                checkable=True, properties=['main-side-nav'])

        self.btnUploadAvatar = push_btn(IconRegistry.upload_icon(color=RELAXED_WHITE_COLOR), text='Upload image',
                                        properties=['base', 'positive'])
        self.btnUploadAvatar.clicked.connect(self._upload_avatar)
        if character.avatar:
            pass
        else:
            self.btnImage.setHidden(True)
            if self.character.prefs.avatar.use_image:
                self.character.prefs.avatar.allow_initial()
        self.btnGroupSelectors = QButtonGroup()
        self.btnGroupSelectors.addButton(self.btnImage)
        self.btnGroupSelectors.addButton(self.btnInitial)
        self.btnGroupSelectors.addButton(self.btnRole)
        self.btnGroupSelectors.buttonToggled.connect(self._selectorToggled)

        self.wdgLeftSide.layout().addWidget(label('Avatar options', h5=True),
                                            alignment=Qt.AlignmentFlag.AlignCenter)
        self.wdgLeftSide.layout().addWidget(line(color='lightgrey'))
        self.wdgSelectors.layout().addWidget(self.btnImage)
        self.wdgSelectors.layout().addWidget(self.btnInitial)
        self.wdgSelectors.layout().addWidget(self.btnRole)
        self.wdgLeftSide.layout().addWidget(self.wdgSelectors)
        self.wdgLeftSide.layout().addWidget(line(color='lightgrey'))
        self.wdgLeftSide.layout().addWidget(self.btnUploadAvatar)

    def refresh(self):
        prefs = self.character.prefs.avatar
        if prefs.use_image:
            self.btnImage.setChecked(True)
            self.btnImage.setVisible(True)
        elif prefs.use_initial or prefs.use_custom_icon:
            self.btnInitial.setChecked(True)
        elif prefs.use_role:
            self.btnRole.setChecked(True)

        if self.character.role:
            self.btnRole.setIcon(IconRegistry.from_name(self.character.role.icon, color_on=RELAXED_WHITE_COLOR))
        if avatars.has_name_initial_icon(self.character):
            self.btnInitial.setIcon(
                avatars.name_initial_icon(self.character, color='black', color_on=RELAXED_WHITE_COLOR))
        if self.character.avatar:
            self.btnImage.setIcon(QIcon(avatars.image(self.character)))

        clear_layout(self.wdgFirstLetterVariants)

        letters = []
        if self.character.name:
            for name in self.character.name.split():
                if name[0].isnumeric() or name[0].isalpha() and 'a' <= name[0].lower() <= 'z':
                    letters.append(name[0])
        else:
            for alpha in string.ascii_lowercase:
                letters.append(alpha)

        for letter in letters:
            for icon_suffix in ['', '-box', '-box-outline', '-circle', '-circle-outline']:
                icon = f'mdi.alpha-{letter.lower()}{icon_suffix}'
                btn = tool_btn(IconRegistry.from_name(icon))
                btn.installEventFilter(OpacityEventFilter(btn, leaveOpacity=0.7))
                btn.clicked.connect(partial(self._iconSelected, icon))
                incr_icon(btn, 2)
                self.wdgFirstLetterVariants.layout().addWidget(btn)

    def _selectorToggled(self, _, toggled: bool):
        if not toggled:
            return

        if self.btnImage.isChecked():
            self.character.prefs.avatar.allow_image()
            self.wdgRightSide.setHidden(True)
        elif self.btnInitial.isChecked():
            if self.character.prefs.avatar.icon:
                self.character.prefs.avatar.allow_custom_icon()
            else:
                self.character.prefs.avatar.allow_initial()
            self.wdgRightSide.setVisible(True)
        elif self.btnRole.isChecked():
            self.character.prefs.avatar.allow_role()
            self.wdgRightSide.setHidden(True)

        self.selectorChanged.emit()

    def _selectCustomIcon(self):
        result = IconSelectorDialog.popup(pickColor=False, color=QColor(self.character.prefs.avatar.icon_color))
        if result:
            self._iconSelected(result[0])

    def _iconSelected(self, icon: str):
        self.character.prefs.avatar.allow_custom_icon()
        self.character.prefs.avatar.icon = icon
        self.selectorChanged.emit()

    def _colorChanged(self, color: QColor):
        self.character.prefs.avatar.icon_color = color.name()
        self.colorSelector.setIcon(IconRegistry.from_name('fa5s.circle', self.character.prefs.avatar.icon_color))
        self.selectorChanged.emit()

    def _upload_avatar(self):
        filename: str = QFileDialog.getOpenFileName(None, 'Choose an image', '', 'Images (*.png *.jpg *jpeg *.webp)')
        if not filename or not filename[0]:
            return
        reader = QImageReader(filename[0])
        reader.setAutoTransform(True)
        image: QImage = reader.read()
        if image is None:
            QMessageBox.warning(self, 'Error while loading image',
                                'Could not load image. Did you select a valid image? (e.g.: png, jpg, jpeg)')
            return
        if image.width() < 128 or image.height() < 128:
            QMessageBox.warning(self, 'Uploaded image is too small',
                                'The uploaded image is too small. It must be larger than 128 pixels')
            return

        pixmap = QPixmap.fromImage(image)
        crop = ImageCropDialog.popup(pixmap)
        if crop:
            self._update_avatar(crop)

    def _update_avatar(self, image: Union[QImage, QPixmap]):
        array = QByteArray()
        buffer = QBuffer(array)
        buffer.open(QIODevice.WriteOnly)
        image.save(buffer, 'PNG')
        self.character.avatar = array
        self.character.prefs.avatar.allow_image()
        self.refresh()

        self.updated.emit()

    # def _select_ai(self):
    #     diag = ArtbreederDialog()
    #     pixmap = diag.display()
    #     if pixmap:
    #         self._update_avatar(pixmap)


class CharacterAvatar(QWidget):
    avatarUpdated = pyqtSignal()

    def __init__(self, parent=None, defaultIconSize: int = 118, avatarSize: int = 168, customIconSize: int = 132,
                 margins: int = 17):
        super().__init__(parent)
        self._menu: Optional[MenuWidget] = None
        self._overlay: Optional[OverlayWidget] = None
        self._wdgAvatarSelectors: Optional[AvatarSelectors] = None

        self._defaultIconSize = defaultIconSize
        self._avatarSize = avatarSize
        self._customIconSize = customIconSize
        self.wdgFrame = QWidget()
        self.wdgFrame.setProperty('border-image', True)
        hbox(self, 0, 0).addWidget(self.wdgFrame)
        self.btnAvatar = tool_btn(IconRegistry.character_icon(), transparent_=True, icon_resize=False)
        hbox(self.wdgFrame, margins).addWidget(self.btnAvatar)
        self.btnAvatar.installEventFilter(OpacityEventFilter(parent=self.btnAvatar, enterOpacity=0.7, leaveOpacity=1.0))
        apply_border_image(self.wdgFrame, resource_registry.circular_frame1)

        self._character: Optional[Character] = None
        self._uploaded: bool = False
        self._uploadSelectorsEnabled: bool = False

        self.reset()

    def popupMenu(self) -> Optional[MenuWidget]:
        return self._menu

    def setUploadPopupMenu(self):
        if not self._character:
            raise ValueError('Set character first')
        if self._menu is None:
            self._menu = MenuWidget(self.btnAvatar)
            self._menu.aboutToShow.connect(self._aboutToShowMenu)
            self._menu.aboutToHide.connect(self._aboutToHideMenu)
            transparent_menu(self._menu)

        self._wdgAvatarSelectors = AvatarSelectors(self._character)
        self._wdgAvatarSelectors.updated.connect(self._uploadedAvatar)
        self._wdgAvatarSelectors.selectorChanged.connect(self.updateAvatar)

        self._menu.clear()
        self._menu.addWidget(self._wdgAvatarSelectors)

    def character(self) -> Optional[Character]:
        return self._character

    def setCharacter(self, character: Character):
        self._character = character
        self.updateAvatar()

    def updateAvatar(self):
        self.btnAvatar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        if self._character.prefs.avatar.use_role or self._character.prefs.avatar.use_custom_icon:
            self.btnAvatar.setIconSize(QSize(self._customIconSize, self._customIconSize))
        else:
            self.btnAvatar.setIconSize(QSize(self._avatarSize, self._avatarSize))
        avatar = avatars.avatar(self._character, fallback=False)
        if avatar:
            self.btnAvatar.setIcon(avatar)
        else:
            self.reset()
        self.avatarUpdated.emit()

    def reset(self):
        self.btnAvatar.setIconSize(QSize(self._defaultIconSize, self._defaultIconSize))
        self.btnAvatar.setIcon(IconRegistry.character_icon(color='grey'))
        self.btnAvatar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)

    def imageUploaded(self) -> bool:
        return self._uploaded

    def _aboutToShowMenu(self):
        self._overlay = OverlayWidget.getActiveWindowOverlay(alpha=75)
        self._overlay.show()
        if self._wdgAvatarSelectors:
            self._wdgAvatarSelectors.refresh()
            self._menu._frame.updateGeometry()

    def _aboutToHideMenu(self):
        if self._overlay:
            self._overlay.hide()
            self._overlay = None

    def _uploadedAvatar(self):
        self._uploaded = True
        avatars.update_image(self._character)
        self.updateAvatar()


class CharactersProgressWidget(QWidget, Ui_CharactersProgressWidget, EventListener):
    characterClicked = pyqtSignal(Character)

    RowOverall: int = 1
    RowName: int = 3
    RowRole: int = 4
    RowGender: int = 5

    @dataclass
    class Header:
        header: TemplateField
        row: int
        max_value: int = 0

        def __hash__(self):
            return hash(str(self.header.id))

    def __init__(self, parent=None):
        super(CharactersProgressWidget, self).__init__(parent)
        self.setupUi(self)
        self._layout = QGridLayout()
        self.scrollAreaProgress.setLayout(self._layout)
        margins(self, 2, 2, 2, 2)
        self._layout.setSpacing(5)
        self._refreshNext: bool = False
        self._sectionRows: Dict[CharacterProfileSectionType, int] = {}
        self._backstoryRow: int = -1
        self._topicRow: int = -1

        self.novel: Optional[Novel] = None

        self._chartMajor = CharacterRoleProgressChart(RoleImportance.MAJOR)
        self.chartViewMajor.setChart(self._chartMajor)
        self._chartSecondary = CharacterRoleProgressChart(RoleImportance.SECONDARY)
        self.chartViewSecondary.setChart(self._chartSecondary)
        self._chartMinor = CharacterRoleProgressChart(RoleImportance.MINOR)
        self.chartViewMinor.setChart(self._chartMinor)

        self._chartMajor.setBackgroundBrush(QColor(RELAXED_WHITE_COLOR))
        self._chartSecondary.setBackgroundBrush(QColor(RELAXED_WHITE_COLOR))
        self._chartMinor.setBackgroundBrush(QColor(RELAXED_WHITE_COLOR))

        self._chartMajor.refresh()
        self._chartSecondary.refresh()
        self._chartMinor.refresh()

    def setNovel(self, novel: Novel):
        self.novel = novel
        dispatcher = event_dispatchers.instance(self.novel)
        dispatcher.register(self, CharacterSummaryChangedEvent, CharacterBackstoryChangedEvent)

    @overrides
    def event_received(self, event: Event):
        self._refreshNext = True

    @overrides
    def showEvent(self, event: QShowEvent) -> None:
        if self._refreshNext:
            self._refreshNext = False
            self.refresh()

    def refreshNext(self):
        if self.isVisible():
            self.refresh()
            self._refreshNext = False
        else:
            self._refreshNext = True

    def refresh(self):
        if not self.novel:
            return

        clear_layout(self._layout)
        for chart_ in [self._chartMajor, self._chartSecondary, self._chartMinor]:
            chart_.setValue(0)
            chart_.setMaxValue(0)

        for i, char in enumerate(self.novel.characters):
            btn = tool_btn(avatars.avatar(char), tooltip=char.name, transparent_=True, parent=self)
            btn.setIconSize(QSize(45, 45))
            btn.installEventFilter(OpacityEventFilter(btn, 0.8, 1.0))
            btn.clicked.connect(partial(self.characterClicked.emit, char))
            self._layout.addWidget(btn, 0, i + 1)
        self._layout.addWidget(spacer(), 0, self._layout.columnCount())

        self._addLabel(self.RowOverall, 'Overall', IconRegistry.progress_check_icon(), Qt.AlignmentFlag.AlignCenter)
        self._addLine(self.RowOverall + 1)
        self._addLabel(self.RowName, 'Name', IconRegistry.character_icon())
        self._addLabel(self.RowRole, 'Role', IconRegistry.major_character_icon())
        self._addLabel(self.RowGender, 'Gender', IconRegistry.male_gender_icon())

        row = self.RowGender + 1
        self._addLine(row)

        row += 1

        for sectionType in CharacterProfileSectionType:
            self._sectionRows[sectionType] = row
            self._addLabel(row, sectionType.name)
            row += 1
        self._addLine(row)

        if app_env.profile().get('backstory', False):
            row += 1
            self._backstoryRow = row
            self._addLabel(row, 'Backstory', IconRegistry.backstory_icon())

        if app_env.profile().get('origin', False):
            row += 1
            self._topicRow = row
            self._addLabel(row, 'Topics', IconRegistry.topics_icon())

        row += 1
        self._layout.addWidget(vspacer(), row, 0)

        for col, char in enumerate(self.novel.characters):
            self._updateForCharacter(char, col + 1)

        self._chartMajor.refresh()
        self._chartSecondary.refresh()
        self._chartMinor.refresh()

    def _updateForCharacter(self, character: Character, col: int):
        def handleMultiAttribute(attributes: List[CharacterMultiAttribute]):
            for attrs in attributes:
                progress.addMaxValue(1)
                if attrs.value:
                    progress.addValue(1)
                for attr in attrs.attributes.values():
                    progress.addMaxValue(1)
                    if attr.value:
                        progress.addValue(1)

        name_progress = CircularProgressBar(parent=self)
        if character.name:
            name_progress.setValue(1)
        self._addWidget(name_progress, self.RowName, col)

        role_value = 0
        if character.role:
            role_value = 1
            self._addItem(character.role, self.RowRole, col)
        else:
            self._addWidget(CircularProgressBar(parent=self), self.RowRole, col)

        gender_value = 0
        if character.gender:
            gender_value = 1
            self._addIcon(IconRegistry.gender_icon(character.gender), self.RowGender, col)
        else:
            self._addWidget(CircularProgressBar(parent=self), self.RowGender, col)

        overall_progress = CircularProgressBar(maxValue=2, parent=self)
        overall_progress.setTooltipMode(ProgressTooltipMode.PERCENTAGE)
        overall_progress.setValue((name_progress.value() + gender_value) // 2 + role_value)

        for section in character.profile:
            if not section.enabled:
                continue

            row = self._sectionRows[section.type]
            progress = CircularProgressBar(parent=self)
            if section.type == CharacterProfileSectionType.Summary:
                if character.summary:
                    progress.setValue(1)
            elif section.type == CharacterProfileSectionType.Philosophy:
                if character.values:
                    progress.setValue(1)
            elif section.type == CharacterProfileSectionType.Faculties:
                progress.setMaxValue(5)
                progress.setValue(len(character.faculties.values()))
            elif section.type == CharacterProfileSectionType.Strengths:
                progress.setMaxValue(0)
                for attr in character.strengths:
                    if attr.has_strength and attr.has_weakness:
                        progress.addMaxValue(2)
                    if attr.has_strength and attr.strength:
                        progress.addValue(1)
                    if attr.has_weakness and attr.weakness:
                        progress.addValue(1)
            elif section.type == CharacterProfileSectionType.Goals:
                progress.setMaxValue(0)
                handleMultiAttribute(character.gmc)
            elif section.type == CharacterProfileSectionType.Lack:
                progress.setMaxValue(0)
                handleMultiAttribute(character.lack)
            elif section.type == CharacterProfileSectionType.Flaws:
                progress.setMaxValue(0)
                handleMultiAttribute(character.flaws)
            elif section.type == CharacterProfileSectionType.Baggage:
                progress.setMaxValue(0)
                handleMultiAttribute(character.baggage)
            elif section.type == CharacterProfileSectionType.Personality:
                if character.prefs.toggled(NovelSetting.Character_enneagram):
                    progress.addMaxValue(1)
                    if character.personality.enneagram:
                        progress.addValue(1)
                if character.prefs.toggled(NovelSetting.Character_mbti):
                    progress.addMaxValue(1)
                    if character.personality.mbti:
                        progress.addValue(1)
                if character.prefs.toggled(NovelSetting.Character_love_style):
                    progress.addMaxValue(1)
                    if character.personality.love:
                        progress.addValue(1)
                if character.prefs.toggled(NovelSetting.Character_work_style):
                    progress.addMaxValue(1)
                    if character.personality.work:
                        progress.addValue(1)
                if character.traits:
                    progress.addValue(1)

            if progress.maxValue() == 0:
                progress.setMaxValue(1)
            overall_progress.addMaxValue(progress.maxValue())
            overall_progress.addValue(progress.value())
            self._addWidget(progress, row, col)

        # for h, v in headers.items():
        #     if not h.header.required and char.is_minor():
        #         continue
        #     if not char.disabled_template_headers.get(str(h.header.id), h.header.enabled):
        #         continue
        #     value_progress = CircularProgressBar(v, h.max_value, parent=self)
        #     self._addWidget(value_progress, h.row, col + 1)
        #     overall_progress.addMaxValue(h.max_value)
        #     overall_progress.addValue(v)
        if not character.is_minor() and app_env.profile().get('backstory', False):
            backstory_progress = CircularProgressBar(parent=self)
            backstory_progress.setMaxValue(5 if character.is_major() else 3)
            backstory_progress.setValue(len(character.backstory))
            overall_progress.addMaxValue(backstory_progress.maxValue())
            overall_progress.addValue(backstory_progress.value())
            self._addWidget(backstory_progress, self._backstoryRow, col)

        if character.topics and app_env.profile().get('origin', False):
            topics_progress = CircularProgressBar(parent=self)
            topics_progress.setMaxValue(len(character.topics))
            topics_progress.setValue(len([x for x in character.topics if x.blocks and x.blocks[0].text]))
            overall_progress.addMaxValue(topics_progress.maxValue())
            overall_progress.addValue(topics_progress.value())
            self._addWidget(topics_progress, self._topicRow, col)

        self._addWidget(overall_progress, self.RowOverall, col)

        if character.is_major():
            self._chartMajor.setMaxValue(self._chartMajor.maxValue() + overall_progress.maxValue())
            self._chartMajor.setValue(self._chartMajor.value() + overall_progress.value())
        elif character.is_secondary():
            self._chartSecondary.setMaxValue(self._chartSecondary.maxValue() + overall_progress.maxValue())
            self._chartSecondary.setValue(self._chartSecondary.value() + overall_progress.value())
        elif character.is_minor():
            self._chartMinor.setMaxValue(self._chartMinor.maxValue() + overall_progress.maxValue())
            self._chartMinor.setValue(self._chartMinor.value() + overall_progress.value())

    def _addLine(self, row: int):
        self._layout.addWidget(line(), row, 0, 1, self._layout.columnCount() - 1)

    def _addLabel(self, row: int, text: str, icon=None, alignment=Qt.AlignmentFlag.AlignRight):
        if icon:
            wdg = IconText(self)
            wdg.setIcon(icon)
        else:
            wdg = QLabel(parent=self)
        wdg.setText(text)

        self._layout.addWidget(wdg, row, 0, alignment=alignment)

    def _addWidget(self, progress: QWidget, row: int, col: int):
        if row > self.RowOverall:
            progress.installEventFilter(OpacityEventFilter(parent=progress))
        self._layout.addWidget(progress, row, col, alignment=Qt.AlignmentFlag.AlignCenter)

    def _addIcon(self, icon: QIcon, row: int, col: int):
        _icon = Icon()
        _icon.setIcon(icon)
        self._addWidget(_icon, row, col)

    def _addItem(self, item: SelectionItem, row: int, col: int):
        icon = Icon()
        icon.iconName = item.icon
        icon.iconColor = item.icon_color
        icon.setToolTip(item.text)
        self._addWidget(icon, row, col)
