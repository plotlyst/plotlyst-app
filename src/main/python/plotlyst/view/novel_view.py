"""
Plotlyst
Copyright (C) 2021  Zsolt Kovari

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
import emoji
from PyQt5.QtCore import QPropertyAnimation
from PyQt5.QtGui import QIcon
from fbs_runtime import platform
from overrides import overrides

from src.main.python.plotlyst.core.client import json_client
from src.main.python.plotlyst.core.domain import Novel
from src.main.python.plotlyst.event.core import emit_event
from src.main.python.plotlyst.events import NovelUpdatedEvent, \
    NovelStoryStructureUpdated
from src.main.python.plotlyst.model.novel import NovelDramaticQuestionsModel
from src.main.python.plotlyst.view._view import AbstractNovelView
from src.main.python.plotlyst.view.common import ask_confirmation, emoji_font
from src.main.python.plotlyst.view.generated.novel_view_ui import Ui_NovelView
from src.main.python.plotlyst.view.icons import IconRegistry


class NovelView(AbstractNovelView):

    def __init__(self, novel: Novel):
        super().__init__(novel, [NovelUpdatedEvent])
        self.ui = Ui_NovelView()
        self.ui.setupUi(self.widget)

        self.ui.lblTitle.setText(self.novel.title)

        self._emoji_font = emoji_font(14) if platform.is_windows() else emoji_font(20)
        self.ui.lblStoryStructureEmoji.setFont(self._emoji_font)
        self.ui.lblStoryStructureEmoji.setText(emoji.emojize(':performing_arts:'))
        self.ui.lblDramaticQuestionEmoji.setFont(self._emoji_font)
        self.ui.lblDramaticQuestionEmoji.setText(emoji.emojize(':red_question_mark:'))
        for story_structure in json_client.project.story_structures:
            icon = IconRegistry.from_name(story_structure.icon,
                                          story_structure.icon_color) if story_structure.icon else QIcon('')
            self.ui.cbStoryStructure.addItem(icon, story_structure.title, story_structure)
        self.ui.cbStoryStructure.setCurrentText(self.novel.story_structure.title)
        self.ui.cbStoryStructure.currentIndexChanged.connect(self._story_structure_changed)

        self.ui.wdgStoryStructureInfo.setVisible(False)
        self._update_story_structure_info()

        self.story_lines_model = NovelDramaticQuestionsModel(self.novel)
        self.ui.wdgDramaticQuestions.setModel(self.story_lines_model)
        self.ui.wdgDramaticQuestions.setAskRemovalConfirmation(True)
        self.ui.wdgDramaticQuestions.setBgColorFieldEnabled(True)

        self.ui.btnStoryStructureInfo.setText(u'\u00BB')
        self.ui.btnStoryStructureInfo.setIcon(IconRegistry.general_info_icon())
        self.ui.btnStoryStructureInfo.clicked.connect(self._story_structure_info_clicked)

    @overrides
    def refresh(self):
        self.ui.lblTitle.setText(self.novel.title)
        self.story_lines_model.modelReset.emit()
        self.ui.cbStoryStructure.setCurrentText(self.novel.story_structure.title)

    def _update_story_structure_info(self):
        self.ui.textStoryStructureInfo.setText('''
        <h3>Info on Story structures</h3>
<p>By selecting a story structure, you will organize your scenes into <strong>Acts.</strong></p>
<p>An Act consists of <strong>Beats&nbsp;</strong>which represent your story's pivotal moments.
The scenes can be associated to such story beats.</p>''')

    def _story_structure_changed(self):
        structure = self.ui.cbStoryStructure.currentData()
        if self.novel.story_structure.id == structure.id:
            return
        beats = [x for x in self.novel.scenes if x.beat]
        if beats and not ask_confirmation(
                'Scenes are already associated to your previous story beats. Continue?'):
            self.ui.cbStoryStructure.setCurrentText(self.novel.story_structure.title)
            return
        for scene in beats:
            scene.beat = None
            self.repo.update_scene(scene)
        self.novel.story_structure = structure
        self.repo.update_novel(self.novel)
        emit_event(NovelStoryStructureUpdated(self))

    def _story_structure_info_clicked(self, checked: bool):
        if checked:
            self.ui.wdgStoryStructureInfo.setVisible(checked)
            self.animation = QPropertyAnimation(self.ui.wdgStoryStructureInfo, b'maximumHeight')
            self.animation.setStartValue(10)
            self.animation.setEndValue(200)
            self.animation.start()
        else:
            self.animation = QPropertyAnimation(self.ui.wdgStoryStructureInfo, b'maximumHeight')
            self.animation.setStartValue(200)
            self.animation.setEndValue(0)
            self.animation.start()

        self.ui.btnStoryStructureInfo.setText(u'\u02C7' if checked else u'\u00BB')
