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
import logging
import os
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, List

import pkg_resources
from atomicwrites import atomic_write
from dataclasses_json import Undefined, dataclass_json
from fbs_runtime.application_context.PyQt6 import ApplicationContext
from overrides import overrides

from plotlyst.env import app_env
from plotlyst.event.core import EventListener, Event, emit_global_event
from plotlyst.event.handler import global_event_dispatcher


class ResourceRegistry:

    def __init__(self):
        self._cork = None
        self._frame1 = None
        self._cover1 = None
        self._paper_bg1 = None
        self._vintage_pocket_banner = None
        self._divider1 = None
        self._top_frame1 = None
        self._top_frame2 = None
        self._banner = None
        self._circular_frame1 = None
        self._manuscript_docx_template = None
        self._plotlyst_icon = None
        self._confetti_anim = None
        self._profile = None
        self._public_key = None
        self._signature = None
        self._manuscript_template = None

    def set_up(self, context: Optional[ApplicationContext] = None):
        self._cork = self.__get_resource('cork.wav', context)
        self._frame1 = self.__get_resource('frame_1.png', context)
        self._cover1 = self.__get_resource('cover_1.jpg', context)
        self._paper_bg1 = self.__get_resource('paper_bg.jpg', context)
        self._divider1 = self.__get_resource('divider_1.svg', context)
        self._top_frame1 = self.__get_resource('top_frame1.svg', context)
        self._top_frame2 = self.__get_resource('top_frame2.svg', context)
        self._banner = self.__get_resource('plotlyst_banner.png', context)
        self._circular_frame1 = self.__get_resource('circular_frame1.png', context)
        self._manuscript_docx_template = self.__get_resource('manuscript-template.docx', context)
        self._plotlyst_icon = self.__get_resource('Icon.ico', context)
        self._confetti_anim = self.__get_resource('confetti.gif', context)
        self._profile = self.__get_resource('profile.cbor', context)
        self._public_key = self.__get_resource('public.pem', context)
        self._signature = self.__get_resource('profile.sig', context)
        self._manuscript_template = self.__get_resource('manuscript.tex', context)

    def __get_resource(self, name: str, context: Optional[ApplicationContext] = None):
        if context:
            resource_url = context.get_resource(name)
            logging.info(f'Resource through app context ({name}) was found: {resource_url}')
            return resource_url

        resource_url = pkg_resources.resource_filename(__name__, f'images/{name}')
        if app_env.is_windows():
            resource_url = resource_url.replace('\\', '/')

        logging.info(f'Local resource ({name}) was found: {resource_url}')

        return resource_url

    @property
    def cork(self) -> str:
        return self._cork

    @property
    def frame1(self) -> str:
        return self._frame1

    @property
    def cover1(self) -> str:
        return self._cover1

    @property
    def divider1(self) -> str:
        return self._divider1

    @property
    def top_frame1(self) -> str:
        return self._top_frame1

    @property
    def top_frame2(self) -> str:
        return self._top_frame2

    @property
    def paper_bg(self) -> str:
        return self._paper_bg1

    @property
    def banner(self) -> str:
        return self._banner

    @property
    def circular_frame1(self) -> str:
        return self._circular_frame1

    @property
    def manuscript_docx_template(self) -> str:
        return self._manuscript_docx_template

    @property
    def plotlyst_icon(self) -> str:
        return self._plotlyst_icon

    @property
    def confetti_anim(self) -> str:
        return self._confetti_anim

    @property
    def profile(self) -> str:
        return self._profile

    @property
    def public_key(self) -> str:
        return self._public_key

    @property
    def signature(self) -> str:
        return self._signature

    @property
    def manuscript_template(self) -> str:
        return self._manuscript_template


resource_registry = ResourceRegistry()


class ResourceType(str, Enum):
    NLTK_PUNKT_TOKENIZER = 'nltk_punkt_tokenizer'
    NLTK_AVERAGED_PERCEPTRON_TAGGER = 'nltk_averaged_perceptron_tagger'
    JRE_8 = 'jre_8'
    PANDOC = 'pandoc'


def is_nltk(resourceType: ResourceType) -> bool:
    return resourceType.name.startswith('NLTK')


class ResourceExtension(Enum):
    tar_gz = 'tar.gz'
    zip = 'zip'


@dataclass
class ResourceDescriptor:
    name: str
    folder: str
    web_url: str
    extension: str = 'zip'
    version: str = ''
    human_name: str = ''
    description: str = ''

    def filename(self) -> str:
        return f'{self.name}.{self.extension}'


PANDOC_VERSION: str = '3.4'

_pandoc_resource = ResourceDescriptor('pandoc', 'formatting', '', human_name='Exporter', version=PANDOC_VERSION,
                                      description='Necessary for exporting to docx format')

_punkt_nltk_resource = ResourceDescriptor('punkt', 'tokenizers',
                                          'https://github.com/nltk/nltk_data/raw/gh-pages/packages/tokenizers/punkt.zip',
                                          human_name='Punctuation tokenizer',
                                          description='Necessary for a precise sentence number calculation')
