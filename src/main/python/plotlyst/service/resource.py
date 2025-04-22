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
import shutil
import tarfile
import zipfile
from typing import List, Optional, Dict

import requests
from PyQt6.QtCore import QRunnable, QThreadPool, QObject, pyqtSignal, Qt
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QDialog, QLabel, QToolButton, QPushButton, QWidget, QGridLayout
from overrides import overrides
from pypandoc import download_pandoc
from qthandy import italic, vspacer, incr_font, bold, decr_font, transparent, decr_icon, pointy, ask_confirmation, grid, \
    underline, line, spacer, vbox
from qthandy.filter import OpacityEventFilter
from requests import ConnectionError

from plotlyst.common import has_internet, PLOTLYST_MAIN_COLOR
from plotlyst.env import app_env, open_location
from plotlyst.event.core import emit_global_event, EventListener, Event
from plotlyst.event.handler import global_event_dispatcher
from plotlyst.resources import ResourceType, resource_manager, ResourceDownloadedEvent, \
    ResourceRemovedEvent, is_nltk, ResourceExtension, ResourceDescriptor, ResourceStatusChangedEvent, PANDOC_VERSION, \
    ResourceDownloadFailedEvent
from plotlyst.view.common import ButtonPressResizeEventFilter, spin, push_btn, fade_in
from plotlyst.view.generated.resource_manager_dialog_ui import Ui_ResourceManagerDialog
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group


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
        super().__init__()
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
            try:
                download_file(resource.web_url, resource_zip_path)
            except ConnectionError:
                handle_resource_connection_error(self, resource_type)
                return
            with zipfile.ZipFile(resource_zip_path) as zip_ref:
                zip_ref.extractall(resource_path)

            emit_global_event(ResourceDownloadedEvent(self, resource_type))


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
        try:
            download_file(resource.web_url, compressed_resource_path)
        except ConnectionError:
            handle_resource_connection_error(self, self._type)
            return

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

        try:
            download_pandoc(version=PANDOC_VERSION, targetfolder=target_path, download_folder=resource_path)
        except ConnectionError:
            handle_resource_connection_error(self, self._type)
        else:
            emit_global_event(ResourceDownloadedEvent(self, self._type))


def handle_resource_connection_error(runnable: QRunnable, resource_type: ResourceType):
    if has_internet():
        logging.exception('Could not establish connection to download resource: %s', resource_type.name)
    else:
        logging.warning('There was no internet connection to download resource: %s', resource_type.name)
    emit_global_event(ResourceDownloadFailedEvent(runnable, resource_type))


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
            response = requests.get(self._url, timeout=10)
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


def ask_for_resource(resource_type: ResourceType) -> bool:
    if not resource_manager.has_resource(resource_type):
        MissingResourceManagerDialog([resource_type]).display()
        if not resource_manager.has_resource(resource_type):
            return False

    return True


