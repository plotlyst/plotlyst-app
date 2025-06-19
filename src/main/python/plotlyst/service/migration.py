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
from typing import Dict

from plotlyst.core.domain import Novel, Document, DocumentType, StoryElementType, SceneReaderInformation, \
    ReaderInformationType, Scene, Plot, DynamicPlotPrincipleGroupType, BackstoryEvent, Position, PlotType, \
    RelationshipDynamics, Character, TopicType, WorldBuildingEntity, WorldBuildingEntityElement, \
    WorldBuildingEntityElementType
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.view.widget.character.topic import topic_ids


def migrate_novel(novel: Novel):
    if novel.events_map is not None:
        doc = Document('Mindmap', type=DocumentType.MIND_MAP, icon='ri.mind-map', diagram=novel.events_map)
        novel.documents.append(doc)
        novel.events_map = None
        RepositoryPersistenceManager.instance().update_novel(novel)

    if novel.synopsis is not None:
        novel.synopsis.icon = 'fa5s.scroll'
        novel.synopsis.title = 'Synopsis'
        novel.documents.append(novel.synopsis)
        novel.synopsis = None
        RepositoryPersistenceManager.instance().update_novel(novel)

    for plot in novel.plots:
        migrate_plot_principles(novel, plot)
        migrate_plot_timeline(novel, plot)
        migrate_plot_relationships(novel, plot)

    for scene in novel.scenes:
        if scene.migration.migrated_functions:
            continue
        migrate_scene_functions(scene)

    character_docs_parent = None
    for character in novel.characters:
        if character.topics:
            migrate_character_topics(character)
            character.topics.clear()
            RepositoryPersistenceManager.instance().update_character(character)
        if character.document:
            if character_docs_parent is None:
                character_docs_parent = Document('Characters (migrated)', icon='fa5s.user')
            character_docs_parent.children.append(character.document)
            character.document = None
            RepositoryPersistenceManager.instance().update_character(character)

    if character_docs_parent is not None:
        novel.documents.append(character_docs_parent)
        RepositoryPersistenceManager.instance().update_novel(novel)


def migrate_plot_principles(novel: Novel, plot: Plot):
    if not plot.dynamic_principles:
        return

    for dyn_prin in plot.dynamic_principles:
        if dyn_prin.type == DynamicPlotPrincipleGroupType.SUSPECTS:
            plot.suspects = dyn_prin
            plot.has_suspects = True
        if dyn_prin.type == DynamicPlotPrincipleGroupType.CAST:
            plot.cast = dyn_prin
            plot.has_cast = True
        if dyn_prin.type == DynamicPlotPrincipleGroupType.ALLIES_AND_ENEMIES:
            plot.allies = dyn_prin
            plot.has_allies = True
        if dyn_prin.type == DynamicPlotPrincipleGroupType.ESCALATION:
            plot.escalation = dyn_prin
            plot.has_escalation = True
        if dyn_prin.type == DynamicPlotPrincipleGroupType.EVOLUTION_OF_THE_MONSTER:
            for el in dyn_prin.principles:
                plot.villain.append(BackstoryEvent('Evolution', el.text, position=Position.CENTER))
            plot.has_villain = True

    plot.dynamic_principles.clear()

    RepositoryPersistenceManager.instance().update_novel(novel)


def migrate_plot_timeline(novel: Novel, plot: Plot):
    if not plot.progression:
        return

    for event in plot.progression:
        bk_event = BackstoryEvent('', event.text, position=Position.CENTER)
        plot.timeline.append(bk_event)

    plot.has_progression = True
    plot.progression.clear()

    RepositoryPersistenceManager.instance().update_novel(novel)


def migrate_plot_relationships(novel: Novel, plot: Plot):
    if plot.plot_type != PlotType.Relation or plot.relationship is not None:
        return

    plot.relationship = RelationshipDynamics()
    if plot.character_id:
        plot.relationship.source_characters.append(plot.character_id)
    if plot.relation_character_id:
        plot.relationship.target_characters.append(plot.character_id)
        plot.relation_character_id = None

    RepositoryPersistenceManager.instance().update_novel(novel)


def migrate_scene_functions(scene: Scene):
    for function in scene.functions.primary:
        if function.type == StoryElementType.Character:
            info = SceneReaderInformation(ReaderInformationType.Character, text=function.text,
                                          character_id=function.character_id)
            scene.info.append(info)

    for function in scene.functions.secondary:
        if function.type == StoryElementType.Character:
            info = SceneReaderInformation(ReaderInformationType.Character, text=function.text,
                                          character_id=function.character_id)
            scene.info.append(info)
        if function.type == StoryElementType.Information:
            info = SceneReaderInformation(ReaderInformationType.Story, text=function.text)
            scene.info.append(info)
        if function.type == StoryElementType.Setup:
            info = SceneReaderInformation(ReaderInformationType.Story, subtype=StoryElementType.Setup,
                                          text=function.text)
            scene.info.append(info)
        if function.type == StoryElementType.Resonance:
            scene.functions.primary.append(function)
        if function.type == StoryElementType.Mystery:
            scene.functions.primary.append(function)

    scene.functions.secondary.clear()
    scene.functions.primary[:] = [x for x in scene.functions.primary if x.type != StoryElementType.Character]

    scene.migration.migrated_functions = True
    RepositoryPersistenceManager.instance().update_scene(scene)


def migrate_character_topics(character: Character):
    groupPages: Dict[TopicType, WorldBuildingEntity] = {}

    for element in character.topics:
        topic = topic_ids.get(str(element.id))
        if topic:
            if topic.type not in groupPages.keys():
                groupPages[topic.type] = WorldBuildingEntity(topic.type.display_name(), icon=topic.type.icon(),
                                                             side_visible=False)
            entity = groupPages[topic.type]
            section = WorldBuildingEntityElement(WorldBuildingEntityElementType.Section)
            section.blocks.append(
                WorldBuildingEntityElement(WorldBuildingEntityElementType.Header, title=topic.text, icon=topic.icon))
            section.blocks.append(
                WorldBuildingEntityElement(WorldBuildingEntityElementType.Text, text=element.blocks[0].text))
            entity.elements.append(section)

    character.codex.children.clear()
    for entity in groupPages.values():
        character.codex.children.append(entity)
