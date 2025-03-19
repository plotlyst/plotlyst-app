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
from datetime import datetime
from pathlib import Path
from typing import Optional, List

import pypandoc
from PyQt6.QtCore import Qt, QMarginsF
from PyQt6.QtGui import QTextDocument, QTextCursor, QTextBlockFormat, QTextFormat, QTextBlock, QFont, QTextCharFormat, \
    QPageSize, QPageLayout
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtWidgets import QFileDialog
from qthandy import busy
from slugify import slugify

from plotlyst.common import DEFAULT_MANUSCRIPT_INDENT, DEFAULT_MANUSCRIPT_LINE_SPACE
from plotlyst.core.client import json_client
from plotlyst.core.domain import Novel, Document, DocumentProgress, Scene, DocumentStatistics, Chapter
from plotlyst.core.text import wc
from plotlyst.env import open_location, app_env
from plotlyst.resources import resource_registry, ResourceType
from plotlyst.service.common import today_str
from plotlyst.service.dir import default_exported_location
from plotlyst.service.persistence import RepositoryPersistenceManager
from plotlyst.service.resource import ask_for_resource
from plotlyst.view.widget.confirm import asked


def export_manuscript_to_docx(novel: Novel, sceneTitle: bool = False, povTitle: bool = False, titlePage: bool = True,
                              author: str = ''):
    if not ask_for_resource(ResourceType.PANDOC):
        return

    json_client.load_manuscript(novel)
    if app_env.is_dev():
        target_path = 'test.docx'
    else:
        title = slugify(novel.title if novel.title else 'my-novel')
        target_path, _ = QFileDialog.getSaveFileName(None, 'Export Docx', default_exported_location(f'{title}.docx'),
                                                     'Docx files (*.docx);;All Files()')
        if not target_path:
            return

    html: str = ''
    if titlePage:
        title = novel.title if novel.title else "My Novel"
        if novel.subtitle:
            title += ':'
        html += f'<div custom-style="Title">{title}</div>'

        if novel.subtitle:
            html += f'<div custom-style="Subtitle">{novel.subtitle}</div>'

        html += f'<div custom-style="Author">{author}</div>'
        html += f'<div custom-style="Date">{datetime.today().strftime("%B %d, %Y")}</div>'

    if novel.prefs.is_scenes_organization():
        for i, chapter in enumerate(novel.chapters):
            scenes = novel.scenes_in_chapter(chapter)
            chapter_heading = chapter_title(chapter, scenes, sceneTitle, povTitle)
            html += f'<h1>{chapter_heading}</h1>'
            first_paragraph = True
            for j, scene in enumerate(scenes):
                if not scene.manuscript:
                    continue

                md_content = _prepare_scene_for_export(scene, first_paragraph)

                scene_html = pypandoc.convert_text(md_content, to='html', format='md')
                html += scene_html
    else:
        for i, scene in enumerate(novel.scenes):
            if povTitle and scene.pov:
                title = scene.pov.displayed_name()
            else:
                title = scene.title_or_index(novel)

            html += f'<h1>{title}</h1>'
            first_paragraph = True

            if not scene.manuscript:
                continue

            md_content = _prepare_scene_for_export(scene, first_paragraph)

            scene_html = pypandoc.convert_text(md_content, to='html', format='md')
            html += scene_html

    spec_args = ['--reference-doc', resource_registry.manuscript_docx_template]
    pypandoc.convert_text(html, to='docx', format='html', extra_args=spec_args, outputfile=target_path)

    ask_to_open_file(target_path)


def _prepare_scene_for_export(scene: Scene, first_paragraph: bool) -> str:
    text_doc = QTextDocument()
    text_doc.setHtml(scene.manuscript.content)
    block: QTextBlock = text_doc.begin()
    md_content: str = ''
    while block.isValid():
        text = block.text()
        if not text:
            first_paragraph = True
            block_content = ''
        elif text == '***' or text == '###':
            block_content = '<div custom-style="Text Aligned Center">***</div>'
            first_paragraph = True
        else:
            cursor = QTextCursor(block)
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            block_content = cursor.selection().toMarkdown()

            if block.blockFormat().alignment() & Qt.AlignmentFlag.AlignCenter:
                block_content = f'<div custom-style="Text Aligned Center">{block_content}</div>'
            elif block.blockFormat().alignment() & Qt.AlignmentFlag.AlignRight:
                block_content = f'<div custom-style="Text Aligned Right">{block_content}</div>'

            if first_paragraph:
                block_content = f'<div custom-style="First Paragraph">{block_content}</div>'
                first_paragraph = False

        md_content += block_content

        block = block.next()
    return md_content


