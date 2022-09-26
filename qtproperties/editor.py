from functools import partial

from PySide2 import QtWidgets, QtCore


QWIDGETSIZE_MAX = (1 << 24) - 1


# TODO: initialize widget with updated min_size_hint?

class PropertyEditor(QtWidgets.QWidget):
    values_changed = QtCore.Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.tab_widget = None
        self.tabs = {}  # {'tab_name': tab_widget}
        self.current_tab = None

        self.groups = {}  # {'tab_name': {'group_name': group_widget}}

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addStretch()

    def create_tab(self, name):
        if name in self.tabs:
            raise ValueError(f'Cannot create tab {name} (name already exsits)')

        if not isinstance(name, str):
            raise TypeError(
                'TypeError: Argument \'name\' has incorrect type '
                f'(expected str, got {type(name).__name__})'
                )

        if not self.tab_widget:
            self.tab_widget = QtWidgets.QTabWidget()
            # insert widget to account for stretch
            self.layout().takeAt(self.layout().count() - 1)
            self.layout().addWidget(self.tab_widget)

        scroll_area = VerticalScrollArea()
        scroll_area.setWidget(QtWidgets.QWidget())
        scroll_area.widget().setLayout(QtWidgets.QVBoxLayout())
        scroll_area.widget().layout().addStretch()

        self.add_tab(name, scroll_area)
        return scroll_area

    def add_tab(self, name, widget):
        label = name.replace('_', ' ').title()
        self.tab_widget.addTab(widget, label)
        self.tabs[name] = widget

    def create_property_group(self, name, tab=None, collapsible=False, link=None):
        if name in self.groups.get(tab, {}):
            raise ValueError(f'Cannot create property group {name} (name already exsits)')

        group = PropertyGroup(link=link)

        self.add_property_group(name, group, tab, collapsible)
        return group

    def add_property_group(self, name, widget, tab, collapsible=False):
        if tab is None:
            parent = self
        elif tab in self.tabs:
            parent = self.tabs[tab].widget()
        else:
            parent = self.create_tab(tab).widget()

        label = name.replace('_', ' ').title() if name else ''
        if collapsible:
            box = CollapsibleBox(label)
        else:
            box = QtWidgets.QGroupBox(label)

        box.setLayout(QtWidgets.QVBoxLayout())
        box.layout().setContentsMargins(0, 0, 0, 0)
        box.layout().addWidget(widget)

        # insert widget to account for stretch
        parent.layout().insertWidget(parent.layout().count() - 1, box)

        widget.values_changed.connect(partial(self.group_values_changed, name, tab))

        if not self.groups.get(tab):
            self.groups[tab] = {}
        self.groups[tab][name] = widget

    def add_property(self, widget, group=None, tab=None, box=None):
        if self.groups.get(tab):
            if self.groups[tab].get(group):
                group_widget = self.groups[tab][group]
            else:
                group_widget = self.create_property_group(group, tab)
        else:
            if tab is not None:
                self.create_tab(tab)
            group_widget = self.create_property_group(group, tab)

        group_widget.add_property(widget, box)

    def group_values_changed(self, group, tab, values):
        self.values_changed.emit(self.values)

    @property
    def values(self):
        values = {}
        for tab, groups in self.groups.items():
            values[tab] = {}
            for name, group in groups.items():
                values[tab][name] = group.values

        return values

    @values.setter
    def values(self, values):
        for tab, groups in self.groups.items():
            if tab not in values:
                continue
            for name, group in groups.items():
                if name in values[tab]:
                    group.values = values[tab][name]


class PropertyGroup(QtWidgets.QWidget):
    values_changed = QtCore.Signal(dict)

    def __init__(self, link=None, parent=None):
        super().__init__(parent)
        self.widgets = {}
        self.boxes = {}
        self.link = link

        self.setLayout(QtWidgets.QGridLayout())

        if link:
            for linked_widget in self.link.widgets.values():
                cls = linked_widget.__class__
                widget = cls.from_widget(linked_widget)
                self.add_property(widget, link=linked_widget)

    def __repr__(self):
        args = f'({self.link})' if self.link else ''
        return f'{self.__class__.__name__}{args}'

    def add_property(self, widget, link=None, box=None):
        if widget.name in self.widgets:
            raise ValueError(f'Cannot add property {widget.name} (name already exsits)')

        layout = self.layout()
        row = layout.rowCount()

        if box:
            box_widget = self.boxes.get(box)
            if not box_widget:
                box_widget = CollapsibleBox(box, border=False)
                layout.addWidget(box_widget, row, 0, 1, -1)
                layout = QtWidgets.QGridLayout()
                layout.setContentsMargins(0, 0, 0, 0)
                box_widget.setLayout(layout)
                self.boxes[box] = box_widget

            layout = box_widget.layout()
            row = layout.rowCount()

        label = QtWidgets.QLabel(widget.label)
        layout.addWidget(label, row, 1)
        layout.addWidget(widget, row, 2)

        if link is not None:
            checkbox = QtWidgets.QCheckBox()
            checkbox.stateChanged.connect(partial(self.override_changed, checkbox))
            layout.addWidget(checkbox, row, 0)
            widget.link = link
            self.set_widget_row_enabled(checkbox, False)

        widget.valueChanged.connect(self.value_changed)

        self.widgets[widget.name] = widget

    def override_changed(self, checkbox, state):
        self.set_widget_row_enabled(checkbox, checkbox.isChecked())

    def set_widget_row_enabled(self, widget, enabled):
        # get parent grid layout
        layout = widget.parentWidget().layout()
        if not isinstance(layout, QtWidgets.QGridLayout):
            return

        # find row of widget
        index = layout.indexOf(widget)
        if index < 0:
            return
        row, column, rowspan, colspan = layout.getItemPosition(index)

        # label
        item = layout.itemAtPosition(row, 1)
        if item:
            label = item.widget()
            label.setEnabled(enabled)

        # widget
        item = layout.itemAtPosition(row, 2)
        if item:
            widget = item.widget()
            widget.setEnabled(enabled)

            if self.link is not None:
                linked_widget = widget.link
                if not hasattr(widget, 'set_value'):
                    widget.set_value = partial(setattr, widget, 'value')

                if enabled:
                    linked_widget.valueChanged.disconnect(widget.set_value)
                else:
                    widget.value = linked_widget.value
                    linked_widget.valueChanged.connect(widget.set_value)

    def value_changed(self):
        self.values_changed.emit(self.values)

    @property
    def values(self):
        values = {name: widget.value for name, widget in self.widgets.items()}
        return values

    @values.setter
    def values(self, values):
        for name, widget in self.widgets.items():
            if name in values:
                widget.value = values[name]


