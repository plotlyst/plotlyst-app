"""
Plotlyst
Copyright (C) 2021-2025  Zsolt Kovari

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
import datetime
import random
from dataclasses import dataclass, field
from functools import partial
from typing import List, Dict, Optional

from PyQt6.QtCore import QThreadPool, QSize, Qt, QEvent, pyqtSignal
from PyQt6.QtGui import QShowEvent, QMouseEvent, QCursor, QGuiApplication
from PyQt6.QtWidgets import QWidget, QTabWidget, QPushButton, QProgressBar, QButtonGroup, QFrame, QComboBox, \
    QTextBrowser, QLineEdit
from dataclasses_json import dataclass_json, Undefined
from overrides import overrides
from qthandy import vbox, hbox, clear_layout, line, vspacer, spacer, translucent, margins, transparent, incr_font, flow, \
    vline, pointy, decr_icon, sp, incr_icon
from qthandy.filter import OpacityEventFilter, ObjectReferenceMimeData
from qtmenu import MenuWidget

from plotlyst.common import PLOTLYST_MAIN_COLOR, PLOTLYST_SECONDARY_COLOR, PLOTLYST_TERTIARY_COLOR, truncate_string, \
    RELAXED_WHITE_COLOR, IGNORE_CAPITALIZATION_PROPERTY
from plotlyst.core.domain import Board, Task, TaskStatus
from plotlyst.env import app_env
from plotlyst.service.resource import JsonDownloadResult, JsonDownloadWorker
from plotlyst.view.common import label, set_tab_enabled, push_btn, spin, scroll_area, wrap, frame, shadow, tool_btn, \
    action, open_url, ExclusiveOptionalButtonGroup
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.widget.button import SmallToggleButton
from plotlyst.view.widget.cards import Card
from plotlyst.view.widget.chart import ChartItem, PolarChart, PieChart
from plotlyst.view.widget.display import IconText, ChartView, PopupDialog, HintButton, icon_text, CopiedTextMessage
from plotlyst.view.widget.input import AutoAdjustableTextEdit, DecoratedLineEdit
from plotlyst.view.widget.list import ListView, ListItemWidget


@dataclass
class PatreonTier:
    name: str
    description: str
    perks: List[str]
    price: str
    icon: str = ''
    has_roadmap_form: bool = False
    has_plotlyst_plus: bool = False
    has_early_access: bool = False
    has_recognition: bool = False
    has_premium_recognition: bool = False


@dataclass
class SurveyResults:
    title: str
    description: str
    items: Dict[str, ChartItem]


@dataclass
class PatreonSurvey:
    stage: SurveyResults
    panels: SurveyResults
    genres: SurveyResults
    new: SurveyResults
    secondary: SurveyResults
    personalization: SurveyResults


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Patreon:
    tiers: List[PatreonTier]
    survey: PatreonSurvey


@dataclass
class PatronNovelInfo:
    title: str
    premise: str = ''
    web: str = ''


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Patron:
    name: str
    web: str = ''
    icon: str = ''
    bio: str = ''
    description: str = ''
    genre: str = ''
    vip: bool = False
    profession: str = ''
    novels: List[PatronNovelInfo] = field(default_factory=list)
    socials: Dict[str, str] = field(default_factory=dict)
    favourites: List[str] = field(default_factory=list)


example_patron = Patron('Zsolt', web='https://plotlyst.com', bio='Fantasy Writer | Developer of Plotlyst',
                        icon='fa5s.gem', vip=True, socials={"ig": "https://instagram.com/plotlyst",
                                                            "threads": "https://threads.net/@plotlyst",
                                                            "patreon": "https://patreon.com/user?u=24283978"},
                        favourites=["Rebecca", "The Picture of Dorian Gray", "Anna Karenina", "Jane Eyre", "Malazan"],
                        description="I write adult High Fantasy with magical gemstones, artifacts, golems, and titans.")


@dataclass_json(undefined=Undefined.EXCLUDE)
@dataclass
class Community:
    patrons: List[Patron]


class PlusTaskWidget(QWidget):
    def __init__(self, task: Task, status: TaskStatus, parent=None, appendLine: bool = True):
        super().__init__(parent)
        self.task = task
        self.status = status
        vbox(self, 10, spacing=5)

        self.lblStatus = label(self.status.text)
        self.lblStatus.setStyleSheet(f'''
            color: {self.status.color_hexa};
        ''')

        self.lblName = IconText()
        incr_font(self.lblName, 4)
        self.lblName.setText(self.task.title)
        if self.task.icon:
            self.lblName.setIcon(IconRegistry.from_name(self.task.icon))
        self.lblDescription = label(self.task.summary, description=True, wordWrap=True)
        self.lblDescription.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        incr_font(self.lblDescription)

        self._btnOpenInExternal = tool_btn(IconRegistry.from_name('fa5s.external-link-alt', 'grey'), transparent_=True,
                                           tooltip='Open in browser')
        decr_icon(self._btnOpenInExternal, 4)
        self._btnOpenInExternal.clicked.connect(lambda: open_url(self.task.web_link))

        self.layout().addWidget(self.lblStatus, alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(group(self.lblName, self._btnOpenInExternal), alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout().addWidget(self.lblDescription)
        if appendLine:
            self.layout().addWidget(line())


class PlusFeaturesWidget(QWidget):
    DOWNLOAD_THRESHOLD_SECONDS = 60 * 60 * 8  # 8 hours in seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_fetched = None
        self._downloading = False
        self._board: Optional[Board] = None
        self._thread_pool = QThreadPool()

        vbox(self)

        self._scroll = scroll_area(frameless=True)
        self._scroll.setProperty('relaxed-white-bg', True)
        self.centerWdg = QWidget()
        self.centerWdg.setProperty('relaxed-white-bg', True)
        vbox(self.centerWdg, spacing=15)
        self._scroll.setWidget(self.centerWdg)
        self.layout().addWidget(self._scroll)

        self.lblLastUpdated = label('', description=True, decr_font_diff=1)
        self.btnVisitRoadmap = push_btn(IconRegistry.from_name('fa5s.external-link-alt', 'grey'), transparent_=True,
                                        text='Visit online roadmap')
        self.btnVisitRoadmap.clicked.connect(lambda: open_url(
            'https://plotlyst.featurebase.app/?s=66cd8ba9b3152ae64e027821%2C66cd8ba9b3152ae64e02781f%2C66cd8ba9b3152ae64e027820%2C66cd8ba9b3152ae64e027822&t=66db16cff80243b72d39bcdd'))
        self.btnVisitRoadmap.installEventFilter(OpacityEventFilter(self.btnVisitRoadmap, enterOpacity=0.7))

        self.wdgTasks = QWidget()
        vbox(self.wdgTasks)

        self.wdgLoading = QWidget()
        vbox(self.wdgLoading, 0, 0)
        self.centerWdg.layout().addWidget(group(self.lblLastUpdated, self.btnVisitRoadmap),
                                          alignment=Qt.AlignmentFlag.AlignRight)
        self.centerWdg.layout().addWidget(self.wdgLoading)
        self.centerWdg.layout().addWidget(self.wdgTasks)
        self.centerWdg.layout().addWidget(vspacer())
        self.wdgLoading.setHidden(True)

    @overrides
    def showEvent(self, event: QShowEvent):
        super().showEvent(event)

        if self._downloading:
            return

        if self._last_fetched is None or (
                datetime.datetime.now() - self._last_fetched).total_seconds() > self.DOWNLOAD_THRESHOLD_SECONDS:
            self._handle_downloading_status(True)
            self._download_data()

    def _download_data(self):
        clear_layout(self.wdgTasks)
        result = JsonDownloadResult()
        runnable = JsonDownloadWorker("https://raw.githubusercontent.com/plotlyst/feed/refs/heads/main/plus.json",
                                      result)
        result.finished.connect(self._handle_downloaded_data)
        result.failed.connect(self._handle_download_failure)
        self._thread_pool.start(runnable)

    def _handle_downloaded_data(self, data):
        self._board: Board = Board.from_dict(data)

        statuses = {}
        for status in self._board.statuses:
            statuses[str(status.id)] = status

        toolbar = QWidget()
        hbox(toolbar)
        btnAll = push_btn(IconRegistry.from_name('msc.debug-stackframe-dot'), text='All',
                          properties=['secondary-selector', 'transparent-rounded-bg-on-hover'], checkable=True)
        btnAll.clicked.connect(self._displayAll)
        btnAll.setChecked(True)
        btnPlanned = push_btn(IconRegistry.from_name('fa5.calendar-alt'), text='Planned',
                              properties=['secondary-selector', 'transparent-rounded-bg-on-hover'], checkable=True)
        btnPlanned.clicked.connect(self._displayPlanned)
        btnCompleted = push_btn(IconRegistry.from_name('fa5s.check'), text='Completed',
                                properties=['secondary-selector', 'transparent-rounded-bg-on-hover'], checkable=True)
        btnCompleted.clicked.connect(self._displayCompleted)
        btnGroup = QButtonGroup(self)
        btnGroup.addButton(btnAll)
        btnGroup.addButton(btnPlanned)
        btnGroup.addButton(btnCompleted)

        self.wdgTasks.layout().addWidget(group(btnAll, vline(), btnPlanned, btnCompleted),
                                         alignment=Qt.AlignmentFlag.AlignLeft)
        self.wdgTasks.layout().addWidget(line())

        allCounter = 0
        plannedCounter = 0
        completedCounter = 0
        for i, task in enumerate(self._board.tasks):
            status = statuses[str(task.status_ref)]
            wdg = PlusTaskWidget(task, status, appendLine=i < len(self._board.tasks) - 1)
            self.wdgTasks.layout().addWidget(wdg)

            allCounter += 1
            if status.text == 'Completed':
                completedCounter += 1
            else:
                plannedCounter += 1

        btnAll.setText(btnAll.text() + f' ({allCounter})')
        btnPlanned.setText(btnPlanned.text() + f' ({plannedCounter})')
        btnCompleted.setText(btnCompleted.text() + f' ({completedCounter})')

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.lblLastUpdated.setText(f"Last updated: {now}")
        self._last_fetched = datetime.datetime.now()

        self._handle_downloading_status(False)

    def _handle_download_failure(self, status_code: int, message: str):
        if self._board is None:
            self.lblLastUpdated.setText("Failed to update data.")
        self._handle_downloading_status(False)

    def _handle_downloading_status(self, loading: bool):
        self._downloading = loading
        self.wdgLoading.setVisible(loading)
        if loading:
            btn = push_btn(transparent_=True)
            btn.setIconSize(QSize(128, 128))
            self.wdgLoading.layout().addWidget(btn,
                                               alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            spin(btn, PLOTLYST_SECONDARY_COLOR)
        else:
            clear_layout(self.wdgLoading)

    def _displayAll(self):
        for i in range(self.wdgTasks.layout().count()):
            wdg = self.wdgTasks.layout().itemAt(i).widget()
            if isinstance(wdg, PlusTaskWidget):
                wdg.setVisible(True)

    def _displayPlanned(self):
        for i in range(self.wdgTasks.layout().count()):
            wdg = self.wdgTasks.layout().itemAt(i).widget()
            if isinstance(wdg, PlusTaskWidget):
                wdg.setVisible(wdg.status.text == 'Planned')

    def _displayCompleted(self):
        for i in range(self.wdgTasks.layout().count()):
            wdg = self.wdgTasks.layout().itemAt(i).widget()
            if isinstance(wdg, PlusTaskWidget):
                wdg.setVisible(wdg.status.text == 'Completed')


class GenreCard(Card):
    def __init__(self, item: ChartItem, parent=None):
        super().__init__(parent)
        self.item = item
        self.setFixedSize(200, 80)
        vbox(self)

        title = IconText()
        title.setText(item.text)
        if item.icon:
            title.setIcon(IconRegistry.from_name(item.icon, PLOTLYST_SECONDARY_COLOR))

        bar = QProgressBar()
        bar.setMinimum(0)
        bar.setMaximum(100)
        bar.setValue(item.value)
        if item.value == 0:
            bar.setDisabled(True)
            translucent(title, 0.5)
        bar.setTextVisible(True)
        bar.setMaximumHeight(30)
        bar.setStyleSheet(f'''
                        QProgressBar {{
                            border: 1px solid lightgrey;
                            border-radius: 8px;
                            text-align: center;
                        }}

                        QProgressBar::chunk {{
                            background-color: {PLOTLYST_TERTIARY_COLOR};
                        }}
                    ''')
        shadow(bar)

        self.layout().addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(bar)

    @overrides
    def enterEvent(self, event: QEvent) -> None:
        pass

    @overrides
    def leaveEvent(self, event: QEvent) -> None:
        pass

    @overrides
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        pass

    @overrides
    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        pass


class SurveyResultsWidget(QWidget):
    showTiers = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        vbox(self)

        self._scroll = scroll_area(frameless=True)
        self._scroll.setProperty('relaxed-white-bg', True)
        self.centerWdg = QWidget()
        self.centerWdg.setProperty('relaxed-white-bg', True)
        vbox(self.centerWdg)
        self._scroll.setWidget(self.centerWdg)
        self.layout().addWidget(self._scroll)

    def setPatreon(self, patreon: Patreon):
        clear_layout(self.centerWdg)

        # patreon.survey.stage['Brainstorming'] = 16
        # patreon.survey.stage['Outlining and planning'] = 160
        # patreon.survey.stage['Drafting'] = 54
        # patreon.survey.stage['Developmental editing'] = 5
        # patreon.survey.stage['Line and copy-editing'] = 0

        title = label('Plotlyst Roadmap Form Results', h2=True)
        desc_text = 'Patrons can share their preferences and become an integral part of Plotlyst’s roadmap. Their answers will help shape the future direction of Plotlyst and influence upcoming releases.'
        desc_text += '\n\nThe collective results are displayed anonymously on this panel. These results depict the community-driven direction of Plotlyst.'
        desc_text += '\n\nPatrons can update their preferences at any time.'
        desc = label(
            desc_text,
            description=True, incr_font_diff=1, wordWrap=True)

        btnTiers = push_btn(IconRegistry.from_name('fa5b.patreon'), 'See Patreon tiers', transparent_=True)
        btnTiers.installEventFilter(OpacityEventFilter(btnTiers, leaveOpacity=0.7))
        btnTiers.clicked.connect(self.showTiers)

        self.centerWdg.layout().addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        self.centerWdg.layout().addWidget(desc)
        self.centerWdg.layout().addWidget(btnTiers, alignment=Qt.AlignmentFlag.AlignRight)

        stages = self._polarChart(patreon.survey.stage.items)
        panels = self._polarChart(patreon.survey.panels.items)
        newVsOld = self._pieChart(patreon.survey.new.items)
        personalization = self._pieChart(patreon.survey.personalization.items)

        self._addTitle(patreon.survey.stage)
        self.centerWdg.layout().addWidget(stages)
        self._addTitle(patreon.survey.panels)
        self.centerWdg.layout().addWidget(panels)
        self._addTitle(patreon.survey.genres)

        wdgGenres = QWidget()
        flow(wdgGenres)
        for k, item in patreon.survey.genres.items.items():
            item.text = k
            card = GenreCard(item)
            wdgGenres.layout().addWidget(card)
        self.centerWdg.layout().addWidget(wdgGenres)

        self._addTitle(patreon.survey.new)
        self.centerWdg.layout().addWidget(newVsOld)
        self._addTitle(patreon.survey.personalization)
        self.centerWdg.layout().addWidget(personalization)
        self._addTitle(patreon.survey.secondary)

        for k, item in patreon.survey.secondary.items.items():
            wdg = QWidget()
            vbox(wdg)
            margins(wdg, left=35, bottom=5, right=35)
            title = IconText()
            incr_font(title, 2)
            title.setText(k)
            if item.icon:
                title.setIcon(IconRegistry.from_name(item.icon))
            wdg.layout().addWidget(title, alignment=Qt.AlignmentFlag.AlignLeft)
            if item.description:
                wdg.layout().addWidget(label(item.description, description=True))

            bar = QProgressBar()
            bar.setMinimum(0)
            bar.setMaximum(100)
            bar.setValue(item.value)
            bar.setTextVisible(True)
            bar.setStyleSheet(f'''
                QProgressBar {{
                    border: 1px solid lightgrey;
                    border-radius: 8px;
                    text-align: center;
                }}

                QProgressBar::chunk {{
                    background-color: {PLOTLYST_TERTIARY_COLOR};
                }}
            ''')
            shadow(bar)
            wdg.layout().addWidget(bar)
            self.centerWdg.layout().addWidget(wdg)

        self.centerWdg.layout().addWidget(vspacer())

    def _polarChart(self, values: Dict[str, ChartItem]) -> ChartView:
        view = ChartView()
        chart = PolarChart()
        chart.setMinimumSize(400, 400)
        chart.setAngularRange(0, len(values.keys()))
        chart.setLogarithmicScaleEnabled(True)
        items = []
        i = 0
        for k, v in values.items():
            i += 1
            if not v.value:
                v.value = 0.1
            v.text = k
            items.append(v)
        chart.setItems(items)
        view.setChart(chart)

        return view

    def _pieChart(self, values: Dict[str, ChartItem]) -> ChartView:
        view = ChartView()
        chart = PieChart()

        items = []
        for k, v in values.items():
            if not v.value:
                v.value = 0.1
            v.text = k
            items.append(v)

        chart.setItems(items)
        view.setChart(chart)

        return view

    def _addTitle(self, result: SurveyResults):
        self.centerWdg.layout().addWidget(wrap(label(result.title, h4=True), margin_top=20))
        self.centerWdg.layout().addWidget(line())
        self.centerWdg.layout().addWidget(label(result.description, description=True, wordWrap=True))


class PriceLabel(QPushButton):
    def __init__(self, price: str, parent=None):
        super().__init__(parent)

        self.setText(f'{price}$')
        self.setStyleSheet(f'''
            background: {PLOTLYST_TERTIARY_COLOR};
            border: 1px solid {PLOTLYST_SECONDARY_COLOR};
            padding: 8px;
            border-radius: 4px;
            font-family: {app_env.serif_font()};
        ''')
        translucent(self, 0.7)


class PatreonTierSection(QWidget):
    def __init__(self, tier: PatreonTier, parent=None):
        super().__init__(parent)
        self.tier = tier
        self.lblHeader = IconText()
        self.lblHeader.setText(self.tier.name)
        if self.tier.icon:
            self.lblHeader.setIcon(IconRegistry.from_name(self.tier.icon, PLOTLYST_SECONDARY_COLOR))
        incr_font(self.lblHeader, 4)
        incr_icon(self.lblHeader, 2)
        self.lblDesc = label(self.tier.description, wordWrap=True, description=True)
        incr_font(self.lblDesc, 1)
        self.wdgPerks = frame()
        self.wdgPerks.setProperty('large-rounded', True)
        self.wdgPerks.setProperty('highlighted-bg', True)
        vbox(self.wdgPerks, margin=8)
        self.textPerks = AutoAdjustableTextEdit()
        incr_font(self.textPerks, 2)
        self.textPerks.setReadOnly(True)
        self.textPerks.setAcceptRichText(True)
        transparent(self.textPerks)
        html = '<html><ul>'
        for perk in self.tier.perks:
            html += f'<li>{perk}</li>'
        self.textPerks.setHtml(html)
        self.wdgPerks.layout().addWidget(self.textPerks)

        vbox(self)
        margins(self, top=13, bottom=13)
        self.layout().addWidget(group(self.lblHeader, spacer(), PriceLabel(self.tier.price)))
        self.layout().addWidget(line())
        self.layout().addWidget(wrap(self.lblDesc, margin_left=20))
        self.layout().addWidget(wrap(self.wdgPerks, margin_left=20, margin_right=20))
        if tier.has_roadmap_form:
            self.btnResults = push_btn(IconRegistry.from_name('fa5s.chart-pie'), 'See results', transparent_=True)
            self.btnResults.installEventFilter(OpacityEventFilter(self.btnResults, leaveOpacity=0.7))
            self.layout().addWidget(wrap(self.btnResults, margin_left=20), alignment=Qt.AlignmentFlag.AlignLeft)
        if tier.has_plotlyst_plus:
            self.btnPlus = push_btn(IconRegistry.from_name('mdi.certificate'), 'See Plotlyst Plus features',
                                    transparent_=True)
            self.btnPlus.installEventFilter(OpacityEventFilter(self.btnPlus, leaveOpacity=0.7))
            self.layout().addWidget(wrap(self.btnPlus, margin_left=20), alignment=Qt.AlignmentFlag.AlignLeft)

        if tier.has_recognition or tier.has_premium_recognition:
            wdgRecognition = frame()
            wdgRecognition.setProperty('large-rounded', True)
            wdgRecognition.setProperty('muted-bg', True)
            vbox(wdgRecognition, 10, 10)

            wdgRecognition.layout().addWidget(
                label('Recognition preview, displayed under Patrons and Knowledge Base panels:',
                      description=True),
                alignment=Qt.AlignmentFlag.AlignCenter)

            if tier.has_recognition:
                lbl = push_btn(text='Zsolt', transparent_=True, pointy_=False)
                lbl.setIcon(IconRegistry.from_name('fa5s.gem', PLOTLYST_SECONDARY_COLOR))
                lbl.clicked.connect(self._labelPreviewClicked)
            else:
                lbl = VipPatronCard(example_patron)
                lbl.setMinimumHeight(75)
            pointy(lbl)
            wdgRecognition.layout().addWidget(lbl, alignment=Qt.AlignmentFlag.AlignCenter)
            self.layout().addWidget(wdgRecognition, alignment=Qt.AlignmentFlag.AlignCenter)

    def _labelPreviewClicked(self):
        menu = MenuWidget()
        menu.addSection('Visit website of Zsolt')
        menu.addSeparator()
        menu.addAction(action('https://plotlyst.com', icon=IconRegistry.from_name('mdi.web'),
                              slot=lambda: open_url('https://plotlyst.com')))
        menu.exec(QCursor.pos())


class PatreonTiersWidget(QWidget):
    showResults = pyqtSignal()
    showPlus = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        vbox(self)
        margins(self, bottom=15)

        self._scroll = scroll_area(frameless=True)
        self._scroll.setProperty('relaxed-white-bg', True)
        self.centerWdg = QWidget()
        self.centerWdg.setProperty('relaxed-white-bg', True)
        vbox(self.centerWdg)
        self._scroll.setWidget(self.centerWdg)
        self.layout().addWidget(self._scroll)

    def setPatreon(self, patreon: Patreon):
        clear_layout(self.centerWdg)

        title = label('Patreon Tiers', h2=True)
        desc = label(
            'Plotlyst is an indie project created by a solo developer with a passion for writing and storytelling.',
            description=True, incr_font_diff=1, wordWrap=True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btnPatreon = self._joinButton()

        self.centerWdg.layout().addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        self.centerWdg.layout().addWidget(desc)
        self.centerWdg.layout().addWidget(btnPatreon, alignment=Qt.AlignmentFlag.AlignRight)

        for tier in patreon.tiers:
            section = PatreonTierSection(tier)
            self.centerWdg.layout().addWidget(section)
            if tier.has_roadmap_form:
                section.btnResults.clicked.connect(self.showResults)
            if tier.has_plotlyst_plus:
                section.btnPlus.clicked.connect(self.showPlus)

        self.centerWdg.layout().addWidget(vspacer())

    def _joinButton(self) -> QPushButton:
        btnPatreon = push_btn(IconRegistry.from_name('fa5b.patreon', RELAXED_WHITE_COLOR), text='Join Patreon',
                              properties=['positive', 'confirm'])
        btnPatreon.clicked.connect(lambda: open_url(
            'https://patreon.com/user?u=24283978&utm_medium=unknown&utm_source=join_link&utm_campaign=creatorshare_creator&utm_content=copyLink'))
        return btnPatreon


social_icons = {
    "ig": "fa5b.instagram",
    "x": "fa5b.twitter",
    "twitch": "fa5b.twitch",
    "threads": "mdi.at",
    "snapchat": "fa5b.snapchat",
    "facebook": "fa5b.facebook",
    "tiktok": "fa5b.tiktok",
    "youtube": "fa5b.youtube",
    "reddit": "fa5b.reddit",
    "linkedin": "fa5b.linkedin",
    "pinterest": "fa5b.pinterest",
    "amazon": "fa5b.amazon",
    "discord": "fa5b.discord",
    "goodreads": "fa5b.goodreads-g",
    "medium": "fa5b.medium-m",
    "patreon": "fa5b.patreon",
    "quora": "fa5b.quora",
    "steam": "fa5b.steam",
    "tumblr": "fa5b.tumblr",
    'coffee': "mdi.coffee",
}

social_descriptions = {
    "ig": "Instagram",
    "x": "X (Twitter)",
    "twitch": "Twitch",
    "threads": "Threads.net",
    "snapchat": "Snapchat",
    "facebook": "Facebook",
    "tiktok": "TikTok",
    "youtube": "Youtube",
    "reddit": "Reddit",
    "linkedin": "LinkedIn",
    "pinterest": "Pinterest",
    "amazon": "Amazon",
    "discord": "Discord",
    "goodreads": "Goodreads",
    "medium": "Medium",
    "patreon": "Patreon",
    "quora": "Quora",
    "steam": "Steam",
    "tumblr": "Tumblr",
    'coffee': "Buy me coffee",
}


class VipPatronProfile(QFrame):
    def __init__(self, patron: Patron, parent=None):
        super().__init__(parent)

        self.name = label(patron.name, h4=True)
        self.bio = label(patron.bio, description=True)

        self.setStyleSheet(f'''
                   VipPatronProfile {{
                       border: 1px solid lightgrey;
                       border-radius: 16px;
                       background-color: #F7F0F0;
                   }}''')

        vbox(self, 10, 8)
        self.layout().addWidget(self.name, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout().addWidget(self.bio, alignment=Qt.AlignmentFlag.AlignCenter)

        wdgSocials = QWidget()
        hbox(wdgSocials)
        if patron.web:
            btn = tool_btn(IconRegistry.from_name('mdi.web', 'grey'), transparent_=True, tooltip=patron.web)
            btn.clicked.connect(partial(open_url, patron.web))
            wdgSocials.layout().addWidget(btn)
            if patron.socials:
                wdgSocials.layout().addWidget(vline(color='grey'))
        for k, social in patron.socials.items():
            icon = social_icons.get(k)
            if icon:
                btn = tool_btn(IconRegistry.from_name(icon, 'grey'), transparent_=True, tooltip=social)
                btn.installEventFilter(OpacityEventFilter(btn, leaveOpacity=0.7))
                btn.clicked.connect(partial(open_url, social))
                decr_icon(btn, 2)
                wdgSocials.layout().addWidget(btn)

        self.layout().addWidget(wdgSocials, alignment=Qt.AlignmentFlag.AlignCenter)

        self.layout().addWidget(line(color=PLOTLYST_SECONDARY_COLOR))
        if patron.description:
            self.layout().addWidget(label(patron.description, description=True, wordWrap=True))

        if patron.favourites:
            favourite = IconText()
            favourite.setText('My favourite stories:')
            favourite.setIcon(IconRegistry.from_name('ei.heart', '#F18989'))
            self.layout().addWidget(favourite, alignment=Qt.AlignmentFlag.AlignLeft)
            wdg = QWidget()
            vbox(wdg)
            margins(wdg, left=20)
            lblFavourite = label(' | '.join(patron.favourites), wordWrap=True, description=True)
            wdg.layout().addWidget(lblFavourite)
            self.layout().addWidget(wdg)

        if patron.novels and any([x.title for x in patron.novels]):
            published = IconText()
            published.setText('My published books:')
            published.setIcon(IconRegistry.book_icon(PLOTLYST_SECONDARY_COLOR))
            self.layout().addWidget(published, alignment=Qt.AlignmentFlag.AlignLeft)
            wdg = QWidget()
            vbox(wdg)
            margins(wdg, left=20)
            for novel in patron.novels:
                if not novel.title:
                    continue
                btn = push_btn(IconRegistry.book_icon(), novel.title, transparent_=True, tooltip=novel.web)
                btn.installEventFilter(OpacityEventFilter(btn, 0.7))
                if novel.web:
                    btn.clicked.connect(partial(open_url, novel.web))
                wdg.layout().addWidget(btn, alignment=Qt.AlignmentFlag.AlignLeft)

            self.layout().addWidget(wdg)
            self.layout().addWidget(vspacer())


class VipPatronCard(Card):
    def __init__(self, patron: Patron, parent=None):
        super().__init__(parent)
        self.patron = patron
        vbox(self, margin=5)
        sp(self).v_max()

        self.lblName = push_btn(text=patron.name, transparent_=True, icon_resize=False)
        incr_font(self.lblName)
        self.lblName.clicked.connect(self._displayProfile)
        if patron.icon:
            try:
                self.lblName.setIcon(IconRegistry.from_name(patron.icon, PLOTLYST_SECONDARY_COLOR))
            except:  # if a new icon is not supported yet in an older version of the app
                pass

        if patron.socials:
            socialButtons = []
            for k, social in patron.socials.items():
                icon = social_icons.get(k)
                if icon:
                    btn = tool_btn(IconRegistry.from_name(icon, 'grey'), transparent_=True, icon_resize=False)
                    btn.clicked.connect(self._displayProfile)
                    decr_icon(btn, 6)
                    socialButtons.append(btn)

                if len(socialButtons) > 2:
                    break
            self.layout().addWidget(group(self.lblName, spacer(), *socialButtons, margin=0, spacing=0),
                                    alignment=Qt.AlignmentFlag.AlignLeft)
        else:
            self.layout().addWidget(self.lblName, alignment=Qt.AlignmentFlag.AlignLeft)
        self.bio = label(patron.bio, description=True, decr_font_diff=2, wordWrap=True)
        sp(self.bio).v_max()
        self.layout().addWidget(self.bio)
        if not patron.bio:
            self.bio.setHidden(True)

        self._setStyleSheet()

    @overrides
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._displayProfile()

    @overrides
    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        pass

    def refresh(self):
        self.lblName.setText(self.patron.name)
        if self.patron.icon:
            self.lblName.setIcon(IconRegistry.from_name(self.patron.icon, PLOTLYST_SECONDARY_COLOR))
        if self.patron.bio:
            self.bio.setText(self.patron.bio)
            self.bio.setVisible(True)
        else:
            self.bio.setVisible(False)

    @overrides
    def _bgColor(self, selected: bool = False) -> str:
        return '#F7F0F0'

    def _displayProfile(self):
        menu = MenuWidget()
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        wdg = VipPatronProfile(self.patron)
        menu.addWidget(wdg)
        menu.exec(QCursor.pos())


class PatronRecognitionWidget(QWidget):
    def __init__(self, patron: Patron, parent=None):
        super().__init__(parent)
        self.patron = patron
        vbox(self, 0, 0)
        margins(self, left=self.__randomMargin(), right=self.__randomMargin(), top=self.__randomMargin(),
                bottom=self.__randomMargin())

        if patron.vip:
            self.lbl = VipPatronCard(patron)
            pointy(self.lbl)
        else:
            self.lbl = push_btn(text=patron.name, transparent_=True, pointy_=False)
            if patron.icon:
                try:
                    self.lbl.setIcon(IconRegistry.from_name(patron.icon, PLOTLYST_SECONDARY_COLOR))
                except:  # if a new icon is not supported yet in an older version of the app
                    pass

            if self.patron.web:
                self.lbl.clicked.connect(self._labelClicked)
                pointy(self.lbl)

        self.layout().addWidget(self.lbl)

    def refresh(self):
        if self.patron.vip:
            self.lbl.refresh()
        else:
            self.lbl.setText(self.patron.name)
            if self.patron.icon:
                self.lbl.setIcon(IconRegistry.from_name(self.patron.icon, PLOTLYST_SECONDARY_COLOR))

    def _labelClicked(self):
        menu = MenuWidget()
        menu.addSection(f'Visit website of {self.patron.name}')
        menu.addSeparator()
        menu.addAction(action(truncate_string(self.patron.web, 50), icon=IconRegistry.from_name('mdi.web'),
                              slot=lambda: open_url(self.patron.web)))
        menu.exec(QCursor.pos())

    def __randomMargin(self) -> int:
        return random.randint(3, 10)


class PatronsWidget(QWidget):
    DOWNLOAD_THRESHOLD_SECONDS = 60 * 60 * 8  # 8 hours in seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_fetched = None
        self._downloading = False
        self._community: Optional[Community] = None
        self._thread_pool = QThreadPool()

        vbox(self)

        self._scroll = scroll_area(frameless=True)
        self._scroll.setProperty('relaxed-white-bg', True)
        self.centerWdg = QWidget()
        self.centerWdg.setProperty('relaxed-white-bg', True)
        vbox(self.centerWdg)
        self._scroll.setWidget(self.centerWdg)
        self.layout().addWidget(self._scroll)

        self.lblLastUpdated = label('', description=True, decr_font_diff=1)

        self.wdgPatrons = QWidget()
        flow(self.wdgPatrons, 10, spacing=5)

        self.wdgTopHeader = QWidget()
        hbox(self.wdgTopHeader)
        self.btnAll = push_btn(IconRegistry.from_name('ri.quill-pen-fill'), 'All writers',
                               properties=['secondary-selector', 'transparent-rounded-bg-on-hover'], checkable=True)
        self.btnAll.setChecked(True)
        self.btnArtists = push_btn(IconRegistry.from_name('fa5s.palette'), 'Artists',
                                   properties=['secondary-selector', 'transparent-rounded-bg-on-hover'], checkable=True)
        self.btnEditors = push_btn(IconRegistry.from_name('fa5s.pen-fancy'), 'Editors',
                                   properties=['secondary-selector', 'transparent-rounded-bg-on-hover'], checkable=True)
        self.btnContentCreators = push_btn(IconRegistry.from_name('mdi6.laptop-account'), 'Content Creators',
                                           properties=['secondary-selector', 'transparent-rounded-bg-on-hover'],
                                           checkable=True)

        self.btnGroup = QButtonGroup()
        self.btnGroup.addButton(self.btnAll)
        self.btnGroup.addButton(self.btnArtists)
        self.btnGroup.addButton(self.btnEditors)
        self.btnGroup.addButton(self.btnContentCreators)
        self.btnGroup.buttonClicked.connect(self._typeClicked)

        self.wdgTopHeader.layout().addWidget(spacer())
        self.wdgTopHeader.layout().addWidget(self.btnAll)
        self.wdgTopHeader.layout().addWidget(vline())
        self.wdgTopHeader.layout().addWidget(self.btnArtists)
        self.wdgTopHeader.layout().addWidget(self.btnEditors)
        self.wdgTopHeader.layout().addWidget(self.btnContentCreators)
        self.wdgTopHeader.layout().addWidget(spacer())

        self.btnVisitPatreon = push_btn(IconRegistry.from_name('fa5s.external-link-alt', 'grey'), transparent_=True,
                                        text='Visit Patreon')
        self.btnVisitPatreon.clicked.connect(lambda: open_url(
            'https://patreon.com/user?u=24283978&utm_medium=unknown&utm_source=join_link&utm_campaign=creatorshare_creator&utm_content=copyLink'))
        self.btnVisitPatreon.installEventFilter(OpacityEventFilter(self.btnVisitPatreon, enterOpacity=0.7))

        self.wdgLoading = QWidget()
        vbox(self.wdgLoading, 0, 0)
        self.centerWdg.layout().addWidget(group(self.lblLastUpdated, self.btnVisitPatreon),
                                          alignment=Qt.AlignmentFlag.AlignRight)
        self.centerWdg.layout().addWidget(label('The following writers support the development of Plotlyst', h4=True),
                                          alignment=Qt.AlignmentFlag.AlignCenter)
        self.centerWdg.layout().addWidget(self.wdgTopHeader)
        # self.centerWdg.layout().addWidget(
        #     label('The following writers support the development of Plotlyst.', description=True, incr_font_diff=1),
        #     alignment=Qt.AlignmentFlag.AlignCenter)
        self.centerWdg.layout().addWidget(self.wdgLoading)
        self.centerWdg.layout().addWidget(self.wdgPatrons)
        self.centerWdg.layout().addWidget(vspacer())
        self.wdgLoading.setHidden(True)
        self.wdgTopHeader.setHidden(True)

    @overrides
    def showEvent(self, event: QShowEvent):
        super().showEvent(event)

        if self._downloading:
            return

        if self._last_fetched is None or (
                datetime.datetime.now() - self._last_fetched).total_seconds() > self.DOWNLOAD_THRESHOLD_SECONDS:
            self._handle_downloading_status(True)
            self._download_data()

    def _download_data(self):
        clear_layout(self.wdgPatrons)

        result = JsonDownloadResult()
        runnable = JsonDownloadWorker(
            "https://raw.githubusercontent.com/plotlyst/feed/refs/heads/main/patrons.json",
            result)
        result.finished.connect(self._handle_downloaded_data)
        result.failed.connect(self._handle_download_failure)
        self._thread_pool.start(runnable)

    def _handle_downloaded_data(self, data):
        self._community: Community = Community.from_dict(data)
        random.shuffle(self._community.patrons)

        professions = {
            'artist': 0,
            'editor': 0,
            'content': 0
        }
        for patron in self._community.patrons:
            lbl = PatronRecognitionWidget(patron)
            if patron.profession:
                professions[patron.profession] += 1
            self.wdgPatrons.layout().addWidget(lbl)

        self.btnAll.setText(f'All Writers ({len(self._community.patrons)})')
        self.btnArtists.setText(f'Artists ({professions["artist"]})')
        self.btnEditors.setText(f'Editors ({professions["editor"]})')
        self.btnContentCreators.setText(f'Content Creators ({professions["content"]})')

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.lblLastUpdated.setText(f"Last updated: {now}")
        self._last_fetched = datetime.datetime.now()

        self._handle_downloading_status(False)

    def _handle_download_failure(self, status_code: int, message: str):
        if self._community is None:
            self.lblLastUpdated.setText("Failed to update data.")
        self._handle_downloading_status(False)

    def _handle_downloading_status(self, loading: bool):
        self._downloading = loading
        self.wdgLoading.setVisible(loading)
        self.wdgTopHeader.setVisible(not loading)
        if loading:
            btn = push_btn(transparent_=True)
            btn.setIconSize(QSize(128, 128))
            self.wdgLoading.layout().addWidget(btn,
                                               alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            spin(btn, PLOTLYST_SECONDARY_COLOR)
        else:
            clear_layout(self.wdgLoading)

    def _typeClicked(self):
        if self.btnArtists.isChecked():
            profession = 'artist'
        elif self.btnEditors.isChecked():
            profession = 'editor'
        elif self.btnContentCreators.isChecked():
            profession = 'content'
        else:
            profession = ''

        for i in range(self.wdgPatrons.layout().count()):
            wdg = self.wdgPatrons.layout().itemAt(i).widget()
            if isinstance(wdg, PatronRecognitionWidget):
                wdg.setVisible(wdg.patron.profession == profession)


@dataclass
class FavouriteNovelReference:
    novel: str = ''


@dataclass
class SocialReference:
    patron: Patron
    social: str
    link: str = ''


class NovelListItemWidget(ListItemWidget):
    def __init__(self, ref: FavouriteNovelReference, parent=None):
        super().__init__(ref, parent)
        self.ref = ref
        self._lineEdit.setText(ref.novel)
        self._lineEdit.setPlaceholderText('My favourite story')

    @overrides
    def _textChanged(self, text: str):
        self.ref.novel = text
        super()._textChanged(text)


class SocialListItemWidget(ListItemWidget):
    def __init__(self, ref: SocialReference, parent=None):
        super().__init__(ref, parent)
        self.ref = ref
        self._lineEdit.setText(self.ref.link)
        self._lineEdit.setPlaceholderText(social_descriptions.get(self.ref.social, 'Social link'))
        self._lineEdit.setProperty(IGNORE_CAPITALIZATION_PROPERTY, True)

    @overrides
    def _textChanged(self, text: str):
        self.ref.link = text
        self.ref.patron.socials[self.ref.social] = text
        super()._textChanged(text)


class SocialsListView(ListView):
    changed = pyqtSignal()

    def __init__(self, patron: Patron, parent=None):
        super().__init__(parent)
        self.patron = patron
        menu = MenuWidget(self._btnAdd)
        self.setAcceptDrops(False)

        wdgSocials = QWidget()
        wdgSocials.setMinimumWidth(200)
        wdgSocials.setMaximumHeight(150)
        sp(wdgSocials).v_max()
        flow(wdgSocials)
        for k, v in social_icons.items():
            btn = tool_btn(IconRegistry.from_name(v), transparent_=True, tooltip=social_descriptions.get(k, k))
            btn.clicked.connect(partial(self._socialSelected, k))
            incr_icon(btn, 4)
            wdgSocials.layout().addWidget(btn)

        menu.addWidget(wdgSocials)

    @overrides
    def _listItemWidgetClass(self):
        return SocialListItemWidget

    @overrides
    def _deleteItemWidget(self, widget: SocialListItemWidget):
        super()._deleteItemWidget(widget)
        self.patron.socials.pop(widget.ref.social)
        self._changed()

    @overrides
    def _dropped(self, mimeData: ObjectReferenceMimeData):
        wdg = super()._dropped(mimeData)
        wdg.changed.connect(self._changed)
        items: List[SocialReference] = []
        for wdg in self.widgets():
            items.append(wdg.item())
        self.patron.socials.clear()
        for ref in items:
            self.patron.socials[ref.social] = ref.link

        self._changed()

    def _socialSelected(self, social: str):
        if social in self.patron.socials.keys():
            return

        ref = SocialReference(self.patron, social)
        self.patron.socials[social] = ''
        wdg = self.addItem(ref)
        wdg.changed.connect(self._changed)

    def _changed(self):
        self.changed.emit()


class FavouriteNovelsListView(ListView):
    changed = pyqtSignal()

    def __init__(self, patron: Patron, parent=None):
        super().__init__(parent)
        self.patron = patron
        self.refs: List[FavouriteNovelReference] = []
        self._btnAdd.setText('Add new story')

    @overrides
    def _addNewItem(self):
        ref = FavouriteNovelReference()
        self.refs.append(ref)
        wdg = self.addItem(ref)
        wdg.changed.connect(self._changed)

    @overrides
    def _listItemWidgetClass(self):
        return NovelListItemWidget

    @overrides
    def _deleteItemWidget(self, widget: NovelListItemWidget):
        super()._deleteItemWidget(widget)
        self.refs.remove(widget.ref)
        self._changed()

    @overrides
    def _dropped(self, mimeData: ObjectReferenceMimeData):
        wdg = super()._dropped(mimeData)
        wdg.changed.connect(self._changed)
        items = []
        for wdg in self.widgets():
            items.append(wdg.item())
        self.refs[:] = items

        self._changed()

    def _changed(self):
        self.patron.favourites.clear()
        for ref in self.refs:
            self.patron.favourites.append(ref.novel)

        self.changed.emit()


class PublishedNovelWidget(QWidget):
    changed = pyqtSignal()

    def __init__(self, info: PatronNovelInfo, parent=None):
        super().__init__(parent)
        self.info = info
        self.title = QLineEdit()
        self.title.setPlaceholderText('Book title')
        self.title.setProperty('rounded', True)
        self.title.textEdited.connect(self._titleEdited)
        self.url = QLineEdit()
        self.url.setProperty(IGNORE_CAPITALIZATION_PROPERTY, True)
        self.url.setPlaceholderText('Link (https://...)')
        self.url.setProperty('rounded', True)
        self.url.textEdited.connect(self._linkEdited)
        vbox(self)
        margins(self, left=20)
        self.layout().addWidget(self.title)
        self.layout().addWidget(self.url)

    def _titleEdited(self, title: str):
        self.info.title = title

        self.changed.emit()

    def _linkEdited(self, link: str):
        self.info.web = link

        self.changed.emit()


class PublishedNovelListWidget(QWidget):
    def __init__(self, patron: Patron, parent=None):
        super().__init__(parent)
        self.patron = patron

        self.novel1 = PublishedNovelWidget(self.patron.novels[0])
        self.novel2 = PublishedNovelWidget(self.patron.novels[1])
        self.novel3 = PublishedNovelWidget(self.patron.novels[2])

        vbox(self, spacing=8)
        margins(self, left=10)
        self.layout().addWidget(label('Book 1:'))
        self.layout().addWidget(self.novel1)
        self.layout().addWidget(label('Book 2:'))
        self.layout().addWidget(self.novel2)
        self.layout().addWidget(label('Book 3:'))
        self.layout().addWidget(self.novel3)


class PatronRecognitionBuilderPopup(PopupDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.patron = Patron('My name', web='https://plotlyst.com')
        self.patronVip = Patron('My name', vip=True, web='https://plotlyst.com', novels=[
            PatronNovelInfo(''), PatronNovelInfo(''), PatronNovelInfo('')
        ])

        desc = 'Patrons can gain recognition in Plotlyst.'
        desc += ' If you subscribed to my page, you should have received a form to upload your information. To make the process easier, you can edit your info here and then export.'
        self.lblDesc = label(
            desc,
            description=True, wordWrap=True)
        sp(self.lblDesc).v_max()

        self.tabWidget = QTabWidget()
        self.tabWidget.setProperty('relaxed-white-bg', True)
        self.tabWidget.setProperty('centered', True)
        self.tabMain = QWidget()
        self.tabMain.setProperty('muted-bg', True)
        vbox(self.tabMain, 10, 10)
        self.tabProfile = QWidget()
        self.tabProfile.setProperty('muted-bg', True)
        vbox(self.tabProfile, 10, 10)
        self.tabExport = QWidget()
        self.tabExport.setProperty('muted-bg', True)
        vbox(self.tabExport, 10, 10)

        self.tabWidget.addTab(self.tabMain, IconRegistry.from_name('fa5s.hand-holding-heart'),
                              'Basic info')
        self.tabWidget.addTab(self.tabProfile, IconRegistry.from_name('ri.vip-diamond-fill'), 'VIP Profile')
        self.tabWidget.addTab(self.tabExport, IconRegistry.from_name('mdi6.export-variant'), 'Export')

        self.textJson = QTextBrowser()
        self.btnCopy = push_btn(IconRegistry.from_name('fa5.copy', RELAXED_WHITE_COLOR), 'Copy to clipboard',
                                properties=['positive', 'confirm'])
        self.btnCopy.clicked.connect(self._copyJson)
        self.lblCopied = CopiedTextMessage()
        self.tabExport.layout().addWidget(group(self.lblCopied, self.btnCopy, margin=0),
                                          alignment=Qt.AlignmentFlag.AlignRight)
        self.tabExport.layout().addWidget(
            label("Copy this text to the form you've received on Patreon", description=True, decr_font_diff=1))
        self.tabExport.layout().addWidget(self.textJson)

        self.btnArtist = SmallToggleButton()
        self.btnEditor = SmallToggleButton()
        self.btnContentCreator = SmallToggleButton()
        self.btnTypeGroup = ExclusiveOptionalButtonGroup()
        self.btnTypeGroup.addButton(self.btnArtist)
        self.btnTypeGroup.addButton(self.btnEditor)
        self.btnTypeGroup.addButton(self.btnContentCreator)
        self.btnTypeGroup.buttonClicked.connect(self._typeChanged)

        self.wdgType = QWidget()
        hbox(self.wdgType, 0, 0)
        self.wdgType.layout().addWidget(spacer())
        self.wdgType.layout().addWidget(icon_text('fa5s.palette', "I'm an Artist"))
        self.wdgType.layout().addWidget(self.btnArtist)
        self.wdgType.layout().addWidget(spacer())
        self.wdgType.layout().addWidget(icon_text('fa5s.pen-fancy', "I'm an Editor"))
        self.wdgType.layout().addWidget(self.btnEditor)
        self.wdgType.layout().addWidget(spacer())
        self.wdgType.layout().addWidget(icon_text('mdi6.laptop-account', "I'm a Content Creator"))
        self.wdgType.layout().addWidget(self.btnContentCreator)
        self.wdgType.layout().addWidget(spacer())

        self.lineName = self.__lineedit('Name and icon', iconEditable=True)
        self.lineName.setIcon(IconRegistry.icons_icon('grey'))
        self.lineName.lineEdit.textEdited.connect(self._nameEdited)
        self.lineName.iconChanged.connect(self._iconChanged)
        self.nameFrame = self.__framed(self.lineName)

        self.wdgGenre = QWidget()
        hbox(self.wdgGenre)
        self.cbGenre = QComboBox()
        self.cbGenre.setMaxVisibleItems(15)
        self.cbGenre.currentTextChanged.connect(self._genreChanged)
        self.cbGenre.addItem('')
        self.cbGenre.addItem('Fantasy')
        self.cbGenre.addItem('Sci-Fi')
        self.cbGenre.addItem("Romance")
        self.cbGenre.addItem("Mystery")
        self.cbGenre.addItem("Action or Adventure")
        self.cbGenre.addItem("Thriller/Suspense")
        self.cbGenre.addItem("Horror")
        self.cbGenre.addItem("Crime")
        self.cbGenre.addItem("Caper")
        self.cbGenre.addItem("Coming of Age")
        self.cbGenre.addItem("Cozy")
        self.cbGenre.addItem("Historical Fiction")
        self.cbGenre.addItem("War")
        self.cbGenre.addItem("Western")
        self.cbGenre.addItem("Upmarket")
        self.cbGenre.addItem("Literary Fiction")
        self.cbGenre.addItem("Society")
        self.cbGenre.addItem("Memoir")
        self.cbGenre.addItem("Children's Books")
        self.cbGenre.addItem("Slice of Life")
        self.cbGenre.addItem("Comedy")
        self.cbGenre.addItem("Contemporary")

        self.wdgGenre.layout().addWidget(label('Genre:'))
        self.wdgGenre.layout().addWidget(self.cbGenre)
        self.wdgGenre.layout().addWidget(spacer())

        self.lineWebsite = self.__lineedit('Website (https://...)')
        self.lineWebsite.lineEdit.textEdited.connect(self._websiteEdited)
        self.lineWebsite.lineEdit.setProperty(IGNORE_CAPITALIZATION_PROPERTY, True)
        self.websiteFrame = self.__framed(self.lineWebsite)
        hintWebsite = HintButton()
        hintWebsite.setHint(
            'Users will be able to click on your Patron label and visit your website.')
        self.websiteFrame.layout().addWidget(hintWebsite, alignment=Qt.AlignmentFlag.AlignRight)

        self.lineBio = self.__lineedit('Bio', iconEditable=False)
        self.lineBio.lineEdit.textEdited.connect(self._bioEdited)
        self.bioFrame = self.__framed(self.lineBio)

        self.wdgPreview = QWidget()
        hbox(self.wdgPreview)
        self.patronRecognition = PatronRecognitionWidget(self.patron)
        self.framePatron = self.__framed(self.patronRecognition, margin=5)
        self.patronVipRecognition = PatronRecognitionWidget(self.patronVip)
        self.frameVipPatron = self.__framed(self.patronVipRecognition, margin=5)
        self.patronLbl = label('Preview:')
        self.patronVipLbl = label('VIP Preview:')

        self.wdgPreview.layout().addWidget(spacer())
        self.wdgPreview.layout().addWidget(self.patronLbl)
        self.wdgPreview.layout().addWidget(self.framePatron)
        self.wdgPreview.layout().addWidget(self.patronVipLbl)
        self.wdgPreview.layout().addWidget(self.frameVipPatron)
        self.wdgPreview.layout().addWidget(spacer())

        self.patronVipLbl.setHidden(True)
        self.frameVipPatron.setHidden(True)

        self.tabMain.layout().addWidget(self.wdgType)
        self.tabMain.layout().addWidget(self.nameFrame)
        self.tabMain.layout().addWidget(self.websiteFrame)
        self.tabMain.layout().addWidget(self.wdgGenre)
        self.tabMain.layout().addWidget(vspacer())

        self.lineDescription = self.__lineedit('More detailed description', iconEditable=False)
        self.lineDescription.lineEdit.textEdited.connect(self._descEdited)
        self.descFrame = self.__framed(self.lineDescription)

        self.listFavouriteNovels = FavouriteNovelsListView(self.patronVip)
        self.listFavouriteNovels.setProperty('bg', True)
        self.listFavouriteNovels.changed.connect(self._updateJson)

        self.socialsListView = SocialsListView(self.patronVip)
        self.socialsListView.setProperty('bg', True)
        self.socialsListView.changed.connect(self._socialsChanged)

        self.publishedNovels = PublishedNovelListWidget(self.patronVip)
        self.publishedNovels.novel1.changed.connect(self._updateJson)
        self.publishedNovels.novel2.changed.connect(self._updateJson)
        self.publishedNovels.novel3.changed.connect(self._updateJson)

        self.profileScroll = scroll_area(frameless=True)
        self.profileScroll.setProperty('muted-bg', True)
        self.wdgProfile = QWidget()
        self.profileScroll.setWidget(self.wdgProfile)
        self.wdgProfile.setProperty('muted-bg', True)
        vbox(self.wdgProfile, 0, 5)

        self.wdgProfile.layout().addWidget(self.bioFrame)
        self.wdgProfile.layout().addWidget(self.descFrame)
        self.wdgProfile.layout().addWidget(icon_text('fa5s.heart', 'Favourite stories'),
                                           alignment=Qt.AlignmentFlag.AlignLeft)
        self.wdgProfile.layout().addWidget(self.listFavouriteNovels)
        self.wdgProfile.layout().addWidget(icon_text('mdi.camera-account', 'Socials'),
                                           alignment=Qt.AlignmentFlag.AlignLeft)
        self.wdgProfile.layout().addWidget(self.socialsListView)
        self.wdgProfile.layout().addWidget(icon_text('fa5s.book', 'Published novels (max 3)'),
                                           alignment=Qt.AlignmentFlag.AlignLeft)
        self.wdgProfile.layout().addWidget(self.publishedNovels)
        self.wdgProfile.layout().addWidget(vspacer())
        self.tabProfile.layout().addWidget(self.profileScroll)

        self.btnCancel = push_btn(text='Close', properties=['confirm', 'cancel'])
        self.btnCancel.clicked.connect(self.reject)

        self.frame.layout().addWidget(self.lblDesc)
        self.frame.layout().addWidget(self.wdgPreview)
        self.frame.layout().addWidget(self.tabWidget)
        self.frame.layout().addWidget(self.btnCancel, alignment=Qt.AlignmentFlag.AlignRight)

        self.tabWidget.currentChanged.connect(self._tabChanged)

    def display(self):
        self.exec()

    def _tabChanged(self, index: int):
        wdg = self.tabWidget.currentWidget()
        if wdg is self.tabMain:
            self.patronLbl.setVisible(True)
            self.framePatron.setVisible(True)
            self.patronVipLbl.setVisible(False)
            self.frameVipPatron.setVisible(False)
        elif wdg is self.tabProfile:
            self.patronLbl.setVisible(False)
            self.framePatron.setVisible(False)
            self.patronVipLbl.setVisible(True)
            self.frameVipPatron.setVisible(True)

    def _nameEdited(self, name: str):
        self.patron.name = name
        self.patronVip.name = name

        self.patronRecognition.refresh()
        self.patronVipRecognition.refresh()

        self._updateJson()

    def _genreChanged(self, genre: str):
        self.patron.genre = genre
        self.patronVip.genre = genre

        self._updateJson()

    def _typeChanged(self):
        if self.btnTypeGroup.checkedButton() is None:
            profession = ''
        elif self.btnTypeGroup.checkedButton() is self.btnArtist:
            profession = 'artist'
        elif self.btnTypeGroup.checkedButton() is self.btnEditor:
            profession = 'editor'
        elif self.btnTypeGroup.checkedButton() is self.btnContentCreator:
            profession = 'content'
        else:
            return

        self.patron.profession = profession
        self.patronVip.profession = profession

        self._updateJson()

    def _iconChanged(self, name: str):
        self.patron.icon = name
        self.patronVip.icon = name

        self.patronRecognition.refresh()
        self.patronVipRecognition.refresh()

        self._updateJson()

    def _websiteEdited(self, web: str):
        self.patron.web = web
        self.patronVip.web = web

        self.patronVipRecognition.refresh()

        self._updateJson()

    def _bioEdited(self, bio: str):
        self.patron.bio = bio
        self.patronVip.bio = bio

        self.patronVipRecognition.refresh()

        self._updateJson()

    def _descEdited(self, desc: str):
        self.patron.description = desc
        self.patronVip.description = desc

        self._updateJson()

    def _socialsChanged(self):
        self._updateJson()
        self.patronVipRecognition.refresh()

    def _updateJson(self):
        self.textJson.setText(self.patronVip.to_json())

    def _copyJson(self):
        QGuiApplication.clipboard().setText(self.textJson.toPlainText())
        self.lblCopied.trigger()

    def __lineedit(self, placeholder: str, iconEditable=False) -> DecoratedLineEdit:
        editor = DecoratedLineEdit(iconEditable=iconEditable, autoAdjustable=False, pickIconColor=False)
        editor.lineEdit.setPlaceholderText(placeholder)
        editor.lineEdit.setMinimumWidth(500)
        incr_font(editor.lineEdit, 3)

        return editor

    def __framed(self, editor: QWidget, margin: int = 10) -> QFrame:
        _frame = frame()
        hbox(_frame, margin, 10).addWidget(editor, alignment=Qt.AlignmentFlag.AlignLeft)
        _frame.setProperty('relaxed-white-bg', True)
        _frame.setProperty('large-rounded', True)

        return _frame


class PlotlystPlusWidget(QWidget):
    DOWNLOAD_THRESHOLD_SECONDS = 60 * 60 * 8  # 8 hours in seconds

    def __init__(self, parent=None):
        super().__init__(parent)
        hbox(self)
        self._patreon: Optional[Patreon] = None
        self._last_fetched = None
        self._downloading = False

        self.tabWidget = QTabWidget()
        self.tabWidget.setProperty('centered', True)
        self.tabWidget.setProperty('large-rounded', True)
        self.tabWidget.setProperty('relaxed-white-bg', True)
        self.tabWidget.setMaximumWidth(1000)
        self.tabReport = QWidget()
        vbox(self.tabReport, 10, 5)
        self.tabPatreon = QWidget()
        vbox(self.tabPatreon, 10, 5)
        self.tabPatrons = QWidget()
        vbox(self.tabPatrons, 10, 5)

        self.tabWidget.addTab(self.tabPatreon, IconRegistry.from_name('fa5b.patreon', color_on=PLOTLYST_MAIN_COLOR),
                              'Patreon')
        self.tabWidget.addTab(self.tabReport, IconRegistry.from_name('mdi.crystal-ball', color_on=PLOTLYST_MAIN_COLOR),
                              'Vision')
        self.tabWidget.addTab(self.tabPatrons, IconRegistry.from_name('msc.organization', color_on=PLOTLYST_MAIN_COLOR),
                              'Patrons')

        self.layout().addWidget(self.tabWidget)

        self.lblVisionLastUpdated = label('', description=True, decr_font_diff=1)
        self.wdgLoading = QWidget()
        vbox(self.wdgLoading, 0, 0)
        self._patreonWdg = PatreonTiersWidget()
        self._patreonWdg.showResults.connect(lambda: self.tabWidget.setCurrentWidget(self.tabReport))
        self._surveyWdg = SurveyResultsWidget()
        self._surveyWdg.showTiers.connect(lambda: self.tabWidget.setCurrentWidget(self.tabPatreon))

        self.tabReport.layout().addWidget(self.lblVisionLastUpdated, alignment=Qt.AlignmentFlag.AlignRight)
        self.tabReport.layout().addWidget(self._surveyWdg)
        self.tabReport.layout().addWidget(self.wdgLoading)
        self.wdgLoading.setHidden(True)

        self._patronsWidget = PatronsWidget()
        self.tabPatrons.layout().addWidget(self._patronsWidget)

        self.tabPatreon.layout().addWidget(self._patreonWdg)

        self._thread_pool = QThreadPool()

    @overrides
    def showEvent(self, event: QShowEvent):
        super().showEvent(event)

        if self._downloading:
            return

        if self._last_fetched is None or (
                datetime.datetime.now() - self._last_fetched).total_seconds() > self.DOWNLOAD_THRESHOLD_SECONDS:
            self._handle_downloading_patreon_status(True)
            self._download_data()

    def _download_data(self):
        result = JsonDownloadResult()
        runnable = JsonDownloadWorker("https://raw.githubusercontent.com/plotlyst/feed/refs/heads/main/patreon.json",
                                      result)
        result.finished.connect(self._handle_downloaded_patreon_data)
        result.failed.connect(self._handle_download_patreon_failure)
        self._thread_pool.start(runnable)

    def _handle_downloaded_patreon_data(self, data):
        self._handle_downloading_patreon_status(False)

        self._patreon = Patreon.from_dict(data)
        self._surveyWdg.setPatreon(self._patreon)
        self._patreonWdg.setPatreon(self._patreon)

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        self.lblVisionLastUpdated.setText(f"Last updated: {now}")
        self._last_fetched = datetime.datetime.now()

    def _handle_download_patreon_failure(self, status_code: int, message: str):
        if self._patreon is None:
            self.lblVisionLastUpdated.setText("Failed to update data.")
        self._handle_downloading_patreon_status(False)

    def _handle_downloading_patreon_status(self, loading: bool):
        self._downloading = loading
        set_tab_enabled(self.tabWidget, self.tabPatreon, not loading)
        self.wdgLoading.setVisible(loading)
        if loading:
            btn = push_btn(transparent_=True)
            btn.setIconSize(QSize(128, 128))
            self.wdgLoading.layout().addWidget(btn,
                                               alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
            spin(btn, PLOTLYST_SECONDARY_COLOR)
        else:
            clear_layout(self.wdgLoading)