def export_manuscript_to_pdf(novel: Novel, manuscript: QTextDocument):
    title = slugify(novel.title if novel.title else 'my-novel')
    target_path, _ = QFileDialog.getSaveFileName(None, 'Export PDF', f'{title}.pdf',
                                                 'PDF files (*.pdf);;All Files()')
    if not target_path:
        return
    printer = QPrinter()
    printer.setPageSize(QPageSize(QPageSize.PageSizeId.Letter))
    printer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Inch)  # margin is already set it seems
    printer.setOutputFileName(target_path)
    printer.setDocName(title)
    manuscript.print(printer)

    ask_to_open_file(target_path)


def ask_to_open_file(target_path: str):
    if asked('The file will be opened in an external editor associated with that file format.',
             'Export was finished. Open file in editor?', btnCancelText='No', btnConfirmText='Open file'):
        open_location(target_path)


def format_manuscript(novel: Novel, sceneTitle: bool = False, povTitle: bool = False) -> QTextDocument:
    json_client.load_manuscript(novel)

    font = QFont('Times New Roman', 12)

    chapter_title_block_format = QTextBlockFormat()
    chapter_title_block_format.setAlignment(Qt.AlignmentFlag.AlignCenter)
    chapter_title_block_format.setHeadingLevel(1)
    chapter_title_char_format = QTextCharFormat()
    chapter_title_char_format.setFont(font)
    chapter_title_char_format.setFontPointSize(16)

    default_block_format = QTextBlockFormat()
    default_block_format.setAlignment(Qt.AlignmentFlag.AlignLeft)
    default_block_format.setTextIndent(40)
    default_block_format.setTopMargin(0)
    default_block_format.setBottomMargin(0)
    default_block_format.setLeftMargin(0)
    default_block_format.setRightMargin(0)
    default_block_format.setLineHeight(200, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)

    first_block_format = QTextBlockFormat(default_block_format)
    first_block_format.setTextIndent(0)

    page_break_format = QTextBlockFormat()
    page_break_format.setPageBreakPolicy(QTextFormat.PageBreakFlag.PageBreak_AlwaysAfter)

    document = QTextDocument()
    document.setDefaultFont(font)
    document.setDocumentMargin(0)

    cursor: QTextCursor = document.rootFrame().firstCursorPosition()

    if novel.prefs.is_scenes_organization():
        for i, chapter in enumerate(novel.chapters):
            cursor.insertBlock(chapter_title_block_format, chapter_title_char_format)

            scenes = novel.scenes_in_chapter(chapter)
            chapterTitle = chapter_title(chapter, scenes, sceneTitle, povTitle)
            cursor.insertText(chapterTitle)

            cursor.insertBlock(default_block_format)

            first_paragraph = True
            for j, scene in enumerate(scenes):
                if not scene.manuscript:
                    continue

                _format_scene(cursor, default_block_format, first_block_format, first_paragraph, scene)
                if j == len(scenes) - 1 and i != len(novel.chapters) - 1:
                    cursor.insertBlock(page_break_format)
    else:
        for i, scene in enumerate(novel.scenes):
            cursor.insertBlock(chapter_title_block_format, chapter_title_char_format)
            if povTitle and scene.pov:
                title = scene.pov.displayed_name()
            else:
                title = scene.title_or_index(novel)
            cursor.insertText(title)

            cursor.insertBlock(default_block_format)

            first_paragraph = True
            if not scene.manuscript:
                continue

            _format_scene(cursor, default_block_format, first_block_format, first_paragraph, scene)
            if i != len(novel.scenes) - 1:
                cursor.insertBlock(page_break_format)

    return document


def _format_scene(cursor: QTextCursor, default_block_format: QTextBlockFormat, first_block_format: QTextBlockFormat,
                  first_paragraph: bool, scene: Scene):
    scene_text_doc = QTextDocument()
    scene_text_doc.setHtml(scene.manuscript.content)
    block = scene_text_doc.begin()
    while block.isValid():
        if first_paragraph:
            first_paragraph = False
            block_format = first_block_format
        else:
            block_format = default_block_format

        block_format.setAlignment(block.blockFormat().alignment())
        cursor.insertBlock(block_format)

        block_cursor = QTextCursor(block)
        block_cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)

        text = block.text()
        if not text or text == '###' or text == '***':
            first_paragraph = True
            cursor.insertText(text)
        else:
            cursor.insertMarkdown(block_cursor.selection().toMarkdown())

        block = block.next()


