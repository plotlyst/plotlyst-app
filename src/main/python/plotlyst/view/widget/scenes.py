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
from enum import Enum
from functools import partial
from typing import List
from typing import Optional

import qtanim
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QModelIndex, QItemSelection, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QFrame, QToolButton, QTreeView, QLabel, QTableView, \
    QAbstractItemView, QButtonGroup
from overrides import overrides
from qthandy import busy, margins, pointy, vline, grid, line, retain_when_hidden
from qthandy import transparent, flow, \
    clear_layout, hbox, btn_popup, italic
from qtmenu import MenuWidget

from plotlyst.common import PLOTLYST_SECONDARY_COLOR, PLOTLYST_TERTIARY_COLOR
from plotlyst.core.client import json_client
from plotlyst.core.domain import Scene, Novel, SceneOutcome, Tag, SceneStage, \
    ReaderPosition, InformationAcquisition, Document, \
    NovelSetting, CardSizeRatio
from plotlyst.core.help import scene_disaster_outcome_help, scene_trade_off_outcome_help, \
    scene_resolution_outcome_help, scene_motion_outcome_help
from plotlyst.env import app_env
from plotlyst.event.core import Event, EventListener, emit_event
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import SceneStatusChangedEvent, \
    ActiveSceneStageChanged, AvailableSceneStagesChanged, NovelConflictTrackingToggleEvent
from plotlyst.model.common import DistributionFilterProxyModel
from plotlyst.model.distribution import CharactersScenesDistributionTableModel, TagScenesDistributionTableModel, \
    ConflictScenesDistributionTableModel, InformationScenesDistributionTableModel
from plotlyst.model.novel import NovelTagsTreeModel, TagNode
from plotlyst.model.scenes_model import ScenesTableModel
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import action, stretch_col, \
    tool_btn, label, ExclusiveOptionalButtonGroup, set_tab_icon, wrap
from plotlyst.view.generated.scene_drive_editor_ui import Ui_SceneDriveTrackingEditor
from plotlyst.view.generated.scene_dstribution_widget_ui import Ui_CharactersScenesDistributionWidget
from plotlyst.view.generated.scenes_view_preferences_widget_ui import Ui_ScenesViewPreferences
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.widget.button import SecondaryActionPushButton, \
    FadeOutButtonGroup
from plotlyst.view.widget.characters import CharacterSelectorButtons
from plotlyst.view.widget.input import DocumentTextEditor
from plotlyst.view.widget.labels import SelectionItemLabel, SceneLabel
from plotlyst.view.widget.structure.selector import ActSelectorButtons


