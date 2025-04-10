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
from abc import abstractmethod
from functools import partial
from typing import Optional, Any, Tuple, List

import emoji
import qtanim
from PyQt6.QtCharts import QChartView
from PyQt6.QtCore import pyqtProperty, QSize, Qt, QPoint, pyqtSignal, QRectF, QTimer, QEvent, QPointF, QObject
from PyQt6.QtGui import QPainter, QShowEvent, QColor, QPaintEvent, QBrush, QKeyEvent, QIcon, QRadialGradient, \
    QPen
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QPushButton, QWidget, QLabel, QToolButton, QSizePolicy, QTextBrowser, QFrame, QDialog, \
    QApplication, QTimeEdit, QAbstractSpinBox, QDateTimeEdit
from overrides import overrides
from qthandy import spacer, incr_font, bold, transparent, vbox, incr_icon, pointy, hbox, busy, italic, decr_font, \
    margins, translucent, sp, decr_icon
from qthandy.filter import OpacityEventFilter
from qtmenu import MenuWidget

from plotlyst.common import PLOTLYST_TERTIARY_COLOR, RELAXED_WHITE_COLOR, DEFAULT_PREMIUM_LINK, \
    PLOTLYST_SECONDARY_COLOR, PLACEHOLDER_TEXT_COLOR
from plotlyst.core.help import mid_revision_scene_structure_help
from plotlyst.core.template import Role
from plotlyst.core.text import wc
from plotlyst.env import app_env
from plotlyst.event.core import emit_global_event
from plotlyst.events import ShowRoadmapEvent
from plotlyst.resources import resource_registry
from plotlyst.view.common import emoji_font, insert_before_the_end, \
    ButtonPressResizeEventFilter, restyle, label, frame, tool_btn, push_btn, action, open_url, fade_in, wrap
from plotlyst.view.icons import IconRegistry
from plotlyst.view.layout import group
from plotlyst.view.widget.preview import preview_button


class ChartView(QChartView):
    def __init__(self, parent=None):
        super(ChartView, self).__init__(parent)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)

    @overrides
    def wheelEvent(self, event: 'QGraphicsSceneWheelEvent') -> None:
        event.ignore()

        return super(ChartView, self).wheelEvent(event)


class Subtitle(QWidget):
    def __init__(self, parent=None, title: str = '', description: str = '', icon: str = '', iconColor: str = 'black'):
        super(Subtitle, self).__init__(parent)
        vbox(self, margin=0, spacing=0)
        self.lblTitle = QLabel(title, self)
        self.icon = QToolButton(self)
        transparent(self.icon)
        self.lblDescription = QLabel(description, self)
        bold(self.lblTitle)
        incr_font(self.lblTitle)
        self._btnHint: Optional[HintButton] = None

        self._iconName: str = icon
        self._iconColor: str = iconColor
        self._descSpacer = spacer(20)

        self.lblDescription.setProperty('description', True)
        self.lblDescription.setWordWrap(True)
        self.lblDescription.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        if app_env.is_mac():
            incr_font(self.lblDescription, 2)
        self._top = group(self.icon, self.lblTitle, spacer(), parent=self)
        self.layout().addWidget(self._top)
        self.layout().addWidget(group(self._descSpacer, self.lblDescription, parent=self))

    def setIconName(self, icon: str, color: str = 'black'):
        self._iconName = icon
        self._iconColor = color

    @pyqtProperty(str)
    def title(self):
        return self.lblTitle.text()

    @title.setter
    def title(self, value):
        self.lblTitle.setText(value)

    def setTitle(self, value):
        self.lblTitle.setText(value)

    def setDescription(self, value):
        self.lblDescription.setText(value)

    def setHint(self, hint: str):
        if not self._btnHint:
            self._btnHint = HintButton(self)
            self._top.layout().addWidget(self._btnHint)

        self._btnHint.setHint(hint)

    @overrides
    def showEvent(self, event: QShowEvent) -> None:
        if not self.lblTitle.text():
            self.lblTitle.setText(self.property('title'))
        if not self.lblDescription.text():
            desc = self.property('description')
            if desc:
                self.lblDescription.setText(desc)
            else:
                self.lblDescription.setHidden(True)
        if not self._iconName:
            self._iconName = self.property('icon')

        if self._iconName:
            self.icon.setIcon(IconRegistry.from_name(self._iconName, self._iconColor))
            self._descSpacer.setMaximumWidth(20)
        else:
            self.icon.setHidden(True)
            self._descSpacer.setMaximumWidth(5)

    def addWidget(self, widget: QWidget):
        insert_before_the_end(self._top, widget, leave=1 if self._btnHint is None else 2)


