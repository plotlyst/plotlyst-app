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
import codecs
import copy
import os
import pathlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from pathlib import Path
from typing import List, Optional, Any, Dict, Set, Union

from PyQt6.QtCore import QByteArray, QBuffer, QIODevice
from PyQt6.QtGui import QImage, QImageReader, QImageWriter
from atomicwrites import atomic_write
from dataclasses_json import dataclass_json, Undefined, config
from qthandy import busy

from plotlyst.common import recursive
from plotlyst.core.domain import Novel, Character, Scene, Chapter, SceneStage, \
    default_stages, StoryStructure, \
    default_story_structures, NovelDescriptor, TemplateValue, \
    Conflict, BackstoryEvent, Comment, Document, default_documents, DocumentType, Causality, \
    Plot, ScenePlotReference, SceneStructureAgenda, \
    three_act_structure, SceneStoryBeat, Tag, default_general_tags, TagType, \
    default_tag_types, LanguageSettings, ImportOrigin, NovelPreferences, Goal, CharacterPreferences, TagReference, \
    ScenePlotReferenceData, MiceQuotient, SceneDrive, WorldBuilding, Board, \
    default_big_five_values, CharacterPlan, ManuscriptGoals, Diagram, DiagramData, default_character_networks, \
    ScenePurposeType, StoryElement, SceneOutcome, ChapterType, SceneStructureItem, \
    DocumentProgress, ReaderQuestion, SceneReaderQuestion, ImageRef, SceneReaderInformation, \
    CharacterProfileSectionReference, CharacterMultiAttribute, default_character_profile, CharacterPersonality, \
    StrengthWeaknessAttribute, PremiseBuilder, SceneFunctions, Location, default_locations, TopicElement, StoryType, \
    DailyProductivity, NovelInfo
from plotlyst.core.template import Role, exclude_if_empty, exclude_if_black, exclude_if_false
from plotlyst.env import app_env


class ApplicationNovelVersion(IntEnum):
    R0 = 0


LATEST_VERSION = [x for x in ApplicationNovelVersion][-1]


class SqlClient:

    def novels(self) -> List[NovelDescriptor]:
        return json_client.novels()

    def has_novel(self, id: uuid.UUID) -> bool:
        return json_client.has_novel(id)

    def insert_novel(self, novel: Novel):
        json_client.insert_novel(novel)

    def delete_novel(self, novel: Novel):
        json_client.delete_novel(novel)

    def update_project_novel(self, novel: Novel):
        json_client.update_project_novel(novel)

    def update_novel(self, novel: Novel):
        json_client.update_novel(novel)

    def fetch_novel(self, id: uuid.UUID) -> Novel:
        return json_client.fetch_novel(id)

    def insert_character(self, novel: Novel, character: Character):
        json_client.insert_character(novel, character)

    def update_character(self, character: Character, update_avatar: bool = False):
        json_client.update_character(character, update_avatar)

    def delete_character(self, novel: Novel, character: Character):
        json_client.delete_character(novel, character)

    def update_scene(self, scene: Scene):
        json_client.update_scene(scene)

    def insert_scene(self, novel: Novel, scene: Scene):
        json_client.insert_scene(novel, scene)

    def delete_scene(self, novel: Novel, scene: Scene):
        json_client.delete_scene(novel, scene)


client = SqlClient()


def load_image(path: pathlib.Path):
    if not os.path.exists(path):
        return None
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    image: QImage = reader.read()
    if image is None:
        return None
    array = QByteArray()
    buffer = QBuffer(array)
    buffer.open(QIODevice.WriteOnly)
    image.save(buffer, 'PNG')
    return array


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class CharacterInfo:
    name: str
    id: uuid.UUID
    gender: str = ''
    role: Optional[Role] = None
    age: Optional[int] = None
    age_infinite: bool = field(default=False, metadata=config(exclude=exclude_if_false))
    occupation: Optional[str] = None
    avatar_id: Optional[uuid.UUID] = None
    template_values: List[TemplateValue] = field(default_factory=list)
    disabled_template_headers: Dict[str, bool] = field(default_factory=dict)
    backstory: List[BackstoryEvent] = field(default_factory=list)
    plans: List[CharacterPlan] = field(default_factory=list)
    document: Optional[Document] = None
    journals: List[Document] = field(default_factory=list)
    prefs: CharacterPreferences = field(default_factory=CharacterPreferences)
    topics: List[TopicElement] = field(default_factory=list)
    big_five: Dict[str, List[int]] = field(default_factory=default_big_five_values)
    profile: List[CharacterProfileSectionReference] = field(default_factory=default_character_profile)
    summary: str = field(default='', metadata=config(exclude=exclude_if_empty))
    faculties: Dict[str, int] = field(default_factory=dict, metadata=config(exclude=exclude_if_empty))
    traits: List[str] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    values: List[str] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    gmc: List[CharacterMultiAttribute] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    lack: List[CharacterMultiAttribute] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    baggage: List[CharacterMultiAttribute] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    flaws: List[CharacterMultiAttribute] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    strengths: List[StrengthWeaknessAttribute] = field(default_factory=list, metadata=config(exclude=exclude_if_empty))
    personality: CharacterPersonality = field(default_factory=CharacterPersonality)
    alias: str = field(default='', metadata=config(exclude=exclude_if_empty))
    origin_id: Optional[uuid.UUID] = field(default=None, metadata=config(exclude=exclude_if_empty))