class SceneOutcomeSelector(QWidget):
    selected = pyqtSignal(SceneOutcome)

    def __init__(self, parent=None, autoSelect: bool = True, extended: bool = False):
        super().__init__(parent)
        self._outcome = SceneOutcome.DISASTER
        hbox(self)
        self.btnDisaster = tool_btn(IconRegistry.disaster_icon(color='grey'), scene_disaster_outcome_help,
                                    checkable=True)
        self.btnResolution = tool_btn(IconRegistry.success_icon(color='grey'), scene_resolution_outcome_help,
                                      checkable=True)
        self.btnTradeOff = tool_btn(IconRegistry.tradeoff_icon(color='grey'), scene_trade_off_outcome_help,
                                    checkable=True)
        self.btnMotion = tool_btn(IconRegistry.motion_icon(color='grey'), scene_motion_outcome_help,
                                  checkable=True)
        self._initStyle(self.btnDisaster, '#FDD7D2')
        self._initStyle(self.btnTradeOff, '#F0C4E1')
        self._initStyle(self.btnResolution, '#CDFAEC')
        self._initStyle(self.btnMotion, '#E6CBAF')

        self.btnGroupOutcome = QButtonGroup()
        self._initButtonGroup()
        if autoSelect:
            self.btnDisaster.setChecked(True)

        self.layout().addWidget(self.btnDisaster)
        self.layout().addWidget(self.btnTradeOff)
        self.layout().addWidget(self.btnResolution)

        self._lineMotion = vline()
        self.layout().addWidget(self._lineMotion)
        self.layout().addWidget(self.btnMotion)
        self._lineMotion.setVisible(extended)
        self.btnMotion.setVisible(extended)

    def reset(self):
        btn = self.btnGroupOutcome.checkedButton()
        if btn:
            self.btnGroupOutcome.removeButton(self.btnDisaster)
            self.btnGroupOutcome.removeButton(self.btnResolution)
            self.btnGroupOutcome.removeButton(self.btnTradeOff)
            self.btnGroupOutcome.removeButton(self.btnMotion)
            btn.setChecked(False)

            self.btnGroupOutcome = QButtonGroup()
            self._initButtonGroup()

    def refresh(self, outcome: SceneOutcome):
        if outcome == SceneOutcome.DISASTER:
            self.btnDisaster.setChecked(True)
        elif outcome == SceneOutcome.RESOLUTION:
            self.btnResolution.setChecked(True)
        elif outcome == SceneOutcome.TRADE_OFF:
            self.btnTradeOff.setChecked(True)
        elif outcome == SceneOutcome.MOTION:
            self.btnMotion.setChecked(True)

    def _clicked(self, checked: bool):
        if not checked:
            return
        if self.btnDisaster.isChecked():
            self._outcome = SceneOutcome.DISASTER
        elif self.btnResolution.isChecked():
            self._outcome = SceneOutcome.RESOLUTION
        elif self.btnTradeOff.isChecked():
            self._outcome = SceneOutcome.TRADE_OFF
        elif self.btnMotion.isChecked():
            self._outcome = SceneOutcome.MOTION

        self.selected.emit(self._outcome)

    def _initButtonGroup(self):
        self.btnGroupOutcome.setExclusive(True)
        self.btnGroupOutcome.addButton(self.btnDisaster)
        self.btnGroupOutcome.addButton(self.btnTradeOff)
        self.btnGroupOutcome.addButton(self.btnResolution)
        self.btnGroupOutcome.addButton(self.btnMotion)

        self.btnGroupOutcome.buttonClicked.connect(self._clicked)

    def _initStyle(self, btn: QToolButton, color: str):
        btn.setIconSize(QSize(20, 20))
        btn.setStyleSheet(f'''
        QToolButton {{
            border-radius: 12px;
            border: 1px hidden lightgrey;
            padding: 2px;
        }}
        QToolButton:hover {{
            background: {color};
        }}
        ''')


class SceneTagSelector(QWidget):
    def __init__(self, novel: Novel, parent=None):
        super(SceneTagSelector, self).__init__(parent)
        self.novel = novel

        hbox(self)
        self.btnSelect = QToolButton(self)
        self.btnSelect.setIcon(IconRegistry.tag_plus_icon())
        self.btnSelect.setCursor(Qt.CursorShape.PointingHandCursor)

        self._tagsModel = NovelTagsTreeModel(self.novel)
        self._tagsModel.selectionChanged.connect(self._selectionChanged)
        self._treeSelectorView = QTreeView()
        self._treeSelectorView.setCursor(Qt.CursorShape.PointingHandCursor)
        self._treeSelectorView.setModel(self._tagsModel)
        self._treeSelectorView.setHeaderHidden(True)
        self._treeSelectorView.clicked.connect(self._toggle)
        self._treeSelectorView.expandAll()
        self._tagsModel.modelReset.connect(self._treeSelectorView.expandAll)
        btn_popup(self.btnSelect, self._treeSelectorView)

        self.wdgTags = QFrame(self)
        flow(self.wdgTags)

        self.layout().addWidget(group(self.btnSelect, QLabel('Tags:'), margin=0), alignment=Qt.AlignmentFlag.AlignTop)
        self.layout().addWidget(self.wdgTags)

    def setScene(self, scene: Scene):
        self._tagsModel.clear()
        for tag in scene.tags(self.novel):
            self._tagsModel.check(tag)

    def tags(self) -> List[Tag]:
        return self._tagsModel.checkedTags()

    def _selectionChanged(self):
        tags = self._tagsModel.checkedTags()
        clear_layout(self.wdgTags)
        for tag in tags:
            label = SelectionItemLabel(tag, self.wdgTags, removalEnabled=True)
            label.removalRequested.connect(partial(self._tagsModel.uncheck, tag))
            self.wdgTags.layout().addWidget(label)

    def _toggle(self, index: QModelIndex):
        node = index.data(NovelTagsTreeModel.NodeRole)
        if isinstance(node, TagNode):
            self._tagsModel.toggle(node.tag)


