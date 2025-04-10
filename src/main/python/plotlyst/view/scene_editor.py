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
from typing import Optional

import qtanim
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QTableView, QFrame
from overrides import overrides
from qthandy import incr_font, margins, pointy, clear_layout, busy, flow, retain_when_hidden, translucent
from qthandy.filter import OpacityEventFilter
from qtmenu import MenuWidget

from plotlyst.common import PLOTLYST_SECONDARY_COLOR
from plotlyst.core.client import json_client
from plotlyst.core.domain import Novel, Scene, Document, StoryBeat, \
    Character, Plot, ScenePlotReference, NovelSetting, StoryElementType, SceneOutcome, ScenePurposeType
from plotlyst.env import app_env
from plotlyst.event.core import EventListener, Event, emit_event
from plotlyst.event.handler import event_dispatchers
from plotlyst.events import NovelAboutToSyncEvent, SceneStoryBeatChangedEvent, \
    NovelStorylinesToggleEvent, NovelStructureToggleEvent, NovelPovTrackingToggleEvent, SceneChangedEvent, \
    NovelSyncEvent, NovelScenesOrganizationToggleEvent
from plotlyst.model.characters_model import CharactersSceneAssociationTableModel
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.common import emoji_font, set_tab_icon, \
    push_btn, fade_out_and_gc, set_tab_visible, scroll_to_bottom, link_buttons_to_pages
from plotlyst.view.generated.scene_editor_ui import Ui_SceneEditor
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.characters import CharacterSelectorMenu
from plotlyst.view.widget.labels import CharacterLabel
from plotlyst.view.widget.scene.agency import SceneAgencyEditor
from plotlyst.view.widget.scene.editor import ScenePurposeTypeButton, SceneProgressEditor
from plotlyst.view.widget.scene.functions import SceneFunctionsWidget
from plotlyst.view.widget.scene.plot import ScenePlotLabels, \
    ScenePlotSelectorMenu
from plotlyst.view.widget.scene.reader_drive import ReaderInformationEditor
from plotlyst.view.widget.structure.selector import StructureBeatSelectorButton
from plotlyst.view.widget.tree import TreeSettings


