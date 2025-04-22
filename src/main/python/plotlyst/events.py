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
from dataclasses import dataclass
from typing import Any, List
from uuid import UUID

from language_tool_python import LanguageTool

from plotlyst.core.domain import Character, NovelDescriptor, Scene, SceneStage, Task, NovelSetting, \
    StoryStructure, Novel, Plot, StoryBeat, Location, WorldBuildingEntity, SnapshotType
from plotlyst.event.core import Event


@dataclass
class CharacterChangedEvent(Event):
    character: Character


@dataclass
class CharacterSummaryChangedEvent(Event):
    character: Character


@dataclass
class CharacterBackstoryChangedEvent(Event):
    character: Character


@dataclass
class CharacterDeletedEvent(Event):
    character: Character


@dataclass
class LocationAddedEvent(Event):
    location: Location


@dataclass
class RequestMilieuDictionaryResetEvent(Event):
    pass


@dataclass
class LocationDeletedEvent(Event):
    location: Location


@dataclass
class WorldEntityAddedEvent(Event):
    entity: WorldBuildingEntity


@dataclass
class ItemLinkedEvent(Event):
    item: Any


@dataclass
class ItemUnlinkedEvent(Event):
    item: Any
    ref: UUID


@dataclass
class WorldEntityDeletedEvent(Event):
    entity: WorldBuildingEntity


@dataclass
class SceneAddedEvent(Event):
    scene: Scene


@dataclass
class SceneEditRequested(Event):
    scene: Scene


@dataclass
class SceneChangedEvent(Event):
    scene: Scene


@dataclass
class SceneStoryBeatChangedEvent(Event):
    scene: Scene
    beat: StoryBeat
    toggled: bool


@dataclass
class SceneStatusChangedEvent(Event):
    scene: Scene


@dataclass
class ChapterChangedEvent(Event):
    pass


@dataclass
class SceneDeletedEvent(Event):
    scene: Scene


@dataclass
class SceneSelectedEvent(Event):
    scene: Scene


@dataclass
class SceneSelectionClearedEvent(Event):
    pass


@dataclass
class SceneOrderChangedEvent(Event):
    pass


@dataclass
class ActiveSceneStageChanged(Event):
    stage: SceneStage


@dataclass
class AvailableSceneStagesChanged(Event):
    pass


# @dataclass
# class LocationChangedEvent(Event):
#     location: Location


@dataclass
class NovelUpdatedEvent(Event):
    novel: NovelDescriptor


@dataclass
class NovelDeletedEvent(Event):
    novel: NovelDescriptor


@dataclass
class NovelStoryStructureUpdated(Event):
    pass


@dataclass
class NovelStoryStructureActivationRequest(Event):
    novel: Novel
    structure: StoryStructure


@dataclass
class NovelAboutToSyncEvent(Event):
    novel: NovelDescriptor


@dataclass
class NovelSyncEvent(Event):
    novel: NovelDescriptor
    new_scenes: List[Scene]
    deleted_scenes: List[Scene]


@dataclass
class SelectNovelEvent(Event):
    novel: NovelDescriptor


@dataclass
class CloseNovelEvent(Event):
    novel: NovelDescriptor


@dataclass
class NovelPanelCustomizationEvent(Event):
    setting: NovelSetting
    toggled: bool


@dataclass
class NovelManuscriptToggleEvent(NovelPanelCustomizationEvent):
    pass


@dataclass
class NovelCharactersToggleEvent(NovelPanelCustomizationEvent):
    pass


@dataclass
class NovelCharacterEnneagramToggleEvent(NovelPanelCustomizationEvent):
    pass


@dataclass
class NovelCharacterMbtiToggleEvent(NovelPanelCustomizationEvent):
    pass


@dataclass
class NovelCharacterLoveStyleToggleEvent(NovelPanelCustomizationEvent):
    pass


@dataclass
class NovelCharacterWorkStyleToggleEvent(NovelPanelCustomizationEvent):
    pass


@dataclass
class NovelScenesToggleEvent(NovelPanelCustomizationEvent):
    pass


@dataclass
class NovelScenesOrganizationToggleEvent(NovelPanelCustomizationEvent):
    pass


@dataclass
class ScenesOrganizationResetEvent(Event):
    pass


@dataclass
class NovelEmotionTrackingToggleEvent(NovelPanelCustomizationEvent):
    pass


@dataclass
class NovelMotivationTrackingToggleEvent(NovelPanelCustomizationEvent):
    pass


@dataclass
class NovelConflictTrackingToggleEvent(NovelPanelCustomizationEvent):
    pass


@dataclass
class NovelPovTrackingToggleEvent(NovelPanelCustomizationEvent):
    pass


@dataclass
class NovelStructureToggleEvent(NovelPanelCustomizationEvent):
    pass


@dataclass
class NovelStorylinesToggleEvent(NovelPanelCustomizationEvent):
    pass


@dataclass
class NovelDocumentsToggleEvent(NovelPanelCustomizationEvent):
    pass


@dataclass
class NovelManagementToggleEvent(NovelPanelCustomizationEvent):
    pass


@dataclass
class NovelWorldBuildingToggleEvent(NovelPanelCustomizationEvent):
    pass


@dataclass
class StorylineCreatedEvent(Event):
    storyline: Plot


@dataclass
class StorylineRemovedEvent(Event):
    storyline: Plot


@dataclass
class StorylineChangedEvent(Event):
    storyline: Plot


@dataclass
class StorylineCharacterAssociationChanged(Event):
    storyline: Plot


@dataclass
class OpenDistractionFreeMode(Event):
    pass


@dataclass
class ExitDistractionFreeMode(Event):
    pass


@dataclass
class LanguageToolSet(Event):
    tool: LanguageTool


@dataclass
class TaskChanged(Event):
    task: Task


@dataclass
class TaskDeleted(Event):
    task: Task


@dataclass
class TaskChangedToWip(Event):
    task: Task


@dataclass
class TaskChangedFromWip(Event):
    task: Task


@dataclass
class SocialSnapshotRequested(Event):
    snapshotType: SnapshotType


@dataclass
class ShowRoadmapEvent(Event):
    pass


@dataclass
class PreviewFeatureEvent(Event):
    feature: str


@dataclass
class DailyProductivityChanged(Event):
    pass
