# 笔记导出为 Markdown 文件 — 实现方案

## 需求理解

用户需要实现笔记导出功能：
1. 页面新增一个导出按钮
2. 点击后将当前笔记内容导出为 `.md` 文件
3. 页面排版美观

## 代码研究结论

| 项目 | 说明 |
|------|------|
| 笔记内容获取 | 已有 `_extract_markdown_from_doc()` 方法可提取 Markdown 文本 |
| 标题获取 | `self.title_edit.text()` 获取笔记标题 |
| 保存按钮位置 | 在 `meta_row` 布局中，位于分类选择器右侧 |
| QFileDialog | 已导入，可用于保存文件对话框 |
| 样式系统 | 主题系统中已有 `save_btn` 样式，可参考创建 `export_btn` 样式 |

## 修改方案

### 1. 在 `editor.py` 中添加导出按钮

**位置**：`MarkdownEditor.__init__` 的 meta_row 布局中，保存按钮之后

```python
# 导出按钮（在保存按钮之后）
self.export_btn = QToolButton()
self.export_btn.setText("📤  导出")
self.export_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
self.export_btn.clicked.connect(self._export_note)
meta_row.addWidget(self.export_btn)
```

### 2. 添加 `_export_note` 方法

**位置**：`MarkdownEditor` 类中

```python
def _export_note(self):
    """导出笔记为 Markdown 文件"""
    title = self.title_edit.text().strip() or "untitled"
    md_content = self._extract_markdown_from_doc()
    
    # 弹出保存文件对话框
    default_name = f"{title}.md"
    file_path, _ = QFileDialog.getSaveFileName(
        self, "导出 Markdown", default_name, 
        "Markdown 文件 (*.md);;所有文件 (*)"
    )
    
    if file_path:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
            # 显示保存成功提示
            self.save_status.setText("✓ 导出成功")
            self.save_status.setStyleSheet("color:#22c55e; font-size:12px; font-weight:500;")
            QTimer.singleShot(2000, lambda: self.save_status.setText("✓ 已保存"))
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"无法导出文件：{str(e)}")
```

### 3. 添加导出按钮样式

**位置**：`theme.py` 中的 `get_editor_qss` 函数

在 `save_btn` 样式之后添加 `export_btn` 样式，使用不同颜色区分（如绿色系表示导出操作）：

```python
"export_btn": f"""
QToolButton {{
    padding: 6px 14px;
    border: none;
    border-radius: 7px;
    font-size: 12px;
    font-weight: 600;
    color: #FFFFFF;
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #10b981, stop:1 #059669);
}}
QToolButton:hover {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #34d399, stop:1 #10b981);
}}
QToolButton:pressed {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 #059669, stop:1 #047857);
}}
""",
```

### 4. 在 `apply_theme` 方法中应用样式

**位置**：`editor.py` 中的 `apply_theme` 方法

```python
self.export_btn.setStyleSheet(qss["export_btn"])
```

## 修改文件清单

| # | 文件 | 修改内容 |
|---|------|---------|
| 1 | `ui/editor.py` | 添加导出按钮 UI、`_export_note` 方法、样式应用 |
| 2 | `ui/theme.py` | 添加 `export_btn` 样式定义 |

## 实现步骤

1. 在 `theme.py` 中添加导出按钮样式
2. 在 `editor.py` 的 meta_row 中添加导出按钮
3. 在 `apply_theme` 中为导出按钮应用样式
4. 实现 `_export_note` 导出方法
5. 测试导出功能

## 风险评估

- **风险等级**：低
- **改动范围**：仅新增代码，不修改现有功能
- **兼容性**：完全兼容现有功能
- **注意事项**：导出的 Markdown 内容可能不包含 YAML front matter（元数据），仅导出正文

## 验证步骤

1. 打开一篇笔记
2. 点击 "📤 导出" 按钮
3. 在保存对话框中选择位置
4. 确认文件保存成功
5. 打开导出的 `.md` 文件检查内容完整性
6. 检查样式是否正确显示