@dataclass
class CharacterArcInfo:
    arc: int
    character: uuid.UUID


@dataclass
class ScenePlotReferenceInfo:
    plot_id: uuid.UUID
    data: ScenePlotReferenceData = ScenePlotReferenceData()


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class SceneInfo:
    title: str
    id: uuid.UUID
    synopsis: str = ''
    pov: Optional[uuid.UUID] = None
    characters: List[uuid.UUID] = field(default_factory=list)
    agendas: List[SceneStructureAgenda] = field(default_factory=list)
    wip: bool = False
    plots: List[ScenePlotReferenceInfo] = field(default_factory=list)
    day: int = 1
    chapter: Optional[uuid.UUID] = None
    stage: Optional[uuid.UUID] = None
    beats: List[SceneStoryBeat] = field(default_factory=list)
    comments: List[Comment] = field(default_factory=list)
    tag_references: List[TagReference] = field(default_factory=list)
    document: Optional[Document] = None
    manuscript: Optional[Document] = None
    drive: SceneDrive = field(default_factory=SceneDrive)
    purpose: Optional[ScenePurposeType] = None
    outcome: Optional[SceneOutcome] = None
    story_elements: List[StoryElement] = field(default_factory=list)
    structure: List[SceneStructureItem] = field(default_factory=list)
    questions: List[SceneReaderQuestion] = field(default_factory=list)
    info: List[SceneReaderInformation] = field(default_factory=list)
    progress: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    plot_pos_progress: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    plot_neg_progress: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    functions: SceneFunctions = field(default_factory=SceneFunctions)


@dataclass
class ChapterInfo:
    title: str
    id: uuid.UUID
    type: Optional[ChapterType] = field(default=None, metadata=config(exclude=exclude_if_empty))


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class NovelInfo:
    id: uuid.UUID
    story_structures: List[StoryStructure] = field(default_factory=list)
    scenes: List[uuid.UUID] = field(default_factory=list)
    characters: List[uuid.UUID] = field(default_factory=list)
    plots: List[Plot] = field(default_factory=list)
    chapters: List[ChapterInfo] = field(default_factory=list)
    custom_chapters: int = field(default=0, metadata=config(exclude=exclude_if_empty))
    stages: List[SceneStage] = field(default_factory=default_stages)
    conflicts: List[Conflict] = field(default_factory=list)
    goals: List[Goal] = field(default_factory=list)
    tags: List[Tag] = field(default_factory=default_general_tags)
    tag_types: List[TagType] = field(default_factory=default_tag_types, metadata=config(exclude=exclude_if_empty))
    documents: List[Document] = field(default_factory=default_documents)
    premise: str = ''
    synopsis: Optional['Document'] = None
    version: ApplicationNovelVersion = ApplicationNovelVersion.R0
    prefs: NovelPreferences = field(default_factory=NovelPreferences)
    world: WorldBuilding = field(default_factory=WorldBuilding)
    locations: List[Location] = field(default_factory=default_locations)
    board: Board = field(default_factory=Board)
    manuscript_goals: ManuscriptGoals = field(default_factory=ManuscriptGoals)
    events_map: Optional[Diagram] = field(default=None, metadata=config(exclude=exclude_if_empty))
    character_networks: List[Diagram] = field(default_factory=default_character_networks)
    manuscript_progress: Dict[str, DocumentProgress] = field(default_factory=dict,
                                                             metadata=config(exclude=exclude_if_empty))
    questions: Dict[str, ReaderQuestion] = field(default_factory=dict)
    productivity: DailyProductivity = field(default_factory=DailyProductivity)
    descriptors: NovelInfo = field(default_factory=NovelInfo)