class Emoji(QLabel):
    def __init__(self, parent=None, emoji: str = ''):
        super(Emoji, self).__init__(parent)
        self._emoji = emoji
        self._emojiFont = emoji_font()

        self.setFont(self._emojiFont)

        self.setMaximumWidth(30)

    @overrides
    def showEvent(self, event: QShowEvent) -> None:
        if self.text():
            return
        emoji_name = self._emoji if self._emoji else self.property('emoji')
        if not emoji_name:
            return

        if emoji_name.startswith(':'):
            self.setText(emoji.emojize(emoji_name))
        else:
            self.setText(emoji.emojize(f':{emoji_name}:'))


class WordsDisplay(QLabel):
    def __init__(self, parent=None):
        super(WordsDisplay, self).__init__(parent)
        self._text = ''
        self.setText(self._text)

    def calculateWordCount(self, text: str):
        count = wc(text)
        self.setWordCount(count)

    def setNightModeEnabled(self, enabled: bool):
        self.setProperty('night-mode-secondary', enabled)
        restyle(self)

    def setWordCount(self, count: int):
        if count:
            self._text = f'<html><b>{count:,}</b> word{"s" if count > 1 else ""}'
            self.setText(self._text)
        else:
            self._text = ''
            self.clear()

    def calculateSecondaryWordCount(self, text: str):
        if text:
            self.setSecondaryWordCount(wc(text))
        else:
            self.setText(self._text)

    def setSecondaryWordCount(self, count: int):
        if count:
            self.setText(f'{count:,} of {self._text}')
        else:
            self.setText(self._text)

    def clearSecondaryWordCount(self):
        self.setText(self._text)


class _AbstractRoleIcon(QPushButton):
    def __init__(self, parent=None):
        super(_AbstractRoleIcon, self).__init__(parent)
        transparent(self)


class MajorRoleIcon(_AbstractRoleIcon):
    def __init__(self, parent=None):
        super(MajorRoleIcon, self).__init__(parent)
        self.setIcon(IconRegistry.major_character_icon())


class SecondaryRoleIcon(_AbstractRoleIcon):
    def __init__(self, parent=None):
        super(SecondaryRoleIcon, self).__init__(parent)
        self.setIcon(IconRegistry.secondary_character_icon())


class MinorRoleIcon(_AbstractRoleIcon):
    def __init__(self, parent=None):
        super(MinorRoleIcon, self).__init__(parent)
        self.setIcon(IconRegistry.minor_character_icon())


class RoleIcon(_AbstractRoleIcon):

    def setRole(self, role: Role, showText: bool = False):
        if role.icon:
            self.setIcon(IconRegistry.from_name(role.icon, role.icon_color))
        if showText:
            self.setText(role.text)
            self.setStyleSheet(self.styleSheet() + f'QPushButton {{color: {role.icon_color};}}')


class _AbstractIcon:
    def __init__(self):
        self._iconName: str = ''
        self._iconColor: str = 'black'

    @pyqtProperty(str)
    def iconName(self):
        return self._iconName

    @iconName.setter
    def iconName(self, value: str):
        self.setIconName(value)
        self._iconName = value
        self._setIcon()

    def setIconName(self, value: str):
        self._iconName = value
        self._setIcon()

    @pyqtProperty(str)
    def iconColor(self):
        return self._iconColor

    @iconColor.setter
    def iconColor(self, value):
        self._iconColor = value
        self._setIcon()

    @abstractmethod
    def _setIcon(self):
        pass


class Icon(QToolButton, _AbstractIcon):
    def __init__(self, parent=None):
        super(Icon, self).__init__(parent)
        transparent(self)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    @overrides
    def _setIcon(self):
        if self._iconName:
            self.setIcon(IconRegistry.from_name(self._iconName, self._iconColor))


class IconText(QPushButton, _AbstractIcon):
    def __init__(self, parent=None):
        super(IconText, self).__init__(parent)
        transparent(self)
        self.setIconSize(QSize(20, 20))
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    @overrides
    def _setIcon(self):
        if self._iconName:
            self.setIcon(IconRegistry.from_name(self._iconName, self._iconColor))


