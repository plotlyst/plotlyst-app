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
from typing import Optional, List, Dict, Any, Set

from PyQt6.QtCore import Qt, pyqtSignal, QObject, QEvent, QSize, QPointF, QMimeData
from PyQt6.QtGui import QIcon, QResizeEvent
from PyQt6.QtWidgets import QScrollArea, QFrame, QSizePolicy, QToolButton, QDialog
from PyQt6.QtWidgets import QWidget, QLabel
from overrides import overrides
from qthandy import vbox, hbox, bold, margins, clear_layout, transparent, retain_when_hidden, incr_font, pointy, \
    translucent, gc, sp
from qthandy.filter import DragEventFilter, DropEventFilter
from qtmenu import MenuWidget

from plotlyst.common import ALT_BACKGROUND_COLOR, PLOTLYST_TERTIARY_COLOR
from plotlyst.view.common import ButtonPressResizeEventFilter, action, fade_out_and_gc, push_btn, label
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.widget.button import EyeToggle, SmallToggleButton
from plotlyst.view.widget.display import Icon, PopupDialog
from plotlyst.view.widget.input import TextInputDialog
from plotlyst.view.widget.utility import IconSelectorDialog


@dataclass
class TreeSettings:
    font_incr: int = 0
    bg_color: str = ''
    action_buttons_color: str = 'grey'
    selection_bg_color: str = PLOTLYST_TERTIARY_COLOR
    selection_text_color: str = ''
    hover_bg_color: str = ALT_BACKGROUND_COLOR


