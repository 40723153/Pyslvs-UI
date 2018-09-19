# -*- coding: utf-8 -*-

"""The chart dialog of dimensional synthesis result."""

__author__ = "Yuan Chang"
__copyright__ = "Copyright (C) 2016-2018"
__license__ = "AGPL"
__email__ = "pyslvs@gmail.com"

from core.QtModules import (
    QDialog,
    Qt,
    QSize,
    QVBoxLayout,
    QTabWidget,
    QCategoryAxis,
    QValueAxis,
    QLineSeries,
    QScatterSeries,
    QColor,
    QPointF,
    QWidget,
    QIcon,
    QChartView,
    QSizePolicy,
)
from core.graphics import DataChart


class ChartDialog(QDialog):
    
    """There are three charts are in the dialog.
    
    + Fitness / Generation Chart.
    + Generation / Time Chart.
    + Fitness / Time Chart.
    """
    
    def __init__(self, title, mechanism_data, parent: QWidget):
        """Add three tabs of chart."""
        super(ChartDialog, self).__init__(parent)
        self.setWindowTitle("Chart")
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.setSizeGripEnabled(True)
        self.setModal(True)
        self.setMinimumSize(QSize(800, 600))
        
        self.__title = title
        self.__mechanism_data = mechanism_data
        
        # Widgets
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(6, 6, 6, 6)
        self.tabWidget = QTabWidget(self)
        self.__setChart("Fitness / Generation Chart", 0, 1)
        self.__setChart("Generation / Time Chart", 2, 0)
        self.__setChart("Fitness / Time Chart", 2, 1)
        main_layout.addWidget(self.tabWidget)
    
    def __setChart(self, tab_name: str, pos_x: int, pos_y: int):
        """Setting charts by data index.
        
        pos_x / pos_y: [0], [1], [2]
        time_fitness: List[List[Tuple[gen, fitness, time]]]
        """
        axis_x = QCategoryAxis()
        axis_y = QValueAxis()
        axis_x.setLabelsPosition(QCategoryAxis.AxisLabelsPositionOnValue)
        axis_x.setMin(0)
        axis_y.setTickCount(11)
        
        if self.__mechanism_data:
            
            if type(self.__mechanism_data[0]['time_fitness'][0]) == float:
                plot = [[
                    (data['last_gen']*i/len(data['time_fitness']), tnf, 0)
                    for i, tnf in enumerate(data['time_fitness'])
                ] for data in self.__mechanism_data]
            else:
                # Just copy from __mechanism_data
                plot = [[tnf for tnf in data['time_fitness']] for data in self.__mechanism_data]

            # X max.
            max_x = int(max([max([tnf[pos_x] for tnf in data]) for data in plot]) * 100)
            axis_x.setMax(max_x)
            i10 = int(max_x / 10)
            if i10:
                for i in range(0, max_x + 1, i10):
                    axis_x.append(str(i / 100), i)
            else:
                for i in range(0, 1000, 100):
                    axis_x.append(str(i / 100), i)
            
            # Y max.
            max_y = max(max([tnf[pos_y] for tnf in data]) for data in plot) + 10
        else:
            plot = None
            # Y max.
            max_y = 100
        
        max_y -= max_y % 10
        axis_y.setRange(0., max_y)
        chart = DataChart(self.__title, axis_x, axis_y)
        
        # Append data set.
        for data in self.__mechanism_data:
            line = QLineSeries()
            scatter = QScatterSeries()
            gen = data['last_gen']
            tnf = plot[self.__mechanism_data.index(data)]
            points = tnf[:-1] if (tnf[-1] == tnf[-2]) else tnf
            line.setName(f"{data['Algorithm']}({gen} gen): {data['Expression']}")
            scatter.setMarkerSize(7)
            scatter.setColor(QColor(110, 190, 30))
            for i, e in enumerate(points):
                y = e[pos_y]
                x = e[pos_x] * 100
                line.append(QPointF(x, y))
                scatter.append(QPointF(x, y))
            for series in (line, scatter):
                chart.addSeries(series)
                series.attachAxis(axis_x)
                series.attachAxis(axis_y)
            chart.legend().markers(scatter)[0].setVisible(False)
        # Add chart into tab widget
        widget = QWidget()
        self.tabWidget.addTab(widget, QIcon(), tab_name)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        chart_view = QChartView(chart)
        chart_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(chart_view)