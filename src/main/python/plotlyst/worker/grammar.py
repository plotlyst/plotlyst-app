"""
Plotlyst
Copyright (C) 2021-2022  Zsolt Kovari

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
import language_tool_python
from PyQt6.QtCore import QRunnable
from overrides import overrides


class LanguageToolServerSetupWorker(QRunnable):

    def __init__(self, source):
        super(LanguageToolServerSetupWorker, self).__init__()
        self.source = source

    @overrides
    def run(self) -> None:
        try:
            tool = language_tool_python.LanguageTool('en-US')
            tool.check('Test sentence.')
            self.source.set_language_tool(tool)
        except Exception as e:
            self.source.set_language_tool_error(str(e))
