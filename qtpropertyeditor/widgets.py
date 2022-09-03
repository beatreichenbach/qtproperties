import logging
import sys
import os
from dataclasses import dataclass, field
from typing import Union, Optional, TypeVar, Type
from enum import Enum
from functools import partial

from PySide2 import QtWidgets, QtGui, QtCore

import gui

PARM_MIN = 0
PARM_MAX = 10000000


class ParameterGroupWidget(QtWidgets.QWidget):
    # okay so this is going to be the class for each group. That way another class can be used
    # as a collection of many parametergroupwidgets and we can also easily override a whole
    # parameter group as a whole.
    def __init__(self, parent=None):
        super().__init__(parent)
        self.widgets = []
        self.override = False

        self.layout = QtWidgets.QGridLayout()

        self.setLayout(self.layout)

    def add_parameter(self, widget):
        row = self.layout.rowCount()

        label = QtWidgets.QLabel(widget.label)
        self.layout.addWidget(label, row, 1)
        self.layout.addWidget(widget, row, 2)

        if self.override:
            checkbox = QtWidgets.QCheckBox()
            checkbox.stateChanged.connect(partial(self.override_changed, checkbox))
            self.layout.addWidget(checkbox, row, 0)
            self.set_row_enabled(row, False)

        self.widgets.append(widget)

    def override_changed(self, checkbox, state):
        index = self.layout.indexOf(checkbox)
        if index < 0:
            return
        row, column, rowspan, colspan = self.layout.getItemPosition(index)
        self.set_row_enabled(row, checkbox.isChecked())

    def set_row_enabled(self, row, enabled):
        item = self.layout.itemAtPosition(row, 1)
        if item:
            label = item.widget()
            label.setEnabled(enabled)

        item = self.layout.itemAtPosition(row, 2)
        if item:
            widget = item.widget()
            widget.setEnabled(enabled)



class ParameterWidget(QtWidgets.QWidget):
    value_changed = QtCore.Signal()

    defaults = {
        'name': 'parameter',
        'default': None
    }

    def __init__(self, **kwargs):
        super().__init__()
        self.init_kwargs(kwargs)
        self.init_ui()
        self.connect_ui()
        self.value = self.default

    def init_kwargs(self, kwargs):
        kwargs = self.defaults | kwargs

        if 'label' not in kwargs:
            kwargs['label'] = kwargs['name'].replace('_', ' ').title()

        for arg, value in kwargs.items():
            if hasattr(self, arg):
                raise AttributeError(
                    f'The attribute {arg} already exists for class {self.__name__}'
                    )
            setattr(self, arg, value)

    def init_ui(self):
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

    def connect_ui(self):
        pass

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    def validate_value(self, value):
        if hasattr(self, '_value') and not isinstance(value, type(self._value)):
            raise TypeError(
                'Class {} expects type {} for value.'.format(
                self.__class__.__name__, self._value.__class__.__name__)
                )


class FloatParameterWidget(ParameterWidget):
    def __init__(self, **kwargs):
        self.defaults['default'] = float(0)
        self.defaults['slider_min'] = 0
        self.defaults['slider_max'] = 10
        self.defaults['spin_min'] = PARM_MIN
        self.defaults['spin_max'] = PARM_MAX
        self.defaults['show_slider'] = True

        super().__init__(**kwargs)


    def init_ui(self):
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        self.spin = QtWidgets.QDoubleSpinBox()
        self.spin.setMinimum(self.spin_min)
        self.spin.setMaximum(self.spin_max)
        self.spin.setDecimals(2)
        self.layout.addWidget(self.spin)

        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setMinimum(self.slider_min * 100)
        self.slider.setMaximum(self.slider_max * 100)
        self.layout.addWidget(self.slider)
        self.slider.setVisible(self.show_slider)

    def connect_ui(self):
        self.slider.valueChanged.connect(self.slider_value_changed)
        self.spin.valueChanged.connect(self.spin_value_changed)

    def slider_value_changed(self, value):
        percentage = value / (self.slider.maximum() - self.slider.minimum())
        float_value = self.slider_min + (self.slider_max - self.slider_min) * percentage

        self.value = float_value

    def spin_value_changed(self, value):
        self.value = value

    def set_spin_value(self, value):
        self.spin.blockSignals(True)
        self.spin.setValue(value)
        self.spin.blockSignals(False)

    def set_slider_value(self, value):
        percentage = (value - self.slider_min) / (self.slider_max - self.slider_min)
        int_value = min(max(percentage, 0), 1) * self.slider.maximum() + self.slider.minimum()

        self.slider.blockSignals(True)
        self.slider.setSliderPosition(int_value)
        self.slider.blockSignals(False)

    @ParameterWidget.value.setter
    def value(self, value):
        self._value = value
        self.set_slider_value(value)
        self.set_spin_value(value)


