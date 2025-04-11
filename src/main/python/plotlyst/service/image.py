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
from pathlib import Path
from typing import Optional

from PyQt6.QtGui import QImage, QImageReader, QPixmap
from PyQt6.QtWidgets import QApplication, QFileDialog

from plotlyst.core.client import json_client
from plotlyst.core.domain import ImageRef, Novel
from plotlyst.view.widget.utility import ImageCropDialog


def has_clipboard_image() -> bool:
    mime_data = QApplication.clipboard().mimeData()
    return mime_data.hasImage()


@dataclass
class LoadedImage:
    ref: ImageRef
    image: QImage


def save_clipboard_image(novel: Novel) -> Optional[LoadedImage]:
    mime_data = QApplication.clipboard().mimeData()
    if mime_data.hasImage():
        image: QImage = mime_data.imageData()
        if not image.isNull():
            ref = ImageRef('png')
            save_image(novel, image, ref)
            return LoadedImage(ref, image)


def upload_image(novel: Novel, crop: bool = False, roundedCroppedPreview: bool = False) -> Optional[LoadedImage]:
    file_path, _ = QFileDialog.getOpenFileName(None, "Choose an image", "", "Images (*.png *.jpg *.jpeg *.webp)")
    if file_path:
        reader = QImageReader(file_path)
        reader.setAutoTransform(True)
        image: Optional[QImage] = reader.read()
        if image is None:
            return

        if crop:
            cropped_pixmap: Optional[QPixmap] = ImageCropDialog.popup(QPixmap.fromImage(image), roundedCroppedPreview)
            if cropped_pixmap:
                image = cropped_pixmap.toImage()
            else:
                return None

        file_extension = Path(file_path).suffix.lower()
        ref = ImageRef(file_extension)
        ref.loaded = True
        ref.data = image
        if not novel.tutorial:
            save_image(novel, image, ref)
        return LoadedImage(ref, image)


def save_image(novel: Novel, image: QImage, ref: ImageRef):
    json_client.save_image(novel, ref, image)


def load_image(novel: Novel, ref: ImageRef) -> Optional[QImage]:
    if ref.loaded:
        return ref.data

    image = json_client.load_image(novel, ref)
    if image:
        ref.loaded = True
        ref.data = image
        return image
