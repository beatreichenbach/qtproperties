import math
from enum import Enum
from typing import Any, Union

from PySide2 import QtWidgets, QtGui, QtCore

from qtproperties import data, utils


MAX_INT = (1 << 31) - 1


class PropertyWidget(QtWidgets.QWidget):
    valueChanged = QtCore.Signal()
    accepted_type = Any

    defaults = {
        'default': None
    }

    def __init__(self, name=None, **kwargs):
        super().__init__()
        kwargs['name'] = name
        self.init_kwargs(kwargs)
        self.init_ui()
        self.connect_ui()
        self.value = self.default

    def init_kwargs(self, kwargs):
        kwargs = dict(self.defaults, **kwargs)

        # store kwargs to be able to clone the widget later
        self.kwargs = kwargs

        if kwargs['name'] and 'label' not in kwargs:
            kwargs['label'] = utils.title(kwargs['name'])

        for arg, value in kwargs.items():
            if hasattr(self, arg):
                raise AttributeError(
                    f'The attribute {arg} already exists for class {self.__name__}'
                    )
            setattr(self, arg, value)

    def init_ui(self):
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

    def connect_ui(self):
        pass

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self.validate_value(value)
        self._value = value

    def validate_value(self, value):
        if not isinstance(value, self.accepted_type):

            raise TypeError(
                'TypeError: Argument \'value\' has incorrect type '
                f'(expected {self.accepted_type.__name__}, got {type(value).__name__})'
                )

    @classmethod
    def from_widget(cls, widget, **kwargs):
        if not isinstance(widget, cls):
            raise TypeError(
                'TypeError: Argument \'widget\' has incorrect type '
                f'(expected {cls.__name__}, got {type(widget).__name__})'
                )
        new_kwargs = widget.kwargs
        new_kwargs.update(kwargs)
        name = new_kwargs.pop('name')
        return cls(name, **new_kwargs)


class IntProperty(PropertyWidget):
    valueChanged = QtCore.Signal(int)
    accepted_type = int

    def __init__(self, *args, **kwargs):
        self.defaults['default'] = 0
        self.defaults['slider_min'] = 0
        self.defaults['slider_max'] = 10
        self.defaults['line_min'] = -MAX_INT
        self.defaults['line_max'] = MAX_INT
        self.defaults['show_slider'] = True

        super().__init__(*args, **kwargs)

    def init_ui(self):
        super().init_ui()

        # line
        self.line = IntLineEdit()
        self.line.setMinimum(self.line_min)
        self.line.setMaximum(self.line_max)
        self.layout().addWidget(self.line)

        # slider
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setTickPosition(QtWidgets.QSlider.TicksBothSides)
        self.slider.setFocusPolicy(QtCore.Qt.NoFocus)
        self.layout().addWidget(self.slider)
        self.layout().setStretch(1, 1)

        # prevent any size changes when slider shows
        self.slider.setMaximumHeight(self.line.minimumSizeHint().height())

        # automatically adjust step size and tick interval based on slider range
        num_range = abs(self.slider_max - self.slider_min)
        exponent = math.log10(num_range)

        # round exponent up or down with weighting towards down
        if exponent % 1 > 0.8:
            exponent = math.ceil(exponent)
        else:
            exponent = math.floor(exponent)

        # store value for subclasses
        self.exponent = exponent

        step = pow(10, max(self.exponent - 2, 0))

        self.slider.setSingleStep(step)
        self.slider.setPageStep(step * 10)
        self.slider.setTickInterval(step * 10)
        self.slider.setMinimum(self.slider_min)
        self.slider.setMaximum(self.slider_max)
        self.slider.setVisible(self.show_slider)

        self.slider.mouseDoubleClickEvent = self.mouseDoubleClickEvent

        self.setFocusProxy(self.line)

    def connect_ui(self):
        self.slider.valueChanged.connect(self.slider_value_changed)
        self.line.valueChanged.connect(self.line_value_changed)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.show_slider:
            self.slider.setVisible(event.size().width() > 200)

    def mouseDoubleClickEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.value = self.default
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def slider_value_changed(self, value):
        self._value = value
        self.set_line_value(value)
        self.valueChanged.emit(value)

    def line_value_changed(self, value):
        self._value = value
        self.set_slider_value(value)
        self.valueChanged.emit(value)

    def set_line_value(self, value):
        self.line.blockSignals(True)
        self.line.setValue(value)
        self.line.blockSignals(False)

    def set_slider_value(self, value):
        self.slider.blockSignals(True)
        self.slider.setSliderPosition(value)
        self.slider.blockSignals(False)

    @PropertyWidget.value.setter
    def value(self, value):
        self.validate_value(value)
        self._value = value
        self.set_slider_value(value)
        self.set_line_value(value)
        self.valueChanged.emit(value)


