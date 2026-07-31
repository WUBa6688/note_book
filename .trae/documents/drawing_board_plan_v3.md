# Zhuibook 画板功能需求文档 V3（UI 重构 + 交互增强版）

> 本文档基于用户最新反馈重新设计。核心变化：**UI 重构为折叠分组面板**（类 Windows 画图 Ribbon 风格），**比例尺**、**滚轮缩放**、**按钮高亮**、**富文本工具**、**趣味光标**、**系统剪贴板粘贴**等功能同步加入。

---

## 一、用户需求汇总与优先级

### 1.1 用户 6 条建议

| # | 建议 | 风险等级 | 实现方案 |
|---|------|---------|---------|
| ① | UI 过于简洁单调，仿照 Windows 画图将功能收纳 | 高 | 折叠分组面板（CollapsibleSection），每个分组可展开/收起 |
| ② | 添加比例尺功能（画布上方和左侧） | 中 | 自定义 QWidget 绘制刻度，随缩放联动 |
| ③ | 鼠标滚轮控制画布放大/缩小 | 低 | 重写 `wheelEvent` |
| ④ | 点击按钮时变色高亮 | 低 | 确保 QSS `:checked` 样式正确应用 |
| ⑤ | 文字工具改为富文本输入（字体/加粗等），可拖动 | 中 | 小型格式工具栏 + 点击画布即可输入 + ItemIsMovable |
| ⑥ | 工具光标趣味化（画笔变画笔形状等） | 低 | 用 QPixmap 构造自定义 QCursor |

### 1.2 系统补充功能

| # | 补充 | 说明 |
|---|------|------|
| ⑦ | 系统剪贴板粘贴图片 | `Ctrl+V` 可直接粘贴剪贴板中的图片到画板 |
| ⑧ | 全选 + Delete 删除 | 选中图形后按 Delete 键删除 |
| ⑨ | 工具快捷键提示 | 每个工具按钮 tooltip 显示快捷键 |

### 1.3 实施优先级

按"先易后难、先低后高"原则分三批实施：

- **第一批（快速见效）**：③滚轮缩放、④按钮高亮、⑥趣味光标、⑨快捷键提示
- **第二批（核心增强）**：②比例尺、⑤富文本工具、⑦系统剪贴板、⑧Delete 删除
- **第三批（UI 重构）**：①折叠分组面板（最大工作量，需充分测试）

---

## 二、UI 重构方案

### 2.1 新布局（折叠分组面板风格）

