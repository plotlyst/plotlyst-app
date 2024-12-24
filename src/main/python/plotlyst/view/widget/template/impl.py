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
from functools import partial
from typing import Optional, List, Any, Dict, Set

from PyQt6 import QtGui
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QModelIndex, QSize
from PyQt6.QtGui import QMouseEvent, QIcon, QWheelEvent
from PyQt6.QtWidgets import QHBoxLayout, QWidget, QLineEdit, QToolButton, QLabel, \
    QSpinBox, QButtonGroup, QListView, QSlider, QFrame
from overrides import overrides
from qthandy import spacer, hbox, vbox, bold, line, underline, retain_when_hidden

from plotlyst.core.template import TemplateField, SelectionItem
from plotlyst.model.template import TemplateFieldSelectionModel, TraitsFieldItemsSelectionModel, \
    TraitsProxyModel
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.widget.button import CollapseButton
from plotlyst.view.widget.display import Subtitle, Icon
from plotlyst.view.widget.input import AutoAdjustableTextEdit, Toggle, SearchField
from plotlyst.view.widget.labels import TraitLabel, LabelsEditorWidget
from plotlyst.view.widget.progress import CircularProgressBar
from plotlyst.view.widget.template.base import TemplateDisplayWidget, TemplateFieldWidgetBase, \
    TemplateWidgetBase


def _icon(item: SelectionItem) -> QIcon:
    if item.icon:
        return IconRegistry.from_name(item.icon, item.icon_color)
    else:
        return QIcon('')


class LabelsSelectionWidget(LabelsEditorWidget):
    selectionChanged = pyqtSignal()

    def __init__(self, field: TemplateField, parent=None):
        self.field = field
        super(LabelsSelectionWidget, self).__init__(parent)
        self._model.selection_changed.connect(self.selectionChanged.emit)
        self._model.item_edited.connect(self.selectionChanged.emit)

    @overrides
    def items(self) -> List[SelectionItem]:
        return self.field.selections

    @overrides
    def _initModel(self) -> TemplateFieldSelectionModel:
        return TemplateFieldSelectionModel(self.field)