class MissingResourceManagerDialog(QDialog, Ui_ResourceManagerDialog):
    def __init__(self, resourceTypes: List[ResourceType], parent=None):
        super(MissingResourceManagerDialog, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle('Resource is missing')

        self._label = QLabel()
        self._label.setWordWrap(True)
        self._label.setText(
            "Additional resources are necessary to perform this action." +
            " Please click download to proceed (internet access is necessary)")
        italic(self._label)

        self.wdgCentral.layout().addWidget(self._label)
        self.wdgCentral.layout().addWidget(vspacer(40))
        wdg = ResourceManagerWidget(resourceTypes)
        self.wdgCentral.layout().addWidget(wdg)
        self.wdgCentral.layout().addWidget(vspacer())

    def display(self):
        self.exec()


class ResourceManagerDialog(QDialog, Ui_ResourceManagerDialog):
    def __init__(self, resourceTypes: Optional[List[ResourceType]] = None, parent=None):
        super(ResourceManagerDialog, self).__init__(parent)
        self.setupUi(self)

        wdg = ResourceManagerWidget(resourceTypes)
        self.wdgCentral.layout().addWidget(wdg)
        self.wdgCentral.layout().addWidget(vspacer())

    def display(self):
        self.exec()


class _ResourceControllers:
    def __init__(self, resourceType: ResourceType):
        super(_ResourceControllers, self).__init__()
        self._resourceType = resourceType
        self._resource: ResourceDescriptor = resource_manager.resource(self._resourceType)

        self.label = QLabel(self._resource.human_name)
        incr_font(self.label)
        bold(self.label)
        self.description = QLabel(self._resource.description)
        decr_font(self.description)
        self.description.setProperty('description', True)
        self.error = QLabel()
        self.error.setProperty('error', True)
        self.btnStatus = QToolButton()
        italic(self.btnStatus)
        transparent(self.btnStatus)

        self.btnRemove = QPushButton()
        self.btnRemove.setToolTip('Remove downloaded resource. Some functionality might stop working')
        self.btnRemove.setProperty('base', True)
        self.btnRemove.setProperty('deconstructive', True)
        decr_icon(self.btnRemove, 2)
        pointy(self.btnRemove)
        self.btnRemove.setIcon(IconRegistry.trash_can_icon('white'))
        self.btnRemove.installEventFilter(OpacityEventFilter(self.btnRemove, leaveOpacity=0.7))
        self.btnRemove.installEventFilter(ButtonPressResizeEventFilter(self.btnRemove))

        self.btnDownload = QPushButton()
        self.btnDownload.setToolTip('Download external resource. Internet access is necessary')
        self.btnDownload.setProperty('base', True)
        self.btnDownload.setProperty('highlighted', True)
        decr_icon(self.btnDownload, 2)
        pointy(self.btnDownload)
        self.btnDownload.setIcon(IconRegistry.from_name('mdi.download', 'white'))
        self.btnDownload.installEventFilter(OpacityEventFilter(self.btnDownload, leaveOpacity=0.7))
        self.btnDownload.installEventFilter(ButtonPressResizeEventFilter(self.btnDownload))

        self.btnRemove.clicked.connect(self._askRemove)
        self.btnDownload.clicked.connect(self.download)

        self.refresh()

    def resource(self) -> ResourceDescriptor:
        return self._resource

    def remove(self):
        spin(self.btnStatus)
        self.btnRemove.setDisabled(True)
        remove_resource(self._resourceType)

    def download(self):
        spin(self.btnStatus)
        self.btnDownload.setDisabled(True)
        download_resource(self._resourceType)

    def refresh(self):
        self.error.setHidden(True)
        if resource_manager.has_resource(self._resourceType):
            self.btnStatus.setIcon(IconRegistry.ok_icon(PLOTLYST_MAIN_COLOR))
            self.btnStatus.setToolTip('Downloaded')
            self.btnRemove.setVisible(True)
            self.btnRemove.setEnabled(True)
            self.btnDownload.setHidden(True)
        else:
            self.btnStatus.setIcon(IconRegistry.from_name('fa5s.minus'))
            self.btnStatus.setToolTip('Missing')
            self.btnRemove.setHidden(True)
            self.btnDownload.setVisible(True)
            self.btnDownload.setEnabled(True)

    def failed(self, message: str):
        self.error.setText(message)
        fade_in(self.error)
        self.btnStatus.setIcon(IconRegistry.from_name('fa5s.minus'))

    def _askRemove(self):
        # still use old ask_confirmation because it is opened from a dialog
        if ask_confirmation(
                f'Are you sure you want to remove the downloaded resource "{self._resource.human_name}"? Some functionality might stop working.'):
            self.remove()


class ResourceManagerWidget(QWidget, EventListener):

    def __init__(self, resourceTypes: Optional[List[ResourceType]] = None, parent=None):
        super(ResourceManagerWidget, self).__init__(parent)
        if not resourceTypes:
            resourceTypes = [ResourceType.JRE_8, ResourceType.PANDOC,
                             ResourceType.NLTK_PUNKT_TOKENIZER]
        self._resources: Dict[ResourceType, _ResourceControllers] = {}

        self._wdgDisplay = QWidget()
        vbox(self)

        btnOpenCacheFolder = push_btn(IconRegistry.from_name('fa5.folder-open'), 'Open cache folder', transparent_=True)
        btnOpenCacheFolder.installEventFilter(OpacityEventFilter(btnOpenCacheFolder))
        btnOpenCacheFolder.clicked.connect(lambda: open_location(app_env.cache_dir))

        self.layout().addWidget(btnOpenCacheFolder, alignment=Qt.AlignmentFlag.AlignRight)
        self.layout().addWidget(self._wdgDisplay)
        self._gridLayout: QGridLayout = grid(self._wdgDisplay)

        header = QLabel('Resource')
        underline(header)
        self._gridLayout.addWidget(header, 0, 0)
        header = QLabel('Status')
        underline(header)
        self._gridLayout.addWidget(header, 0, 1)
        self._gridLayout.addWidget(line(), 1, 0, 1, 3)

        for i, resourceType in enumerate(resourceTypes):
            contr = _ResourceControllers(resourceType)
            self._resources[resourceType] = contr
            self._gridLayout.addWidget(group(contr.label, contr.description, contr.error, vertical=False, spacing=2),
                                       i + 2, 0)
            self._gridLayout.addWidget(contr.btnStatus, i + 2, 1, alignment=Qt.AlignmentFlag.AlignCenter)
            self._gridLayout.addWidget(contr.btnRemove, i + 2, 2, alignment=Qt.AlignmentFlag.AlignCenter)
            self._gridLayout.addWidget(contr.btnDownload, i + 2, 3, alignment=Qt.AlignmentFlag.AlignCenter)
            self._gridLayout.addWidget(spacer(), i + 2, 4)

        global_event_dispatcher.register(self, ResourceStatusChangedEvent, ResourceDownloadFailedEvent)

    @overrides
    def event_received(self, event: Event):
        if isinstance(event, ResourceStatusChangedEvent):
            if event.type in self._resources:
                self._resources[event.type].refresh()
        elif isinstance(event, ResourceDownloadFailedEvent):
            if event.type in self._resources:
                self._resources[event.type].failed('Could not download resource')