```
┌──────────────────────────────────────────────────────────────────────┐
│ [📝 笔记] [🖌 画板]                                                   │
├──────────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │ ▼ 📁 文件                              [保存] [插入笔记]            │ │
│ ├──────────────────────────────────────────────────────────────────┤ │
│ │ ▼ 🖊 绘制工具                          [画笔][喷枪][刷子][橡皮]    │ │
│ │                                        [取色][填充][文字]          │ │
│ ├──────────────────────────────────────────────────────────────────┤ │
│ │ ▼ ➡️ 形状工具                          [直线][曲线][矩形][圆角]   │ │
│ │                                        [椭圆][三角][星形][箭头]   │ │
│ │                                        [对话框]                   │ │
│ ├──────────────────────────────────────────────────────────────────┤ │
│ │ ▼ 🎨 颜色与样式                        [色板...] [自定义]           │ │
│ │                                        粗细: ▬▬●▬▬  空心/实心     │ │
│ ├──────────────────────────────────────────────────────────────────┤ │
│ │ ▼ 🧭 选择与操作                        [矩形选][自由选][全选]     │ │
│ │                                        [复制][剪切][粘贴][删除]   │ │
│ ├──────────────────────────────────────────────────────────────────┤ │
│ │ ▼ 🔍 视图控制                          [放大][缩小][100%][适应]   │ │
│ │                                        滚轮缩放: 开/关            │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│ ┌─────┐┌────────────────────────────────────────────────────────────┐ │
│ │ 400 ││                                                            │ │
│ │ 300 ││                                                            │ │
│ │ 200 ││                                                            │ │
│ │ 100 ││                     画布（白色 800×600）                      │ │
│ │   0 ││                                                            │ │
│ │     ││                                                            │ │
│ └─────┘│────────────────────────────────────────────────────────────│ │
│       0  100  200  300  400  500  600  700  800                     │
│ ─────────────────────────────────────────────────────────────────── │
│ 坐标(120, 85)  缩放100%  画布800×600  当前工具:画笔  鼠标滚轮缩放:开   │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 折叠分组组件设计

新增 `CollapsibleSection` 组件（自定义 QWidget）：

```
┌──────────────────────────────────────┐
│ ▼ 📁 文件                         ▼  │ ← 标题栏（可点击折叠/展开）
├──────────────────────────────────────┤
│ [保存为文件] [插入到笔记]              │ ← 内容区（可展开/收起）
│ [导出 PNG] [导出 JPG]                 │
└──────────────────────────────────────┘
```

**交互行为**：
- 点击标题栏切换展开/收起状态
- 展开时高度自适应内容
- 收起时仅显示标题栏（高度 ~36px）
- 标题左侧有 ▼/▶ 箭头图标
- 标题文字加粗，使用主题 `text_primary`
- 分组间有 4px 间距

### 2.3 分组内容与工具映射

| 分组 | 图标 | 内容 |
|------|------|------|
| 📁 文件 | 保存/插入笔记 | 保存为文件、插入到笔记、导出 PNG、导出 JPG |
| 🖊 绘制工具 | 画笔/喷枪/刷子/橡皮/取色/填充/文字 | 9 个绘图工具按钮 |
| ➡️ 形状工具 | 直线/曲线/矩形/圆角矩形/椭圆/三角/星形/箭头/对话框 | 9 个形状工具按钮 |
| 🎨 颜色与样式 | 色板（20 色）+ 自定义 + 粗细滑块 + 空心/实心切换 | 颜色选择区 |
| 🧭 选择与操作 | 矩形选/自由选/全选 + 复制/剪切/粘贴/删除 + 撤销/重做/清空 | 选择与操作按钮 |
| 🔍 视图控制 | 放大/缩小/100%/适应窗口 + 滚轮缩放开关 | 视图控制按钮 |

### 2.4 比例尺设计

```
        0   100   200   300   400   500   600   700   800
       ├─────┼─────┼─────┼─────┼─────┼─────┼─────┼─────┤  ← 水平标尺
   400 ┤                                                  │
   300 ┤                                                  │
   200 ┤              画布（白色）                          │  ← 垂直标尺
   100 ┤                                                  │
     0 ┤                                                  │
       └──────────────────────────────────────────────────┘
```

**比例尺规格**：
- **水平标尺**：画布上方，高度 ~24px，显示刻度 0~800
- **垂直标尺**：画布左侧，宽度 ~32px，显示刻度 0~600
- **刻度间距**：每 100px 一个主刻度（带数字标签），每 20px 一个次刻度
- **缩放联动**：缩放时刻度同步更新（200% 时刻度间距加倍）
- **鼠标指示**：鼠标移动时刻度上显示蓝色指示线
- **颜色**：主刻度 `text_primary`，次刻度 `text_secondary`，指示线 `accent`

### 2.5 按钮选中态高亮

**问题**：当前按钮选中态（checked）视觉反馈不够明显。

**解决方案**：
- 选中态背景色：`primary`（主题色，如 matcha 的 `#5B8DEF`）
- 选中态文字色：白色 `#FFFFFF`
- 选中态边框：`primary` 同色，宽度 1px
- 选中态字体：加粗 600
- 选中态阴影：`blurRadius=8, yOffset=1, alpha=20`
- 鼠标悬停选中按钮：颜色加深为 `primary_hover`
- QSS 实现：
  ```css
  QPushButton:checked {
      background: primary;
      color: #FFFFFF;
      border: 1px solid primary;
      border-radius: 8px;
      font-weight: 600;
  }
  QPushButton:checked:hover {
      background: primary_hover;
  }
  ```