class SceneEditor(QObject, EventListener):
    close = pyqtSignal()

    def __init__(self, novel: Novel):
        super().__init__()
        self.widget = QWidget()
        self.ui = Ui_SceneEditor()
        self.ui.setupUi(self.widget)
        self.novel = novel
        self.scene: Optional[Scene] = None
        self.notes_updated: bool = False

        self._emoji_font = emoji_font()

        set_tab_icon(self.ui.tabWidget, self.ui.tabFunctions,
                     IconRegistry.storylines_icon(color_on=PLOTLYST_SECONDARY_COLOR))
        set_tab_icon(self.ui.tabWidget, self.ui.tabDrive,
                     IconRegistry.from_name('mdi.chemical-weapon', color_on=PLOTLYST_SECONDARY_COLOR))
        set_tab_icon(self.ui.tabWidget, self.ui.tabStructure,
                     IconRegistry.from_name('mdi6.timeline-outline', rotated=90, color_on=PLOTLYST_SECONDARY_COLOR))
        set_tab_icon(self.ui.tabWidget, self.ui.tabNotes, IconRegistry.document_edition_icon())

        set_tab_icon(self.ui.tabWidgetDrive, self.ui.tabAgency, IconRegistry.character_icon())
        # set_tab_icon(self.ui.tabWidgetDrive, self.ui.tabCuriosity,
        #              IconRegistry.from_name('ei.question-sign', color_on=PLOTLYST_SECONDARY_COLOR))
        # set_tab_icon(self.ui.tabWidgetFunctions, self.ui.tabDramaticFunctions,
        #              IconRegistry.from_name('mdi.yin-yang', color_on=PLOTLYST_SECONDARY_COLOR))
        # set_tab_icon(self.ui.tabWidgetFunctions, self.ui.tabInformationFunctions,
        #              IconRegistry.from_name('fa5s.book-reader', color_on=PLOTLYST_SECONDARY_COLOR))
        set_tab_visible(self.ui.tabWidget, self.ui.tabFunctions, app_env.profile().get('scene-functions', False))
        set_tab_visible(self.ui.tabWidget, self.ui.tabStructure, False)
        set_tab_visible(self.ui.tabWidget, self.ui.tabDrive, False)

        self.ui.btnDramaticFunctions.setIcon(
            IconRegistry.from_name('mdi.yin-yang', 'grey', color_on=PLOTLYST_SECONDARY_COLOR))
        self.ui.btnReaderInfo.setIcon(
            IconRegistry.from_name('fa5s.book-reader', 'grey', color_on=PLOTLYST_SECONDARY_COLOR))
        self.ui.btnReaderQuestions.setIcon(
            IconRegistry.from_name('ei.question-sign', 'grey', color_on=PLOTLYST_SECONDARY_COLOR))
        translucent(self.ui.btnDramaticFunctions, 0.7)
        translucent(self.ui.btnReaderInfo, 0.7)
        translucent(self.ui.btnReaderQuestions, 0.7)
        self.ui.btnReaderQuestions.setHidden(True)

        if app_env.is_mac():
            incr_font(self.ui.lineTitle)
            incr_font(self.ui.textSynopsis)
        self.ui.lineTitle.setReadOnly(self.novel.is_readonly())
        self.ui.lineTitle.textEdited.connect(self._title_edited)

        self.ui.iconTitle.setIcon(IconRegistry.scene_icon('grey'))
        self.ui.iconSynopsis.setIcon(IconRegistry.from_name('mdi.text-short', 'grey'))
        self.ui.iconCharacters.setIcon(IconRegistry.character_icon('grey'))
        self.ui.iconType.setIcon(IconRegistry.from_name('fa5s.yin-yang', 'grey'))

        self._povMenu = CharacterSelectorMenu(self.novel, self.ui.wdgPov.btnAvatar)
        self._povMenu.selected.connect(self._pov_changed)
        self.ui.wdgPov.btnAvatar.setText('POV')
        self.ui.wdgPov.setFixedSize(170, 170)

        margins(self.ui.wdgCharacters, 10, 5, 10, 5)
        self.ui.wdgCharacters.setProperty('relaxed-white-bg', True)
        self.ui.wdgCharacters.setProperty('rounded', True)

        self._structureSelector = StructureBeatSelectorButton(self.novel)
        self._structureSelector.selected.connect(self._beat_selected)
        self._structureSelector.removed.connect(self._beat_removed)
        self.ui.wdgStructureParent.layout().addWidget(self._structureSelector, alignment=Qt.AlignmentFlag.AlignRight)

        self._structureSelector.setVisible(self.novel.prefs.toggled(NovelSetting.Structure))
        if not app_env.profile().get('structure', False):
            self._structureSelector.setHidden(True)

        self.ui.textNotes.setTitleVisible(False)
        self.ui.textNotes.setToolbarVisible(False)
        self.ui.textNotes.textEdit.setDocumentMargin(20)

        self.tblCharacters = QTableView()
        self.tblCharacters.setFrameShape(QFrame.Shape.NoFrame)
        self.tblCharacters.setShowGrid(False)
        self.tblCharacters.verticalHeader().setVisible(False)
        self.tblCharacters.horizontalHeader().setVisible(False)
        self.tblCharacters.horizontalHeader().setDefaultSectionSize(200)
        pointy(self.tblCharacters)

        self._characters_model = CharactersSceneAssociationTableModel(self.novel)
        self._characters_model.selection_changed.connect(self._character_changed)
        self.tblCharacters.setModel(self._characters_model)
        self.tblCharacters.clicked.connect(self._characters_model.toggleSelection)

        menu = MenuWidget(self.ui.btnStageCharacterLabel)
        menu.addWidget(self.tblCharacters)

        self.ui.treeScenes.setSettings(TreeSettings(font_incr=1))
        self.ui.treeScenes.setNovel(self.novel, readOnly=True)
        self.ui.treeScenes.sceneSelected.connect(self._scene_selected)

        self._btnPurposeType = ScenePurposeTypeButton()
        self.ui.wdgSceneType.layout().insertWidget(1, self._btnPurposeType)
        self._btnPurposeType.setVisible(app_env.profile().get('scene-purpose', False))

        self._progressEditor = SceneProgressEditor()
        self._progressEditor.progressCharged.connect(self._update_scene_type)
        retain_when_hidden(self._progressEditor)
        self.ui.wdgSceneType.layout().insertWidget(2, self._progressEditor)
        self._progressEditor.setVisible(app_env.profile().get('scene-progression', False))

        self._btnPlotSelector = push_btn(IconRegistry.storylines_icon(color='grey'), 'Storylines',
                                         tooltip='Link storylines to this scene', transparent_=True)
        self._btnPlotSelector.installEventFilter(OpacityEventFilter(self._btnPlotSelector, leaveOpacity=0.8))
        self._plotSelectorMenu = ScenePlotSelectorMenu(self.novel, self._btnPlotSelector)
        self._plotSelectorMenu.plotSelected.connect(self._storyline_selected_from_toolbar)
        flow(self.ui.wdgStorylines)
        self.ui.wdgStorylinesParent.layout().insertWidget(0, self._btnPlotSelector)
        if app_env.profile().get('storylines', False):
            self._btnPlotSelector.setVisible(True)
            self.ui.wdgStorylines.setVisible(True)
            self.ui.iconType.setVisible(True)
        else:
            self._btnPlotSelector.setHidden(True)
            self.ui.wdgStorylines.setHidden(True)
            self.ui.iconType.setHidden(True)

        self._functionsEditor = SceneFunctionsWidget(self.novel)
        self._functionsEditor.storylineLinked.connect(self._storyline_linked_from_function)
        self._functionsEditor.storylineRemoved.connect(self._storyline_removed_from_function)
        self._functionsEditor.storylineCharged.connect(self._update_storyline_progress)
        self._functionsEditor.functionAdded.connect(self._update_scene_type)
        self._functionsEditor.functionRemoved.connect(self._update_scene_type)

        self.ui.scrollAreaWidgetDramaticFunctions.layout().addWidget(self._functionsEditor)

        self._agencyEditor = SceneAgencyEditor(self.novel)
        self._agencyEditor.setUnsetCharacterSlot(self._character_not_selected_notification)
        self._agencyEditor.agencyAdded.connect(lambda: scroll_to_bottom(self.ui.scrollArea_2))
        self.ui.scrollAgency.layout().addWidget(self._agencyEditor)

        self._informationEditor = ReaderInformationEditor(self.novel)
        self._informationEditor.added.connect(self._update_scene_type)
        self._informationEditor.removed.connect(self._update_scene_type)
        self.ui.pageInfo.layout().addWidget(self._informationEditor)

        # self._curiosityEditor = ReaderCuriosityEditor(self.novel)
        # self.ui.pageQuestions.layout().addWidget(self._curiosityEditor)

        link_buttons_to_pages(self.ui.stackedWidgetFunctions,
                              [
                                  (self.ui.btnDramaticFunctions, self.ui.pageDramaticFunctions),
                                  (self.ui.btnReaderInfo, self.ui.pageInfo),
                                  (self.ui.btnReaderQuestions, self.ui.pageQuestions),
                              ])

        self.ui.btnClose.clicked.connect(self._on_close)

        if app_env.profile().get('scene-functions', False):
            self.ui.tabWidget.setCurrentWidget(self.ui.tabFunctions)
        self.ui.tabWidgetDrive.setCurrentWidget(self.ui.tabAgency)
        self.ui.tabWidget.currentChanged.connect(self._page_toggled)

        self.repo = RepositoryPersistenceManager.instance()

        self.ui.wdgPov.setVisible(self.novel.prefs.toggled(NovelSetting.Track_pov))

        self.ui.splitter.setSizes([140, 500])

        dispatcher = event_dispatchers.instance(self.novel)
        dispatcher.register(self, NovelAboutToSyncEvent, NovelSyncEvent, NovelStorylinesToggleEvent,
                            NovelStructureToggleEvent,
                            NovelPovTrackingToggleEvent, NovelScenesOrganizationToggleEvent)

        self._handle_scenes_organization()

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, NovelAboutToSyncEvent):
            if self.scene is not None:
                self._on_close()
        elif isinstance(event, NovelSyncEvent):
            self.ui.treeScenes.refresh()
        elif isinstance(event, NovelStorylinesToggleEvent):
            self.ui.wdgStorylines.setVisible(event.toggled)
            self._btnPlotSelector.setVisible(event.toggled)
        elif isinstance(event, NovelStructureToggleEvent):
            self._structureSelector.setVisible(event.toggled)
        elif isinstance(event, NovelPovTrackingToggleEvent):
            self.ui.wdgPov.setVisible(event.toggled)
        elif isinstance(event, NovelScenesOrganizationToggleEvent):
            self._handle_scenes_organization()

    def close_event(self):
        if self.scene is not None:
            self._on_close()

    def refresh(self):
        self.ui.treeScenes.refresh()

    def set_scene(self, scene: Scene):
        self.scene = scene
        self.ui.treeScenes.selectScene(self.scene)

        self._update_pov_avatar()

        # self.ui.wdgSceneStructure.setScene(self.novel, self.scene)
        # self.tag_selector.setScene(self.scene)
        self._functionsEditor.setScene(self.scene)
        # self._agencyEditor.setScene(self.scene)
        # self._curiosityEditor.setScene(self.scene)
        self._informationEditor.setScene(self.scene)
        self._progressEditor.setScene(self.scene)
        self._structureSelector.setScene(self.scene)

        self.ui.lineTitle.setText(self.scene.title)
        self.ui.textSynopsis.setText(self.scene.synopsis)

        self.notes_updated = False
        if self.ui.tabWidget.currentWidget() is self.ui.tabNotes or (
                self.scene.document and self.scene.document.loaded):
            self._update_notes()
        else:
            self.ui.textNotes.clear()

        if self.scene.purpose is None or self.scene.purpose == ScenePurposeType.Other:
            self.scene.purpose = ScenePurposeType.Story
        self._btnPurposeType.setScene(self.scene)

        self._plotSelectorMenu.setScene(self.scene)
        clear_layout(self.ui.wdgStorylines)
        for ref in self.scene.plot_values:
            self._add_plot_ref(ref)

        self._characters_model.setScene(self.scene)
        self._character_changed()

    def _page_toggled(self):
        if self.ui.tabWidget.currentWidget() is self.ui.tabNotes:
            self._update_notes()

    def _beat_selected(self, beat: StoryBeat):
        if self.scene.beat(self.novel) and self.scene.beat(self.novel) != beat:
            self.scene.remove_beat(self.novel)
        self.scene.link_beat(self.novel.active_story_structure, beat)
        self._structureSelector.setBeat(beat)
        qtanim.colorize(self._structureSelector, duration=350, strength=0.8, color=QColor(beat.icon_color))
        emit_event(self.novel, SceneStoryBeatChangedEvent(self, self.scene, beat, toggled=True))

    def _beat_removed(self):
        beat = self.scene.beat(self.novel)
        self.scene.remove_beat(self.novel)
        self._structureSelector.reset()

        emit_event(self.novel, SceneStoryBeatChangedEvent(self, self.scene, beat, toggled=False))

    def _update_notes(self):
        if self.scene and self.scene.document:
            if not self.scene.document.loaded:
                json_client.load_document(self.novel, self.scene.document)
            if not self.notes_updated:
                self.ui.textNotes.setText(self.scene.document.content, self.scene.title, title_read_only=True)
                self.notes_updated = True
        else:
            self.ui.textNotes.clear()

    def _character_not_selected_notification(self):
        qtanim.shake(self.ui.wdgPov)
        qtanim.shake(self.ui.btnStageCharacterLabel)

    def _pov_changed(self, pov: Character):
        self.scene.pov = pov

        self._agencyEditor.povChangedEvent(pov)

        self._update_pov_avatar()
        self._characters_model.update()
        self._character_changed()
        self.ui.treeScenes.refreshScene(self.scene)

    def _update_pov_avatar(self):
        if self.scene.pov:
            self.ui.wdgPov.setCharacter(self.scene.pov)
            self.ui.wdgPov.btnAvatar.setToolTip(f'<html>Point of view character: <b>{self.scene.pov.name}</b>')
        else:
            self.ui.wdgPov.reset()
            self.ui.wdgPov.btnAvatar.setToolTip('Select point of view character')

    def _storyline_selected_from_toolbar(self, storyline: Plot):
        self._functionsEditor.addPrimaryType(StoryElementType.Plot, storyline)

    def _storyline_removed_from_toolbar(self, labels: ScenePlotLabels, plotRef: ScenePlotReference):
        self._functionsEditor.storylineRemovedEvent(plotRef.plot)
        self._storyline_removed(labels)

    def _storyline_removed(self, labels: ScenePlotLabels):
        fade_out_and_gc(self.ui.wdgStorylines.layout(), labels)
        self._update_storyline_progress()

    def _storyline_linked_from_function(self, ref: ScenePlotReference):
        labels = self._add_plot_ref(ref)
        qtanim.glow(labels.icon(), loop=1, color=QColor(ref.plot.icon_color))

    def _storyline_removed_from_function(self, ref: ScenePlotReference):
        for i in range(self.ui.wdgStorylines.layout().count()):
            widget = self.ui.wdgStorylines.layout().itemAt(i).widget()
            if widget and isinstance(widget, ScenePlotLabels):
                if widget.storylineRef() is ref:
                    self._storyline_removed(widget)
                    break

    def _update_storyline_progress(self):
        self._progressEditor.refresh()
        self._update_scene_type()

    def _update_scene_type(self):
        charge = self._progressEditor.charge()
        alt_charge = self._progressEditor.altCharge()
        if charge > 0:
            if charge == abs(alt_charge):
                self.scene.outcome = SceneOutcome.TRADE_OFF
            else:
                self.scene.outcome = SceneOutcome.RESOLUTION
        else:
            self.scene.outcome = SceneOutcome.DISASTER

        self.scene.update_purpose()
        self._btnPurposeType.refresh()

    def _add_plot_ref(self, plotRef: ScenePlotReference) -> ScenePlotLabels:
        labels = ScenePlotLabels(self.scene, plotRef)
        labels.reset.connect(partial(self._storyline_removed_from_toolbar, labels, plotRef))
        self.ui.wdgStorylines.layout().addWidget(labels)
        self._btnPlotSelector.setText('')

        return labels

    def _title_edited(self, text: str):
        self.scene.title = text
        self.ui.treeScenes.refreshScene(self.scene)

    def _character_changed(self):
        self.ui.wdgCharacters.clear()

        for character in self.scene.characters:
            self.ui.wdgCharacters.addLabel(CharacterLabel(character))

        self._agencyEditor.updateAvailableCharacters()

    def _save_scene(self):
        self.scene.title = self.ui.lineTitle.text()
        self.scene.synopsis = self.ui.textSynopsis.toPlainText()

        self.scene.tag_references.clear()
        # for tag in self.tag_selector.tags():
        #     self.scene.tag_references.append(TagReference(tag.id))

        #     self.novel.scenes.append(self.scene)
        #     self.repo.insert_scene(self.novel, self.scene)
        # else:
        self.repo.update_scene(self.scene)
        emit_event(self.novel, SceneChangedEvent(self, self.scene))

        if not self.scene.document:
            self.scene.document = Document('', scene_id=self.scene.id)
            self.scene.document.loaded = True

        if self.scene.document.loaded:
            self.scene.document.content = self.ui.textNotes.textEdit.toHtml()
            self.repo.update_doc(self.novel, self.scene.document)

    def _on_close(self):
        self._save_scene()
        self.scene = None
        self.close.emit()

    @busy
    def _scene_selected(self, scene: Scene):
        self._save_scene()
        QTimer.singleShot(10, lambda: self.set_scene(scene))

    def _handle_scenes_organization(self):
        unit = 'scene' if self.novel.prefs.is_scenes_organization() else 'chapter'
        self.ui.lineTitle.setPlaceholderText(f'{unit.capitalize()} title')
        self.ui.textSynopsis.setPlaceholderText(f'Briefly summarize this {unit}')
        self.ui.textNotes.setPlaceholderText(f'Write some additional notes for this {unit}')
        self._btnPlotSelector.setToolTip(f'Link storylines to this {unit}')
        self.ui.btnStageCharacterLabel.setToolTip(f'Select which characters are active in this {unit}')