class BaseTreeWidget(QWidget):
    selectionChanged = pyqtSignal(bool)
    deleted = pyqtSignal()
    iconChanged = pyqtSignal()
    titleChanged = pyqtSignal()

    def __init__(self, title: str, icon: Optional[QIcon] = None, parent=None, settings: Optional[TreeSettings] = None,
                 readOnly: bool = False, checkable: bool = False):
        super(BaseTreeWidget, self).__init__(parent)
        self._menuEnabled: bool = True
        self._plusEnabled: bool = True
        self._translucentIcon: bool = False
        self._pickIconColor: bool = True
        self._checkable = checkable

        if settings is None:
            self._settings = TreeSettings()
        else:
            self._settings = settings

        self._selectionEnabled: bool = not self._checkable
        self._selected: bool = False
        self._wdgTitle = QWidget(self)
        self._wdgTitle.setObjectName('wdgTitle')
        hbox(self._wdgTitle, spacing=0)

        self._lblTitle = QLabel(title)
        self._lblTitle.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self._icon = Icon(self._wdgTitle)
        if icon:
            self._icon.setIcon(icon)
        else:
            self._icon.setHidden(True)

        if self._checkable:
            self._toggleButton = SmallToggleButton()
            self._toggleButton.toggled.connect(self._checked)

        self._btnMenu = QToolButton(self._wdgTitle)
        transparent(self._btnMenu)
        self._btnMenu.setIcon(IconRegistry.dots_icon(self._settings.action_buttons_color, vertical=True))
        self._btnMenu.setIconSize(QSize(18, 18))
        self._btnMenu.setHidden(True)
        retain_when_hidden(self._btnMenu)

        self._btnAdd = QToolButton(self._wdgTitle)
        transparent(self._btnAdd)
        self._btnAdd.setIcon(IconRegistry.plus_icon(self._settings.action_buttons_color))
        self._btnAddPressFilter = ButtonPressResizeEventFilter(self._btnAdd)
        self._btnAdd.installEventFilter(self._btnAddPressFilter)
        self._btnAdd.setHidden(True)

        self._actionChangeIcon = action('Change icon', IconRegistry.icons_icon(), self._changeIcon)
        self._actionChangeTitle = action('Rename', IconRegistry.edit_icon(), self._changeTitle)
        self._actionDelete = action('Delete', IconRegistry.trash_can_icon(), self.deleted.emit)
        if not readOnly:
            self._initMenu()

        if self._checkable:
            self._wdgTitle.layout().addWidget(self._toggleButton)

        self._wdgTitle.layout().addWidget(self._icon)
        self._wdgTitle.layout().addWidget(self._lblTitle)
        # self._wdgTitle.layout().addWidget(self._btnMenu)
        # self._wdgTitle.layout().addWidget(self._btnAdd)

    def _initMenu(self):
        menu = MenuWidget(self._btnMenu)
        self._initMenuActions(menu)
        menu.aboutToHide.connect(self._hideAll)

        self._actionChangeIcon.setVisible(False)
        self._actionChangeTitle.setVisible(False)

        self._btnMenu.installEventFilter(ButtonPressResizeEventFilter(self._btnMenu))

    def _initMenuActions(self, menu: MenuWidget):
        menu.addAction(self._actionChangeTitle)
        menu.addAction(self._actionChangeIcon)
        menu.addSeparator()
        menu.addAction(self._actionDelete)

    def titleWidget(self) -> QWidget:
        return self._wdgTitle

    def titleLabel(self) -> QLabel:
        return self._lblTitle

    def select(self):
        self._toggleSelection(True)

    def deselect(self):
        self._toggleSelection(False)

    def isSelected(self) -> bool:
        return self._selected

    def setSelectionEnabled(self, enabled: bool):
        self._selectionEnabled = enabled

    def isSelectionEnabled(self) -> bool:
        return self._selectionEnabled

    def setTranslucentIconEnabled(self, enabled: bool):
        self._translucentIcon = enabled
        if enabled:
            translucent(self._icon, 0.4)
        else:
            self._icon.setGraphicsEffect(None)

    def setMenuEnabled(self, enabled: bool):
        self._menuEnabled = enabled

    def setPlusButtonEnabled(self, enabled: bool):
        self._plusEnabled = enabled

    def setPlusMenu(self, menu: MenuWidget):
        menu.aboutToHide.connect(self._hideAll)
        self._btnAdd.removeEventFilter(self._btnAddPressFilter)
        self._btnAddPressFilter = ButtonPressResizeEventFilter(self._btnAdd)
        self._btnAdd.installEventFilter(self._btnAddPressFilter)

    def checked(self) -> bool:
        return self._checkable and self._toggleButton.isChecked()

    def setChecked(self, checked: bool):
        self._toggleButton.setChecked(checked)

    def _toggleSelection(self, selected: bool):
        if not self._selectionEnabled:
            return
        self._selected = selected
        bold(self._lblTitle, self._selected)
        if self._translucentIcon:
            translucent(self._icon, 0.9 if selected else 0.4)
        self._reStyle()

    def _changeIcon(self):
        result = IconSelectorDialog.popup(pickColor=self._pickIconColor)
        if result:
            self._icon.setIcon(IconRegistry.from_name(result[0], result[1].name()))
            self._icon.setVisible(True)
            self._iconChanged(result[0], result[1].name())
            self.iconChanged.emit()

    def _iconChanged(self, iconName: str, iconColor: str):
        pass

    def _changeTitle(self):
        title = TextInputDialog.edit(placeholder='Untitled', value=self._titleValue())
        if title:
            self._lblTitle.setText(title)
            self._titleChanged(title)
            self.titleChanged.emit()

    def _titleValue(self) -> str:
        return self._lblTitle.text()

    def _titleChanged(self, title: str):
        pass

    def _hideAll(self):
        self._btnMenu.setHidden(True)
        self._btnAdd.setHidden(True)

    def _checked(self, checked: bool):
        self._lblTitle.setEnabled(checked)
        self._icon.setEnabled(checked)

    def _reStyle(self):
        if self._selected:
            self._wdgTitle.setStyleSheet(f'''
                    #wdgTitle {{
                        background-color: {self._settings.selection_bg_color};
                    }}
                ''')
        else:
            self._wdgTitle.setStyleSheet('')


