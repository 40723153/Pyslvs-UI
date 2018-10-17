# -*- coding: utf-8 -*-

"""The widget of 'Triangular iteration' tab."""

__author__ = "Yuan Chang"
__copyright__ = "Copyright (C) 2016-2018"
__license__ = "AGPL"
__email__ = "pyslvs@gmail.com"

from typing import (
    Dict,
    Tuple,
    Sequence,
    Set,
    Callable,
    Any,
    Optional,
)
from math import hypot
import pprint
from networkx import Graph
from core.QtModules import (
    Qt,
    pyqtSignal,
    QWidget,
    pyqtSlot,
    QMessageBox,
    QInputDialog,
    QListWidgetItem,
    QLabel,
    QApplication,
)
from core.graphics import (
    PreviewCanvas,
    edges_view,
    graph2vpoints,
)
from core.io import str_before, str_between
from core.libs import vpoints_configure
from .ti_dialog import (
    CollectionsDialog,
    ConstraintsDialog,
    CustomsDialog,
    TargetsDialog,
    SolutionsDialog,
    list_texts,
    list_items,
)
from .Ui_triangular_iteration_widget import Ui_Form


class _PreviewWindow(PreviewCanvas):

    """Customized preview window has some functions of mouse interaction.

    Emit signal call to change current point when pressed a dot.
    """

    set_joint_number = pyqtSignal(int)

    def __init__(self, get_solutions: Callable[[], str], parent: QWidget):
        """Add a function use to get current point from parent."""
        super(_PreviewWindow, self).__init__(get_solutions, parent)
        self.pressed = False
        self.get_joint_number = parent.joint_name.currentIndex

    def mousePressEvent(self, event):
        """Check if get close to a joint."""
        mx = (event.x() - self.ox) / self.zoom
        my = (event.y() - self.oy) / -self.zoom
        for node, (x, y) in self.pos.items():
            if node in self.same:
                continue
            if hypot(x - mx, y - my) <= 5:
                self.set_joint_number.emit(node)
                self.pressed = True
                break

    def mouseReleaseEvent(self, event):
        """Cancel the drag."""
        self.pressed = False

    def mouseMoveEvent(self, event):
        """Drag to move the joint."""
        if not self.pressed:
            return
        row = self.get_joint_number()
        if not row > -1:
            return
        mx = (event.x() - self.ox) / self.zoom
        my = (event.y() - self.oy) / -self.zoom
        if -120 <= mx <= 120:
            self.pos[row] = (mx, self.pos[row][1])
        else:
            self.pos[row] = (120 if -120 <= mx else -120, self.pos[row][1])
        if -120 <= my <= 120:
            self.pos[row] = (self.pos[row][0], my)
        else:
            self.pos[row] = (self.pos[row][0], 120 if -120 <= my else -120)
        self.update()


def _set_warning(label: QLabel, warning: bool):
    """Show a warning sign front of label."""
    warning_icon = "<img width=\"15\" src=\":/icons/warning.png\"/> "
    label.setText(label.text().replace(warning_icon, ''))
    if warning:
        label.setText(warning_icon + label.text())


