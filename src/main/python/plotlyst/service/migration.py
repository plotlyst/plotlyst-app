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
from plotlyst.core.domain import Novel, Document, DocumentType
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