class FloatProperty(IntProperty):
    valueChanged = QtCore.Signal(float)
    accepted_type = Union[float, int]

    def __init__(self, *args, **kwargs):
        self.defaults['decimals'] = 4

        super().__init__(*args, **kwargs)

    def init_ui(self):
        super().init_ui()

        old_line = self.line

        self.line = FloatLineEdit()
        self.line.setDecimals(self.decimals)
        self.line.setMinimum(self.line_min)
        self.line.setMaximum(self.line_max)
        self.layout().replaceWidget(old_line, self.line)
        old_line.deleteLater()
        self.setTabOrder(self.line, self.slider)

        # find a value that brings our float range into an int range
        # with step size locked to 1 and 10
        normalize = pow(10, -(self.exponent - 2))

        self.slider.setSingleStep(1)
        self.slider.setPageStep(10)
        self.slider.setTickInterval(10)
        self.slider.setMinimum(self.slider_min * normalize)
        self.slider.setMaximum(self.slider_max * normalize)

        self.setFocusProxy(self.line)

    def slider_value_changed(self, value):
        slider_range = self.slider.maximum() - self.slider.minimum()
        percentage = (value - self.slider.minimum()) / slider_range
        float_value = self.slider_min + (self.slider_max - self.slider_min) * percentage
        super().slider_value_changed(float_value)

    def set_slider_value(self, value):
        percentage = (value - self.slider_min) / (self.slider_max - self.slider_min)
        slider_range = self.slider.maximum() - self.slider.minimum()
        int_value = min(max(percentage, 0), 1) * slider_range + self.slider.minimum()
        super().set_slider_value(int_value)


class Int2Property(PropertyWidget):
    valueChanged = QtCore.Signal(data.Int2)
    accepted_type = data.Int2

    def __init__(self, *args, **kwargs):
        self.defaults['default'] = data.Int2(0, 0)
        self.defaults['line_min'] = -(MAX_INT)
        self.defaults['line_max'] = MAX_INT

        super().__init__(*args, **kwargs)

    def init_ui(self):
        super().init_ui()

        self.line1 = IntLineEdit()
        self.line1.setMinimum(self.line_min)
        self.line1.setMaximum(self.line_max)
        self.layout().addWidget(self.line1)

        self.line2 = IntLineEdit()
        self.line2.setMinimum(self.line_min)
        self.line2.setMaximum(self.line_max)
        self.layout().addWidget(self.line2)

        self.setFocusProxy(self.line1)

    def connect_ui(self):
        self.line1.valueChanged.connect(self.line_value_changed)
        self.line2.valueChanged.connect(self.line_value_changed)

    def line_value_changed(self, value):
        value = data.Int2(self.line1.value, self.line2.value)
        self._value = value
        self.valueChanged.emit(value)

    @PropertyWidget.value.setter
    def value(self, value):
        self.validate_value(value)
        self._value = value
        self.line1.setValue(value.x)
        self.line2.setValue(value.y)
        self.valueChanged.emit(value)


