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
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QComboBox

from plotlyst.core.template import TemplateField, TemplateFieldType, enneagram_field, mbti_field, \
    traits_field, SelectionItemType, SelectionItem, gmc_field, baggage_field, love_style_field, disc_field, flaws_field, \
    strengths_weaknesses_field
from plotlyst.view.icons import IconRegistry
from plotlyst.view.widget.template.impl import SubtitleTemplateDisplayWidget, \
    LabelTemplateDisplayWidget, HeaderTemplateDisplayWidget, LineTemplateDisplayWidget, IconTemplateDisplayWidget, \
    EnneagramFieldWidget, MbtiFieldWidget, TraitsFieldWidget, NumericTemplateFieldWidget, SmallTextTemplateFieldWidget, \
    LineTextTemplateFieldWidget, LabelsTemplateFieldWidget, GmcFieldWidget, BaggageFieldWidget, \
    BarTemplateFieldWidget, LoveStyleFieldWidget, WorkStyleFieldWidget, FlawsFieldWidget, StrengthsWeaknessesFieldWidget


def _icon(item: SelectionItem) -> QIcon:
    if item.icon:
        return IconRegistry.from_name(item.icon, item.icon_color)
    else:
        return QIcon('')


class TemplateFieldWidgetFactory:

    @staticmethod
    def widget(field: TemplateField, parent=None):
        if field.type == TemplateFieldType.DISPLAY_SUBTITLE:
            return SubtitleTemplateDisplayWidget(field, parent)
        elif field.type == TemplateFieldType.DISPLAY_LABEL:
            return LabelTemplateDisplayWidget(field, parent)
        elif field.type == TemplateFieldType.DISPLAY_HEADER:
            return HeaderTemplateDisplayWidget(field, parent)
        elif field.type == TemplateFieldType.DISPLAY_LINE:
            return LineTemplateDisplayWidget(field, parent)
        elif field.type == TemplateFieldType.DISPLAY_ICON:
            return IconTemplateDisplayWidget(field, parent)

        if field.id == enneagram_field.id:
            return EnneagramFieldWidget(field, parent)
        elif field.id == mbti_field.id:
            return MbtiFieldWidget(field, parent)
        elif field.id == love_style_field.id:
            return LoveStyleFieldWidget(field, parent)
        elif field.id == disc_field.id:
            return WorkStyleFieldWidget(field, parent)
        elif field.id == flaws_field.id:
            return FlawsFieldWidget(field)
        elif field.id == strengths_weaknesses_field.id:
            return StrengthsWeaknessesFieldWidget(field)
        elif field.id == traits_field.id:
            return TraitsFieldWidget(field)
        elif field.id == gmc_field.id:
            return GmcFieldWidget(field)
        elif field.id == baggage_field.id:
            return BaggageFieldWidget(field)
        elif field.type == TemplateFieldType.NUMERIC:
            return NumericTemplateFieldWidget(field, parent)
        elif field.type == TemplateFieldType.TEXT_SELECTION:
            widget = QComboBox()
            if not field.required:
                widget.addItem('')
            for item in field.selections:
                if item.type == SelectionItemType.CHOICE:
                    widget.addItem(_icon(item), item.text)
                if item.type == SelectionItemType.SEPARATOR:
                    widget.insertSeparator(widget.count())
            return widget
        # elif field.type == TemplateFieldType.BUTTON_SELECTION:
        #     widget = ButtonSelectionWidget(field)
        elif field.type == TemplateFieldType.SMALL_TEXT:
            return SmallTextTemplateFieldWidget(field, parent)
        elif field.type == TemplateFieldType.TEXT:
            return LineTextTemplateFieldWidget(field, parent)
        elif field.type == TemplateFieldType.LABELS:
            return LabelsTemplateFieldWidget(field, parent)
        elif field.type == TemplateFieldType.BAR:
            return BarTemplateFieldWidget(field, parent)
        else:
            return SmallTextTemplateFieldWidget(field, parent)
