# 大纲功能实现方案

## 需求理解

用户需要类似论文目录的大纲功能：
- 展示当前笔记中所有标题（H1~H6）的层级结构
- 写笔记时大纲实时更新
- 点击大纲项可跳转到对应位置

## 代码研究结论

| 发现 | 说明 |
|------|------|
| 标题识别 | 高亮器 `highlightBlock` 中通过正则 `r"^(#{1,6})\s(.*)"` 识别标题，存储在 `block_meta[block_num]`（值为 `h1`~`h6`） |
| 内容变化信号 | `_on_src_changed` → `_on_any_changed` 处理文档变化，已有防抖定时器机制 |
| block_meta | `self._highlighter.block_meta` 字典，key=block序号，value=类型字符串 |
| 编辑器布局 | `MarkdownEditor._build_ui` 中用 QVBoxLayout 放置 header + toolbar + edit area |
| MainWindow | 使用 `QSplitter(Horizontal)` 放置 Sidebar | MarkdownEditor |
| 标题文本提取 | 可通过 `block.text()` 获取行文本，去掉 `#` 前缀即为标题内容 |

## 修改方案

### 核心思路

在 `MarkdownEditor._build_ui` 中，将编辑区（`self.edit`）包裹进一个水平 `QSplitter`，左侧是编辑器，右侧是可折叠的大纲面板。利用已有的 `block_meta` 字典实时识别标题，监听 `textChanged` 信号延迟更新大纲。

### 修改点清单

| # | 文件 | 修改内容 |
|---|------|---------|
| 1 | `ui/editor.py` | 修改 `_build_ui`：用 QSplitter 包裹编辑器 + 大纲面板 |
| 2 | `ui/editor.py` | 新增 `_build_outline_panel` 方法：构建大纲 UI |
| 3 | `ui/editor.py` | 新增 `_update_outline` 方法：从 block_meta 提取标题并更新大纲 |
| 4 | `ui/editor.py` | 新增 `_on_outline_clicked` 方法：点击大纲跳转到对应位置 |
| 5 | `ui/editor.py` | 在 `_on_src_changed` 中触发大纲更新（防抖） |
| 6 | `ui/editor.py` | 在 `set_note` 中触发大纲更新 |
| 7 | `ui/editor.py` | 在 `apply_theme` 中应用大纲面板样式 |
| 8 | `ui/theme.py` | 新增 `outline_panel` 样式定义 |

### 详细设计

#### 1. `_build_ui` 修改

```python
# 之前：
# root.addWidget(self.header)
# ...
# root.addWidget(self.edit)

# 之后：
root.addWidget(self.header)
# ... toolbar ...
# 用 QSplitter 包裹编辑器和大纲面板
content_splitter = QSplitter(Qt.Orientation.Horizontal)
content_splitter.setChildrenCollapsible(False)
content_splitter.addWidget(self.edit)
self.outline_panel = self._build_outline_panel()
content_splitter.addWidget(self.outline_panel)
content_splitter.setStretchFactor(0, 1)  # 编辑器占主要空间
content_splitter.setStretchFactor(1, 0)
content_splitter.setSizes([800, 200])
root.addWidget(content_splitter, 1)
```

#### 2. `_build_outline_panel` 方法

```python
def _build_outline_panel(self):
    """构建大纲面板"""
    panel = QFrame()
    panel.setObjectName("outline_panel")
    panel.setFixedWidth(220)
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(12, 16, 12, 16)
    layout.setSpacing(8)

    # 标题行
    header = QHBoxLayout()
    title = QLabel("📋 大纲")
    title.setStyleSheet("font-size:13px; font-weight:600;")
    header.addWidget(title)
    header.addStretch()
    # 折叠按钮
    self.outline_toggle_btn = QPushButton("›")
    self.outline_toggle_btn.setFixedSize(20, 20)
    self.outline_toggle_btn.clicked.connect(self._toggle_outline)
    header.addWidget(self.outline_toggle_btn)
    layout.addLayout(header)

    # 大纲树
    self.outline_tree = QTreeWidget()
    self.outline_tree.setHeaderHidden(True)
    self.outline_tree.itemClicked.connect(self._on_outline_clicked)
    layout.addWidget(self.outline_tree, 1)

    return panel
```