class ContainerNode(BaseTreeWidget):
    doubleClicked = pyqtSignal()

    def __init__(self, title: str, icon: Optional[QIcon] = None, parent=None, settings: Optional[TreeSettings] = None,
                 readOnly: bool = False, checkable: bool = False):
        super(ContainerNode, self).__init__(title, icon, parent, settings, readOnly, checkable)
        vbox(self, 0, 0)

        self._container = QWidget(self)
        self._container.setHidden(True)
        vbox(self._container, 1, spacing=0)
        margins(self._container, left=20)
        margins(self._wdgTitle, top=2, bottom=2)
        self.layout().addWidget(self._wdgTitle)
        self.layout().addWidget(self._container)

        if settings:
            incr_font(self._lblTitle, settings.font_incr)

        if readOnly:
            self.setPlusButtonEnabled(not readOnly)
            self.setMenuEnabled(not readOnly)

        self._icon.installEventFilter(self)
        self._wdgTitle.installEventFilter(self)

    @overrides
    def resizeEvent(self, event: QResizeEvent) -> None:
        if self._plusEnabled:
            self._btnAdd.setGeometry(self._wdgTitle.width() - 20, 5, 20, 20)
            self._btnMenu.setGeometry(self._wdgTitle.width() - 40, 5, 20, 20)
        elif self._menuEnabled:
            self._btnMenu.setGeometry(self._wdgTitle.width() - 20, 5, 20, 20)

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self._wdgTitle:
            if event.type() == QEvent.Type.Enter:
                if self._menuEnabled and self.isEnabled():
                    self._btnMenu.setVisible(True)
                    self._btnMenu.raise_()
                if self._plusEnabled and self.isEnabled():
                    self._btnAdd.setVisible(True)
                    self._btnAdd.raise_()
                if not self._selected and self.isEnabled() and self._selectionEnabled:
                    self._wdgTitle.setStyleSheet(f'#wdgTitle {{background-color: {self._settings.hover_bg_color};}}')
            elif event.type() == QEvent.Type.Leave:
                if (self._menuEnabled and self._btnMenu.menu().isVisible()) or \
                        (self._plusEnabled and self._btnAdd.menu() and self._btnAdd.menu().isVisible()):
                    return super(ContainerNode, self).eventFilter(watched, event)
                self._btnMenu.setHidden(True)
                self._btnAdd.setHidden(True)
                if not self._selected:
                    self._wdgTitle.setStyleSheet('')
        if event.type() == QEvent.Type.MouseButtonRelease and self.isEnabled() and self.isSelectionEnabled():
            if not self._selected:
                self.select()
                self.selectionChanged.emit(self._selected)
        elif event.type() == QEvent.Type.MouseButtonDblClick and self.isEnabled():
            self.doubleClicked.emit()
        return super(ContainerNode, self).eventFilter(watched, event)

    def containerWidget(self) -> QWidget:
        return self._container

    def addChild(self, wdg: QWidget):
        self._container.setVisible(True)
        self._container.layout().addWidget(wdg)

    def insertChild(self, i: int, wdg: QWidget):
        self._container.setVisible(True)
        self._container.layout().insertWidget(i, wdg)

    def indexOf(self, wdg: QWidget) -> int:
        return self._container.layout().indexOf(wdg)

    def clearChildren(self):
        clear_layout(self._container)
        self._container.setHidden(True)

    def childrenWidgets(self) -> List[QWidget]:
        widgets = []
        for i in range(self._container.layout().count()):
            item = self._container.layout().itemAt(i)
            if item is None:
                continue
            widgets.append(item.widget())

        return widgets

    @overrides
    def _checked(self, checked: bool):
        super()._checked(checked)
        self._container.setEnabled(checked)
        self._container.setVisible(checked)


class EyeToggleNode(ContainerNode):
    toggled = pyqtSignal(bool)

    def __init__(self, title: str = '', icon: Optional[QIcon] = None, parent=None):
        super().__init__(title, icon, parent)

        self.setPlusButtonEnabled(False)
        self.setMenuEnabled(False)
        self.setSelectionEnabled(False)

        self._btnVisible = EyeToggle()
        self._btnVisible.toggled.connect(self._toggled)
        self._wdgTitle.layout().addWidget(self._btnVisible)
        pointy(self._wdgTitle)

    @overrides
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonRelease and self.isEnabled():
            self._btnVisible.toggle()
            return True
        return super().eventFilter(watched, event)

    def setToggleTooltip(self, tooltip: str):
        self._wdgTitle.setToolTip(tooltip)

    def isToggled(self):
        return self._btnVisible.isChecked()

    def _toggled(self, toggled: bool):
        bold(self._lblTitle, toggled)
        self.toggled.emit(toggled)