class HintButton(QToolButton):
    def __init__(self, parent=None):
        super(HintButton, self).__init__(parent)
        self.setIcon(IconRegistry.general_info_icon())
        pointy(self)
        transparent(self)
        incr_icon(self)
        self.installEventFilter(OpacityEventFilter(self, leaveOpacity=0.6, enterOpacity=0.9))
        self.installEventFilter(ButtonPressResizeEventFilter(self))
        self._menu: Optional[MenuWidget] = None

        self._hint: str = ''

    def setHint(self, hint: str):
        if not self.menu():
            self._menu = MenuWidget(self)
            self._menu.aboutToShow.connect(self._beforeShow)

        self._hint = hint

    def _beforeShow(self):
        if self._menu.isEmpty():
            textedit = QTextBrowser()
            textedit.setText(self._hint)
            incr_font(textedit, 4)
            self._menu.addWidget(textedit)


class IdleWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

    @overrides
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(PLOTLYST_TERTIARY_COLOR), Qt.BrushStyle.Dense5Pattern))
        painter.drawRect(event.rect())


class OverlayWidget(QFrame):
    def __init__(self, parent, alpha: int = 125):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet(f"background-color: rgba(0, 0, 0, {alpha});")
        self.setFixedSize(self.parent().size())

    @staticmethod
    def getActiveWindowOverlay(alpha: int = 125) -> 'OverlayWidget':
        window = QApplication.activeWindow()
        overlay = OverlayWidget(window, alpha)
        return overlay


class MenuOverlayEventFilter(QObject):
    def __init__(self, menu: MenuWidget):
        super().__init__(menu)
        self._overlay: Optional[OverlayWidget] = None
        menu.aboutToShow.connect(self._aboutToShowMenu)
        menu.aboutToHide.connect(self._aboutToHideMenu)

    def _aboutToShowMenu(self):
        self._overlay = OverlayWidget.getActiveWindowOverlay(alpha=75)
        self._overlay.show()

    def _aboutToHideMenu(self):
        if self._overlay:
            self._overlay.hide()
            self._overlay = None