### 2.6 趣味工具光标

每个工具激活时自动切换为对应形状的鼠标光标：

| 工具 | 光标样式 | 实现方式 |
|------|---------|---------|
| 画笔 | 画笔形状 | QPixmap 绘制 → QCursor |
| 喷枪 | 喷雾形状 | QPixmap 绘制 → QCursor |
| 刷子 | 刷子形状 | QPixmap 绘制 → QCursor |
| 橡皮 | 橡皮形状 | QPixmap 绘制 → QCursor |
| 取色器 | 吸管形状 | 使用 `Qt.CursorShape.CrossCursor`（系统内置） |
| 填充 | 油漆桶形状 | QPixmap 绘制 → QCursor |
| 文字 | 文本光标 | 使用 `Qt.CursorShape.IBeamCursor`（系统内置） |
| 选择 | 十字箭头 | 使用 `Qt.CursorShape.CrossCursor`（系统内置） |
| 直线/形状 | 十字光标 | 使用 `Qt.CursorShape.CrossCursor`（系统内置） |
| 默认 | 箭头 | 使用 `Qt.CursorShape.ArrowCursor` |

**实现方式**：
- 用 `QPainter` 在 `QPixmap` 上绘制简易图标（32×32px）
- 设置 `hotSpot` 为图标中心点或操作点
- 在 `BaseTool.activate()` 中调用 `view.setCursor(QCursor(pixmap, hotX, hotY))`
- 在 `BaseTool.deactivate()` 中恢复默认光标

### 2.7 滚轮缩放

**功能**：鼠标滚轮控制画布缩放。

```python
def wheelEvent(self, event: QWheelEvent):
    # Ctrl + 滚轮：缩放（覆盖 QGraphicsView 原生行为）
    if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
        delta = event.angleDelta().y()
        if delta > 0:
            self._board.set_zoom(min(800, self._board.zoom_level + 25))
        else:
            self._board.set_zoom(max(25, self._board.zoom_level - 25))
        event.accept()
    else:
        # 非 Ctrl 滚轮：正常上下平移（QGraphicsView 默认行为）
        super().wheelEvent(event)
```

**增强**：
- 状态栏显示"鼠标滚轮缩放: 开/关"
- 可在视图控制分组中切换滚轮缩放开关
- 缩放中心：以鼠标位置为中心缩放（`setTransformationAnchor(AnchorUnderMouse)`）

### 2.8 富文本工具

**当前**：`QInputDialog.getText()` 简单文本输入框。

**改为**：小型格式工具栏 + 画布上直接编辑。

```
┌─────────────────────────────────────────────┐
│ [字体▼] [8▼] [B] [I] [U] [S] [左对齐] [居中] │ ← 浮动格式工具栏
├─────────────────────────────────────────────┤
│                                             │
│        用户直接在画布上输入文字               │
│                                             │
└─────────────────────────────────────────────┘
```

**交互流程**：
1. 用户点击文字工具按钮 → 工具栏出现浮动格式工具栏
2. 用户点击画布位置 → 在该位置创建 `QGraphicsTextItem`
3. 用户直接输入文字（`QGraphicsTextItem` 支持 `setPlainText` + 内联编辑）
4. 用户选中文字 → 使用格式工具栏调整字体/大小/加粗/斜体/下划线等
5. 用户点击文字外任意位置 → 完成编辑
6. 文字默认 `ItemIsMovable + ItemIsSelectable` → 可拖动

**格式工具栏**：
| 控件 | 说明 |
|------|------|
| QFontComboBox | 字体选择（使用系统字体列表） |
| QSpinBox | 字号（1~99） |
| QToolButton(B) | 加粗 |
| QToolButton(I) | 斜体 |
| QToolButton(U) | 下划线 |
| QToolButton(S) | 删除线 |
| QToolButton(左) | 左对齐 |
| QToolButton(中) | 居中对齐 |
| QToolButton(右) | 右对齐 |
| QColorDialog 按钮 | 文字颜色 |