class TraitSelectionWidget(LabelsSelectionWidget):

    def __init__(self, field: TemplateField, parent=None):
        super(TraitSelectionWidget, self).__init__(field, parent)
        self._model.setEditable(False)

    @overrides
    def _initModel(self) -> TemplateFieldSelectionModel:
        return TraitsFieldItemsSelectionModel(self.field)

    @overrides
    def _initPopupWidget(self) -> QWidget:
        wdg = self.Popup()
        wdg.setModel(self._model)
        return wdg

    @overrides
    def _addItems(self, items: Set[SelectionItem]):
        for item in items:
            if item.meta.get('positive', True):
                self._wdgLabels.addLabel(TraitLabel(item.text))
        for item in items:
            if not item.meta.get('positive', True):
                self._wdgLabels.addLabel(TraitLabel(item.text, positive=False))

    class Popup(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            vbox(self, 0, 0)

            self.wdgMain = QWidget()
            self.wdgMain.setProperty('relaxed-white-bg', True)
            vbox(self.wdgMain, 5, 10)
            self.layout().addWidget(self.wdgMain)

            self.lineFilter = SearchField()
            self.lstPositiveTraitsView = QListView()
            self.lstPositiveTraitsView.setFrameShape(QFrame.Shape.NoFrame)
            self.lstNegativeTraitsView = QListView()
            self.lstNegativeTraitsView.setFrameShape(QFrame.Shape.NoFrame)

            self.wdgLists = QWidget()
            hbox(self.wdgLists)
            self.wdgLists.layout().addWidget(self.lstPositiveTraitsView)
            self.wdgLists.layout().addWidget(self.lstNegativeTraitsView)
            self.wdgMain.layout().addWidget(self.lineFilter, alignment=Qt.AlignmentFlag.AlignLeft)
            self.wdgMain.layout().addWidget(self.wdgLists)

            self.positiveProxy = TraitsProxyModel()
            self.negativeProxy = TraitsProxyModel(positive=False)
            self._model: Optional[TraitsFieldItemsSelectionModel] = None
            self.lstPositiveTraitsView.clicked.connect(self._toggleSelection)
            self.lstNegativeTraitsView.clicked.connect(self._toggleSelection)

        def setModel(self, model: TraitsFieldItemsSelectionModel):
            self._model = model

            self.positiveProxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.positiveProxy.setSourceModel(model)
            self.positiveProxy.setFilterKeyColumn(TemplateFieldSelectionModel.ColName)
            self.lstPositiveTraitsView.setModel(self.positiveProxy)

            self.negativeProxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self.negativeProxy.setSourceModel(model)
            self.negativeProxy.setFilterKeyColumn(TemplateFieldSelectionModel.ColName)
            self.lstNegativeTraitsView.setModel(self.negativeProxy)

            self.lineFilter.lineSearch.textChanged.connect(self.positiveProxy.setFilterRegularExpression)
            self.lineFilter.lineSearch.textChanged.connect(self.negativeProxy.setFilterRegularExpression)

            for lst in [self.lstPositiveTraitsView, self.lstNegativeTraitsView]:
                lst.setModelColumn(TemplateFieldSelectionModel.ColName)
                lst.setViewMode(QListView.ViewMode.IconMode)
                lst.setFixedSize(300, 300)

        @overrides
        def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
            pass

        def _toggleSelection(self, index: QModelIndex):
            if self._model is None:
                return

            item = index.data(role=TraitsFieldItemsSelectionModel.ItemRole)
            self._model.toggleCheckedItem(item)


class ButtonSelectionWidget(QWidget):

    def __init__(self, field: TemplateField, parent=None):
        super(ButtonSelectionWidget, self).__init__(parent)
        self.field = field

        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        self.group = QButtonGroup()
        self.group.setExclusive(self.field.exclusive)
        self.buttons = []
        for i, item in enumerate(self.field.selections):
            btn = QToolButton()
            btn.setIcon(_icon(item))
            btn.setToolTip(item.text)
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.buttons.append(btn)
            self.layout.addWidget(btn)
            self.group.addButton(btn, i)

    @overrides
    def mouseReleaseEvent(self, event: QMouseEvent):
        event.ignore()

    def value(self) -> List[int]:
        values = []
        for btn in self.group.buttons():
            if btn.isChecked():
                values.append(self.group.id(btn))
        return values

    def setValue(self, value: List[int]):
        for v in value:
            btn = self.group.button(v)
            if btn:
                btn.setChecked(True)


class SubtitleTemplateDisplayWidget(TemplateDisplayWidget):
    def __init__(self, field: TemplateField, parent=None):
        super(SubtitleTemplateDisplayWidget, self).__init__(field, parent)
        hbox(self)
        self.subtitle = Subtitle(self)
        self.subtitle.setTitle(field.name)
        self.subtitle.setDescription(field.description)
        self.layout().addWidget(self.subtitle)


class LabelTemplateDisplayWidget(TemplateDisplayWidget):
    def __init__(self, field: TemplateField, parent=None):
        super(LabelTemplateDisplayWidget, self).__init__(field, parent)
        hbox(self)
        self.label = QLabel(self)
        self.label.setText(field.name)
        self.label.setToolTip(field.description)
        self.layout().addWidget(self.label)


class IconTemplateDisplayWidget(TemplateDisplayWidget):
    def __init__(self, field: TemplateField, parent=None):
        super(IconTemplateDisplayWidget, self).__init__(field, parent)
        self.icon = Icon(self)
        self.icon.iconName = field.name
        if field.color:
            self.icon.iconColor = field.color
        vbox(self, 0, 0).addWidget(self.icon, alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)


class HeaderTemplateDisplayWidget(TemplateDisplayWidget):
    headerEnabledChanged = pyqtSignal(bool)

    def __init__(self, field: TemplateField, parent=None):
        super(HeaderTemplateDisplayWidget, self).__init__(field, parent)
        hbox(self, margin=1, spacing=0)
        self.btnHeader = CollapseButton(Qt.Edge.BottomEdge, Qt.Edge.RightEdge)
        self.btnHeader.setIconSize(QSize(16, 16))
        bold(self.btnHeader)
        underline(self.btnHeader)
        self.btnHeader.setText(field.name)
        self.btnHeader.setToolTip(field.description)
        self.layout().addWidget(self.btnHeader)

        self.progress = CircularProgressBar()
        self.layout().addWidget(self.progress, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.layout().addWidget(spacer())

        self._toggle: Optional[Toggle] = None
        if not field.required:
            self._toggle = Toggle(self)
            self._toggle.setToolTip(f'Character has {field.name}')

            retain_when_hidden(self._toggle)
            self._toggle.toggled.connect(self._headerEnabledChanged)
            self.layout().addWidget(self._toggle)

        self.children: List[TemplateWidgetBase] = []
        self.progressStatuses: Dict[TemplateWidgetBase, float] = {}

        self.btnHeader.toggled.connect(self._toggleCollapse)

    def attachWidget(self, widget: TemplateWidgetBase):
        self.children.append(widget)
        if not widget.field.type.is_display():
            self.progressStatuses[widget] = False
        widget.valueFilled.connect(partial(self._valueFilled, widget))
        widget.valueReset.connect(partial(self._valueReset, widget))

    def updateProgress(self):
        self.progress.setMaxValue(len(self.progressStatuses.keys()))
        self.progress.update()

    def collapse(self, collapsed: bool):
        self.btnHeader.setChecked(collapsed)

    @overrides
    def enterEvent(self, event: QtGui.QEnterEvent) -> None:
        if self._toggle and self.progress.value() == 0:
            self._toggle.setVisible(True)

    @overrides
    def leaveEvent(self, a0: QEvent) -> None:
        if self._toggle and self._toggle.isChecked():
            self._toggle.setHidden(True)

    def _toggleCollapse(self, checked: bool):
        for wdg in self.children:
            wdg.setHidden(checked)

    def setHeaderEnabled(self, enabled: bool):
        self.collapse(not enabled)
        self.btnHeader.setEnabled(enabled)
        self.progress.setVisible(enabled)
        if self._toggle:
            self._toggle.setChecked(enabled)
            self._toggle.setHidden(enabled)

    def _headerEnabledChanged(self, enabled: bool):
        self.setHeaderEnabled(enabled)
        self.headerEnabledChanged.emit(enabled)

        self._toggle.setVisible(True)

    def _valueFilled(self, widget: TemplateWidgetBase, value: float):
        if self.progressStatuses[widget] == value:
            return

        self.progressStatuses[widget] = value
        self.progress.setValue(sum(self.progressStatuses.values()))

    def _valueReset(self, widget: TemplateWidgetBase):
        if not self.progressStatuses[widget]:
            return

        self.progressStatuses[widget] = 0
        self.progress.setValue(sum(self.progressStatuses.values()))


class LineTemplateDisplayWidget(TemplateDisplayWidget):
    def __init__(self, field: TemplateField, parent=None):
        super(LineTemplateDisplayWidget, self).__init__(field, parent)
        hbox(self)
        self.layout().addWidget(line())


class LineTextTemplateFieldWidget(TemplateFieldWidgetBase):
    def __init__(self, field: TemplateField, parent=None):
        super(LineTextTemplateFieldWidget, self).__init__(field, parent)
        _layout = hbox(self)
        self.wdgEditor = QLineEdit(self)

        _layout.addWidget(self.lblEmoji)
        _layout.addWidget(self.lblName)
        _layout.addWidget(self.wdgEditor)

        if self.field.compact:
            _layout.addWidget(spacer())

        self.wdgEditor.textChanged.connect(self._textChanged)

    @overrides
    def value(self) -> Any:
        return self.wdgEditor.text()

    @overrides
    def setValue(self, value: Any):
        self.wdgEditor.setText(value)

    def _textChanged(self, text: str):
        if text:
            self.valueFilled.emit(1)
        else:
            self.valueReset.emit()


class SmallTextTemplateFieldWidget(TemplateFieldWidgetBase):
    def __init__(self, field: TemplateField, parent=None, minHeight: int = 60):
        super(SmallTextTemplateFieldWidget, self).__init__(field, parent)
        _layout = vbox(self, margin=self._boxMargin, spacing=self._boxSpacing)
        self.wdgEditor = AutoAdjustableTextEdit(height=minHeight)
        self.wdgEditor.setProperty('white-bg', True)
        self.wdgEditor.setProperty('rounded', True)
        self.wdgEditor.setAcceptRichText(False)
        self.wdgEditor.setTabChangesFocus(True)
        self.wdgEditor.setPlaceholderText(field.placeholder)
        self.wdgEditor.setToolTip(field.description if field.description else field.placeholder)
        self.setMaximumWidth(600)

        self._filledBefore: bool = False

        # self.btnNotes = QToolButton()

        self.wdgTop = group(self.lblEmoji, self.lblName, spacer())
        _layout.addWidget(self.wdgTop)
        _layout.addWidget(self.wdgEditor)

        self.wdgEditor.textChanged.connect(self._textChanged)
        # if field.has_notes:
        #     self.btnNotes.setIcon(IconRegistry.from_name('mdi6.note-plus-outline'))
        #     pointy(self.btnNotes)
        #     transparent(self.btnNotes)
        #     translucent(self.btnNotes)
        #     self._notesEditor = EnhancedTextEdit()
        #     self._notesEditor.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        #     self._notesEditor.setMinimumSize(400, 300)
        #     self._notesEditor.setAutoFormatting(QTextEdit.AutoFormattingFlag.AutoAll)
        #     self._notesEditor.setPlaceholderText(f'Add notes to {field.name}')
        #     self._notesEditor.setViewportMargins(5, 5, 5, 5)
        #     menu = btn_popup(self.btnNotes, self._notesEditor)
        #     menu.aboutToShow.connect(self._notesEditor.setFocus)
        #     self.installEventFilter(VisibilityToggleEventFilter(self.btnNotes, self))
        #     retain_when_hidden(self.btnNotes)
        # else:
        #     self.btnNotes.setHidden(True)

    @overrides
    def value(self) -> Any:
        return self.wdgEditor.toPlainText()

    @overrides
    def setValue(self, value: Any):
        self.wdgEditor.setText(value)

    def _textChanged(self):
        if self.wdgEditor.toPlainText() and not self._filledBefore:
            self.valueFilled.emit(1)
            self._filledBefore = True
        elif not self.wdgEditor.toPlainText():
            self.valueReset.emit()
            self._filledBefore = False


class NumericTemplateFieldWidget(TemplateFieldWidgetBase):
    def __init__(self, field: TemplateField, parent=None):
        super(NumericTemplateFieldWidget, self).__init__(field, parent)

        _layout = hbox(self)
        self.wdgEditor = QSpinBox()
        if field.placeholder:
            self.wdgEditor.setPrefix(field.placeholder + ': ')
        self.wdgEditor.setMinimum(field.min_value)
        self.wdgEditor.setMaximum(field.max_value)

        _layout.addWidget(self.lblEmoji)
        _layout.addWidget(self.lblName)
        _layout.addWidget(self.wdgEditor)
        if self.field.compact:
            _layout.addWidget(spacer())

        self.wdgEditor.valueChanged.connect(self._valueChanged)

    @overrides
    def value(self) -> Any:
        return self.wdgEditor.value()

    @overrides
    def setValue(self, value: Any):
        self.wdgEditor.setValue(value)

    def _valueChanged(self, value: int):
        if value:
            self.valueFilled.emit(1)
        else:
            self.valueReset.emit()


class BarSlider(QSlider):
    @overrides
    def wheelEvent(self, event: QWheelEvent) -> None:
        event.ignore()


# class EnneagramFieldWidget(TemplateFieldWidgetBase):
#     def __init__(self, field: TemplateField, parent=None):
#         super(EnneagramFieldWidget, self).__init__(field, parent)
#         self.wdgEditor = EnneagramSelector()
#         self._defaultTooltip: str = 'Select Enneagram personality'
#         _layout = vbox(self)
#         _layout.addWidget(self.wdgEditor, alignment=Qt.AlignmentFlag.AlignTop)
#
#         emojiDesire = Emoji()
#         emojiDesire.setText(emoji.emojize(':smiling_face:'))
#         emojiDesire.setToolTip('Core desire')
#         emojiFear = Emoji()
#         emojiFear.setText(emoji.emojize(':face_screaming_in_fear:'))
#         emojiFear.setToolTip('Core fear')
#         self.lblDesire = QLabel('')
#         self.lblDesire.setToolTip('Core desire')
#         self.lblFear = QLabel('')
#         self.lblFear.setToolTip('Core fear')
#
#         decr_font(emojiDesire, 2)
#         decr_font(self.lblDesire)
#         decr_font(emojiFear, 2)
#         decr_font(self.lblFear)
#
#         self.wdgAttr = group(
#             group(dash_icon(), emojiDesire, self.lblDesire, spacer()),
#             group(dash_icon(), emojiFear, self.lblFear, spacer()),
#             vertical=False)
#         margins(self.wdgAttr, left=10)
#         _layout.addWidget(self.wdgAttr)
#         self.wdgAttr.setHidden(True)
#
#         if self.field.compact:
#             _layout.addWidget(spacer())
#
#         self.wdgEditor.selected.connect(self._selectionChanged)
#         self.wdgEditor.ignored.connect(self._ignored)
#
#     @overrides
#     def value(self) -> Any:
#         return self.wdgEditor.value()
#
#     @overrides
#     def setValue(self, value: Any):
#         self.wdgEditor.setValue(value)
#         enneagram = enneagram_choices.get(value)
#         if enneagram:
#             # self.wdgEditor.setToolTip(enneagram_help[value])
#             self._selectionChanged(enneagram)
#         elif value is None:
#             self._ignored()
#         else:
#             self.wdgEditor.setToolTip(self._defaultTooltip)
#
#     def _selectionChanged(self, item: SelectionItem):
#         self.lblDesire.setText(item.meta['desire'])
#         self.lblFear.setText(item.meta['fear'])
#         self.wdgEditor.setToolTip(enneagram_help[item.text])
#         if self.isVisible():
#             qtanim.fade_in(self.wdgAttr)
#         else:
#             self.wdgAttr.setVisible(True)
#
#         self.valueFilled.emit(1)
#
#     def _ignored(self):
#         self.wdgEditor.setToolTip('Enneagram field is ignored for this character')
#         self.lblDesire.setText('')
#         self.lblFear.setText('')
#         self.wdgAttr.setHidden(True)
#         self.valueFilled.emit(1)
#
#
# class MbtiFieldWidget(TemplateFieldWidgetBase):
#     def __init__(self, field: TemplateField, parent=None):
#         super(MbtiFieldWidget, self).__init__(field, parent)
#         self.wdgEditor = MbtiSelector()
#         self._defaultTooltip: str = 'Select MBTI personality type'
#         self.wdgEditor.setToolTip(self._defaultTooltip)
#
#         _layout = vbox(self)
#         _layout.addWidget(self.wdgEditor)
#
#         self.lblKeywords = label(wordWrap=True)
#         decr_font(self.lblKeywords)
#
#         self.wdgAttr = group(dash_icon(), self.lblKeywords, spacer())
#         margins(self.wdgAttr, left=10)
#         _layout.addWidget(self.wdgAttr)
#         self.wdgAttr.setHidden(True)
#
#         if self.field.compact:
#             _layout.addWidget(spacer())
#
#         self.wdgEditor.selected.connect(self._selectionChanged)
#         self.wdgEditor.ignored.connect(self._ignored)
#
#     @overrides
#     def value(self) -> Any:
#         return self.wdgEditor.value()
#
#     @overrides
#     def setValue(self, value: Any):
#         self.wdgEditor.setValue(value)
#         if value:
#             mbti = mbti_choices[value]
#             self._selectionChanged(mbti)
#         elif value is None:
#             self._ignored()
#         else:
#             self.wdgEditor.setToolTip(self._defaultTooltip)
#
#     def _selectionChanged(self, item: SelectionItem):
#         self.lblKeywords.setText(mbti_keywords.get(item.text, ''))
#         if self.isVisible():
#             qtanim.fade_in(self.wdgAttr)
#         else:
#             self.wdgAttr.setVisible(True)
#
#         self.wdgEditor.setToolTip(mbti_help[item.text])
#         self.valueFilled.emit(1)
#
#     def _ignored(self):
#         self.wdgEditor.setToolTip('MBTI field is ignored for this character')
#         self.wdgAttr.setHidden(True)
#         self.valueFilled.emit(1)
#
#
# class LoveStyleFieldWidget(TemplateFieldWidgetBase):
#     def __init__(self, field: TemplateField, parent=None):
#         super().__init__(field, parent)
#         self.wdgEditor = LoveStyleSelector()
#         self._defaultTooltip: str = 'Select love style'
#         _layout = vbox(self)
#         _layout.addWidget(self.wdgEditor, alignment=Qt.AlignmentFlag.AlignLeft)
#
#         self.wdgEditor.selected.connect(self._selectionChanged)
#         self.wdgEditor.ignored.connect(self._ignored)
#
#     @overrides
#     def value(self) -> Any:
#         return self.wdgEditor.value()
#
#     @overrides
#     def setValue(self, value: Any):
#         self.wdgEditor.setValue(value)
#         if value:
#             mbti = love_style_choices[value]
#             self._selectionChanged(mbti)
#         elif value is None:
#             self._ignored()
#         else:
#             self.wdgEditor.setToolTip(self._defaultTooltip)
#
#     def _selectionChanged(self, item: SelectionItem):
#         pass
#
#     def _ignored(self):
#         self.wdgEditor.setToolTip('Love style field is ignored for this character')
#         self.valueFilled.emit(1)
#
#
# class WorkStyleFieldWidget(TemplateFieldWidgetBase):
#     def __init__(self, field: TemplateField, parent=None):
#         super().__init__(field, parent)
#         self.wdgEditor = DiscSelector()
#         self._defaultTooltip: str = 'Select work style'
#         _layout = vbox(self)
#         _layout.addWidget(self.wdgEditor, alignment=Qt.AlignmentFlag.AlignLeft)
#
#         self.wdgEditor.selected.connect(self._selectionChanged)
#         self.wdgEditor.ignored.connect(self._ignored)
#
#     @overrides
#     def value(self) -> Any:
#         return self.wdgEditor.value()
#
#     @overrides
#     def setValue(self, value: Any):
#         self.wdgEditor.setValue(value)
#         if value:
#             mbti = work_style_choices[value]
#             self._selectionChanged(mbti)
#         elif value is None:
#             self._ignored()
#         else:
#             self.wdgEditor.setToolTip(self._defaultTooltip)
#
#     def _selectionChanged(self, item: SelectionItem):
#         pass
#
#     def _ignored(self):
#         self.wdgEditor.setToolTip('Work style field is ignored for this character')
#         self.valueFilled.emit(1)


class LabelsTemplateFieldWidget(TemplateFieldWidgetBase):
    def __init__(self, field: TemplateField, parent=None):
        super().__init__(field, parent)
        self.wdgEditor = LabelsSelectionWidget(field)
        _layout = vbox(self)
        _layout.addWidget(group(self.lblEmoji, self.lblName, spacer()))
        _layout.addWidget(self.wdgEditor)

        self.wdgEditor.selectionChanged.connect(self._selectionChanged)

    @overrides
    def value(self) -> Any:
        return self.wdgEditor.value()

    @overrides
    def setValue(self, value: Any):
        self.wdgEditor.setValue(value)

    def _selectionChanged(self):
        if self.wdgEditor.selectedItems():
            self.valueFilled.emit(1)
        else:
            self.valueReset.emit()

# class StrengthsWeaknessesHeader(QWidget):
#     edit = pyqtSignal()
#     remove = pyqtSignal()
#
#     def __init__(self, attribute: StrengthWeaknessAttribute, parent=None):
#         super().__init__(parent)
#         self.attribute = attribute
#         hbox(self, 0)
#
#         self.btnKey = push_btn(text=self.attribute.name, transparent_=True)
#         bold(self.btnKey)
#         self.btnKey.clicked.connect(self.edit)
#
#         self.btnMenu = DotsMenuButton()
#         self.btnMenu.installEventFilter(OpacityEventFilter(self.btnMenu))
#         retain_when_hidden(self.btnMenu)
#
#         menu = MenuWidget(self.btnMenu)
#         menu.addAction(action('Edit', IconRegistry.edit_icon(), slot=self.edit))
#         menu.addSeparator()
#         menu.addAction(action('Remove', IconRegistry.trash_can_icon(), slot=self.remove))
#
#         self.layout().addWidget(self.btnKey, alignment=Qt.AlignmentFlag.AlignLeft)
#         self.layout().addWidget(self.btnMenu, alignment=Qt.AlignmentFlag.AlignRight)
#
#         self.installEventFilter(VisibilityToggleEventFilter(self.btnMenu, self))
#
#     def refreshAttribute(self, attribute: StrengthWeaknessAttribute):
#         self.attribute = attribute
#         self.btnKey.setText(self.attribute.name)
#
#
# class StrengthsWeaknessesTableRow(QWidget):
#     changed = pyqtSignal()
#
#     def __init__(self, attribute: StrengthWeaknessAttribute, parent=None):
#         super().__init__(parent)
#         self.attribute = attribute
#         hbox(self, 0, spacing=10)
#         self.textStrength = self._textEditor()
#         self.textStrength.setPlaceholderText('Define the strength of this attribute')
#         self.textStrength.setText(self.attribute.strength)
#         self.textStrength.textChanged.connect(self._strengthChanged)
#
#         self.textWeakness = self._textEditor()
#         self.textWeakness.setPlaceholderText('Define the weakness of this attribute')
#         self.textWeakness.setText(self.attribute.weakness)
#         self.textWeakness.textChanged.connect(self._weaknessChanged)
#
#         self.layout().addWidget(self.textStrength)
#         self.layout().addWidget(self.textWeakness)
#
#         self.textStrength.setVisible(self.attribute.has_strength)
#         self.textWeakness.setVisible(self.attribute.has_weakness)
#
#     def refreshAttribute(self, attribute: StrengthWeaknessAttribute):
#         self.attribute = attribute
#         self.attribute.strength = self.textStrength.toPlainText()
#         self.attribute.weakness = self.textWeakness.toPlainText()
#         self.textStrength.setVisible(self.attribute.has_strength)
#         self.textWeakness.setVisible(self.attribute.has_weakness)
#
#     def _strengthChanged(self):
#         self.attribute.strength = self.textStrength.toPlainText()
#         self.changed.emit()
#
#     def _weaknessChanged(self):
#         self.attribute.weakness = self.textWeakness.toPlainText()
#         self.changed.emit()
#
#     def _textEditor(self) -> AutoAdjustableTextEdit:
#         editor = AutoAdjustableTextEdit(height=75)
#         editor.setMaximumWidth(500)
#         editor.setProperty('white-bg', True)
#         editor.setProperty('rounded', True)
#         retain_when_hidden(editor)
#         return editor


# class StrengthsWeaknessesFieldWidget(EditableTemplateWidget):
#     def __init__(self, field: TemplateField, parent=None):
#         super().__init__(field, parent)
#         self._rows: List[StrengthsWeaknessesTableRow] = []
#
#         vbox(self, 0)
#         self._center = QWidget()
#         self._centerlayout: QGridLayout = grid(self._center, 0, 0, 5)
#         margins(self._centerlayout, left=5)
#         self._centerlayout.setColumnMinimumWidth(0, 70)
#         self._centerlayout.setColumnStretch(1, 1)
#         self._centerlayout.setColumnStretch(2, 1)
#
#         self.emojiStrength = label('')
#         self.emojiStrength.setFont(emoji_font())
#         self.emojiStrength.setText(emoji.emojize(':flexed_biceps:'))
#         self.emojiWeakness = label('')
#         self.emojiWeakness.setFont(emoji_font())
#         self.emojiWeakness.setText(emoji.emojize(':nauseated_face:'))
#         self.lblStrength = label('Strength', underline=True)
#         self.lblWeakness = label('Weakness', underline=True)
#         incr_font(self.lblStrength)
#         incr_font(self.lblWeakness)
#         self._centerlayout.addWidget(group(self.emojiStrength, self.lblStrength), 0, 1,
#                                      alignment=Qt.AlignmentFlag.AlignCenter)
#         self._centerlayout.addWidget(group(self.emojiWeakness, self.lblWeakness), 0, 2,
#                                      alignment=Qt.AlignmentFlag.AlignCenter)
#
#         self._btnPrimary = SecondaryActionPushButton()
#         self._btnPrimary.setText('Add new attribute')
#         self._btnPrimary.setIcon(IconRegistry.plus_icon('grey'))
#         self._btnPrimary.clicked.connect(self._addNewAttribute)
#         decr_font(self._btnPrimary)
#
#         self.layout().addWidget(self._center)
#         self.layout().addWidget(wrap(self._btnPrimary, margin_left=5), alignment=Qt.AlignmentFlag.AlignLeft)
#
#     @property
#     def wdgEditor(self):
#         return self
#
#     @overrides
#     def value(self) -> Any:
#         values = []
#         for row in self._rows:
#             values.append({
#                 'key': row.attribute.name,
#                 'has_strength': row.attribute.has_strength,
#                 'has_weakness': row.attribute.has_weakness,
#                 'strength': row.attribute.strength,
#                 'weakness': row.attribute.weakness
#             })
#
#         return values
#
#     @overrides
#     def setValue(self, value: Any):
#         self._rows.clear()
#         if value is None:
#             return
#         if isinstance(value, str):
#             return
#
#         for item in value:
#             attribute = StrengthWeaknessAttribute(item.get('key', ''),
#                                                   has_strength=item.get('has_strength', True),
#                                                   has_weakness=item.get('has_weakness', True),
#                                                   strength=item.get('strength', ''),
#                                                   weakness=item.get('weakness', '')
#                                                   )
#             self._addAttribute(attribute)
#
#         self._valueChanged()
#
#     def _addNewAttribute(self):
#         attribute = StrengthWeaknessEditor.popup()
#         if attribute:
#             header, rowWdg = self._addAttribute(attribute)
#             qtanim.fade_in(header, teardown=lambda: header.setGraphicsEffect(None))
#             qtanim.fade_in(rowWdg, teardown=lambda: rowWdg.setGraphicsEffect(None))
#             self._valueChanged()
#
#     def _addAttribute(self, attribute: StrengthWeaknessAttribute):
#         rowWdg = StrengthsWeaknessesTableRow(attribute)
#         rowWdg.changed.connect(self._valueChanged)
#         self._rows.append(rowWdg)
#         header = StrengthsWeaknessesHeader(attribute)
#         header.edit.connect(partial(self._edit, header, rowWdg))
#         header.remove.connect(partial(self._remove, header, rowWdg))
#
#         row = self._centerlayout.rowCount()
#         self._centerlayout.addWidget(header, row, 0, alignment=Qt.AlignmentFlag.AlignTop)
#         self._centerlayout.addWidget(rowWdg, row, 1, 1, 2)
#
#         return header, rowWdg
#
#     def _edit(self, header: StrengthsWeaknessesHeader, row: StrengthsWeaknessesTableRow):
#         attribute = StrengthWeaknessEditor.popup(header.attribute)
#         if attribute:
#             header.refreshAttribute(attribute)
#             row.refreshAttribute(attribute)
#             self._valueChanged()
#
#     def _remove(self, header: StrengthsWeaknessesHeader, row: StrengthsWeaknessesTableRow):
#         self._rows.remove(row)
#         fade_out_and_gc(self._center, header)
#         fade_out_and_gc(self._center, row)
#
#     def _valueChanged(self):
#         count = 0
#         value = 0
#         for wdg in self._rows:
#             if wdg.attribute.has_strength:
#                 count += 1
#                 if wdg.attribute.strength:
#                     value += 1
#             if wdg.attribute.has_weakness:
#                 count += 1
#                 if wdg.attribute.weakness:
#                     value += 1
#         self.valueFilled.emit(value / count if count else 0)
