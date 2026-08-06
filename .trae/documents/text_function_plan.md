# 文字功能重构实施计划

## 需求分析

### 用户核心诉求
1. **编辑时可见输入框**：创建文字时，用户必须能看到虚线边框输入框（如图一），知道文字将在何处输出
2. **8 手柄光标变化**：鼠标悬停到 8 个缩放手柄时，自动变为双向箭头（↔），方便用户识别可拉伸
3. **旋转按钮可交互**：顶部旋转图标可以点击并拖动，顺时针/逆时针旋转文字方向

### 图一所示功能
```
        [旋转按钮]
          │
    ┌────│────┐
    │  □  □  □ │  ← 8 个缩放手柄
    │          │
    │  文字内容  │
    │          │
    │  □  □  □ │
    └──────────┘
```

## 现状分析

| 功能 | 现状 | 差距 |
|------|------|------|
| 编辑时显示边框 | ❌ 仅 `isSelected()` 时绘制 | 编辑模式下文字不是选中态，无边框显示 |
| 手柄光标变化 | ❌ 无 `hoverEvent` | 鼠标到达手柄时无视觉反馈 |
| 旋转按钮 | ❌ 命中检测正常但交互不明显 | 需添加旋转光标提示 + 优化拖拽体验 |
| 编辑/选中态切换 | ⚠️ 逻辑复杂 | 编辑态 → 选中态转换时可能丢失边框 |

## 实施步骤

### 步骤 1：编辑状态下显示输入框边框
**文件**: `ui/drawing_tools.py` - `RotatableTextItem.paint()`

**修改内容**:
- 在 `paint()` 中增加判断：如果文字处于编辑模式（`TextEditorInteraction`），即使未选中也绘制虚线边框
- 边框样式：与选中态一致的蓝色虚线 + 半透明白色背景
- 不显示手柄和旋转按钮（仅选中态显示交互控件）

**伪代码**:
```python
def paint(self, painter, option, widget):
    is_editing = self.textInteractionFlags() & Qt.TextEditorInteraction
    show_frame = self.isSelected() or is_editing
    
    # 文字本体绘制...
    
    if show_frame:
        # 绘制虚线边框
        if self.isSelected():
            # 绘制 8 手柄 + 旋转按钮
            ...
```

### 步骤 2：实现手柄悬停光标变化
**文件**: `ui/drawing_tools.py` - `RotatableTextItem` 类

**新增方法**:
- `hoverEvent(event)` - 检测鼠标悬停位置，根据命中的手柄类型设置光标
- `cursorForHandle(handle)` - 返回对应手柄的 `Qt.CursorShape`

**手柄 → 光标映射**:
| 手柄位置 | 光标 |
|---------|------|
| TL / BR（对角） | `SizeAllCursor` 或斜向自定义 |
| TR / BL（对角） | 反向斜向 |
| L / R（左右） | `SplitHCursor` 或 `SizeHorCursor` |
| T / B（上下） | `SplitVCursor` 或 `SizeVerCursor` |
| ROTATE（旋转） | `PointingHandCursor` 或自定义旋转光标 |

**实现要点**:
- 使用 `sceneTransform().inverted().map()` 将场景坐标转为 item 本地坐标
- 复用 `_hit_handle()` 逻辑但使用 `hover` 事件的位置
- 悬停手柄时设置 view cursor，离开时恢复默认

### 步骤 3：优化创建文字的初始显示
**文件**: `ui/drawing_tools.py` - `TextTool.mouse_press()`

**修改内容**:
- 创建新文字时，先显示空的输入框（虚线边框），用户可立即看到位置
- 文字在编辑态期间，边框持续显示
- 提交后自动切换为选中态，显示完整交互控件

**流程**:
```
点击画布 → 创建空 RotatableTextItem
         → 设置 TextEditorInteraction（编辑模式）
         → paint() 检测到编辑模式 → 显示虚线框
         → 用户输入文字 → 边框持续可见
         → 提交 → 切换为选中态 → 显示手柄+旋转按钮
```

### 步骤 4：验证旋转功能完整性
**文件**: `ui/drawing_tools.py` - `TextTool._do_resize()` / `_SelectToolBase`

**验证要点**:
- 旋转按钮点击后 `_mode` 切换为 `"rotate"`
- 拖动时角度实时更新
- 支持顺时针（正角度）和逆时针（负角度）
- 180° 边界处理正确
- 旋转后 `boundingRect` 更新正确

## 涉及文件
| 文件 | 修改内容 |
|------|---------|
| `ui/drawing_tools.py` | RotatableTextItem: paint()、hoverEvent、cursorForHandle；TextTool: 编辑态边框显示 |

## 风险与应对
| 风险 | 应对 |
|------|------|
| 编辑态与选中态切换冲突 | 使用独立标志 `_show_frame` 控制边框显示，不依赖单一状态 |
| 光标在手柄间闪烁 | 扩大手柄检测命中区域（当前 +4px，可调整为 +6px） |
| 旋转后坐标变换导致手柄位置偏移 | 已在上一轮修复 `transformOriginPoint`，需回归测试 |