class TreeView(QScrollArea):

    def __init__(self, parent=None):
        super(TreeView, self).__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._centralWidget = QWidget(self)
        self._centralWidget.setObjectName('centralWidget')
        self.setWidget(self._centralWidget)
        vbox(self._centralWidget, spacing=0)

    def centralWidget(self) -> QWidget:
        return self._centralWidget


class ItemBasedNode(ContainerNode):

    @abstractmethod
    def item(self) -> Any:
        pass

    @abstractmethod
    def refresh(self):
        pass


class ItemBasedTreeView(TreeView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._nodes: Dict[Any, ItemBasedNode] = {}
        self._selectedItems: Set[Any] = set()

        self._dummyWdg: Optional[ItemBasedNode] = None
        self._toBeRemoved: Optional[ItemBasedNode] = None

    def clearSelection(self):
        for item in self._selectedItems:
            self._nodes[item].deselect()
        self._selectedItems.clear()

    def updateItem(self, item: Any):
        self._nodes[item].refresh()

    def _selectionChanged(self, node: ItemBasedNode, selected: bool):
        if selected:
            self.clearSelection()
            self._selectedItems.add(node.item())
            self._emitSelectionChanged(node.item())

    def _deleteNode(self, node: ItemBasedNode):
        self.clearSelection()
        self._nodes.pop(node.item())

        fade_out_and_gc(node.parent(), node)

    def _topLevelItems(self) -> List[Any]:
        pass

    @abstractmethod
    def _emitSelectionChanged(self, item: Any):
        pass

    def _node(self, item: Any) -> ItemBasedNode:
        pass

    def _initNode(self, item: Any) -> ItemBasedNode:
        pass

    def _save(self):
        pass

    def _enhanceWithDnd(self, node: ItemBasedNode):
        node.installEventFilter(
            DragEventFilter(node, self._mimeType(), dataFunc=lambda node: node.item(),
                            grabbed=node.titleLabel(),
                            startedSlot=partial(self._dragStarted, node),
                            finishedSlot=partial(self._dragStopped, node)))
        node.titleWidget().setAcceptDrops(True)
        node.titleWidget().installEventFilter(
            DropEventFilter(node, [self._mimeType()],
                            motionDetection=Qt.Orientation.Vertical,
                            motionSlot=partial(self._dragMovedOnEntity, node),
                            droppedSlot=self._drop
                            )
        )

    def _mimeType(self) -> str:
        pass

    def _dragStarted(self, node: ItemBasedNode):
        node.setHidden(True)
        self._dummyWdg = self._node(node.item())
        self._dummyWdg.setPlusButtonEnabled(False)
        self._dummyWdg.setMenuEnabled(False)
        translucent(self._dummyWdg)
        self._dummyWdg.setHidden(True)
        self._dummyWdg.setParent(self._centralWidget)
        self._dummyWdg.setAcceptDrops(True)
        self._dummyWdg.installEventFilter(
            DropEventFilter(self._dummyWdg, [self._mimeType()], droppedSlot=self._drop))

    def _dragStopped(self, node: ItemBasedNode):
        if self._dummyWdg:
            gc(self._dummyWdg)
            self._dummyWdg = None

        if self._toBeRemoved:
            gc(self._toBeRemoved)
            self._toBeRemoved = None
        else:
            node.setVisible(True)

    def _dragMovedOnEntity(self, node: ItemBasedNode, edge: Qt.Edge, point: QPointF):
        i = node.parent().layout().indexOf(node)
        if edge == Qt.Edge.TopEdge:
            node.parent().layout().insertWidget(i, self._dummyWdg)
        elif point.x() > 50:
            node.insertChild(0, self._dummyWdg)
        else:
            node.parent().layout().insertWidget(i + 1, self._dummyWdg)

        self._dummyWdg.setVisible(True)

    def _drop(self, mimeData: QMimeData):
        self.clearSelection()

        if self._dummyWdg.isHidden():
            return
        ref: Any = mimeData.reference()
        self._toBeRemoved = self._nodes[ref]
        new_widget = self._initNode(ref)
        for child in self._toBeRemoved.childrenWidgets():
            new_widget.addChild(child)

        if self._dummyWdg.parent() is self._centralWidget:
            # print('1. target parent is central')
            new_index = self._centralWidget.layout().indexOf(self._dummyWdg)
            if self._toBeRemoved.parent() is self._centralWidget:  # swap order on top
                # print('2. source parent is central')
                old_index = self._centralWidget.layout().indexOf(self._toBeRemoved)
                self._topLevelItems().remove(ref)
                if old_index < new_index:
                    # print('2.1 from above')
                    self._topLevelItems().insert(new_index - 1, ref)
                else:
                    # print('2.2 from below')
                    self._topLevelItems().insert(new_index, ref)
            else:
                # print('3. source is not central')
                self._removeFromParentEntity(ref, self._toBeRemoved)
                self._topLevelItems().insert(new_index, ref)

            self._centralWidget.layout().insertWidget(new_index, new_widget)
        elif isinstance(self._dummyWdg.parent().parent(), ItemBasedNode):
            # print('4. target is node')
            doc_parent_wdg: ItemBasedNode = self._dummyWdg.parent().parent()
            new_index = doc_parent_wdg.containerWidget().layout().indexOf(self._dummyWdg)
            if self._toBeRemoved.parent() is not self._centralWidget and \
                    self._toBeRemoved.parent().parent() is self._dummyWdg.parent().parent():  # swap under same parent doc
                # print('4.1. source is not central and swap under the same')
                old_index = doc_parent_wdg.indexOf(self._toBeRemoved)
                doc_parent_wdg.item().children.remove(ref)
                if old_index < new_index:
                    # print('4.2 from above')
                    doc_parent_wdg.item().children.insert(new_index - 1, ref)
                else:
                    # print('4.3 from below')
                    doc_parent_wdg.item().children.insert(new_index, ref)
            else:
                # print('4.1. source can be anything')
                self._removeFromParentEntity(ref, self._toBeRemoved)
                doc_parent_wdg.item().children.insert(new_index, ref)

            doc_parent_wdg.insertChild(new_index, new_widget)

        self._dummyWdg.setHidden(True)
        self._save()

    def _removeFromParentEntity(self, item: Any, node: ItemBasedNode):
        parent: ItemBasedNode = node.parent().parent()
        parent.item().children.remove(item)


class ItemBasedTreeSelectorPopup(PopupDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._selectedElement: Optional[Any] = None

        self.treeView = self._initTreeView()
        self.treeView.setMinimumSize(300, 400)
        self.treeView.setMaximumSize(500, 500)
        sp(self.treeView).v_exp().h_exp()

        self.btnSelect = push_btn(text='Select', properties=['confirm', 'positive'])
        self.btnSelect.setDisabled(True)
        self.btnSelect.clicked.connect(self.accept)
        self.btnClose = push_btn(text='Cancel', properties=['confirm', 'cancel'])
        self.btnClose.clicked.connect(self.reject)

        self.frame.layout().addWidget(self.btnReset, alignment=Qt.AlignmentFlag.AlignRight)
        self.frame.layout().addWidget(label(self._title(), h4=True), alignment=Qt.AlignmentFlag.AlignCenter)
        self.frame.layout().addWidget(self.treeView)
        self.frame.layout().addWidget(group(self.btnClose, self.btnSelect), alignment=Qt.AlignmentFlag.AlignRight)

    def display(self) -> Optional[Any]:
        result = self.exec()
        if result == QDialog.DialogCode.Accepted:
            return self._selectedElement

    @abstractmethod
    def _initTreeView(self) -> TreeView:
        pass

    def _title(self) -> str:
        return 'Select an item'

    def _selected(self, item: Any):
        self._selectedElement = item
        self.btnSelect.setEnabled(True)