class Float2Property(Int2Property):
    valueChanged = QtCore.Signal(data.Float2)
    accepted_type = Union[data.Int2, data.Float2]

    def __init__(self, *args, **kwargs):
        self.defaults['decimals'] = 2

        super().__init__(*args, **kwargs)

    def init_ui(self):
        super().init_ui()

        while self.layout().count():
            child = self.layout().takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.line1 = FloatLineEdit()
        self.line1.setMinimum(self.line_min)
        self.line1.setMaximum(self.line_max)
        self.line1.setDecimals(self.decimals)
        self.layout().addWidget(self.line1)

        self.line2 = FloatLineEdit()
        self.line2.setMinimum(self.line_min)
        self.line2.setMaximum(self.line_max)
        self.line2.setDecimals(self.decimals)
        self.layout().addWidget(self.line2)

        self.setFocusProxy(self.line1)

    def line_value_changed(self, value):
        value = data.Float2(self.line1.value, self.line2.value)
        self._value = value
        self.valueChanged.emit(value)


class StringProperty(PropertyWidget):
    valueChanged = QtCore.Signal(str)
    accepted_type = str

    def __init__(self, *args, **kwargs):
        self.defaults['default'] = ''

        super().__init__(*args, **kwargs)

    def init_ui(self):
        super().init_ui()

        self.line = QtWidgets.QLineEdit()
        self.layout().addWidget(self.line)
        self.setFocusProxy(self.line)

    def connect_ui(self):
        self.line.textChanged.connect(self.valueChanged)

    @property
    def value(self):
        return self.line.text()

    @value.setter
    def value(self, value):
        self.validate_value(value)
        self.line.setText(value)


class PathProperty(PropertyWidget):
    valueChanged = QtCore.Signal(str)
    accepted_type = str

    OPEN_FILE = 1
    SAVE_FILE = 2
    EXISTING_DIR = 3

    def __init__(self, *args, **kwargs):
        self.defaults['default'] = ''
        self.defaults['method'] = self.OPEN_FILE

        super().__init__(*args, **kwargs)

    def init_ui(self):
        super().init_ui()

        self.line = QtWidgets.QLineEdit()
        self.layout().addWidget(self.line)

        self.button = QtWidgets.QToolButton()
        self.button.setText('...')
        self.layout().addWidget(self.button)

        self.layout().setStretch(0, 1)
        self.setFocusProxy(self.line)

    def connect_ui(self):
        self.button.clicked.connect(self.browse)
        self.line.textChanged.connect(self.valueChanged)

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
        self.validate_value(value)
        self.line.setText(value)


class EnumProperty(PropertyWidget):
    valueChanged = QtCore.Signal(Enum)
    accepted_type = Enum

    def __init__(self, *args, **kwargs):
        if args and isinstance(args[0], self.__class__):
            super().__init__(*args, **kwargs)
            return

        if 'enum' not in kwargs:
            raise AttributeError(f'{self.__class__.__name__} requires argument \'enum\'')
        if 'default' not in kwargs:
            kwargs['default'] = next(iter(kwargs['enum']))

        super().__init__(*args, **kwargs)

    def init_ui(self):
        super().init_ui()

        self.combo = QtWidgets.QComboBox()

        formatting = lambda e: utils.title(e.name)
        for e in self.enum:
            # TODO: should we be able to provide a format function?
            # e.g formatting=lambda e: e.name.title()
            self.combo.addItem(formatting(e), e)
        self.layout().addWidget(self.combo)
        # self.layout().addStretch()
        self.setFocusProxy(self.combo)

    def connect_ui(self):
        self.combo.currentIndexChanged.connect(self.combo_index_changed)

    def combo_index_changed(self, index):
        self.valueChanged.emit(self.value)

    @property
    def value(self):
        return self.combo.currentData()

    @value.setter
    def value(self, value):
        self.validate_value(value)
        index = self.combo.findData(value)
        self.combo.setCurrentIndex(index)


class BoolProperty(PropertyWidget):
    valueChanged = QtCore.Signal(bool)
    accepted_type = bool

    def __init__(self, *args, **kwargs):
        self.defaults['default'] = False

        super().__init__(*args, **kwargs)

    def init_ui(self):
        super().init_ui()

        self.checkbox = QtWidgets.QCheckBox()
        self.layout().addWidget(self.checkbox)
        self.layout().addStretch()
        self.setFocusProxy(self.checkbox)

    def connect_ui(self):
        self.checkbox.toggled.connect(self.state_changed)

    def state_changed(self, state):
        self.valueChanged.emit(self.value)

    @property
    def value(self):
        return self.checkbox.isChecked()

    @value.setter
    def value(self, value):
        self.validate_value(value)
        self.checkbox.setChecked(value)