#### 3. `_update_outline` 方法

```python
def _update_outline(self):
    """从 block_meta 提取标题并更新大纲"""
    self.outline_tree.clear()
    hl = self._highlighter
    if not hl or not hasattr(hl, 'block_meta'):
        return

    doc = self.edit.document()
    block = doc.begin()
    # 保存标题所在 block 位置，用于点击跳转
    self._outline_items = []

    # 用栈跟踪层级，构建树形结构
    stack = []  # [(level, QTreeWidgetItem)]
    root_items = []

    while block.isValid():
        block_num = block.blockNumber()
        btype = hl.block_meta.get(block_num, "p")
        if btype in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(btype[1])
            text = block.text().lstrip()
            # 去掉 # 前缀
            text = re.sub(r'^#{1,6}\s*', '', text).strip()
            if not text:
                text = "(无标题)"

            item = QTreeWidgetItem([text])
            item.setData(0, Qt.ItemDataRole.UserRole, block.position())

            # 找到父节点
            while stack and stack[-1][0] >= level:
                stack.pop()

            if stack:
                stack[-1][1].addChild(item)
            else:
                self.outline_tree.addTopLevelItem(item)
                root_items.append(item)

            stack.append((level, item))

        block = block.next()

    self.outline_tree.expandAll()
```

#### 4. `_on_outline_clicked` 方法

```python
def _on_outline_clicked(self, item, column):
    """点击大纲项跳转到对应位置"""
    pos = item.data(0, Qt.ItemDataRole.UserRole)
    if pos is not None:
        cursor = self.edit.textCursor()
        cursor.setPosition(pos)
        self.edit.setTextCursor(cursor)
        self.edit.setFocus()
```

#### 5. 触发时机

- `_on_src_changed`：文档变化时，延迟 300ms 更新大纲（防抖）
- `set_note`：加载笔记后更新大纲

```python
# 在 __init__ 中添加防抖定时器
self._outline_timer = QTimer(self)
self._outline_timer.setSingleShot(True)
self._outline_timer.setInterval(300)
self._outline_timer.timeout.connect(self._update_outline)

# 在 _on_src_changed 中添加
self._outline_timer.start()
```

#### 6. 折叠/展开

```python
def _toggle_outline(self):
    """折叠/展开大纲面板"""
    if self.outline_panel.isVisible():
        self.outline_panel.hide()
        self.outline_toggle_btn.setText("‹")
    else:
        self.outline_panel.show()
        self.outline_toggle_btn.setText("›")
```

#### 7. 样式（theme.py）

```python
"outline_panel": f"""
QFrame#outline_panel {{
    background: {t['surface_bg']};
    border-left: 1px solid {t['border']};
}}
QTreeWidget {{
    background: transparent;
    border: none;
    font-size: 12px;
    color: {t['text_secondary']};
    outline: 0;
}}
QTreeWidget::item {{
    padding: 4px 8px;
    border-radius: 4px;
}}
QTreeWidget::item:hover {{
    background: {t['hover_bg']};
    color: {t['text_primary']};
}}
QTreeWidget::item:selected {{
    background: {t['primary_bg']};
    color: {t['primary_text']};
}}
""",
```

## 假设与决策

1. **大纲面板位置**：放在编辑器右侧（不是左侧），因为左侧已有 Sidebar
2. **默认宽度**：220px，可通过 QSplitter 拖拽调整
3. **默认展开**：大纲树默认全部展开
4. **更新频率**：300ms 防抖，避免频繁更新
5. **标题来源**：直接从 `block_meta` 读取，不需要额外解析
6. **折叠后状态**：隐藏面板，编辑器占满空间

## 验证步骤

1. 打开一篇包含多个标题的笔记 → 大纲正确显示标题层级
2. 编辑笔记内容（添加/删除标题）→ 大纲实时更新
3. 点击大纲中的标题 → 光标跳转到对应位置
4. 点击折叠按钮 → 大纲面板隐藏，编辑器占满空间
5. 再次点击折叠按钮 → 大纲面板恢复显示
6. 切换笔记 → 大纲自动更新为新笔记的目录
7. 切换主题 → 大纲面板样式正确应用