class SceneSelector(SecondaryActionPushButton):
    sceneSelected = pyqtSignal(Scene)

    def __init__(self, novel: Novel, text: str = '', parent=None):
        super(SceneSelector, self).__init__(parent)
        self.novel = novel
        self.setText(text)
        italic(self)
        self.setIcon(IconRegistry.scene_icon('grey'))

        self._lstScenes = QTableView()
        self._lstScenes.verticalHeader().setHidden(True)
        self._lstScenes.horizontalHeader().setHidden(True)
        self._lstScenes.verticalHeader().setDefaultSectionSize(20)
        self._lstScenes.horizontalHeader().setDefaultSectionSize(24)
        self._lstScenes.setShowGrid(False)
        self._lstScenes.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._lstScenes.clicked.connect(self._selected)
        pointy(self._lstScenes)
        self.menu = btn_popup(self, self._lstScenes)
        self.menu.aboutToShow.connect(self._beforePopup)

    @busy
    def _beforePopup(self):
        self._scenesModel = ScenesTableModel(self.novel)

        self._lstScenes.setModel(self._scenesModel)
        for col in range(self._scenesModel.columnCount()):
            self._lstScenes.hideColumn(col)
        self._lstScenes.showColumn(ScenesTableModel.ColPov)
        self._lstScenes.showColumn(ScenesTableModel.ColType)
        self._lstScenes.showColumn(ScenesTableModel.ColTitle)
        self._lstScenes.horizontalHeader().swapSections(ScenesTableModel.ColType, ScenesTableModel.ColTitle)

        stretch_col(self._lstScenes, ScenesTableModel.ColTitle)

    def _selected(self, index: QModelIndex):
        scene = index.data(ScenesTableModel.SceneRole)
        self.sceneSelected.emit(scene)
        self.menu.hide()


class SceneLabelLinkWidget(QWidget):
    sceneSelected = pyqtSignal(Scene)

    def __init__(self, novel: Novel, text: str = '', parent=None):
        super(SceneLabelLinkWidget, self).__init__(parent)
        self.novel = novel
        self.scene: Optional[Scene] = None

        self.label: Optional[SceneLabel] = None

        hbox(self)
        self.btnSelect = SceneSelector(self.novel, text, parent=self)
        self.layout().addWidget(self.btnSelect)
        self.btnSelect.sceneSelected.connect(self.sceneSelected.emit)

    def setScene(self, scene: Scene):
        self.scene = scene
        if self.label is None:
            self.label = SceneLabel(self.scene)
            self.layout().addWidget(self.label)
            self.label.clicked.connect(self.btnSelect.menu.show)
        else:
            self.label.setScene(scene)

        self.btnSelect.setHidden(True)


