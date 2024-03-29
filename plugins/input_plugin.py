from abc import abstractmethod

from PyQt6.QtDesigner import QPyDesignerCustomWidgetPlugin
from overrides import overrides

from plugins import PluginBase
from src.main.python.plotlyst.view.widget.input import Toggle, RotatedButton, DocumentTextEditor, \
    AutoAdjustableTextEdit, RemovalButton, PowerBar


class InputPluginBase(PluginBase):

    def group(self):
        return "Plotlyst input"

    def includeFile(self):
        return "src.main.python.plotlyst.view.widget.input"

    @abstractmethod
    def classType(self):
        pass


class TogglePlugin(QPyDesignerCustomWidgetPlugin, InputPluginBase):

    @overrides
    def classType(self):
        return Toggle


class RotatedButtonPlugin(QPyDesignerCustomWidgetPlugin, InputPluginBase):

    @overrides
    def classType(self):
        return RotatedButton


class PowerBarPlugin(QPyDesignerCustomWidgetPlugin, InputPluginBase):

    @overrides
    def classType(self):
        return PowerBar


class DocumentTextEditorPlugin(QPyDesignerCustomWidgetPlugin, InputPluginBase):

    @overrides
    def classType(self):
        return DocumentTextEditor


class AutoAdjustableTextEditPlugin(QPyDesignerCustomWidgetPlugin, InputPluginBase):

    @overrides
    def classType(self):
        return AutoAdjustableTextEdit


class RemovalButtonPlugin(QPyDesignerCustomWidgetPlugin, InputPluginBase):

    @overrides
    def classType(self):
        return RemovalButton