class TriangularIterationWidget(QWidget, Ui_Form):

    """Triangular iteration widget.

    This interface use to modify structure profile.
    """

    def __init__(
        self,
        add_collection: Callable[[Sequence[Tuple[int, int]]], None],
        parent: QWidget
    ):
        """We need some function from structure collections."""
        super(TriangularIterationWidget, self).__init__(parent)
        self.setupUi(self)
        self.unsaveFunc = parent.workbookNoSave
        self.getCollection = parent.getCollection
        self.addCollection = add_collection

        # Iteration data.
        self.collections: Dict[str, Dict[str, Any]] = {}

        # Customized preview canvas.
        self.PreviewWindow = _PreviewWindow(
            lambda: ';'.join(
                self.expression_list.item(row).text()
                for row in range(self.expression_list.count())
            ),
            self
        )
        self.PreviewWindow.set_joint_number.connect(
            self.joint_name.setCurrentIndex
        )
        self.main_layout.insertWidget(0, self.PreviewWindow)
        self.show_solutions.clicked.connect(self.PreviewWindow.setShowSolutions)

        # Signals
        self.joint_name.currentIndexChanged.connect(self.__has_solution)
        self.clear()

    def addCollections(self, collections: Dict[str, Dict[str, Any]]):
        """Update the new collections."""
        self.collections.update(collections)

    def clear(self):
        """Clear all sub-widgets."""
        self.collections.clear()
        self.__clear_panel()

    def __clear_panel(self):
        """Clear the settings of sub-widgets."""
        self.profile_name = ""
        self.PreviewWindow.clear()
        self.joint_name.clear()
        self.expression_list.clear()
        self.grounded_list.clear()
        self.driver_list.clear()
        self.follower_list.clear()
        self.target_list.clear()
        self.constraint_list.clear()
        self.link_expr_show.clear()
        self.expr_show.clear()
        for label in [
            self.expression_list_label,
            self.grounded_label,
            self.driver_label,
            self.follower_label,
            self.target_label
        ]:
            _set_warning(label, True)

    @pyqtSlot(name='on_clear_button_clicked')
    def __user_clear(self):
        """Ask user before clear."""
        reply = QMessageBox.question(
            self,
            "New profile",
            "Triangular iteration should be added structure diagrams "
            "from structure collections.\n"
            "Do you want to create a new profile?"
        )
        if reply == QMessageBox.Yes:
            self.__clear_panel()

    @pyqtSlot(name='on_add_collection_button_clicked')
    def __add_collection(self):
        """Add the graph back to structure collections."""
        self.addCollection(tuple(self.PreviewWindow.G.edges))

    @pyqtSlot(Graph, dict)
    def setGraph(
        self,
        graph: Graph,
        pos: Dict[int, Tuple[float, float]]
    ):
        """Set the graph to preview canvas."""
        self.__clear_panel()
        self.PreviewWindow.setGraph(graph, pos)
        ev = dict(edges_view(graph))
        joints_count = set()
        for l1, l2 in ev.values():
            joints_count.update({l1, l2})
        links = []
        for i in range(len(joints_count)):
            links.append([])
        for joint, link in ev.items():
            for node in link:
                links[node].append(joint)
        for link in links:
            points_text = ", ".join(f'P{node}' for node in link)
            self.grounded_list.addItem(f"({points_text})")
        # Point name as (P1, P2, P3, ...).
        for node in pos:
            self.joint_name.addItem(f'P{node}')

    @pyqtSlot(int, name='on_grounded_list_currentRowChanged')
    def __set_ground(self, row: int):
        """Change current grounded link. Reset all settings."""
        has_choose = row > -1
        _set_warning(self.grounded_label, not has_choose)
        self.PreviewWindow.setGrounded(row)
        self.__has_solution()
        self.expression_list.clear()
        self.expr_show.clear()
        self.follower_list.clear()
        self.driver_list.clear()
        self.driver_base.clear()
        self.driver_rotator.clear()
        if has_choose:
            items = (
                self.grounded_list.item(row).text()
                .replace('(', '')
                .replace(')', '')
                .split(", ")
            )
            self.follower_list.addItems(items)
            self.driver_base.addItems(items)
        _set_warning(self.follower_label, not has_choose)
        _set_warning(self.driver_label, True)
        _set_warning(self.expression_list_label, True)
        if row != self.grounded_list.currentRow():
            self.grounded_list.blockSignals(True)
            self.grounded_list.setCurrentRow(row)
            self.grounded_list.blockSignals(False)

    @pyqtSlot(str, name='on_driver_base_currentIndexChanged')
    def __set_driver_base(self, name: str):
        self.driver_rotator.clear()
        if not name:
            return

        def find_friends(node: int):
            """Find all the nodes that are same link with input node."""
            ev = dict(edges_view(self.PreviewWindow.G))
            link = set(ev[node])
            tmp_list = []
            for node_, link_ in ev.items():
                if node_ == node:
                    continue
                if set(link_) & link:
                    tmp_list.append(f'P{node_}')
            return tmp_list

        self.driver_rotator.addItems(find_friends(int(name.replace('P', ''))))

    @pyqtSlot(name='on_driver_add_clicked')
    def __add_driver(self):
        """Add a driver joint."""
        d1 = self.driver_base.currentText()
        d2 = self.driver_rotator.currentText()
        if not (d1 and d2):
            return
        d1_d2 = f"({d1}, {d2})"
        for n in list_texts(self.driver_list):
            if n == d1_d2:
                return
        self.__find_follower_to_remove(d1)
        self.driver_list.addItem(d1_d2)
        self.PreviewWindow.setDriver([
            eval(n.replace('P', ''))[0] for n in list_texts(self.driver_list)
        ])
        _set_warning(self.driver_label, False)

    @pyqtSlot(name='on_follower_add_clicked')
    def __add_follower(self):
        """Add a follower joint."""
        row = self.driver_list.currentRow()
        if not row > -1:
            return
        if not self.__clear_expr():
            return
        d1_d2 = self.driver_list.item(row).text()
        d1, d2 = eval(d1_d2.replace('P', ''))
        self.__find_follower_to_add(f'P{d1}')
        self.driver_list.takeItem(row)
        _set_warning(self.driver_label, not self.driver_list.count())

    def __find_follower_to_remove(self, name: str):
        """Remove node if it is in the list."""
        finds = self.follower_list.findItems(name, Qt.MatchExactly)
        for d in finds:
            self.follower_list.takeItem(self.follower_list.row(d))

    def __find_follower_to_add(self, name: str):
        """Add name if it is not in the list."""
        if self.follower_list.findItems(name, Qt.MatchExactly):
            return
        self.follower_list.addItem(name)

    @pyqtSlot(int)
    def __has_solution(self, index: Optional[int] = None):
        """Set buttons enable if there has solution."""
        if index is None:
            index = self.joint_name.currentIndex()
        if not index > -1:
            self.status_show.setText("N/A")
            self.PLAP_solution.setEnabled(False)
            self.PLLP_solution.setEnabled(False)
            return
        status = self.PreviewWindow.getStatus(index)
        if not status:
            status_str = "Not known."
        elif index in self.PreviewWindow.same:
            status_str = f"Same as P{self.PreviewWindow.same[index]}."
        else:
            status_str = "Grounded."
            for expr in list_texts(self.expression_list):
                if index == int(str_between(expr, '(', ')').replace('P', '')):
                    status_str = f"From {str_before(expr, '[')}."
        self.status_show.setText(status_str)
        self.PLAP_solution.setEnabled(not status)
        self.PLLP_solution.setEnabled(not status)

    @pyqtSlot(name='on_add_customization_clicked')
    def __add_cus(self):
        """Show up custom joints dialog."""
        dlg = CustomsDialog(self)
        dlg.show()
        dlg.exec_()
        self.PreviewWindow.update()

    def __get_current_mechanism_params(self) -> Dict[str, Any]:
        """Get the current mechanism parameters."""
        self.__set_parm_bind()
        return {
            # To keep the origin graph.
            'Graph': tuple(self.PreviewWindow.G.edges),
            # To keep the position of points.
            'pos': self.PreviewWindow.pos.copy(),
            'cus': self.PreviewWindow.cus.copy(),
            'same': self.PreviewWindow.same.copy(),
            # Mechanism params.
            'Driver': {
                s.split(',')[0][1:]: None for s in list_texts(self.driver_list)
                if not self.PreviewWindow.isMultiple(s.split(',')[0][1:])
            },
            'Follower': {
                s: None for s in list_texts(self.follower_list)
                if not self.PreviewWindow.isMultiple(s)
            },
            'Target': {
                s: None for s in list_texts(self.target_list)
            },
            'Link_expr': self.link_expr_show.text(),
            'Expression': self.expr_show.text(),
            'constraints': [
                tuple(s.split(", "))
                for s in list_texts(self.constraint_list)
            ],
        }

    @pyqtSlot(name='on_load_button_clicked')
    def __load_data_base(self):
        """Show up the dialog to load structure data."""
        dlg = CollectionsDialog(
            self.collections,
            self.getCollection,
            self
        )
        dlg.show()
        if not dlg.exec_():
            return
        self.profile_name = dlg.name()
        params = dlg.params()
        # Add customize joints.
        graph = Graph(params['Graph'])
        self.setGraph(graph, params['pos'])
        self.PreviewWindow.cus = params['cus']
        self.PreviewWindow.same = params['same']
        # Grounded setting.
        drivers = set(params['Driver'])
        followers = set(params['Follower'])
        for row, link in enumerate(graph.nodes):
            points = {f'P{n}' for n, edge in edges_view(graph) if link in edge}
            if (drivers | followers) <= points:
                self.__set_ground(row)
                break
        # Driver, Follower, Target
        for expr in params['Expression'].split(';'):
            if str_before(expr, '[') != 'PLAP':
                continue
            base = str_between(expr, '[', ']').split(',')[0]
            self.__find_follower_to_remove(base)
            rotator = str_between(expr, '(', ')')
            self.driver_list.addItem(f"({base}, {rotator})")
        _set_warning(self.driver_label, not self.driver_list.count())
        self.target_list.addItems(list(params['Target']))
        _set_warning(self.target_label, not self.target_list.count() > 0)
        # Constraints
        self.constraint_list.addItems([
            ", ".join(c) for c in params['constraints']
        ])
        # Expression
        if params['Expression']:
            for expr in params['Expression'].split(';'):
                func = str_before(expr, '[')
                target = str_between(expr, '(', ')')
                params = str_between(expr, '[', ']').split(',')
                params.insert(0, func)
                params.append(target)
                self.__add_solution(*params)
                self.PreviewWindow.setStatus(target, True)
        _set_warning(self.expression_list_label, not self.PreviewWindow.isAllLock())

    @pyqtSlot(name='on_constraints_button_clicked')
    def __set_constraints(self):
        """Show up constraint dialog."""
        dlg = ConstraintsDialog(self)
        dlg.show()
        if not dlg.exec_():
            return
        self.constraint_list.clear()
        for constraint in list_texts(dlg.main_list):
            self.constraint_list.addItem(constraint)

    @pyqtSlot(name='on_target_button_clicked')
    def __set_target(self):
        """Show up target joints dialog."""
        dlg = TargetsDialog(self)
        dlg.show()
        if not dlg.exec_():
            return
        self.target_list.clear()
        for target in list_texts(dlg.targets_list):
            self.target_list.addItem(target)
        _set_warning(self.target_label, not self.target_list.count() > 0)

    def __symbols(self) -> Set[str]:
        """Return all symbols."""
        expr_list = set()
        for expr in self.expr_show.text().split(';'):
            param_list = str_between(expr, '[', ']').split(',')
            param_list.append(str_between(expr, '(', ')'))
            expr_list.update(param_list)
        return expr_list

    def __get_param(self, angle: bool =False) -> int:
        """Get the link / angle parameter number."""
        i = 0
        p = ('a' if angle else 'L')
        while p + str(i) in self.__symbols():
            i += 1
        return i

    @pyqtSlot(name='on_PLAP_solution_clicked')
    def __add_plap(self):
        """Show up dialog to add a PLAP solution."""
        dlg = SolutionsDialog('PLAP', self)
        dlg.show()
        if not dlg.exec_():
            return
        point = self.joint_name.currentText()
        self.__add_solution(
            "PLAP",
            dlg.point_A.currentText(),
            f'L{self.__get_param()}',
            f'a{self.__get_param(angle=True)}',
            point
        )

    @pyqtSlot(name='on_PLLP_solution_clicked')
    def __add_pllp(self):
        """Show up dialog to add a PLLP solution."""
        dlg = SolutionsDialog('PLLP', self)
        dlg.show()
        if not dlg.exec_():
            return
        point = self.joint_name.currentText()
        link_num = self.__get_param()
        self.__add_solution(
            "PLLP",
            dlg.point_A.currentText(),
            f'L{link_num}',
            f'L{link_num + 1}',
            dlg.point_B.currentText(),
            point
        )

    def __add_solution(self, *expr: str):
        """Add a solution."""
        item = QListWidgetItem()
        self.expression_list.addItem(item)
        item.setText(f"{expr[0]}[{','.join(expr[1:-1])}]({expr[-1]})")
        self.PreviewWindow.setStatus(expr[-1], True)
        self.__set_parm_bind()
        self.__has_solution()
        _set_warning(self.expression_list_label, not self.PreviewWindow.isAllLock())

    @pyqtSlot(QListWidgetItem)
    def __set_parm_bind(self, _: QListWidgetItem):
        """Set parameters binding."""
        self.expr_show.setText(';'.join(list_texts(self.expression_list)))
        link_expr_list = []
        for row, gs in list_texts(self.grounded_list, True):
            try:
                link_expr = []
                # Links from grounded list.
                for name in gs.replace('(', '').replace(')', '').split(", "):
                    if self.PreviewWindow.isMultiple(name):
                        i = self.PreviewWindow.same[int(name.replace('P', ''))]
                        name = f'P{i}'
                    link_expr.append(name)
            except KeyError:
                continue
            else:
                # Customize joints.
                for joint, link in self.PreviewWindow.cus.items():
                    if row == link:
                        link_expr.append(joint)
                link_expr_str = ','.join(sorted(set(link_expr)))
                if row == self.grounded_list.currentRow():
                    link_expr_list.insert(0, link_expr_str)
                else:
                    link_expr_list.append(link_expr_str)
        self.link_expr_show.setText(';'.join(
            ('ground' if i == 0 else '') + f"[{link}]"
            for i, link in enumerate(link_expr_list)
        ))

    @pyqtSlot(name='on_expression_auto_clicked')
    def __auto_configure(self):
        """Auto configure the solutions."""
        if not self.driver_list.count():
            QMessageBox.information(
                self,
                "Auto configure",
                "Please setting the driver joint(s)."
            )
            return
        reply = QMessageBox.question(
            self,
            "Auto configure",
            "This function can detect the structure "
            "to configure the solutions.\n"
            "The current settings will be cleared."
        )
        if (reply != QMessageBox.Yes) or (not self.__clear_expr()):
            return
        exprs = vpoints_configure(
            graph2vpoints(
                self.PreviewWindow.G,
                self.PreviewWindow.pos,
                self.PreviewWindow.cus,
                self.PreviewWindow.same
            ),
            [eval(item.text().replace('P', ''))
                for item in list_items(self.driver_list)],
            self.PreviewWindow.status
        )
        for expr in exprs:
            self.__add_solution(*expr)
        self.__has_solution()
        self.__setWarning(
            self.expression_list_label,
            not self.PreviewWindow.isAllLock()
        )
        self.PreviewWindow.update()

    @pyqtSlot(name='on_expression_pop_clicked')
    def __pop_expr(self):
        """Remove the last solution."""
        count = self.expression_list.count()
        if not count:
            return
        expr = self.expression_list.item(count-1).text()
        self.expression_list.takeItem(count-1)
        self.PreviewWindow.setStatus(str_between(expr, '(', ')'), False)
        self.__set_parm_bind()

    @pyqtSlot(name='on_expression_clear_clicked')
    def __clear_expr(self) -> bool:
        """Clear the solutions. Return true if succeeded."""
        if not self.expression_list.count():
            return True
        reply = QMessageBox.question(
            self,
            "Clear the solutions",
            "Are you sure to clear the solutions?"
        )
        if reply != QMessageBox.Yes:
            return False
        self.PreviewWindow.setGrounded(self.grounded_list.currentRow())
        self.expression_list.clear()
        self.expr_show.clear()
        self.__has_solution()
        return True

    @pyqtSlot(name='on_save_button_clicked')
    def __save(self):
        """Save the profile to database."""
        if self.profile_name:
            name = self.profile_name
            ok = True
        else:
            name, ok = QInputDialog.getText(
                self,
                "Profile name",
                "Please enter the profile name:"
            )
        if not ok:
            return
        i = 0
        while (name not in self.collections) and (not name):
            name = f"Structure_{i}"
        self.collections[name] = self.__get_current_mechanism_params()
        self.profile_name = name
        self.unsaveFunc()

    @pyqtSlot(name='on_clipboard_button_clicked')
    def __copy(self):
        """Copy the mechanism params."""
        QApplication.clipboard().setText(
            pprint.pformat(self.__get_current_mechanism_params())
        )