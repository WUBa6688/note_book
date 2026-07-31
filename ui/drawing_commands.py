"""
Zhuibook 画板撤销/重做命令（基于 QUndoCommand）

PyQt6 中 QUndoCommand 与 QUndoStack 均位于 PyQt6.QtGui。

注意：为兼容前端 drawing_board.py 的调用方式（AddItemCommand(scene, item) /
RemoveItemsCommand(scene, items)）与任务规范顺序（item/scene 先后），
AddItemCommand 与 RemoveItemsCommand 的构造函数对前两个参数做了类型自动识别，
两种调用顺序均可正常工作。

所有命令的 mergeWith() 均返回 False（不与相邻命令合并）。
"""
from __future__ import annotations

from typing import List, Tuple

from PyQt6.QtGui import QUndoCommand
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsItem


class AddItemCommand(QUndoCommand):
    """添加图形项到场景。

    支持两种参数顺序：
      AddItemCommand(scene, item)        —— 前端 drawing_board.py 调用方式
      AddItemCommand(item, scene)        —— 任务规范顺序
    redo/undo 做了幂等保护，避免对已在/不在场景中的项重复操作产生警告。
    """

    def __init__(self, a, b, text: str = "添加图形"):
        super().__init__(text)
        # 自动识别 scene 与 item
        if isinstance(a, QGraphicsScene):
            self.scene = a
            self.item = b
        else:
            self.item = a
            self.scene = b

    def undo(self):
        if self.item is not None and self.item.scene() is self.scene:
            self.scene.removeItem(self.item)

    def redo(self):
        if self.item is not None and self.item.scene() is None:
            self.scene.addItem(self.item)

    def mergeWith(self, other: QUndoCommand) -> bool:
        return False


class RemoveItemsCommand(QUndoCommand):
    """移除多个图形项。

    支持两种参数顺序：
      RemoveItemsCommand(scene, items)   —— 前端调用方式
      RemoveItemsCommand(items, scene)   —— 任务规范顺序
    """

    def __init__(self, a, b, text: str = "删除图形"):
        super().__init__(text)
        if isinstance(a, QGraphicsScene):
            self.scene = a
            self.items: List[QGraphicsItem] = list(b) if b is not None else []
        else:
            self.items = list(a) if a is not None else []
            self.scene = b

    def undo(self):
        for it in self.items:
            if it is not None and it.scene() is None:
                self.scene.addItem(it)

    def redo(self):
        for it in self.items:
            if it is not None and it.scene() is self.scene:
                self.scene.removeItem(it)

    def mergeWith(self, other: QUndoCommand) -> bool:
        return False


class MoveItemsCommand(QUndoCommand):
    """移动多个图形项（记录新旧位置以支持撤销/重做）。

    参数顺序：items, old_positions, new_positions
      - items: 图形项列表
      - old_positions: 与 items 等长的 QPointF/坐标列表
      - new_positions: 与 items 等长的 QPointF/坐标列表
    """

    def __init__(self, items, old_positions, new_positions, text: str = "移动图形"):
        super().__init__(text)
        self.items = list(items) if items is not None else []
        self.old_positions = list(old_positions) if old_positions is not None else []
        self.new_positions = list(new_positions) if new_positions is not None else []

    def undo(self):
        for it, pos in zip(self.items, self.old_positions):
            if it is not None and pos is not None:
                it.setPos(pos)

    def redo(self):
        for it, pos in zip(self.items, self.new_positions):
            if it is not None and pos is not None:
                it.setPos(pos)

    def mergeWith(self, other: QUndoCommand) -> bool:
        return False


class ClearSceneCommand(QUndoCommand):
    """清空场景。

    redo() 时保存并移除场景中所有图形项；undo() 时恢复。
    可选 bg_item 参数用于跳过画布背景项（白色矩形），避免清空后画布变灰。
    """

    def __init__(self, scene, bg_item=None, text: str = "清空画布"):
        super().__init__(text)
        self.scene = scene
        self._bg = bg_item
        self._saved: List[QGraphicsItem] = []

    def undo(self):
        # 恢复之前保存的所有项
        for it in self._saved:
            if it is not None and it.scene() is None:
                self.scene.addItem(it)
        # 注意：不清空 _saved，以便再次 redo 复用

    def redo(self):
        # 保存当前所有项（排除背景项），然后逐个移除
        self._saved = [it for it in self.scene.items() if it is not self._bg]
        for it in self._saved:
            if it is not None and it.scene() is self.scene:
                self.scene.removeItem(it)

    def mergeWith(self, other: QUndoCommand) -> bool:
        return False