class StageRecommendationBadge(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        hbox(self)
        self.setProperty('revision-badge', True)
        self.label = label('Recommended stage: Mid-revision', color='#622675')
        self.info = HintButton()
        self.info.setHint(mid_revision_scene_structure_help)

        self.layout().addWidget(self.label)
        self.layout().addWidget(self.info)


class PopupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        vbox(self)
        self.frame = frame()
        self.frame.setProperty('white-bg', True)
        self.frame.setProperty('large-rounded', True)
        vbox(self.frame, 15, 10)
        self.layout().addWidget(self.frame)

        self.btnReset = tool_btn(IconRegistry.close_icon('grey'), tooltip='Cancel', transparent_=True)
        self.btnReset.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btnReset.setIconSize(QSize(12, 12))
        self.btnReset.clicked.connect(self.reject)

    @overrides
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.reject()

    @classmethod
    def popup(cls, *args, **kwargs) -> Any:
        override_cursor = None
        if QApplication.overrideCursor():
            override_cursor = QApplication.overrideCursor()
            QApplication.restoreOverrideCursor()
        dialog = cls(*args, **kwargs)
        window = QApplication.activeWindow()

        if window and window.size().height() < 768:
            dialog.frame.layout().setSpacing(3)
            margins(dialog.frame, bottom=5, top=5)

        if window:
            overlay = OverlayWidget(window)
            overlay.show()
        else:
            overlay = None

        if window:
            dialog.move(window.frameGeometry().center() - QPoint(dialog.sizeHint().width() // 2,
                                                                 dialog.sizeHint().height() // 2))

        try:
            return dialog.display()
        finally:
            if overlay is not None:
                overlay.setHidden(True)
            if override_cursor:
                QApplication.setOverrideCursor(override_cursor)

    def _adjustedSize(self, percentWidth: float, percentHeight: float, minWidth: int, minHeight: int) -> QSize:
        window = QApplication.activeWindow()
        if window:
            size = QSize(int(window.size().width() * percentWidth), int(window.size().height() * percentHeight))
        else:
            return QSize(minWidth, minHeight)

        size.setWidth(max(size.width(), minWidth))
        size.setHeight(max(size.height(), minHeight))

        return size


class LazyWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._initialized = False

    def refresh(self):
        self._initialized = True

    @overrides
    def showEvent(self, _: QShowEvent) -> None:
        if not self._initialized:
            self.__refreshOnShow()

    @busy
    def __refreshOnShow(self):
        self.refresh()


def dash_icon() -> QToolButton:
    btn = QToolButton()
    transparent(btn)
    btn.setIcon(IconRegistry.from_name('msc.dash'))
    return btn


class TruitySourceWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        ref = push_btn(text='Source: truity.com', properties=['transparent', 'no-menu'])
        italic(ref)
        decr_font(ref)
        ref_menu = MenuWidget(ref)
        ref_menu.addSection('Browse personality types and tests on truity')
        ref_menu.addSeparator()
        ref_menu.addAction(action('Visit truity.com', IconRegistry.from_name('fa5s.external-link-alt'),
                                  slot=lambda: open_url('https://www.truity.com/')))
        ref.installEventFilter(OpacityEventFilter(ref, 0.8, 0.5))

        hbox(self).addWidget(ref)


class DragIcon(Icon):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(IconRegistry.hashtag_icon('grey'))
        self.setIconSize(QSize(14, 14))
        self.setCursor(Qt.CursorShape.OpenHandCursor)


class DotsDragIcon(Icon):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(IconRegistry.from_name('ph.dots-six-vertical-bold', 'grey'))
        self.setIconSize(QSize(18, 18))
        self.setCursor(Qt.CursorShape.OpenHandCursor)


class HeaderColumn(QPushButton):
    def __init__(self, header: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f'''
            QPushButton {{
                background: #622675;
                padding: 4px;
                border-right: 1px solid #f8f0fa;
                color: #f8f0fa;
            }}
        ''')
        self.setText(header)


class ArrowButton(QToolButton):
    stateChanged = pyqtSignal(int)
    stateReset = pyqtSignal()

    STATE_MAX: int = 3

    def __init__(self, edge: Qt.Edge, readOnly: bool = False, parent=None):
        super().__init__(parent)
        self._state: int = 0
        self._edge = edge
        if edge == Qt.Edge.RightEdge:
            self._icons = ['fa5s.arrow-right', 'fa5s.arrow-right', 'fa5s.arrow-left', 'fa5s.arrows-alt-h']
        elif edge == Qt.Edge.BottomEdge:
            self._icons = ['fa5s.arrow-down', 'fa5s.arrow-down', 'fa5s.arrow-up', 'fa5s.arrows-alt-v']
        if not readOnly:
            pointy(self)
        transparent(self)
        self.setToolTip('Click to change direction')
        self.setCheckable(True)

        if not readOnly:
            self.clicked.connect(self._clicked)
        self.reset()

    def setState(self, state: int):
        self._state = state
        self._handleNewState()

    def reset(self):
        self._state = 0
        self.setIconSize(QSize(15, 15))
        self.setIcon(IconRegistry.from_name(self._icons[self._state], 'lightgrey'))
        self.setChecked(False)

    def _increaseState(self):
        self._state += 1
        self._handleNewState()
        self.stateChanged.emit(self._state)

    def _handleNewState(self):
        self.setIconSize(QSize(22, 22))
        self.setIcon(IconRegistry.from_name(self._icons[self._state], '#6c757d'))
        self.setChecked(True)

    def _clicked(self):
        if self._state == self.STATE_MAX:
            self.reset()
            self.stateReset.emit()
        else:
            self._increaseState()


class ReferencesButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        transparent(self)
        self.installEventFilter(OpacityEventFilter(self, leaveOpacity=0.7))
        pointy(self)
        italic(self)
        self.setText('References')

        self._menu = MenuWidget(self)

    def addRefs(self, refs: List[Tuple[str, str]]):
        for ref in refs:
            self._menu.addAction(action(ref[0], slot=partial(open_url, ref[1])))


class DividerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.svg_renderer = QSvgRenderer(resource_registry.divider1)
        self.setMinimumSize(100, 55)

    def setResource(self, resource: str):
        self.svg_renderer = QSvgRenderer(resource)
        self.update()

    @overrides
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setOpacity(0.8)
        rect = QRectF(0, 0, self.width(), self.height())
        self.svg_renderer.render(painter, rect)


class SeparatorLineWithShadow(QWidget):
    def __init__(self, parent=None, color: str = PLACEHOLDER_TEXT_COLOR):
        super().__init__(parent)
        self.setMinimumSize(100, 12)
        self._margin = 10
        self._colorRadiant = QColor(color)
        self._colorRadiant.setAlpha(125)

    def setColor(self, color: str):
        self._colorRadiant = QColor(color)
        self._colorRadiant.setAlpha(125)
        self.update()

    @overrides
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        line_y = self.height() // 2

        shadow_gradient = QRadialGradient(QPointF(self.width() / 2, line_y), self.width() / 3)
        shadow_gradient.setColorAt(0.0, self._colorRadiant)
        shadow_gradient.setColorAt(1.0, QColor(0, 0, 0, 5))

        painter.setBrush(QBrush(shadow_gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        shadow_rect = QRectF(self._margin, line_y, self.width() - self._margin * 2, 8)
        painter.drawEllipse(shadow_rect)

        pen = QPen(self._colorRadiant, 2)
        painter.setPen(pen)
        painter.drawLine(self._margin, line_y, self.width() - self._margin, line_y)


class CopiedTextMessage(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setText('Copied')
        self.setHidden(True)

    def trigger(self):
        def finish():
            QTimer.singleShot(250, lambda: qtanim.fade_out(self))

        qtanim.fade_in(self, 150, teardown=finish)


class _PremiumMessageWidgetBase(QWidget):
    visitRoadmap = pyqtSignal()

    def __init__(self, feature: str, icon: str = '', alt_link: str = '', main_link: str = DEFAULT_PREMIUM_LINK,
                 preview: str = '', parent=None):
        super().__init__(parent)
        vbox(self, 0, 8)
        self.btnUpgrade = push_btn(IconRegistry.from_name('ei.shopping-cart', RELAXED_WHITE_COLOR),
                                   'Purchase',
                                   tooltip='Upgrade Plotlyst',
                                   properties=['confirm', 'positive'])
        self.btnUpgrade.clicked.connect(lambda: open_url(main_link))
        incr_icon(self.btnUpgrade, 10)
        incr_font(self.btnUpgrade, 6)

        self.title = label(f'{feature} is a premium feature', h2=True, wordWrap=True)
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if icon:
            iconWdg = Icon()
            iconWdg.setIcon(IconRegistry.from_name(icon))
            iconWdg.setIconSize(QSize(32, 32))
            self.layout().addWidget(iconWdg, alignment=Qt.AlignmentFlag.AlignCenter)

        self.layout().addWidget(self.title)
        self.layout().addWidget(label("To use this feature, please purchase Plotlyst.", incr_font_diff=2),
                                alignment=Qt.AlignmentFlag.AlignCenter)
        if alt_link:
            btnLink = push_btn(IconRegistry.from_name('fa5s.external-link-alt', 'grey'),
                               'Read more about this feature', transparent_=True)
            btnLink.installEventFilter(OpacityEventFilter(btnLink, leaveOpacity=0.5))
            decr_font(btnLink)
            decr_icon(btnLink, 2)
            btnLink.clicked.connect(lambda: open_url(alt_link))
            self.layout().addWidget(btnLink, alignment=Qt.AlignmentFlag.AlignRight)
        self.layout().addWidget(wrap(self.btnUpgrade, margin_top=10), alignment=Qt.AlignmentFlag.AlignCenter)

        self.btnLinkToAllFeatures = push_btn(IconRegistry.from_name('fa5s.road', 'grey'), 'See roadmap',
                                             transparent_=True)
        self.btnLinkToAllFeatures.installEventFilter(OpacityEventFilter(self.btnLinkToAllFeatures, leaveOpacity=0.5))
        self.btnLinkToAllFeatures.clicked.connect(self.visitRoadmap)
        decr_font(self.btnLinkToAllFeatures, 1)
        decr_icon(self.btnLinkToAllFeatures, 2)
        self.layout().addWidget(self.btnLinkToAllFeatures, alignment=Qt.AlignmentFlag.AlignLeft)

        if preview:
            self.btnPreview = preview_button(preview, self, connect=False)
            self.btnPreview.setGeometry(self.sizeHint().width() - self.btnPreview.sizeHint().width() - 5, 0,
                                        self.btnPreview.sizeHint().width(),
                                        self.btnPreview.sizeHint().height())


class PremiumMessageWidget(QFrame):
    def __init__(self, feature: str, icon: str = '', alt_link: str = '', main_link: str = DEFAULT_PREMIUM_LINK,
                 parent=None):
        super().__init__(parent)
        vbox(self, 15, 8)
        self.setProperty('white-bg', True)
        self.setProperty('large-rounded', True)
        sp(self).h_max().v_max()

        self.wdg = _PremiumMessageWidgetBase(feature, icon, alt_link, main_link)
        self.layout().addWidget(self.wdg)


class PremiumMessagePopup(PopupDialog):
    def __init__(self, feature: str, icon: str = '', alt_link: str = '', main_link: str = DEFAULT_PREMIUM_LINK,
                 preview: str = '',
                 parent=None):
        super().__init__(parent)

        self._preview = preview

        self.frame.layout().addWidget(self.btnReset, alignment=Qt.AlignmentFlag.AlignRight)
        wdg = _PremiumMessageWidgetBase(feature, icon, alt_link, main_link, preview=preview)
        wdg.visitRoadmap.connect(self._visitRoadmap)
        self.frame.layout().addWidget(wdg)

        if self._preview:
            wdg.btnPreview.clicked.connect(self.accept)

    def display(self):
        result = self.exec()
        if result == QDialog.DialogCode.Accepted:
            return self._preview

    def _visitRoadmap(self):
        emit_global_event(ShowRoadmapEvent(self))
        self.accept()


class PremiumOverlayWidget(QFrame):
    def __init__(self, parent, feature: str, icon: str = '', alt_link: str = '', main_link: str = DEFAULT_PREMIUM_LINK,
                 alpha: int = 115):
        super().__init__(parent)
        self.setStyleSheet(f"PremiumOverlayWidget {{background-color: rgba(0, 0, 0, {alpha});}}")
        sp(self).h_exp().v_exp()
        self.parent().installEventFilter(self)
        self.msg = PremiumMessageWidget(feature, icon, alt_link, main_link)
        self.msg.wdg.visitRoadmap.connect(lambda: emit_global_event(ShowRoadmapEvent(self)))
        vbox(self)
        self.layout().addWidget(self.msg, alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

    @overrides
    def eventFilter(self, watched: 'QObject', event: QEvent) -> bool:
        if event.type() == QEvent.Type.Resize:
            self.setGeometry(0, 0, self.parent().width(), self.parent().height())
        return super().eventFilter(watched, event)

    @overrides
    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        fade_in(self.msg)

    @staticmethod
    def storylinesOverlay(parent: QWidget) -> 'PremiumOverlayWidget':
        return PremiumOverlayWidget(parent, 'Storylines',
                                    icon='fa5s.theater-masks',
                                    alt_link='https://plotlyst.com/docs/storylines/')

    @staticmethod
    def worldbuildingOverlay(parent: QWidget) -> 'PremiumOverlayWidget':
        return PremiumOverlayWidget(parent, 'World-building',
                                    icon='mdi.globe-model',
                                    alt_link='https://plotlyst.com/docs/world-building/')


class HighQualityPaintedIcon(QWidget):
    def __init__(self, icon: QIcon, parent=None, size: int = 18):
        super().__init__(parent)
        self._icon = icon
        self.setFixedSize(size, size)

    @overrides
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing |
                               QPainter.RenderHint.TextAntialiasing |
                               QPainter.RenderHint.SmoothPixmapTransform)

        self._icon.paint(painter, event.rect())


class PlotlystFooter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        hbox(self)
        icon = HighQualityPaintedIcon(IconRegistry.book_icon(PLOTLYST_SECONDARY_COLOR), size=16)
        self.layout().addWidget(icon, alignment=Qt.AlignmentFlag.AlignVCenter)
        footer = label('plotlyst.com', color='grey', decr_font_diff=2)
        self.layout().addWidget(wrap(footer, margin_bottom=2))


def icon_text(icon: str, text: str, icon_color: str = 'black', opacity: Optional[float] = None,
              icon_v_flip: bool = False, icon_h_flip: bool = False) -> IconText:
    wdg = IconText()
    wdg.setText(text)
    wdg.setIcon(IconRegistry.from_name(icon, icon_color, vflip=icon_v_flip, hflip=icon_h_flip))
    if opacity:
        translucent(wdg, opacity)

    return wdg


class TimerDisplay(QTimeEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setWrapping(False)
        self.setReadOnly(True)
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.setProperty("showGroupSeparator", False)
        self.setDisplayFormat("mm:ss")
        self.setCurrentSection(QDateTimeEdit.Section.MinuteSection)
        transparent(self)