class ColorProperty(PropertyWidget):
    valueChanged = QtCore.Signal(QtGui.QColor)
    accepted_type = QtGui.QColor

    def __init__(self, *args, **kwargs):
        self.defaults['default'] = QtGui.QColor(0, 0, 0)
        self.defaults['color_min'] = 0
        self.defaults['color_max'] = MAX_INT
        self.defaults['decimals'] = 2

        super().__init__(*args, **kwargs)

    def init_ui(self):
        super().init_ui()

        self.lines = []
        for i in range(3):
            line = FloatLineEdit()
            line.setMinimum(self.color_min)
            line.setMaximum(self.color_max)
            line.setDecimals(self.decimals)
            self.lines.append(line)
            self.layout().addWidget(line)

        self.button = QtWidgets.QPushButton()
        self.button.setFocusPolicy(QtCore.Qt.NoFocus)
        size = self.button.sizeHint()
        self.button.setMaximumWidth(size.height())
        self.layout().addWidget(self.button)

    def connect_ui(self):
        for line in self.lines:
            line.valueChanged.connect(self.line_value_changed)
        self.button.clicked.connect(self.select_color)

    def line_value_changed(self, value):
        color = QtGui.QColor.fromRgbF(
            self.lines[0].value,
            self.lines[1].value,
            self.lines[2].value
            )
        self._value = color
        self.set_button_value(color)
        self.valueChanged.emit(color)

    def select_color(self):
        color = QtWidgets.QColorDialog.getColor(
            initial=self.value,
            options=QtWidgets.QColorDialog.DontUseNativeDialog
            )
        if color.isValid():
            self._value = color
            self.set_line_value(color)
            self.set_button_value(color)
            self.valueChanged.emit(color)

    def set_line_value(self, value):
        for i, line in enumerate(self.lines):
            line.blockSignals(True)
            line.setValue(value.getRgbF()[i])
            line.blockSignals(False)

    def set_button_value(self, value):
        self.button.setPalette(QtGui.QPalette(value))

    @PropertyWidget.value.setter
    def value(self, value):
        self.validate_value(value)
        self._value = value
        self.set_button_value(value)
        self.set_line_value(value)
        self.valueChanged.emit(value)