@dataclass
class ProjectNovelInfo:
    title: str
    id: uuid.UUID
    lang_settings: LanguageSettings = LanguageSettings()
    import_origin: Optional[ImportOrigin] = None
    subtitle: str = field(default='', metadata=config(exclude=exclude_if_empty))
    icon: str = field(default='', metadata=config(exclude=exclude_if_empty))
    icon_color: str = field(default='black', metadata=config(exclude=exclude_if_black))
    creation_date: Optional[datetime] = None
    story_type: StoryType = field(default=StoryType.Novel)
    short_synopsis: str = field(default='', metadata=config(exclude=exclude_if_empty))
    parent: Optional[uuid.UUID] = field(default=None, metadata=config(exclude=exclude_if_empty))
    sequence: int = field(default=0, metadata=config(exclude=exclude_if_empty))


def _default_story_structures():
    return default_story_structures


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Project:
    novels: List[ProjectNovelInfo] = field(default_factory=list)


class JsonClient:

    def __init__(self):
        self.project: Optional[Project] = None
        self._workspace = ''
        self.project_file_path = ''
        self.root_path: Optional[pathlib.Path] = None
        self.novels_dir: Optional[pathlib.Path] = None
        self._old_scenes_dir: Optional[pathlib.Path] = None
        self._old_characters_dir: Optional[pathlib.Path] = None
        self.project_images_dir: Optional[pathlib.Path] = None
        self._old_docs_dir: Optional[pathlib.Path] = None

    def init(self, workspace: str):
        self.project_file_path = os.path.join(workspace, 'project.plotlyst')

        if not os.path.exists(self.project_file_path) or os.path.getsize(self.project_file_path) == 0:
            self.project = Project()
            self._persist_project()
        else:
            with open(self.project_file_path) as json_file:
                data = json_file.read()
                self.project = Project.from_json(data)
            self._persist_project()

        self._workspace = workspace
        self.root_path = pathlib.Path(self._workspace)
        self.novels_dir = self.root_path.joinpath('novels')
        self.project_images_dir = self.root_path.joinpath('images')

        if not os.path.exists(str(self.novels_dir)):
            os.mkdir(self.novels_dir)
        if not os.path.exists(str(self.project_images_dir)):
            os.mkdir(self.project_images_dir)

    def novels(self) -> List[NovelDescriptor]:
        return [NovelDescriptor(title=x.title, id=x.id, import_origin=x.import_origin, lang_settings=x.lang_settings,
                                subtitle=x.subtitle, icon=x.icon, icon_color=x.icon_color,
                                creation_date=x.creation_date, story_type=x.story_type, short_synopsis=x.short_synopsis,
                                parent=x.parent,
                                sequence=x.sequence)
                for x in self.project.novels]

    def has_novel(self, id: uuid.UUID):
        for novel in self.project.novels:
            if novel.id == id:
                return True
        return False

    def characters_dir(self, novel: Optional[Union[Novel, NovelInfo]] = None) -> Path:
        if novel is None:
            novel = app_env.novel
        characters_dir_ = self.novels_dir.joinpath(str(novel.id)).joinpath('characters')
        if not characters_dir_.exists():
            characters_dir_.mkdir()
        return characters_dir_

    def scenes_dir(self, novel: Optional[Union[Novel, NovelInfo]] = None) -> Path:
        if novel is None:
            novel = app_env.novel
        scenes_dir_ = self.novels_dir.joinpath(str(novel.id)).joinpath('scenes')
        if not scenes_dir_.exists():
            scenes_dir_.mkdir()
        return scenes_dir_

    def diagrams_dir(self, novel: Novel) -> Path:
        diagrams_dir_ = self.novels_dir.joinpath(str(novel.id)).joinpath('diagrams')
        if not diagrams_dir_.exists():
            diagrams_dir_.mkdir()
        return diagrams_dir_

    def images_dir(self, novel: Novel) -> Path:
        images_dir_ = self.novels_dir.joinpath(str(novel.id)).joinpath('images')
        if not images_dir_.exists():
            images_dir_.mkdir()
        return images_dir_

    def docs_dir(self, novel: Novel) -> Path:
        docs_dir_ = self.novels_dir.joinpath(str(novel.id)).joinpath('docs')
        if not docs_dir_.exists():
            docs_dir_.mkdir()
        return docs_dir_

    def update_project_novel(self, novel: Novel):
        novel_info = self._find_project_novel_info_or_fail(novel.id)
        novel_info.title = novel.title
        novel_info.lang_settings = novel.lang_settings
        novel_info.import_origin = novel.import_origin
        novel_info.subtitle = novel.subtitle
        novel_info.icon = novel.icon
        novel_info.icon_color = novel.icon_color
        novel_info.story_type = novel.story_type
        novel_info.short_synopsis = novel.short_synopsis
        novel_info.parent = novel.parent
        novel_info.sequence = novel.sequence
        self._persist_project()

    def insert_novel(self, novel: Novel):
        project_novel_info = ProjectNovelInfo(title=novel.title, id=novel.id, lang_settings=novel.lang_settings,
                                              import_origin=novel.import_origin,
                                              subtitle=novel.subtitle, icon=novel.icon, icon_color=novel.icon_color,
                                              creation_date=novel.creation_date, story_type=novel.story_type,
                                              short_synopsis=novel.short_synopsis, parent=novel.parent,
                                              sequence=novel.sequence)
        self.project.novels.append(project_novel_info)
        self._persist_project()
        self._persist_novel(novel)
        novel_dir = self.novels_dir.joinpath(str(project_novel_info.id))
        if not novel_dir.exists():
            novel_dir.mkdir()

    def delete_novel(self, novel: Novel):
        novel_info = self._find_project_novel_info_or_fail(novel.id)
        self.project.novels.remove(novel_info)
        self._persist_project()
        self.__delete_info(self.novels_dir, novel_info.id)

    def update_novel(self, novel: Novel):
        self._persist_novel(novel)

    def update_world(self, novel: Novel):
        self._persist_world(novel.id, novel.world)

    def insert_scene(self, novel: Novel, scene: Scene):
        self._persist_scene(scene, novel)
        self._persist_novel(novel)

    def update_scene(self, scene: Scene):
        self._persist_scene(scene)

    def delete_scene(self, novel: Novel, scene: Scene):
        self._persist_novel(novel)
        self.__delete_info(self.scenes_dir(novel), scene.id)
        if scene.document:
            self.delete_document(novel, scene.document)

    def insert_character(self, novel: Novel, character: Character):
        self.update_character(character, True, novel)
        self._persist_novel(novel)

    def update_character(self, character: Character, update_avatar: bool = False, novel: Optional[Novel] = None):
        avatar_id: Optional[uuid.UUID] = None

        path = self.characters_dir(novel).joinpath(self.__json_file(character.id))
        if os.path.exists(path):
            with open(path) as json_file:
                data = json_file.read()
                info: CharacterInfo = CharacterInfo.from_json(data)
                avatar_id = info.avatar_id

        if update_avatar:
            if avatar_id:
                self.__delete_image(avatar_id)
                avatar_id = None
            if character.avatar:
                avatar_id = uuid.uuid4()
                image = QImage.fromData(character.avatar)
                image.save(str(self.project_images_dir.joinpath(self.__image_file(avatar_id))))

        self._persist_character(character, avatar_id, novel)

    def delete_character(self, novel: Novel, character: Character):
        self._persist_novel(novel)
        self.__delete_info(self.characters_dir(novel), character.id)
        if character.document:
            self.delete_document(novel, character.document)

    def _find_project_novel_info_or_fail(self, id: uuid.UUID) -> ProjectNovelInfo:
        for info in self.project.novels:
            if info.id == id:
                return info
        raise ValueError(f'Could not find novel with id {id}')

    def load_document(self, novel: Novel, document: Document):
        if document.loaded:
            return

        if document.type in [DocumentType.DOCUMENT, DocumentType.STORY_STRUCTURE]:
            content = self.__load_doc(novel, document.id)
            document.content = content
        else:
            data_str: str = self.__load_doc_data(novel, document.data_id)
            if document.type in [DocumentType.CAUSE_AND_EFFECT, DocumentType.REVERSED_CAUSE_AND_EFFECT]:
                document.data = Causality.from_json(data_str)
            elif document.type == DocumentType.MICE:
                document.data = MiceQuotient.from_json(data_str)
            elif document.type == DocumentType.PREMISE:
                document.data = PremiseBuilder.from_json(data_str)
        document.loaded = True

    @busy
    def load_manuscript(self, novel: Novel):
        for scene in novel.scenes:
            if scene.manuscript and not scene.manuscript.loaded:
                self.load_document(novel, scene.manuscript)

    def load_diagram(self, novel: Novel, diagram: Diagram):
        if diagram.loaded:
            return

        json_str = self.__load_diagram(novel, diagram.id)
        if json_str:
            diagram.data = DiagramData.from_json(json_str)
        else:
            diagram.data = DiagramData()
        diagram.loaded = True

    def load_image(self, novel: Novel, ref: ImageRef) -> Optional[QImage]:
        filename = f'{ref.id}.{ref.extension}'
        path = self.images_dir(novel).joinpath(filename)
        if not path.exists():
            return None
        image = QImage()
        image.load(str(path))

        return image

    def save_image(self, novel: Novel, ref: ImageRef, image: QImage):
        file_path = self.images_dir(novel).joinpath(f'{ref.id}.{ref.extension}')
        writer = QImageWriter(str(file_path))
        writer.write(image)

    def update_document(self, novel: Novel, document: Document):
        self.__persist_doc(novel, document)

    def delete_document(self, novel: Novel, document: Document):
        self.__delete_doc(novel, document)

    def update_diagram(self, novel: Novel, diagram: Diagram):
        self._persist_diagram(novel, diagram)

    def fetch_novel(self, id: uuid.UUID) -> Novel:
        project_novel_info: ProjectNovelInfo = self._find_project_novel_info_or_fail(id)
        novel_info = self._read_novel_info(project_novel_info.id)
        self.__persist_info(self.novels_dir, novel_info)

        plot_ids = {}
        for plot in novel_info.plots:
            plot_ids[str(plot.id)] = plot
        chapters = []
        chapters_ids = {}
        for chapter_info in novel_info.chapters:
            chapter = Chapter(title=chapter_info.title, id=chapter_info.id, type=chapter_info.type)
            chapters.append(chapter)
            chapters_ids[str(chapter.id)] = chapter

        characters = []
        for char_id in novel_info.characters:
            path = self.characters_dir(novel_info).joinpath(
                self.__json_file(char_id))
            if not os.path.exists(path):
                continue
            with open(path, encoding='utf8') as json_file:
                data = json_file.read()
                info: CharacterInfo = CharacterInfo.from_json(data)
                character = Character(name=info.name, id=info.id, gender=info.gender, role=info.role, age=info.age,
                                      age_infinite=info.age_infinite,
                                      occupation=info.occupation,
                                      template_values=info.template_values,
                                      disabled_template_headers=info.disabled_template_headers,
                                      backstory=info.backstory, plans=info.plans,
                                      document=info.document,
                                      journals=info.journals, prefs=info.prefs, topics=info.topics,
                                      big_five=info.big_five,
                                      profile=info.profile,
                                      summary=info.summary,
                                      faculties=info.faculties,
                                      traits=info.traits,
                                      values=info.values,
                                      gmc=info.gmc,
                                      lack=info.lack,
                                      baggage=info.baggage,
                                      flaws=info.flaws,
                                      strengths=info.strengths,
                                      personality=info.personality, alias=info.alias,
                                      origin_id=info.origin_id
                                      )
                if info.avatar_id:
                    bytes = self._load_image(self.__image_file(info.avatar_id))
                    if bytes:
                        character.avatar = bytes
                characters.append(character)
        characters_ids: Dict[str, Character] = {}
        for char in characters:
            characters_ids[str(char.id)] = char

        conflicts = []
        conflict_ids = {}
        for conflict in novel_info.conflicts:
            if str(conflict.character_id) not in characters_ids.keys():
                continue
            if conflict.conflicting_character_id and str(
                    conflict.conflicting_character_id) not in characters_ids.keys():
                continue
            conflicts.append(conflict)
            conflict_ids[str(conflict.id)] = conflict

        if not novel_info.story_structures:
            novel_info.story_structures = [copy.deepcopy(three_act_structure)]

        if all([not x.active for x in novel_info.story_structures]):
            novel_info.story_structures[0].active = True

        scenes: List[Scene] = []
        for scene_id in novel_info.scenes:
            path = self.scenes_dir(novel_info).joinpath(
                self.__json_file(scene_id))
            if not os.path.exists(path):
                continue
            with open(path, encoding='utf8') as json_file:
                data = json_file.read()
                info: SceneInfo = SceneInfo.from_json(data)
                scene_plots = []
                for plot_value in info.plots:
                    if str(plot_value.plot_id) in plot_ids.keys():
                        scene_plots.append(ScenePlotReference(plot_ids[str(plot_value.plot_id)], plot_value.data))
                if info.pov and str(info.pov) in characters_ids.keys():
                    pov = characters_ids[str(info.pov)]
                else:
                    pov = None

                scene_characters = []
                for char_id in info.characters:
                    if str(char_id) in characters_ids.keys():
                        scene_characters.append(characters_ids[str(char_id)])

                if info.chapter and str(info.chapter) in chapters_ids.keys():
                    chapter = chapters_ids[str(info.chapter)]
                else:
                    chapter = None

                stage = None
                if info.stage:
                    match = [x for x in novel_info.stages if x.id == info.stage]
                    if match:
                        stage = match[0]

                scene = Scene(title=info.title, id=info.id, synopsis=info.synopsis,
                              wip=info.wip, day=info.day,
                              plot_values=scene_plots, pov=pov, characters=scene_characters, agendas=info.agendas,
                              chapter=chapter, stage=stage, beats=info.beats,
                              comments=info.comments, tag_references=info.tag_references,
                              document=info.document, manuscript=info.manuscript, drive=info.drive,
                              purpose=info.purpose, outcome=info.outcome, story_elements=info.story_elements,
                              structure=info.structure, questions=info.questions, info=info.info,
                              progress=info.progress, plot_pos_progress=info.plot_pos_progress,
                              plot_neg_progress=info.plot_neg_progress, functions=info.functions)
                scenes.append(scene)

        tag_types = novel_info.tag_types
        tags = novel_info.tags

        tags_dict: Dict[TagType, List[Tag]] = {}
        for tt in tag_types:
            tags_dict[tt] = []
            for t in tags:
                if t.tag_type == tt.text:
                    tags_dict[tt].append(t)
        for t in default_general_tags():
            if t not in tags_dict[tag_types[0]]:
                tags_dict[tag_types[0]].append(t)

        goal_ids = set()
        for char in characters:
            self.__collect_goal_ids(goal_ids, char.plans)

        novel = Novel(title=project_novel_info.title, id=novel_info.id, lang_settings=project_novel_info.lang_settings,
                      import_origin=project_novel_info.import_origin,
                      subtitle=project_novel_info.subtitle, icon=project_novel_info.icon,
                      icon_color=project_novel_info.icon_color, creation_date=project_novel_info.creation_date,
                      story_type=project_novel_info.story_type, short_synopsis=project_novel_info.short_synopsis,
                      parent=project_novel_info.parent,
                      sequence=project_novel_info.sequence,
                      plots=novel_info.plots, characters=characters,
                      scenes=scenes, chapters=chapters, custom_chapters=novel_info.custom_chapters,
                      stages=novel_info.stages,
                      story_structures=novel_info.story_structures,
                      conflicts=conflicts, goals=[x for x in novel_info.goals if str(x.id) in goal_ids], tags=tags_dict,
                      documents=novel_info.documents, premise=novel_info.premise, synopsis=novel_info.synopsis,
                      prefs=novel_info.prefs, locations=novel_info.locations,
                      manuscript_goals=novel_info.manuscript_goals,
                      events_map=novel_info.events_map,
                      character_networks=novel_info.character_networks,
                      manuscript_progress=novel_info.manuscript_progress, questions=novel_info.questions,
                      productivity=novel_info.productivity, descriptors=novel_info.descriptors)

        world_path = self.novels_dir.joinpath(str(novel_info.id)).joinpath('world.json')
        if os.path.exists(world_path):
            with open(world_path, encoding='utf8') as json_file:
                novel.world = WorldBuilding.from_json(json_file.read())
        board_path = self.novels_dir.joinpath(str(novel_info.id)).joinpath('board.json')
        if os.path.exists(board_path):
            with open(board_path, encoding='utf8') as json_file:
                novel.board = Board.from_json(json_file.read())

        return novel

    def _read_novel_info(self, id: uuid.UUID) -> NovelInfo:
        path = self.novels_dir.joinpath(self.__json_file(id))
        if not os.path.exists(path):
            raise IOError(f'Could not find novel with id {id}')
        with open(path) as json_file:
            data = json_file.read()
            return NovelInfo.from_json(data)

    def _persist_project(self):
        with atomic_write(self.project_file_path, overwrite=True) as f:
            f.write(self.project.to_json())

    def _persist_novel(self, novel: Novel):
        novel_info = NovelInfo(id=novel.id, scenes=[x.id for x in novel.scenes],
                               plots=novel.plots,
                               characters=[x.id for x in novel.characters],
                               chapters=[ChapterInfo(title=x.title, id=x.id, type=x.type) for x in novel.chapters],
                               custom_chapters=novel.custom_chapters,
                               stages=novel.stages, story_structures=novel.story_structures,
                               conflicts=novel.conflicts,
                               goals=novel.goals,
                               tags=[item for sublist in novel.tags.values() for item in sublist if not item.builtin],
                               tag_types=list(novel.tags.keys()),
                               documents=novel.documents,
                               premise=novel.premise, synopsis=novel.synopsis,
                               version=LATEST_VERSION, prefs=novel.prefs, locations=novel.locations,
                               manuscript_goals=novel.manuscript_goals,
                               events_map=novel.events_map, character_networks=novel.character_networks,
                               manuscript_progress=novel.manuscript_progress, questions=novel.questions,
                               productivity=novel.productivity, descriptors=novel.descriptors)

        self.__persist_info(self.novels_dir, novel_info)
        # self._persist_world(novel.id, novel.world)
        self._persist_board(novel.id, novel.board)

    def _persist_world(self, novel_id: uuid.UUID, world: WorldBuilding):
        novel_dir = self.novels_dir.joinpath(str(novel_id))
        if not novel_dir.exists():
            novel_dir.mkdir()

        self.__persist_info_by_name(novel_dir, world, 'world')

    def _persist_board(self, novel_id: uuid.UUID, board: Board):
        novel_dir = self.novels_dir.joinpath(str(novel_id))
        if not novel_dir.exists():
            novel_dir.mkdir()

        self.__persist_info_by_name(novel_dir, board, 'board')

    def _persist_character(self, char: Character, avatar_id: Optional[uuid.UUID] = None, novel: Optional[Novel] = None):
        char_info = CharacterInfo(id=char.id, name=char.name, gender=char.gender, role=char.role, age=char.age,
                                  age_infinite=char.age_infinite,
                                  occupation=char.occupation,
                                  template_values=char.template_values,
                                  disabled_template_headers=char.disabled_template_headers,
                                  avatar_id=avatar_id,
                                  backstory=char.backstory, plans=char.plans, document=char.document,
                                  journals=char.journals, prefs=char.prefs, topics=char.topics, big_five=char.big_five,
                                  profile=char.profile,
                                  summary=char.summary,
                                  faculties=char.faculties,
                                  traits=char.traits,
                                  values=char.values,
                                  gmc=char.gmc,
                                  lack=char.lack,
                                  baggage=char.baggage,
                                  flaws=char.flaws,
                                  strengths=char.strengths,
                                  personality=char.personality,
                                  alias=char.alias,
                                  origin_id=char.origin_id
                                  )
        self.__persist_info(self.characters_dir(novel), char_info)

    def _persist_scene(self, scene: Scene, novel: Optional[Novel] = None):
        plots = [ScenePlotReferenceInfo(x.plot.id, x.data) for x in scene.plot_values]
        characters = [x.id for x in scene.characters]
        info = SceneInfo(id=scene.id, title=scene.title, synopsis=scene.synopsis,
                         wip=scene.wip, day=scene.day,
                         pov=self.__id_or_none(scene.pov), plots=plots, characters=characters,
                         agendas=scene.agendas,
                         chapter=self.__id_or_none(scene.chapter),
                         stage=self.__id_or_none(scene.stage),
                         beats=scene.beats, comments=scene.comments,
                         tag_references=scene.tag_references, document=scene.document, manuscript=scene.manuscript,
                         drive=scene.drive, purpose=scene.purpose, outcome=scene.outcome,
                         story_elements=scene.story_elements,
                         structure=scene.structure, questions=scene.questions, info=scene.info, progress=scene.progress,
                         plot_pos_progress=scene.plot_pos_progress, plot_neg_progress=scene.plot_neg_progress,
                         functions=scene.functions)
        self.__persist_info(self.scenes_dir(novel), info)

    def _persist_diagram(self, novel: Novel, diagram: Diagram):
        diagrams_dir = self.diagrams_dir(novel)
        if not os.path.exists(str(diagrams_dir)):
            os.mkdir(diagrams_dir)
        self.__persist_json_by_id(diagrams_dir, diagram.data.to_json(), diagram.id)

    @staticmethod
    def __id_or_none(item):
        return item.id if item else None

    def __collect_goal_ids(self, goal_ids: Set[str], plans: List[CharacterPlan]):
        for plan in plans:
            for goal in plan.goals:
                goal_ids.add(str(goal.goal_id))
                for child in goal.children:
                    goal_ids.add(str(child.goal_id))

    def __json_file(self, uuid: uuid.UUID) -> str:
        return f'{uuid}.json'

    def __image_file(self, uuid: uuid.UUID) -> str:
        return f'{uuid}.jpeg'

    def __doc_file(self, uuid: uuid.UUID) -> str:
        return f'{uuid}.html'

    def _load_image(self, filename: str) -> Optional[Any]:
        path = self.project_images_dir.joinpath(filename)
        return load_image(path)

    def __load_doc(self, novel: Novel, doc_uuid: uuid.UUID) -> str:
        novel_doc_dir = self.docs_dir(novel).joinpath(str(novel.id))
        path = novel_doc_dir.joinpath(self.__doc_file(doc_uuid))
        if not os.path.exists(path):
            return ''
        with codecs.open(str(path), "r", "utf-8") as doc_file:
            return doc_file.read()

    def __load_doc_data(self, novel: Novel, data_uuid: uuid.UUID) -> str:
        if not data_uuid:
            return ''
        novel_doc_dir = self.docs_dir(novel).joinpath(str(novel.id))
        path = novel_doc_dir.joinpath(self.__json_file(data_uuid))
        if not os.path.exists(path):
            return ''
        with open(path, encoding='utf-8') as json_file:
            return json_file.read()

    def __load_diagram(self, novel: Novel, diagram_uuid: uuid.UUID) -> str:
        diagrams_dir = self.diagrams_dir(novel)
        path = diagrams_dir.joinpath(self.__json_file(diagram_uuid))
        if not os.path.exists(path):
            return ''
        with open(path, encoding='utf-8') as json_file:
            return json_file.read()

    def __persist_doc(self, novel: Novel, doc: Document):
        novel_doc_dir = self.docs_dir(novel).joinpath(str(novel.id))
        if not os.path.exists(str(novel_doc_dir)):
            os.mkdir(novel_doc_dir)

        if doc.type in [DocumentType.DOCUMENT, DocumentType.STORY_STRUCTURE]:
            doc_file_path = novel_doc_dir.joinpath(self.__doc_file(doc.id))
            with atomic_write(doc_file_path, encoding='utf-8', overwrite=True) as f:
                f.write(doc.content)
        elif doc.type in [DocumentType.REVERSED_CAUSE_AND_EFFECT, DocumentType.CAUSE_AND_EFFECT, DocumentType.MICE,
                          DocumentType.PREMISE]:
            self.__persist_json_by_id(novel_doc_dir, doc.data.to_json(), doc.data_id)

    def __persist_info(self, dir, info: Any):
        self.__persist_json_by_id(dir, info.to_json(), info.id)

    def __persist_info_by_name(self, dir, info: Any, name: str):
        self.__persist_json_by_name(dir, info.to_json(), name)

    def __persist_json_by_name(self, dir, json_data: str, name: str):
        with atomic_write(dir.joinpath(f'{name}.json'), encoding='utf-8', overwrite=True) as f:
            f.write(json_data)

    def __persist_json_by_id(self, dir, json_data: str, id: uuid.UUID):
        with atomic_write(dir.joinpath(self.__json_file(id)), encoding='utf-8', overwrite=True) as f:
            f.write(json_data)

    def __delete_info(self, dir, id: uuid.UUID):
        path = dir.joinpath(self.__json_file(id))
        if os.path.exists(path):
            os.remove(path)

    def __delete_image(self, id: uuid.UUID):
        path = self.project_images_dir.joinpath(self.__image_file(id))
        if os.path.exists(path):
            os.remove(path)

    def __delete_doc(self, novel: Novel, doc: Document):
        novel_doc_dir = self.docs_dir(novel).joinpath(str(novel.id))
        if not os.path.exists(str(novel_doc_dir)):
            return
        doc_file_path = novel_doc_dir.joinpath(self.__doc_file(doc.id))
        if os.path.exists(doc_file_path):
            os.remove(doc_file_path)

        if doc.diagram is not None:
            self.__delete_info(self.diagrams_dir(novel), doc.diagram.id)

        recursive(doc, lambda parent: parent.children, lambda p, child: self.__delete_doc(novel, child))


json_client = JsonClient()
