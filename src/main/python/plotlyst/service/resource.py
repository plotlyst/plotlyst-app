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
import os
import shutil
import tarfile
import zipfile
from typing import List, Optional

import requests
from PyQt6.QtCore import QRunnable, QThreadPool, QObject, pyqtSignal
from PyQt6.QtGui import QImage
from overrides import overrides
from pypandoc import download_pandoc

from plotlyst.env import app_env
from plotlyst.event.core import emit_global_event
from plotlyst.resources import ResourceType, resource_manager, ResourceDownloadedEvent, \
    ResourceRemovedEvent, is_nltk, PANDOC_VERSION, ResourceExtension


def download_file(url, target):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(target, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)


def remove_resource(resource_type: ResourceType):
    resource = resource_manager.resource(resource_type)
    if is_nltk(resource_type):
        resource_path = os.path.join(app_env.nltk_data, resource.folder)
    else:
        resource_path = os.path.join(app_env.cache_dir, resource.folder)

    if os.path.exists(resource_path):
        shutil.rmtree(resource_path)
    emit_global_event(ResourceRemovedEvent(resource, resource_type))


def download_resource(resource_type: ResourceType):
    if resource_manager.has_resource(resource_type):
        return

    if is_nltk(resource_type):
        runner = NltkResourceDownloadWorker(resource_type)
    elif resource_type == ResourceType.JRE_8:
        runner = JreResourceDownloadWorker()
    elif resource_type == ResourceType.PANDOC:
        runner = PandocResourceDownloadWorker()
    else:
        return
    QThreadPool.globalInstance().start(runner)


def download_nltk_resources():
    runner = NltkResourceDownloadWorker()
    QThreadPool.globalInstance().start(runner)


class NltkResourceDownloadWorker(QRunnable):

    def __init__(self, resourceType: Optional[ResourceType] = None):
        super(NltkResourceDownloadWorker, self).__init__()
        if resourceType:
            self.resource_types: List[ResourceType] = [resourceType]
        else:
            self.resource_types = resource_manager.nltk_resource_types()

    @overrides
    def run(self) -> None:
        for resource_type in self.resource_types:
            if resource_manager.has_resource(resource_type):
                continue

            resource = resource_manager.resource(resource_type)
            resource_path = os.path.join(app_env.nltk_data, resource.folder)

            os.makedirs(resource_path, exist_ok=True)

            resource_zip_path = os.path.join(resource_path, resource.filename())
            download_file(resource.web_url, resource_zip_path)
            with zipfile.ZipFile(resource_zip_path) as zip_ref:
                zip_ref.extractall(resource_path)

            emit_global_event(ResourceDownloadedEvent(self, resource_type))
            print(f'Resource {resource.name} was successfully downloaded')


class JreResourceDownloadWorker(QRunnable):

    def __init__(self):
        super().__init__()
        self._type = ResourceType.JRE_8

    @overrides
    def run(self) -> None:
        if resource_manager.has_resource(self._type):
            return
        resource = resource_manager.resource(self._type)
        resource_path = os.path.join(app_env.cache_dir, resource.folder)
        os.makedirs(resource_path, exist_ok=True)

        compressed_resource_path = os.path.join(resource_path, resource.filename())
        download_file(resource.web_url, compressed_resource_path)

        if resource.extension == ResourceExtension.tar_gz.value:
            with tarfile.open(compressed_resource_path) as tar_ref:
                tar_ref.extractall(resource_path)
        elif resource.extension == ResourceExtension.zip.value:
            with zipfile.ZipFile(compressed_resource_path, 'r') as zip_ref:
                zip_ref.extractall(resource_path)

        emit_global_event(ResourceDownloadedEvent(self, self._type))


class PandocResourceDownloadWorker(QRunnable):

    def __init__(self):
        super(PandocResourceDownloadWorker, self).__init__()
        self._type = ResourceType.PANDOC

    @overrides
    def run(self) -> None:
        if resource_manager.has_resource(self._type):
            return
        resource = resource_manager.resource(self._type)
        resource_path = os.path.join(app_env.cache_dir, resource.folder)
        os.makedirs(resource_path, exist_ok=True)

        target_path = os.path.join(resource_path, resource.name)
        os.makedirs(target_path, exist_ok=True)

        download_pandoc(version=PANDOC_VERSION, targetfolder=target_path, download_folder=resource_path)
        emit_global_event(ResourceDownloadedEvent(self, self._type))


class JsonDownloadResult(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(int, str)

    def __init__(self):
        super().__init__()

    def emit_success(self, json_result):
        self.finished.emit(json_result)

    def emit_failure(self, code: int, msg: str):
        self.failed.emit(code, msg)


class JsonDownloadWorker(QRunnable):

    def __init__(self, url: str, result: JsonDownloadResult):
        super().__init__()
        self._url = url
        self._result = result

    @overrides
    def run(self) -> None:
        try:
            response = requests.get(self._url)
            response.raise_for_status()

            self._result.emit_success(response.json())
        except requests.RequestException as e:
            status_code = getattr(e.response, 'status_code', None)
            reason = str(e) if status_code is None else e.response.reason
            self._result.emit_failure(status_code, reason)


class ImageDownloadResult(QObject):
    downloaded = pyqtSignal(QImage)
    failed = pyqtSignal(int, str)

    def emit_success(self, data):
        image = QImage.fromData(data)
        if image.isNull():
            self.failed.emit(500, 'Could not convert data to QImage')
        else:
            self.downloaded.emit(image)

    def emit_failure(self, code: int, msg: str):
        self.failed.emit(code, msg)


class ImagesDownloadWorker(QRunnable):
    def __init__(self, urls: List[str], result: ImageDownloadResult):
        super().__init__()
        self._urls = urls
        self._result = result
        self._stopped = False

    @overrides
    def run(self) -> None:
        for url in self._urls:
            if self._stopped:
                return

            try:
                with requests.Session() as session:
                    with session.get(url) as response:
                        response.raise_for_status()

                        self._result.emit_success(response.content)
            except requests.RequestException as e:
                status_code = getattr(e.response, 'status_code', None)
                reason = str(e) if status_code is None else e.response.reason
                self._result.emit_failure(status_code, reason)

    def stop(self):
        self._stopped = True