class IntLineEdit(QtWidgets.QLineEdit):
    valueChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self.editingFinished.connect(self.strip_padding)
        self.setValidator(IntValidator())

        self.value = 1

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Up:
            self.step(add=True)
        elif event.key() == QtCore.Qt.Key_Down:
            self.step(add=False)
        else:
            return super().keyPressEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta()
        if delta.y() > 0:
            self.step(add=True)
        elif delta.y() < 0:
            self.step(add=False)
        event.accept()

    @property
    def value(self):
        try:
            return int(self.text())
        except ValueError:
            return 0

    @value.setter
    def value(self, value):
        pass
        if value != self._value:
            self.valueChanged.emit(value)
        self._value = value

    def setValue(self, value):
        text = self.validator().fixup(str(value))

        state, text_, pos_ = self.validator().validate(text, 0)
        if state == QtGui.QValidator.State.Acceptable:
            self.setText(text)
            self.strip_padding()

    def sizeHint(self):
        size = super().sizeHint()
        size.setWidth(60)
        return size

    def minimumSizeHint(self):
        size = super().minimumSizeHint()
        size.setWidth(24)
        return size

    def setMinimum(self, minimum):
        self.validator().setBottom(minimum)

    def setMaximum(self, maximum):
        self.validator().setTop(maximum)

    def step(self, add):
        text = self.text() or '0'
        position = self.cursorPosition()
        if self.hasSelectedText():
            position = self.selectionStart()

        # check if cursor is on special character
        if position < len(text) and not text[position].isdigit():
            return False

        step_index = self.step_index(text, position)
        exponent = self.step_exponent(step_index)

        # perform step
        amount = 1 if add else -1
        step = amount * pow(10, exponent)
        value = self.value + step

        # preserve padding
        text = self.match_value_to_text(value, text, exponent)

        # validate before setting new text
        state, text_, pos_ = self.validator().validate(text, 0)
        if state != QtGui.QValidator.State.Acceptable:
            return False
        self.setText(text)
        self.value = value

        # get new position and set selection
        position = self.step_index_to_position(step_index, text)
        self.setSelection(position, 1)
        return True

    def match_value_to_text(self, value, text, exponent):
        # exponent is for subclasses
        padding = len([t for t in text if t.isdigit()])
        if value < 0:
            padding += 1
        text = f'{value:0{padding}}'
        return text

    def step_index(self, text, position):
        # get step index relative to decimal point
        # this preserves position when number gets larger or changes plus/minus sign
        step_index = len(text) - position
        # if cursor is at end, edit first digit
        step_index = max(1, step_index)
        return step_index

    def step_exponent(self, step_index):
        # convert cursor position to exponent
        exponent = step_index - 1
        return exponent

    def step_index_to_position(self, step_index, text):
        position = len(text) - step_index
        return position

    def strip_padding(self):
        value = self.value
        if int(value) == value:
            value = int(value)
        self.value = value
        self.setText(str(value))


class FloatLineEdit(IntLineEdit):
    valueChanged = QtCore.Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)

        validator = DoubleValidator()
        validator.setNotation(QtGui.QDoubleValidator.StandardNotation)
        self.setValidator(validator)

    def setDecimals(self, decimals):
        self.validator().setDecimals(decimals)

    @IntLineEdit.value.getter
    def value(self):
        try:
            return float(self.text())
        except ValueError:
            return float(0)

    def step_index(self, text, position):
        # get step index relative to decimal point
        # this preserves position when number gets larger or changes plus/minus sign
        decimal_index = text.find('.')
        if decimal_index == -1:
            step_index = len(text) - position
        else:
            step_index = decimal_index - position
        return step_index

    def step_exponent(self, step_index):
        # convert cursor position to exponent
        exponent = step_index
        # if cursor is on the decimal then edit the first decimal
        if step_index >= 0:
            exponent = step_index - 1

        return exponent

    def match_value_to_text(self, value, text, exponent):
        decimal_index = text.find('.')

        # preserve padding
        padding_int = 0
        if decimal_index == -1:
            padding_decimal = 0
        else:
            padding_decimal = len(text) - 1 - decimal_index
            text = text[:decimal_index]

        # preserve padding if we switch to something like 1.001 > 1.000
        padding_decimal = max(padding_decimal, -exponent)
        padding_int = len([t for t in text if t.isdigit()])
        # account for minus sign
        if value < 0:
            padding_int += 1

        # padding_int needs to contain both padding for in and decimals
        padding_int += padding_decimal + 1 * bool(padding_decimal)

        value = round(value, padding_decimal)
        text = f'{value:0{padding_int}.{padding_decimal}f}'

        return text

    def step_index_to_position(self, step_index, text):
        decimal_index = text.find('.')
        position = len(text) - step_index
        if decimal_index > -1:
            # if position is on decimal point, move to first decimal
            if step_index == 0:
                step_index = -1
            position = decimal_index - step_index
        return position


class IntValidator(QtGui.QIntValidator):
    def fixup(self, text):
        text = super().fixup(text).replace(',', '')
        return text


class DoubleValidator(QtGui.QDoubleValidator):
    def fixup(self, text):
        try:
            value = float(text)
        except ValueError:
            characters = '+-01234567890.'
            text = [t for t in text if t in characters]

        try:
            value = float(text)
            value = min(max(value, self.bottom()), self.top())
            value = round(value, self.decimals())
            return '{value:.{decimals}f}'.format(value=value, decimals=self.decimals())
        except ValueError:
            return text