class CollapsibleBox(QtWidgets.QWidget):
    # https://stackoverflow.com/questions/52615115/how-to-create-collapsible-box-in-pyqt
    def __init__(self, title='', border=False, parent=None):
        super().__init__(parent)

        self.button = QtWidgets.QToolButton(text=title, checkable=True, checked=False)
        self.button.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
            )
        self.button.setStyleSheet('QToolButton { border: none; }')
        self.button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.button.toggled.connect(self.toggled)

        self.frame = QtWidgets.QFrame()
        if border:
            self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.button)
        layout.addWidget(self.frame)

        self.button.setChecked(True)
        self.button.toggle()

    def toggled(self, checked):
        self.button.setArrowType(QtCore.Qt.DownArrow if checked else QtCore.Qt.RightArrow)
        self.frame.setMaximumHeight(max(QWIDGETSIZE_MAX, 0) if checked else 0)

    def setLayout(self, layout):
        self.frame.setLayout(layout)

    def addWidget(self, widget, *args, **kwargs):
        if not self.frame.layout():
            layout = QtWidgets.QVBoxLayout(self.frame)
            layout.setSpacing(0)
            layout.setContentsMargins(0, 0, 0, 0)

        self.frame.layout().addWidget(widget, *args, **kwargs)

    def layout(self):
        return self.frame.layout()


class VerticalScrollArea(QtWidgets.QScrollArea):
    # ScrollArea widget that has a minimum width based on its content

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)

    def eventFilter(self, watched, event):
        if watched == self.verticalScrollBar():
            if event.type() in (QtCore.QEvent.Show, QtCore.QEvent.Hide) and self.widget():
                min_width = self.widget().minimumSizeHint().width()
                if event.type() == QtCore.QEvent.Show:
                    min_width += self.verticalScrollBar().sizeHint().width()
                self.setMinimumWidth(min_width)
        return super().eventFilter(watched, event)

    def update(self):
        min_width = self.widget().minimumSizeHint().width()
        self.setMinimumWidth(min_width)


def main():
    import sys
    import widgets
    from enum import Enum
    import logging

    logging.getLogger().setLevel(logging.DEBUG)

    app = QtWidgets.QApplication()
    editor = PropertyEditor()

    enum = Enum('Number', ('one', 'two', 'three'))

    editor.add_property(widgets.IntProperty('int'))
    editor.add_property(widgets.FloatProperty('float'))
    editor.add_property(widgets.Int2Property('int2'))
    editor.add_property(widgets.Float2Property('float2'))
    editor.add_property(widgets.BoolProperty('bool'))
    editor.add_property(widgets.PathProperty('path'))
    editor.add_property(widgets.ColorProperty('color'))
    editor.add_property(widgets.EnumProperty('enum', enum=enum))

    editor.add_property(widgets.IntProperty('int'), tab='tab1')
    editor.add_property(widgets.FloatProperty('float'), tab='tab1')

    editor.add_property(widgets.IntProperty('int'), tab='tab2')
    editor.add_property(widgets.FloatProperty('float'), tab='tab2')

    editor.add_property(widgets.IntProperty('int'), group='group1')
    editor.add_property(widgets.FloatProperty('float'), group='group1')

    editor.create_property_group('group1', tab='tab1', collapsible=True)

    editor.add_property(widgets.IntProperty('int'), group='group1', tab='tab1')
    editor.add_property(widgets.FloatProperty('float'), group='group1', tab='tab1')

    editor.create_property_group('group2', tab='tab2', link=editor.groups['tab1']['group1'])

    editor.values_changed.connect(logging.debug)
    editor.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