### 2.9 系统剪贴板粘贴

**功能**：按 `Ctrl+V` 可直接粘贴系统剪贴板中的图片到画板。

```python
def keyPressEvent(self, event: QKeyEvent):
    if event.matches(QKeySequence.StandardKey.Paste):
        self._paste_from_system_clipboard()
        event.accept()
    elif event.key() == Qt.Key.Key_Delete:
        self._delete_selected()
        event.accept()
    else:
        super().keyPressEvent(event)

def _paste_from_system_clipboard(self):
    clipboard = QApplication.clipboard()
    mime_data = clipboard.mimeData()
    if mime_data.hasImage():
        qimage = clipboard.image()
        if not qimage.isNull():
            pm = QPixmap.fromImage(qimage)
            item = QGraphicsPixmapItem(pm)
            item.setPos(0, 0)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
            self.scene.addItem(item)
            self.undo_stack.push(AddItemCommand(self.scene, item))
```

### 2.10 Delete 删除选中项

**功能**：选中图形后按 Delete 键删除。

```python
def _delete_selected(self):
    items = self._selected_items()
    if not items:
        return
    self.undo_stack.push(RemoveItemsCommand(self.scene, items))
    self._update_status(f"已删除 {len(items)} 项")
```

### 2.11 快捷键提示

每个工具按钮的 tooltip 格式：
```
画笔 (P) - 自由绘制
```

操作按钮的 tooltip 格式：
```
撤销 (Ctrl+Z)
```

---

## 三、技术方案补充

### 3.1 新增文件

| 文件 | 职责 |
|------|------|
| `ui/collapsible_section.py` | 折叠分组面板组件（CollapsibleSection） |
| `ui/drawing_ruler.py` | 水平/垂直比例尺组件（HorizontalRuler / VerticalRuler） |
| `ui/drawing_cursors.py` | 自定义工具光标生成器（create_tool_cursor） |
| `ui/drawing_text_editor.py` | 富文本浮动格式工具栏 + 文字编辑逻辑 |

### 3.2 修改文件

| 文件 | 修改内容 |
|------|---------|
| `ui/drawing_board.py` | 全面重构工具栏为折叠分组；新增比例尺；滚轮缩放；富文本工具；系统剪贴板粘贴；Delete 删除；快捷键 tooltip |
| `ui/drawing_tools.py` | 每个工具 activate/deactivate 切换光标；文字工具改为富文本模式 |
| `ui/drawing_commands.py` | 无需修改（已支持 ClearSceneCommand 的 bg_item 参数） |
| `ui/theme.py` | 新增折叠面板、比例尺、格式工具栏的 QSS 样式 |

### 3.3 比例尺与画布联动

```
VerticalRuler (QWidget)
  └── 监听 self.zoom_level 变化 → 更新刻度间距
  └── 监听 mouseMove → 绘制蓝色指示线
  
HorizontalRuler (QWidget)
  └── 同上
  
DrawingBoardView
  └── 将 ruler 与 canvas_view 的滚动/缩放联动
```

### 3.4 模块依赖更新

```
drawing_board.py
  ├── collapsible_section.py   （新：折叠面板）
  ├── drawing_ruler.py         （新：比例尺）
  ├── drawing_cursors.py       （新：自定义光标）
  ├── drawing_text_editor.py  （新：富文本工具栏）
  ├── drawing_tools.py         （修改：光标切换 + 富文本工具）
  ├── drawing_commands.py      （不变）
  └── core/database.py         （不变）
```

---

## 四、实施计划（按优先级分批）

### 第一批：快速见效（低风险）

| 任务 | 文件 | 说明 |
|------|------|------|
| 滚轮缩放 | `drawing_board.py` | 重写 `_CanvasView.wheelEvent` |
| 按钮高亮 | `theme.py` + `drawing_board.py` | 修正 `tool_button_checked` QSS |
| 趣味光标 | `drawing_cursors.py` + `drawing_tools.py` | 生成 QPixmap 光标 + activate/deactivate 切换 |
| 快捷键 tooltip | `drawing_board.py` | 为所有按钮添加 tooltip 含快捷键 |