class IntParameterWidget(ParameterWidget):
    def __init__(self, **kwargs):
        self.defaults['default'] = 0
        self.defaults['slider_min'] = 0
        self.defaults['slider_max'] = 10
        self.defaults['spin_min'] = PARM_MIN
        self.defaults['spin_max'] = PARM_MAX

        super().__init__(**kwargs)


    def init_ui(self):
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        self.spin = QtWidgets.QSpinBox()
        self.spin.setMinimum(self.spin_min)
        self.spin.setMaximum(self.spin_max)
        self.layout.addWidget(self.spin)

        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setMinimum(self.slider_min)
        self.slider.setMaximum(self.slider_max)
        self.layout.addWidget(self.slider)

    def connect_ui(self):
        self.slider.valueChanged.connect(self.slider_value_changed)
        self.spin.valueChanged.connect(self.spin_value_changed)

    def slider_value_changed(self, value):
        self.value = value

    def spin_value_changed(self, value):
        self.value = value

    def set_spin_value(self, value):
        self.spin.blockSignals(True)
        self.spin.setValue(value)
        self.spin.blockSignals(False)

    def set_slider_value(self, value):
        self.slider.blockSignals(True)
        self.slider.setSliderPosition(value)
        self.slider.blockSignals(False)

    @ParameterWidget.value.setter
    def value(self, value):
        self._value = value
        self.set_slider_value(value)
        self.set_spin_value(value)


class Int2ParameterWidget(ParameterWidget):
    def __init__(self, **kwargs):
        self.defaults['default'] = Int2(0, 0)
        self.defaults['spin_min'] = PARM_MIN
        self.defaults['spin_max'] = PARM_MAX

        super().__init__(**kwargs)


    def init_ui(self):
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        self.spin1 = QtWidgets.QSpinBox()
        self.spin1.setMinimum(self.spin_min)
        self.spin1.setMaximum(self.spin_max)
        self.layout.addWidget(self.spin1)

        self.spin2 = QtWidgets.QSpinBox()
        self.spin2.setMinimum(self.spin_min)
        self.spin2.setMaximum(self.spin_max)
        self.layout.addWidget(self.spin2)


    def connect_ui(self):
        self.spin1.valueChanged.connect(self.spin_value_changed)
        self.spin2.valueChanged.connect(self.spin_value_changed)

    def spin_value_changed(self, value):
        value = Int2(self.spin1.value(), self.spin2.value())
        self.value = value

    @ParameterWidget.value.setter
    def value(self, value):
        self._value = value
        self.spin1.setValue(value.x)
        self.spin2.setValue(value.y)


class Float2ParameterWidget(ParameterWidget):
    def __init__(self, **kwargs):
        self.defaults['default'] = Float2(0, 0)
        self.defaults['spin_min'] = PARM_MIN
        self.defaults['spin_max'] = PARM_MAX

        super().__init__(**kwargs)


    def init_ui(self):
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        self.spin1 = QtWidgets.QDoubleSpinBox()
        self.spin1.setMinimum(self.spin_min)
        self.spin1.setMaximum(self.spin_max)
        self.spin1.setDecimals(2)
        self.layout.addWidget(self.spin1)

        self.spin2 = QtWidgets.QDoubleSpinBox()
        self.spin2.setMinimum(self.spin_min)
        self.spin2.setMaximum(self.spin_max)
        self.spin1.setDecimals(2)
        self.layout.addWidget(self.spin2)


    def connect_ui(self):
        self.spin1.valueChanged.connect(self.spin_value_changed)
        self.spin2.valueChanged.connect(self.spin_value_changed)

    def spin_value_changed(self, value):
        value = Float2(self.spin1.value(), self.spin2.value())
        self.value = value

    @ParameterWidget.value.setter
    def value(self, value):
        self._value = value
        self.spin1.setValue(value.x)
        self.spin2.setValue(value.y)