def chapter_title(chapter: Chapter, scenes: List[Scene], sceneTitle: bool = False, povTitle: bool = False) -> str:
    if scenes and not chapter.type:
        if sceneTitle and scenes[0].title:
            return scenes[0].title
        if povTitle and scenes[0].pov:
            return scenes[0].pov.displayed_name()

    return chapter.display_name()


def find_daily_overall_progress(novel: Novel, date: Optional[str] = None) -> Optional[DocumentProgress]:
    if novel.manuscript_progress:
        if date is None:
            date = today_str()
        return novel.manuscript_progress.get(date, None)


def daily_overall_progress(novel: Novel) -> DocumentProgress:
    date = today_str()
    progress = find_daily_overall_progress(novel, date)
    if progress is None:
        progress = DocumentProgress()
        novel.manuscript_progress[date] = progress

        RepositoryPersistenceManager.instance().update_novel(novel)

    return progress


def find_daily_progress(scene: Scene, date: Optional[str] = None) -> Optional[DocumentProgress]:
    if scene.manuscript.statistics is None:
        scene.manuscript.statistics = DocumentStatistics()

    if scene.manuscript.statistics.progress:
        if date is None:
            date = today_str()
        return scene.manuscript.statistics.progress.get(date, None)


def daily_progress(scene: Scene) -> DocumentProgress:
    date = today_str()
    progress = find_daily_progress(scene, date)

    if progress is None:
        progress = DocumentProgress()
        scene.manuscript.statistics.progress[date] = progress

        RepositoryPersistenceManager.instance().update_scene(scene)

    return progress


@busy
def import_docx(path: str, chapter_heading_level: int = 2, infer_scene_titles: bool = False):
    title = Path(path).stem
    novel = Novel.new_novel(title)
    novel.scenes.clear()
    novel.chapters.clear()

    md_text = pypandoc.convert_file(path, to='md', format='docx')

    current_chapter = None
    novel_title_set = False

    chapter_prefix = '#' * chapter_heading_level
    scene_content = []

    lines = md_text.splitlines()
    for i, line in enumerate(lines):
        if chapter_heading_level > 1 and not novel_title_set and line.startswith("# "):
            novel.title = line[2:].strip()
            novel_title_set = True

        elif line.startswith(f"{chapter_prefix} "):  # Chapter heading
            if current_chapter and scene_content:
                _add_scene_to_novel(novel, current_chapter, scene_content, infer_scene_titles)
                scene_content = []

            chapter_title = line[len(chapter_prefix):].strip()
            current_chapter = Chapter(chapter_title)
            novel.chapters.append(current_chapter)

        else:
            if current_chapter:
                scene_content.append(line)

    if current_chapter and scene_content:
        _add_scene_to_novel(novel, current_chapter, scene_content, infer_scene_titles)

    novel.update_chapter_titles()
    _apply_manuscript_format(novel)

    return novel


def _add_scene_to_novel(novel: Novel, chapter: Chapter, scene_content: List[str], infer_scene_titles: bool):
    markdown_text = "\n".join(scene_content)
    qt_doc = QTextDocument()
    qt_doc.setMarkdown(markdown_text)
    html_content = qt_doc.toHtml()

    document = Document('')
    document.content = html_content
    scene = Scene(title=chapter.title if infer_scene_titles else '', chapter=chapter, manuscript=document)

    novel.scenes.append(scene)


def _apply_manuscript_format(novel: Novel):
    blockFmt = QTextBlockFormat()
    blockFmt.setTextIndent(DEFAULT_MANUSCRIPT_INDENT)
    blockFmt.setLineHeight(DEFAULT_MANUSCRIPT_LINE_SPACE, 1)
    blockFmt.setLeftMargin(0)
    blockFmt.setTopMargin(0)
    blockFmt.setRightMargin(0)
    blockFmt.setBottomMargin(0)

    for scene in novel.scenes:
        if scene.manuscript:
            document = QTextDocument()
            document.setHtml(scene.manuscript.content)
            cursor = QTextCursor(document)
            cursor.clearSelection()
            cursor.select(QTextCursor.SelectionType.Document)
            cursor.setBlockFormat(blockFmt)

            scene.manuscript.content = document.toHtml()
            scene.manuscript.statistics = DocumentStatistics(wc(document.toPlainText()))