### 第二批：核心增强（中风险）

| 任务 | 文件 | 说明 |
|------|------|------|
| 比例尺 | `drawing_ruler.py` + `drawing_board.py` | 自定义 QWidget 绘制刻度 |
| 富文本工具 | `drawing_text_editor.py` + `drawing_tools.py` | 格式工具栏 + 画布直接编辑 |
| 系统剪贴板 | `drawing_board.py` | `keyPressEvent` 检测 Ctrl+V |
| Delete 删除 | `drawing_board.py` | `keyPressEvent` 检测 Delete 键 |

### 第三批：UI 重构（高风险）

| 任务 | 文件 | 说明 |
|------|------|------|
| 折叠分组面板 | `collapsible_section.py` | 自定义折叠面板组件 |
| 工具栏重构 | `drawing_board.py` | 替换原 FlowLayout 平铺为折叠分组 |
| 主题适配 | `theme.py` | 新增折叠面板/比例尺 QSS |

---

## 五、验证清单

### 第一批验证
- [ ] 鼠标滚轮在画布上滚动可缩放（Ctrl+滚轮更精细）
- [ ] 点击画笔/橡皮/形状按钮，按钮背景变为主题色高亮
- [ ] 选中按钮悬停时颜色加深
- [ ] 激活画笔工具时，鼠标光标变为画笔形状
- [ ] 激活橡皮工具时，鼠标光标变为橡皮形状
- [ ] 所有按钮 tooltip 显示名称 + 快捷键

### 第二批验证
- [ ] 画布上方出现水平比例尺
- [ ] 画布左侧出现垂直比例尺
- [ ] 缩放时刻度同步更新
- [ ] 鼠标移动时刻度上有蓝色指示线
- [ ] 点击文字工具 → 出现浮动格式工具栏
- [ ] 点击画布 → 可直接输入文字
- [ ] 文字可拖动、可选中、可修改字体
- [ ] 按 Ctrl+V 可粘贴系统剪贴板图片
- [ ] 选中图形后按 Delete 可删除
- [ ] 撤销/重做对粘贴图片和删除均正常

### 第三批验证
- [ ] 工具栏分为 6 个可折叠分组
- [ ] 点击分组标题可展开/收起
- [ ] 窗口缩小时折叠面板自动调整
- [ ] 切换主题时折叠面板样式同步更新
- [ ] 折叠面板内工具按钮功能不受影响

---

## 六、风险处理

| 风险 | 等级 | 应对方案 |
|------|------|---------|
| UI 重构破坏主题适配 | 高 | 先完成低风险项再动 UI 重构；重构时保留 `apply_theme` 逻辑框架 |
| 比例尺与缩放联动 bug | 中 | 比例尺独立实现，通过信号/槽与缩放状态同步；充分测试多档缩放比例 |
| 自定义光标绘制效果差 | 低 | 先用简易几何图标，后续可替换为 PNG 资源 |
| 富文本编辑与撤销栈冲突 | 中 | 文字输入完成后才推入撤销栈；编辑过程不产生撤销命令 |
| 系统剪贴板图片格式兼容 | 低 | 仅处理 `hasImage()` 情况，其他格式提示"不支持的剪贴板格式" |

---

## 七、待用户确认事项

1. **UI 重构时机**：是否同意分三批实施，先完成第一批（滚轮缩放 + 按钮高亮 + 趣味光标 + 快捷键），再推进第二批和第三批？
2. **比例尺范围**：水平 0~800，垂直 0~600 是否合适？还是需要可自定义范围？
3. **富文本工具栏位置**：浮动工具栏（跟随鼠标）还是固定在画布上方？
4. **趣味光标风格**：简约几何图标 vs 更精致的像素图标？