class PathParameterWidget(ParameterWidget):
    OPEN_FILE = 1
    SAVE_FILE = 2
    EXISTING_DIR = 3

    def __init__(self, **kwargs):
        self.defaults['default'] = ''
        self.defaults['method'] = self.OPEN_FILE

        super().__init__(**kwargs)

    def init_ui(self):
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        self.line = QtWidgets.QLineEdit()
        self.layout.addWidget(self.line)

        self.button = QtWidgets.QPushButton('...')
        self.layout.addWidget(self.button)

    def connect_ui(self):
        self.button.clicked.connect(self.browse)

    def browse(self):
        path = ''
        if self.method == self.OPEN_FILE:
            path, filters = QtWidgets.QFileDialog.getOpenFileName(
                parent=self,
                caption='Open File',
                dir=self.value,
                )
        elif self.method == self.SAVE_FILE:
            path, filters = QtWidgets.QFileDialog.getSaveFileName(
                parent=self,
                caption='Save File',
                dir=self.value,
                filter='*.*'
                )
        elif self.method == self.EXISTING_DIR:
            path = QtWidgets.QFileDialog.getExistingDirectory(
                parent=self,
                caption='Select Directory',
                dir=self.value
                )

        if path:
            self.value = path

    @property
    def value(self):
        return self.line.text()

    @value.setter
    def value(self, value):
        self.line.setText(value)

class EnumParameterWidget(ParameterWidget):
    def __init__(self, **kwargs):
        if 'enum' not in kwargs:
            raise AttributeError('{} requires argument \'enum\'.'.format(self.__class__.__name__))
        if 'default' not in kwargs:
            kwargs['default'] = next(iter(kwargs['enum']))

        super().__init__(**kwargs)

    def init_ui(self):
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        self.combo = QtWidgets.QComboBox()
        for e in self.enum:
            self.combo.addItem(e.name, e)
        self.layout.addWidget(self.combo)

    @property
    def value(self):
        return self.combo.currentData()

    @value.setter
    def value(self, value):
        index = self.combo.findData(value)
        self.combo.setCurrentIndex(index)

class ColorParameterWidget(ParameterWidget):
    def __init__(self, **kwargs):

        super().__init__(**kwargs)

    def init_ui(self):
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        for c in ('r', 'g', 'b'):
            spin = QtWidgets.QDoubleSpinBox()
            spin.setMinimum(0)
            spin.setMaximum(1)
            spin.setDecimals(2)
            setattr(self, f'spin_{c}', spin)
            self.layout.addWidget(spin)

        self.button = QtWidgets.QPushButton()
        self.layout.addWidget(self.button)

    def connect_ui(self):
        self.button.clicked.connect(self.select_color)

    def select_color(self):
        QtWidgets.QColorDialog.getColor(
            options=QtWidgets.QColorDialog.DontUseNativeDialog
            )

    @property
    def value(self):
        pass

    @value.setter
    def value(self, value):
        pass

@dataclass
class Float2:
    x: float = 0
    y: float = 0

@dataclass
class Int2:
    x: int = 0
    y: int = 0

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    app = QtWidgets.QApplication()
    gui.apply_style(app)

    group_widget = ParameterGroupWidget()

    widget = FloatParameterWidget(
        name='f-stop',
        label='Aperture',
        slider_min=0,
        slider_max=32,
        default=4.8
        )
    group_widget.add_parameter(widget)

    widget = FloatParameterWidget(
        name='exposure',
        default=1,
        show_slider=False
        )
    group_widget.add_parameter(widget)

    widget = PathParameterWidget(
        name='image_path',
        method=PathParameterWidget.SAVE_FILE
        )
    group_widget.add_parameter(widget)

    widget = IntParameterWidget(
        name='blades',
        slider_min=4,
        slider_max=12,
        spin_min=1,
        default=6
        )
    group_widget.add_parameter(widget)

    widget = Int2ParameterWidget(
        name='format',
        default=Int2(1920, 1080)
        )
    group_widget.add_parameter(widget)

    widget = Float2ParameterWidget(
        name='overscan',
        default=Float2(1, 1)
        )
    group_widget.add_parameter(widget)

    enum = Enum('Filter', ('Box', 'Gauss', 'Triangle'))
    widget = EnumParameterWidget(
        name='filter',
        enum=enum
        )
    group_widget.add_parameter(widget)

    widget = ColorParameterWidget(
        name='color',
        )
    group_widget.add_parameter(widget)

    group_widget.show()

    sys.exit(app.exec_())

    # gui.show(widget)
