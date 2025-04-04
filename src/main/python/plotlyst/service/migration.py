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
from plotlyst.core.domain import Novel, Document, DocumentType, StoryElementType, SceneReaderInformation, \
    ReaderInformationType, Scene
from plotlyst.service.persistence import RepositoryPersistenceManager


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

    for scene in novel.scenes:
        if scene.migration.migrated_functions:
            continue
        migrate_scene_functions(scene)


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
