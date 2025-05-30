import sys
from pathlib import Path
from uuid import UUID

import pytest

from plotlyst.core.domain import Novel, Chapter, Scene, CharacterAgency, Character, ImportOrigin, \
    ImportOriginType
from plotlyst.core.scrivener import ScrivenerParser


def test_empty_folder(tmp_path):
    importer = ScrivenerParser()
    with pytest.raises(ValueError) as excinfo:
        importer.parse_project(str(tmp_path))

        assert 'Could not find main Scrivener file with .scrivx extension under given folder' in str(excinfo)


def test_not_existing_input(tmp_path):
    importer = ScrivenerParser()
    with pytest.raises(ValueError) as excinfo:
        importer.parse_project(str(tmp_path.joinpath('not-existing-directory')))

        assert 'Input folder does not exist' in str(excinfo)


def test_import_with_acts(test_client):
    folder = Path(sys.path[0]).joinpath('../../../resources/scrivener/v3/NovelWithParts')

    importer = ScrivenerParser()
    novel: Novel = importer.parse_project(str(folder))

    assert novel
    assert novel.chapters
    assert novel.scenes

    chapters = [Chapter(title='Chapter', id=UUID('58D0189B-0507-4669-B129-4A392CF07F36')),
                Chapter(title='Chapter', id=UUID('567B89D4-21E4-44DF-BD5C-3F32EEC78ADD')),
                Chapter(title='Chapter', id=UUID('245C2ABD-E9C1-4091-B1B7-DA32402644E7'))]
    scenes = [Scene(title='Scene 1', id=UUID('A9C97B44-46C8-4CA8-8F28-B8C0606A58EF'), chapter=chapters[0],
                    synopsis='Scene 1 synopsis', agency=[CharacterAgency()]),
              Scene(title='Scene 2', id=UUID('E6BBAC10-E639-4E86-A784-EDEEE7DF0206'), chapter=chapters[0],
                    synopsis='Scene 2 synopsis', agency=[CharacterAgency()]),
              Scene(title='Scene 3', id=UUID('2B5EF0AA-74AE-435D-98A6-096CEAF8F721'), chapter=chapters[0],
                    agency=[CharacterAgency()]),
              Scene(title='Scene', id=UUID('F5604565-3F9E-451B-98E0-142BE1BDE83D'), chapter=chapters[1],
                    agency=[CharacterAgency()]),
              Scene(title='Scene', id=UUID('156AAE33-5D68-4ACA-8469-6440CDFED4EA'), chapter=chapters[2],
                    agency=[CharacterAgency()])]
    characters = [Character('John', id=UUID('C33E84AA-CC86-4112-A2B4-713917EDB7EF')),
                  Character('Luna', id=UUID('CA105A6C-E2E7-4A27-9EF3-CB9D6D6B9CD9'))]
    # locations = [Location('Place one', id=UUID('BEF3ADD7-99D3-46B6-829F-D4B7CF08D4D0'))]
    expected_novel = Novel(title='Novel With Parts', id=novel.id, chapters=chapters,
                           scenes=scenes, characters=characters, stages=novel.stages,
                           story_structures=novel.story_structures,
                           import_origin=ImportOrigin(ImportOriginType.SCRIVENER, source=str(folder),
                                                      source_id=UUID('C4B3D990-B9C2-4FE6-861E-B06B498283A4')))
    assert novel.title == expected_novel.title
    assert novel.id == expected_novel.id
    assert novel.scenes[0].manuscript
    assert novel.scenes[0].manuscript.content
    assert novel.scenes[0].manuscript.statistics
    assert novel.scenes[0].manuscript.statistics.wc
    assert novel.scenes[1].manuscript
    assert novel.scenes[1].manuscript.content
    assert novel.scenes[1].manuscript.statistics
    assert novel.scenes[1].manuscript.statistics.wc
    assert novel.id != novel.import_origin.source_id

    novel.import_origin.last_mod_time = 0
    assert novel.import_origin == expected_novel.import_origin

    novel.scenes[0].manuscript = None
    novel.scenes[1].manuscript = None
    assert novel.scenes == expected_novel.scenes

    for c in novel.characters:
        assert c.avatar, 'Character avatar should have been loaded'
        c.avatar = None
    assert novel.characters == expected_novel.characters
