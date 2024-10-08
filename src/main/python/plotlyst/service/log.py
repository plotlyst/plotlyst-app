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

from overrides import overrides

from plotlyst.model.log import LogTableModel


class LogHandler(logging.Handler):
    def __init__(self, model: LogTableModel):
        super().__init__()
        self.model = model
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.setFormatter(formatter)

    @overrides
    def emit(self, record):
        self.format(record)
        self.model.addLogRecord(record)


def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    model = LogTableModel()
    log_handler = LogHandler(model)
    logger.addHandler(log_handler)