__avg_tagger_url = 'https://github.com/nltk/nltk_data/raw/gh-pages/packages/taggers/averaged_perceptron_tagger.zip'
_avg_tagger_nltk_resource = ResourceDescriptor('averaged_perceptron_tagger', 'taggers', __avg_tagger_url,
                                               human_name='Tagger', description='Necessary for adverb highlighting')

_nltk_resources: Dict[ResourceType, ResourceDescriptor] = {
    ResourceType.NLTK_PUNKT_TOKENIZER: _punkt_nltk_resource,
    ResourceType.NLTK_AVERAGED_PERCEPTRON_TAGGER: _avg_tagger_nltk_resource
}


@dataclass
class ResourceDownloadedEvent(Event):
    type: ResourceType


@dataclass
class ResourceDownloadFailedEvent(Event):
    type: ResourceType


@dataclass
class ResourceRemovedEvent(Event):
    type: ResourceType


class ResourceStatus(Enum):
    MISSING = 'missing'
    PENDING = 'pending'
    DOWNLOADED = 'downloaded'


@dataclass
class ResourceStatusChangedEvent(Event):
    type: ResourceType
    status: ResourceStatus


@dataclass
class ResourceInfo:
    resource: ResourceDescriptor
    status: ResourceStatus = ResourceStatus.MISSING
    updated: str = str(date.today())


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class ResourcesConfig:
    resources: Dict[ResourceType, ResourceInfo] = field(default_factory=dict)


class ResourceManager(EventListener):
    def __init__(self):
        self._resources_config: Optional[ResourcesConfig] = None
        self._path = None

    def init(self):
        cache = app_env.cache_dir
        self._path = Path(cache).joinpath('resources.json')
        if self._path.exists():
            with open(self._path, encoding='utf8') as json_file:
                data = json_file.read()
                self._resources_config = ResourcesConfig.from_json(data)
        else:
            self._resources_config = ResourcesConfig()

        jre = self.resource(ResourceType.JRE_8)
        if app_env.is_mac():
            os.environ['LTP_JAVA_PATH'] = os.path.join(app_env.cache_dir,
                                                       f'jre/{jre.version}-jre/Contents/Home/bin/java')
        elif app_env.is_linux():
            os.environ['LTP_JAVA_PATH'] = os.path.join(app_env.cache_dir, f'jre/{jre.version}-jre/bin/java')
        elif app_env.is_windows():
            os.environ['LTP_JAVA_PATH'] = os.path.join(app_env.cache_dir, f'jre/{jre.version}-jre/bin/java')

        os.environ.setdefault('PYPANDOC_PANDOC',
                              os.path.join(app_env.cache_dir, _pandoc_resource.folder, _pandoc_resource.name, 'pandoc'))

        global_event_dispatcher.register(self, ResourceDownloadedEvent)
        global_event_dispatcher.register(self, ResourceRemovedEvent)

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, ResourceDownloadedEvent):
            self._update_resource_status(event.type, ResourceStatus.DOWNLOADED)
        elif isinstance(event, ResourceRemovedEvent):
            self._update_resource_status(event.type, ResourceStatus.MISSING)

    def has_resource(self, resource_type: ResourceType) -> bool:
        if self._resources_config is None:
            raise ValueError('Resources were not initialized yet')

        resource_info = self._resources_config.resources.get(resource_type)
        if resource_info:
            return resource_info.status == ResourceStatus.DOWNLOADED

        return False

    def resource(self, resource_type: ResourceType) -> ResourceDescriptor:
        if resource_type.name.startswith('NLTK'):
            return _nltk_resources[resource_type]
        elif resource_type == ResourceType.PANDOC:
            return _pandoc_resource
        elif resource_type == ResourceType.JRE_8:
            version = 'jdk8u362-b09'
            if app_env.is_linux():
                extension = 'tar.gz'
                distr = 'OpenJDK8U-jre_x64_linux_hotspot_8u362b09.tar.gz'
            elif app_env.is_mac():
                extension = 'tar.gz'
                distr = 'OpenJDK8U-jre_x64_mac_hotspot_8u362b09.tar.gz'
            else:
                extension = 'zip'
                distr = 'OpenJDK8U-jre_x64_windows_hotspot_8u362b09.zip'
            url = f'https://github.com/adoptium/temurin8-binaries/releases/download/{version}/{distr}'
            return ResourceDescriptor('jre', 'jre', url, extension=extension,
                                      version=version, human_name='Java',
                                      description='Necessary for local grammar checking')

    def nltk_resource_types(self) -> List[ResourceType]:
        return [x for x in ResourceType if is_nltk(x)]

    def save(self):
        with atomic_write(self._path, overwrite=True) as f:
            f.write(self._resources_config.to_json())

    def _update_resource_status(self, type_: ResourceType, status: ResourceStatus):
        info = self.__get_resource_info(type_)
        info.status = status
        self.save()

        emit_global_event(ResourceStatusChangedEvent(self, type_, status))

    def __get_resource_info(self, resource_type: ResourceType) -> ResourceInfo:
        if resource_type not in self._resources_config.resources.keys():
            self._resources_config.resources[resource_type] = ResourceInfo(self.resource(resource_type))
        return self._resources_config.resources[resource_type]


resource_manager = ResourceManager()
