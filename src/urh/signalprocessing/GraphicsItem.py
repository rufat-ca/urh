from PyQt5.QtWidgets import QGraphicsObject, QGraphicsItem, QGraphicsTextItem, QGraphicsSceneDragDropEvent, QAbstractItemView
from PyQt5.QtGui import QFontDatabase, QFont, QDropEvent, QPen, QColor, QBrush
from PyQt5.QtCore import QRectF, Qt, QLineF

from urh import constants

from urh.signalprocessing.SimulatorItem import SimulatorItem
from urh.signalprocessing.SimulatorRule import SimulatorRule
from urh.signalprocessing.SimulatorMessage import SimulatorMessage
from urh.signalprocessing.SimulatorProtocolLabel import SimulatorProtocolLabel

class GraphicsItem(QGraphicsObject):
    font = None

    def __init__(self, model_item: SimulatorItem, parent=None):
        super().__init__(parent)
        self.model_item = model_item

        self.hover_active = False
        self.drag_over = False

        self.bounding_rect = QRectF()
        self.drop_indicator_position = None
        self.item_under_mouse = None

        GraphicsItem.font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        GraphicsItem.font.setPointSize(8)

        font_bold = QFont(GraphicsItem.font)
        font_bold.setWeight(QFont.DemiBold)

        self.number = QGraphicsTextItem(self)
        self.number.setFont(font_bold)

    def set_flags(self, is_selectable=False, is_movable=False, accept_hover_events=False, accept_drops=False):
        self.setFlag(QGraphicsItem.ItemIsSelectable, is_selectable)
        self.setFlag(QGraphicsItem.ItemIsMovable, is_movable)
        self.setAcceptHoverEvents(accept_hover_events)
        self.setAcceptDrops(accept_drops)

    def update_flags(self):
        pass
        
    def hoverEnterEvent(self, event):
        self.hover_active = True
        self.update()

    def hoverLeaveEvent(self, event):
        self.hover_active = False
        self.update()

    def dragEnterEvent(self, event: QGraphicsSceneDragDropEvent):
        self.drag_over = True
        self.update()

    def dragLeaveEvent(self, event: QGraphicsSceneDragDropEvent):
        self.drag_over = False
        self.update()

    def dropEvent(self, event: QDropEvent):
        self.drag_over = False
        self.update()

    def dragMoveEvent(self, event: QDropEvent):
        self.update_drop_indicator(event.pos())

    def get_scene_children(self):
        return [self.scene().model_to_scene(child) for child in self.model_item.children]

    def is_selectable(self):
        return self.flags() & QGraphicsItem.ItemIsSelectable

    def is_movable(self):
        return self.flags() & QGraphicsItem.ItemIsMovable

    def select_all(self):
        self.setSelected(True)

        for child in self.get_scene_children():
            child.select_all()

    def next(self):
        if not self.scene():
            return None

        next_item = self.model_item

        while next_item is not None:
            next_item = next_item.next()

            if (not isinstance(next_item, SimulatorProtocolLabel) and
                    not isinstance(next_item, SimulatorRule)):
                break

        return self.scene().model_to_scene(next_item)

    def prev(self):
        prev_item = self.model_item

        while prev_item is not None:
            prev_item = prev_item.prev()

            if (not isinstance(prev_item, SimulatorProtocolLabel) and
                    not isinstance(prev_item, SimulatorRule)):
                break

        return self.scene().model_to_scene(prev_item)

    def update_drop_indicator(self, pos):
        rect = self.boundingRect()

        if pos.y() - rect.top() < rect.height() / 2:
            self.drop_indicator_position = QAbstractItemView.AboveItem
        else:
            self.drop_indicator_position = QAbstractItemView.BelowItem

        self.update()

    def paint(self, painter, option, widget):
        if self.hover_active or self.isSelected():
            painter.setOpacity(constants.SELECTION_OPACITY)
            painter.setBrush(constants.SELECTION_COLOR)
            painter.setPen(QPen(QColor(Qt.transparent), Qt.FlatCap))
            painter.drawRect(self.boundingRect())

        if self.drag_over:
            self.paint_drop_indicator(painter)

    def paint_drop_indicator(self, painter):
        brush = QBrush(QColor(Qt.darkRed))
        pen = QPen(brush, 2, Qt.SolidLine)
        painter.setPen(pen)
        rect = self.boundingRect()

        if self.drop_indicator_position == QAbstractItemView.AboveItem:
            painter.drawLine(QLineF(rect.topLeft(), rect.topRight()))
        else:
            painter.drawLine(QLineF(rect.bottomLeft(), rect.bottomRight()))

    def update_position(self, x_pos, y_pos):
        width = self.scene().items_width()
        self.prepareGeometryChange()
        self.bounding_rect = QRectF(0, 0, width, self.childrenBoundingRect().height())

    def refresh(self):
        pass

    def boundingRect(self):
        return self.bounding_rect

    def update_numbering(self):
        self.number.setPlainText(self.model_item.index())

        for child in self.get_scene_children():
            child.update_numbering()

    def mouseMoveEvent(self, event):
        items = []

        for item in self.scene().items(event.scenePos()):
            if isinstance(item, GraphicsItem) and item != self and item.acceptDrops():
                items.append(item)

        item = None if len(items) == 0 else items[0]

        if self.item_under_mouse and self.item_under_mouse != item:
            self.item_under_mouse.dragLeaveEvent(None)
            self.item_under_mouse = None

            if item:
                self.item_under_mouse = item
                self.item_under_mouse.dragEnterEvent(None)
        elif self.item_under_mouse and self.item_under_mouse == item:
            self.item_under_mouse.update_drop_indicator(self.mapToItem(self.item_under_mouse, event.pos()))
        elif item:
            self.item_under_mouse = item
            self.item_under_mouse.dragEnterEvent(None)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.item_under_mouse:
            self.item_under_mouse.dragLeaveEvent(None)
            self.item_under_mouse.setSelected(False)
            drag_nodes = self.scene().get_drag_nodes()

            ref_item = self.item_under_mouse
            position = self.item_under_mouse.drop_indicator_position

            self.scene().move_items(drag_nodes, ref_item, position)

            self.item_under_mouse = None

        super().mouseReleaseEvent(event)
        self.scene().update_view()