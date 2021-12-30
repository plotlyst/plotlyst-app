#!/bin/bash

# exit when any command fails
set -e

# generates Python code from Qt UI files. See .pyqt5ac.yml for reference
#pyqt5ac --config .pyqt5ac.yml
pyuic6 ui/about_dialog.ui -o src/main/python/plotlyst/view/generated/about_dialog_ui.py
pyuic6 ui/avatar_widget.ui -o src/main/python/plotlyst/view/generated/avatar_widget.ui.py
pyuic6 ui/backstory_editor_dialog.ui -o src/main/python/plotlyst/view/generated/backstory_editor_dialog.ui.py
pyuic6 ui/cause_and_effect_editor.ui -o src/main/python/plotlyst/view/generated/cause_and_effect_editor.ui.py
pyuic6 ui/character_backstory_card.ui -o src/main/python/plotlyst/view/generated/character_backstory_card.ui.py
pyuic6 ui/character_card.ui -o src/main/python/plotlyst/view/generated/character_card.ui.py
pyuic6 ui/character_conflict_widget.ui -o src/main/python/plotlyst/view/generated/character_conflict_widget.ui.py
pyuic6 ui/character_editor.ui -o src/main/python/plotlyst/view/generated/character_editor.ui.py
pyuic6 ui/character_profile_editor_dialog.ui -o src/main/python/plotlyst/view/generated/character_profile_editor_dialog.ui.py
pyuic6 ui/characters_view.ui -o src/main/python/plotlyst/view/generated/characters_view.ui.py
pyuic6 ui/comments_view.ui -o src/main/python/plotlyst/view/generated/comments_view.ui.py
pyuic6 ui/comment_widget.ui -o src/main/python/plotlyst/view/generated/comment_widget.ui.py
pyuic6 ui/directory_picker_dialog.ui -o src/main/python/plotlyst/view/generated/directory_picker_dialog.ui.py
pyuic6 ui/docs_sidebar_widget.ui -o src/main/python/plotlyst/view/generated/docs_sidebar_widget.ui.py
pyuic6 ui/field_text_selection_widget.ui -o src/main/python/plotlyst/view/generated/field_text_selection_widget.ui.py
pyuic6 ui/home_view.ui -o src/main/python/plotlyst/view/generated/home_view.ui.py
pyuic6 ui/icon_selector_widget.ui -o src/main/python/plotlyst/view/generated/icon_selector_widget.ui.py
pyuic6 ui/items_editor_dialog.ui -o src/main/python/plotlyst/view/generated/items_editor_dialog.ui.py
pyuic6 ui/items_editor_widget.ui -o src/main/python/plotlyst/view/generated/items_editor_widget.ui.py
pyuic6 ui/journal_card.ui -o src/main/python/plotlyst/view/generated/journal_card.ui.py
pyuic6 ui/journal_widget.ui -o src/main/python/plotlyst/view/generated/journal_widget.ui.py
pyuic6 ui/locations_view.ui -o src/main/python/plotlyst/view/generated/locations_view.ui.py
pyuic6 ui/main_window.ui -o src/main/python/plotlyst/view/generated/main_window.ui.py
pyuic6 ui/manuscript_view.ui -o src/main/python/plotlyst/view/generated/manuscript_view.ui.py
pyuic6 ui/notes_view.ui -o src/main/python/plotlyst/view/generated/notes_view.ui.py
pyuic6 ui/novel_card.ui -o src/main/python/plotlyst/view/generated/novel_card.ui.py
pyuic6 ui/novel_creation_dialog.ui -o src/main/python/plotlyst/view/generated/novel_creation_dialog.ui.py
pyuic6 ui/novel_view.ui -o src/main/python/plotlyst/view/generated/novel_view.ui.py
pyuic6 ui/plot_editor_dialog.ui -o src/main/python/plotlyst/view/generated/plot_editor_dialog.ui.py
pyuic6 ui/reports_view.ui -o src/main/python/plotlyst/view/generated/reports_view.ui.py
pyuic6 ui/scene_beat_item_widget.ui -o src/main/python/plotlyst/view/generated/scene_beat_item_widget.ui.py
pyuic6 ui/scene_builder_preview_dialog.ui -o src/main/python/plotlyst/view/generated/scene_builder_preview_dialog.ui.py
pyuic6 ui/scene_card.ui -o src/main/python/plotlyst/view/generated/scene_card.ui.py
pyuic6 ui/scene_dstribution_widget.ui -o src/main/python/plotlyst/view/generated/scene_dstribution_widget.ui.py
pyuic6 ui/scene_editor.ui -o src/main/python/plotlyst/view/generated/scene_editor.ui.py
pyuic6 ui/scene_element_edition_dialog.ui -o src/main/python/plotlyst/view/generated/scene_element_edition_dialog.ui.py
pyuic6 ui/scene_filter_widget.ui -o src/main/python/plotlyst/view/generated/scene_filter_widget.ui.py
pyuic6 ui/scene_ouctome_selector.ui -o src/main/python/plotlyst/view/generated/scene_ouctome_selector.ui.py
pyuic6 ui/scene_structure_editor_widget.ui -o src/main/python/plotlyst/view/generated/scene_structure_editor_widget.ui.py
pyuic6 ui/scenes_view.ui -o src/main/python/plotlyst/view/generated/scenes_view.ui.py
pyuic6 ui/sprint_widget.ui -o src/main/python/plotlyst/view/generated/sprint_widget.ui.py
pyuic6 ui/tasks_widget.ui -o src/main/python/plotlyst/view/generated/tasks_widget.ui.py
pyuic6 ui/timeline_view.ui -o src/main/python/plotlyst/view/generated/timeline_view.ui.py
pyuic6 ui/timer_setup_widget.ui -o src/main/python/plotlyst/view/generated/timer_setup_widget.ui.py