class SceneFilterWidget(QWidget):
    def __init__(self, novel: Novel, parent=None):
        super(SceneFilterWidget, self).__init__(parent)
        self.novel = novel
        self.povFilter = CharacterSelectorButtons()
        margins(self.povFilter, left=15)
        self.povFilter.setExclusive(False)
        self.povFilter.setCharacters(self.novel.pov_characters())

        self.wdgActs = ActSelectorButtons(self.novel)
        margins(self.wdgActs, left=15)
        self.lblActs = label('Acts:')

        grid(self)
        self.layout().addWidget(label('Point of view:'), 0, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(self.povFilter, 0, 1)
        self.layout().addWidget(self.lblActs, 1, 0, alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(self.wdgActs, 1, 1, alignment=Qt.AlignmentFlag.AlignLeft)


class ScenePreferencesTabType(Enum):
    CARDS = 0
    TABLE = 1


class ScenesPreferencesWidget(QWidget, Ui_ScenesViewPreferences):
    DEFAULT_CARD_WIDTH: int = 175
    settingToggled = pyqtSignal(NovelSetting, bool)
    cardWidthChanged = pyqtSignal(int)
    cardRatioChanged = pyqtSignal(CardSizeRatio)
    tabChanged = pyqtSignal(ScenePreferencesTabType)

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.novel = novel

        self.btnCardsWidth.setIcon(IconRegistry.from_name('ei.resize-horizontal'))
        self.btnPov.setIcon(IconRegistry.eye_open_icon())
        self.btnPurpose.setIcon(IconRegistry.from_name('fa5s.yin-yang'))
        self.btnPlotProgress.setIcon(IconRegistry.from_name('mdi.chevron-double-up'))
        self.btnCharacters.setIcon(IconRegistry.character_icon())
        self.btnStorylines.setIcon(IconRegistry.storylines_icon())
        self.btnStage.setIcon(IconRegistry.progress_check_icon())

        self.wdgPurpose.setVisible(app_env.profile().get('scene-purpose', False))
        self.wdgProgress.setVisible(app_env.profile().get('scene-progression', False))

        self.bottomLeftButtonGroup = ExclusiveOptionalButtonGroup()
        self.bottomLeftButtonGroup.addButton(self.cbPurpose)
        self.bottomLeftButtonGroup.addButton(self.cbPlotProgress)

        self.btnTablePov.setIcon(IconRegistry.eye_open_icon())
        self.btnTableStorylines.setIcon(IconRegistry.storylines_icon())
        self.btnTableCharacters.setIcon(IconRegistry.character_icon())
        self.btnTablePurpose.setIcon(IconRegistry.from_name('fa5s.yin-yang'))
        self.btnTablePlotProgress.setIcon(IconRegistry.from_name('mdi.chevron-double-up'))

        self.wdgTablePurpose.setVisible(app_env.profile().get('scene-purpose', False))
        self.wdgTableProgress.setVisible(app_env.profile().get('scene-progression', False))
        self.wdgTableStorylines.setVisible(app_env.profile().get('storylines', False))

        self.tabCards.layout().insertWidget(1, line(color='lightgrey'))
        self.tabCards.layout().insertWidget(5, wrap(line(color='lightgrey'), margin_left=10))
        self.tabTable.layout().insertWidget(1, line(color='lightgrey'))

        self.btnGroup = ExclusiveOptionalButtonGroup()
        self.btnGroup.addButton(self.cbCharacters)
        self.btnGroup.addButton(self.cbStorylines)

        self.cbPov.setChecked(self.novel.prefs.toggled(NovelSetting.SCENE_CARD_POV))
        self.cbPurpose.setChecked(self.novel.prefs.toggled(NovelSetting.SCENE_CARD_PURPOSE))
        self.cbPlotProgress.setChecked(self.novel.prefs.toggled(NovelSetting.SCENE_CARD_PLOT_PROGRESS))
        self.cbStage.setChecked(self.novel.prefs.toggled(NovelSetting.SCENE_CARD_STAGE))

        self.cbTablePov.setChecked(self.novel.prefs.toggled(NovelSetting.SCENE_TABLE_POV))
        self.cbTableStorylines.setChecked(self.novel.prefs.toggled(NovelSetting.SCENE_TABLE_STORYLINES))
        self.cbTableCharacters.setChecked(self.novel.prefs.toggled(NovelSetting.SCENE_TABLE_CHARACTERS))
        self.cbTablePurpose.setChecked(self.novel.prefs.toggled(NovelSetting.SCENE_TABLE_PURPOSE))
        self.cbTablePlotProgress.setChecked(self.novel.prefs.toggled(NovelSetting.SCENE_TABLE_PLOT_PROGRESS))

        self.cbPov.clicked.connect(self._cardPovClicked)
        self.cbPurpose.clicked.connect(self._cardPurposeClicked)
        self.cbPlotProgress.clicked.connect(self._cardPlotProgressClicked)
        self.cbStage.clicked.connect(partial(self.settingToggled.emit, NovelSetting.SCENE_CARD_STAGE))

        self.cbTablePov.clicked.connect(partial(self.settingToggled.emit, NovelSetting.SCENE_TABLE_POV))
        self.cbTableStorylines.clicked.connect(partial(self.settingToggled.emit, NovelSetting.SCENE_TABLE_STORYLINES))
        self.cbTableCharacters.clicked.connect(partial(self.settingToggled.emit, NovelSetting.SCENE_TABLE_CHARACTERS))
        self.cbTablePurpose.clicked.connect(partial(self.settingToggled.emit, NovelSetting.SCENE_TABLE_PURPOSE))
        self.cbTablePlotProgress.clicked.connect(
            partial(self.settingToggled.emit, NovelSetting.SCENE_TABLE_PLOT_PROGRESS))

        self.sliderCards.setValue(self.novel.prefs.setting(NovelSetting.SCENE_CARD_WIDTH, self.DEFAULT_CARD_WIDTH))
        self.sliderCards.valueChanged.connect(self.cardWidthChanged)

        # self.rb23.clicked.connect(partial(self.cardRatioChanged.emit, CardSizeRatio.RATIO_2_3))
        # self.rb34.clicked.connect(partial(self.cardRatioChanged.emit, CardSizeRatio.RATIO_3_4))
        self.rb23.setHidden(True)
        self.rb34.setHidden(True)

        self.wdgCharacters.setHidden(True)
        self.wdgStorylines.setHidden(True)

        set_tab_icon(self.tabWidget, self.tabCards, IconRegistry.cards_icon())
        set_tab_icon(self.tabWidget, self.tabTable, IconRegistry.table_icon())

        self.tabWidget.currentChanged.connect(self._tabChanged)

    def showCardsTab(self):
        self.tabWidget.setCurrentWidget(self.tabCards)

    def showTableTab(self):
        self.tabWidget.setCurrentWidget(self.tabTable)

    def _cardPovClicked(self, checked: bool):
        def handle():
            self.settingToggled.emit(NovelSetting.SCENE_CARD_POV, checked)

        QTimer.singleShot(150, handle)

    def _cardPurposeClicked(self, checked: bool):
        def handle():
            if checked:
                self.settingToggled.emit(NovelSetting.SCENE_CARD_PLOT_PROGRESS, False)
            self.settingToggled.emit(NovelSetting.SCENE_CARD_PURPOSE, checked)

        QTimer.singleShot(150, handle)

    def _cardPlotProgressClicked(self, checked: bool):
        def handle():
            if checked:
                self.settingToggled.emit(NovelSetting.SCENE_CARD_PURPOSE, False)
            self.settingToggled.emit(NovelSetting.SCENE_CARD_PLOT_PROGRESS, checked)

        QTimer.singleShot(150, handle)

    def _tabChanged(self, index: int):
        if self.tabWidget.widget(index) is self.tabCards:
            self.tabChanged.emit(ScenePreferencesTabType.CARDS)
        elif self.tabWidget.widget(index) is self.tabTable:
            self.tabChanged.emit(ScenePreferencesTabType.TABLE)


class SceneNotesEditor(DocumentTextEditor):

    def __init__(self, parent=None):
        super(SceneNotesEditor, self).__init__(parent)
        self._scene: Optional[Scene] = None
        self.setTitleVisible(False)
        self.setPlaceholderText('Scene notes')

        self.textEdit.textChanged.connect(self._save)

        self.repo = RepositoryPersistenceManager.instance()

    def setScene(self, scene: Scene):
        self._scene = scene
        if self._scene.document is None:
            self._scene.document = Document('', scene_id=self._scene.id)
            self._scene.document.loaded = True
        if not scene.document.loaded:
            json_client.load_document(app_env.novel, scene.document)

        self.setText(scene.document.content, '')

    def _save(self):
        if self._scene is None:
            return
        self._scene.document.content = self.textEdit.toHtml()
        self.repo.update_doc(app_env.novel, self._scene.document)


class SceneStageButton(QToolButton, EventListener):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene: Optional[Scene] = None
        self._novel: Optional[Novel] = None
        self._stageOk: bool = False
        self._activeColor: str = PLOTLYST_SECONDARY_COLOR

        transparent(self)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        pointy(self)

        self.repo = RepositoryPersistenceManager.instance()

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, (ActiveSceneStageChanged, AvailableSceneStagesChanged)):
            self.updateStage()
        elif isinstance(event, SceneStatusChangedEvent) and event.scene == self._scene:
            self.updateStage()

    def setActiveColor(self, color: str):
        self._activeColor = color

    def setScene(self, scene: Scene, novel: Novel):
        self._scene = scene
        self._novel = novel

        dispatcher = event_dispatchers.instance(self._novel)
        dispatcher.register(self, ActiveSceneStageChanged, SceneStatusChangedEvent, AvailableSceneStagesChanged)

        self.updateStage()

    def stageOk(self) -> bool:
        return self._stageOk

    def updateStage(self):
        if self._scene is None:
            return
        self._stageOk = False
        active_stage = self._novel.active_stage
        if self._scene.stage and active_stage:
            active_stage_index = self._novel.stages.index(active_stage)
            scene_stage_index = self._novel.stages.index(self._scene.stage)

            if scene_stage_index >= active_stage_index:
                self._stageOk = True

        if self._scene.stage:
            if self._stageOk:
                self.setIcon(IconRegistry.ok_icon(self._activeColor))
            else:
                self.setIcon(IconRegistry.progress_check_icon(PLOTLYST_TERTIARY_COLOR))
        else:
            self.setIcon(IconRegistry.progress_check_icon('grey'))

        menu = MenuWidget(self)
        for stage in self._novel.stages:
            act = action(stage.text, slot=partial(self._changeStage, stage), checkable=True, parent=menu)
            act.setChecked(self._scene.stage == stage)
            menu.addAction(act)

    def _changeStage(self, stage: SceneStage):
        self._scene.stage = stage
        self.updateStage()
        self.repo.update_scene(self._scene)

        emit_event(self._novel, SceneStatusChangedEvent(self, self._scene))


class SceneDriveTrackingEditor(QWidget, Ui_SceneDriveTrackingEditor):
    def __init__(self, parent=None):
        super(SceneDriveTrackingEditor, self).__init__(parent)
        self.setupUi(self)
        self.scene: Optional[Scene] = None

        self.sliderWorld.valueChanged.connect(self._worldBuildingChanged)
        self.sliderTension.valueChanged.connect(self._tensionChanged)

        self.informationBtnGroup = FadeOutButtonGroup()
        self.informationBtnGroup.addButton(self.btnDiscovery)
        self.informationBtnGroup.addButton(self.btnRevelation)
        self.informationBtnGroup.buttonClicked.connect(self._informationClicked)

        self.readerPosBtnGroup = FadeOutButtonGroup()
        self.readerPosBtnGroup.addButton(self.btnReaderSuperior)
        self.readerPosBtnGroup.addButton(self.btnReaderInferior)
        self.readerPosBtnGroup.buttonClicked.connect(self._readerPosClicked)

        self.btnDeuxExMachina.clicked.connect(self._deusExClicked)

    def reset(self):
        self.scene = None
        self.sliderWorld.setValue(0)
        self.sliderTension.setValue(0)
        self.readerPosBtnGroup.reset()
        self.informationBtnGroup.reset()
        self.btnDeuxExMachina.setChecked(False)

    def setScene(self, scene: Scene):
        self.reset()
        self.scene = scene

        self.sliderWorld.setValue(self.scene.drive.worldbuilding)
        self.sliderTension.setValue(self.scene.drive.tension)
        self.btnDeuxExMachina.setChecked(self.scene.drive.deus_ex_machina)

        if self.scene.drive.new_information == InformationAcquisition.DISCOVERY:
            self.informationBtnGroup.toggle(self.btnDiscovery)
        elif self.scene.drive.new_information == InformationAcquisition.REVELATION:
            self.informationBtnGroup.toggle(self.btnRevelation)

        if self.scene.drive.reader_position == ReaderPosition.SUPERIOR:
            self.readerPosBtnGroup.toggle(self.btnReaderSuperior)
        elif self.scene.drive.reader_position == ReaderPosition.INFERIOR:
            self.readerPosBtnGroup.toggle(self.btnReaderInferior)

    def _worldBuildingChanged(self, value: int):
        if value > 0 and self.sliderWorld.isVisible():
            qtanim.glow(self.sliderWorld, radius=12, color=QColor('#40916c'))

        if self.scene:
            self.scene.drive.worldbuilding = value

    def _tensionChanged(self, value: int):
        if value > 0 and self.sliderTension.isVisible():
            qtanim.glow(self.sliderTension, radius=12, color=QColor('#d00000'))

        if self.scene:
            self.scene.drive.tension = value

    def _readerPosClicked(self):
        if self.readerPosBtnGroup.checkedButton() == self.btnReaderSuperior:
            self.scene.drive.reader_position = ReaderPosition.SUPERIOR
        elif self.readerPosBtnGroup.checkedButton() == self.btnReaderInferior:
            self.scene.drive.reader_position = ReaderPosition.INFERIOR

    def _informationClicked(self):
        if self.informationBtnGroup.checkedButton() == self.btnDiscovery:
            self.scene.drive.new_information = InformationAcquisition.DISCOVERY
        elif self.informationBtnGroup.checkedButton() == self.btnRevelation:
            self.scene.drive.new_information = InformationAcquisition.REVELATION

    def _deusExClicked(self, checked: bool):
        self.scene.drive.deus_ex_machina = checked


class ScenesDistributionWidget(QWidget, Ui_CharactersScenesDistributionWidget, EventListener):
    avg_text: str = 'Characters per scene: '
    common_text: str = 'Common scenes: '

    def __init__(self, novel: Novel, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.novel = novel
        self.average = 0

        self.btnCharacters.setIcon(IconRegistry.character_icon())
        self.btnConflicts.setIcon(IconRegistry.conflict_icon('black', color_on=PLOTLYST_SECONDARY_COLOR))
        self.btnTags.setIcon(IconRegistry.tags_icon())
        self.btnInformation.setIcon(IconRegistry.from_name('fa5s.book-reader', color_on=PLOTLYST_SECONDARY_COLOR))
        self.btnTags.setHidden(True)
        self.btnInformation.setHidden(True)

        self._model = CharactersScenesDistributionTableModel(self.novel)
        self._scenes_proxy = DistributionFilterProxyModel()
        self._scenes_proxy.setSourceModel(self._model)
        self._scenes_proxy.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._scenes_proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._scenes_proxy.setSortRole(CharactersScenesDistributionTableModel.SortRole)
        self._scenes_proxy.sort(CharactersScenesDistributionTableModel.IndexTags, Qt.SortOrder.DescendingOrder)
        self.tblSceneDistribution.horizontalHeader().setDefaultSectionSize(26)
        self.tblSceneDistribution.setModel(self._scenes_proxy)
        self.tblSceneDistribution.hideColumn(0)
        self.tblSceneDistribution.hideColumn(1)
        self.tblCharacters.setModel(self._scenes_proxy)
        self.tblCharacters.hideColumn(0)
        self.tblCharacters.setColumnWidth(CharactersScenesDistributionTableModel.IndexTags, 70)
        self.tblCharacters.setMaximumWidth(70)

        self.tblCharacters.selectionModel().selectionChanged.connect(self._on_character_selected)
        self.tblSceneDistribution.selectionModel().selectionChanged.connect(self._on_scene_selected)

        self.btnCharacters.toggled.connect(self._toggle_characters)
        self.btnConflicts.toggled.connect(self._toggle_conflicts)
        self.btnInformation.toggled.connect(self._toggle_information)
        self.btnTags.toggled.connect(self._toggle_tags)

        transparent(self.spinAverage)
        retain_when_hidden(self.spinAverage)

        self.btnCharacters.setChecked(True)
        self.btnConflicts.setVisible(self.novel.prefs.toggled(NovelSetting.Track_conflict))
        self.btnConflicts.setHidden(True)
        event_dispatchers.instance(self.novel).register(self, NovelConflictTrackingToggleEvent)

        self.refresh()

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, NovelConflictTrackingToggleEvent):
            self.btnConflicts.setVisible(event.toggled)
            if self.btnConflicts.isChecked():
                self.btnCharacters.setChecked(True)

    def refresh(self):
        self.refreshAverage()
        for col in range(self._model.columnCount()):
            if col == CharactersScenesDistributionTableModel.IndexTags:
                continue
            self.tblCharacters.hideColumn(col)
        self.tblSceneDistribution.horizontalHeader().setMaximumSectionSize(15)
        self._model.modelReset.emit()

    def refreshAverage(self):
        if self.novel.scenes:
            self.average = sum([len(x.characters) + 1 if x.pov else 0 for x in self.novel.scenes]) / len(
                self.novel.scenes)
        else:
            self.average = 0
        self.spinAverage.setValue(self.average)

    def setActsFilter(self, act: int, filter: bool):
        self._scenes_proxy.setActsFilter(act, filter)

    def resetActsFilter(self):
        self._scenes_proxy.resetActsFilter()

    def _toggle_characters(self, toggled: bool):
        if toggled:
            self._model = CharactersScenesDistributionTableModel(self.novel)
            self._scenes_proxy.setSourceModel(self._model)
            self.tblCharacters.hideColumn(0)
            self.tblCharacters.setColumnWidth(CharactersScenesDistributionTableModel.IndexTags, 70)
            self.tblCharacters.setMaximumWidth(70)

            self.spinAverage.setVisible(True)

    # def _toggle_goals(self, toggled: bool):
    #     if toggled:
    #         self._model = GoalScenesDistributionTableModel(self.novel)
    #         self._scenes_proxy.setSourceModel(self._model)
    #         self.tblCharacters.hideColumn(0)
    #         self.tblCharacters.setColumnWidth(CharactersScenesDistributionTableModel.IndexTags, 170)
    #         self.tblCharacters.setMaximumWidth(170)
    #
    #         self.spinAverage.setVisible(False)

    def _toggle_conflicts(self, toggled: bool):
        if toggled:
            self._model = ConflictScenesDistributionTableModel(self.novel)
            self._scenes_proxy.setSourceModel(self._model)
            self.tblCharacters.showColumn(0)
            self.tblCharacters.setColumnWidth(CharactersScenesDistributionTableModel.IndexMeta, 34)
            self.tblCharacters.setColumnWidth(CharactersScenesDistributionTableModel.IndexTags, 170)
            self.tblCharacters.setMaximumWidth(204)

            self.spinAverage.setVisible(False)

    def _toggle_information(self, toggled: bool):
        if toggled:
            self._model = InformationScenesDistributionTableModel(self.novel)
            self._scenes_proxy.setSourceModel(self._model)
            self.tblCharacters.hideColumn(0)
            self.tblCharacters.setColumnWidth(CharactersScenesDistributionTableModel.IndexTags, 170)
            self.tblCharacters.setMaximumWidth(170)

            self.spinAverage.setVisible(False)

    def _toggle_tags(self, toggled: bool):
        if toggled:
            self._model = TagScenesDistributionTableModel(self.novel)
            self._scenes_proxy.setSourceModel(self._model)
            self.tblCharacters.hideColumn(0)
            self.tblCharacters.setColumnWidth(CharactersScenesDistributionTableModel.IndexTags, 170)
            self.tblCharacters.setMaximumWidth(170)

            self.spinAverage.setVisible(False)

    def _on_character_selected(self):
        selected = self.tblCharacters.selectionModel().selectedIndexes()
        self._model.highlightTags(
            [self._scenes_proxy.mapToSource(x) for x in selected])

        if selected and len(selected) > 1:
            self.spinAverage.setPrefix(self.common_text)
            self.spinAverage.setValue(self._model.commonScenes())
        else:
            self.spinAverage.setPrefix(self.avg_text)
            self.spinAverage.setValue(self.average)

        self.tblSceneDistribution.clearSelection()

    def _on_scene_selected(self, selection: QItemSelection):
        indexes = selection.indexes()
        if not indexes:
            return
        self._model.highlightScene(self._scenes_proxy.mapToSource(indexes[0]))
        self.tblCharacters.clearSelection()
