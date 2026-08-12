import sqlite3
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Category:
    id: int
    name: str
    created_at: str
    updated_at: str


@dataclass
class Note:
    id: int
    title: str
    content: str
    category_id: Optional[int]
    created_at: str
    updated_at: str
    is_private: int = 0


_UNSET = object()


def _app_data_root() -> str:
    p = os.path.join(os.path.expanduser("~"), ".zhuibook")
    os.makedirs(p, exist_ok=True)
    return p


def get_assets_root() -> str:
    p = os.path.join(_app_data_root(), "assets")
    os.makedirs(p, exist_ok=True)
    return p


def get_assets_dir(note_id: int) -> str:
    if note_id is None or note_id <= 0:
        p = os.path.join(get_assets_root(), "_unsaved_images")
    else:
        p = os.path.join(get_assets_root(), f"note_{int(note_id)}_images")
    os.makedirs(p, exist_ok=True)
    return p


class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            app_data = os.path.join(os.path.expanduser("~"), ".zhuibook")
            os.makedirs(app_data, exist_ok=True)
            db_path = os.path.join(app_data, "zhuibook.db")
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def init_database(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL DEFAULT '',
                category_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_category ON notes(category_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notes_updated ON notes(updated_at DESC)")
        # 迁移：为旧数据库添加 is_private 列
        try:
            cursor.execute("ALTER TABLE notes ADD COLUMN is_private INTEGER DEFAULT 0")
        except Exception:
            pass  # 列已存在
        self.conn.commit()
        self._init_default_data()

    def _init_default_data(self):
        now = datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM categories")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                "INSERT INTO categories (name, created_at, updated_at) VALUES (?, ?, ?)",
                ("默认分类", now, now)
            )
        cursor.execute("SELECT id FROM categories ORDER BY id LIMIT 1")
        row = cursor.fetchone()
        cat_id = row[0] if row else None

        welcome_content = """# 欢迎使用 Zhuibook ✨ 混合模式

> 这是 **混合所见即所得** 编辑器：**Markdown 源码标记会自动隐藏**，但被包裹的文字会渲染成真实样式！
>
> 🖱️ 试着把光标移动到下面 *heart of the city* 这两个星号附近——星号会 **立刻显示出来**！移开光标，星号又会自动隐藏~

---

## 场景演示

In the *heart of the city*, a small park blooms with life. Colorful flowers dance in the breeze, and birds sing sweet melodies. Children laugh as they chase butterflies, their innocence filling the air with joy.

---

## 语法快速对照（移动光标到文字上看源码标记！）

| 效果 | 说明 |
|------|------|
| **这是粗体** | 光标移到附近会显示两边的 **** 号 |
| *这是斜体* | 光标移到附近会显示两边的 ** 号 |
| ~~删除线文本~~ | 光标移到附近会显示两边的 ~~~~ 号 |
| `print("Hello")` | 光标移到附近会显示两边的反引号符号 |
| [蓝色下划线链接](https://example.com) | 光标移到附近 URL 和括号都会显示 |

---

## 标题层级示例（`#` 号会自动隐藏）

# 一级标题 H1
## 二级标题 H2
### 三级标题 H3
#### 四级标题 H4

## 列表与引用

> 💡 引用块：这里的 `>` 符号光标靠近时才会出现
>
> 引用块支持多行文字。

### 无序列表（`- ` 光标靠近才出现）
- **粗体列表项**
- *斜体列表项*
- 普通项包含 `行内代码`

### 有序列表（`1. ` 光标靠近才出现）
1. 把光标移到本行最开头，`1.` 会出现
2. 第二项
3. 第三项

---

## 代码块

```python
def zhuibook_demo():
    # 代码块的 ``` 围栏永远可见
    name = "Zhuibook"
    print(f"Welcome to {name}!")
```

---

## 常用快捷键

| 快捷键 | 功能 |
|--------|------|
| Ctrl + B | 把选中文本变成 **粗体** |
| Ctrl + I | 把选中文本变成 *斜体* |
| Ctrl + 反引号 | 插入行内 `代码` |
| Ctrl + N / Ctrl + S | 新建笔记 / 保存 |

---

📝 **开始写笔记吧** — 先点左侧「新建笔记」按钮，或者直接修改这篇试试效果！
"""

        cursor.execute("SELECT COUNT(*) FROM notes")
        note_count = cursor.fetchone()[0]
        if note_count == 0:
            cursor.execute(
                "INSERT INTO notes (title, content, category_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                ("欢迎使用 Zhuibook", welcome_content, cat_id, now, now)
            )
        else:
            cursor.execute("SELECT id, content FROM notes WHERE title = ? LIMIT 1", ("欢迎使用 Zhuibook",))
            wn = cursor.fetchone()
            if wn and ("混合模式" not in (wn[1] or "")):
                cursor.execute(
                    "UPDATE notes SET content = ?, updated_at = ? WHERE id = ?",
                    (welcome_content, now, wn[0])
                )
        self.conn.commit()

    def _now(self) -> str:
        return datetime.now().isoformat()

    def create_category(self, name: str) -> Category:
        now = self._now()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO categories (name, created_at, updated_at) VALUES (?, ?, ?)",
            (name, now, now)
        )
        self.conn.commit()
        return self.get_category(cursor.lastrowid)

    def get_category(self, category_id: int) -> Optional[Category]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
        row = cursor.fetchone()
        return Category(**dict(row)) if row else None

    def get_all_categories(self) -> List[Category]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM categories ORDER BY name")
        return [Category(**dict(r)) for r in cursor.fetchall()]

    def update_category(self, category_id: int, name: str) -> Optional[Category]:
        now = self._now()
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE categories SET name = ?, updated_at = ? WHERE id = ?",
            (name, now, category_id)
        )
        self.conn.commit()
        return self.get_category(category_id)

    def delete_category(self, category_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        self.conn.commit()

    def create_note(self, title: str, content: str = "", category_id: Optional[int] = None) -> Note:
        now = self._now()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO notes (title, content, category_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (title, content, category_id, now, now)
        )
        self.conn.commit()
        return self.get_note(cursor.lastrowid)

    def get_note(self, note_id: int) -> Optional[Note]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        return Note(**dict(row)) if row else None

    def get_notes_by_category(self, category_id: Optional[int]) -> List[Note]:
        cursor = self.conn.cursor()
        if category_id is None:
            cursor.execute(
                "SELECT * FROM notes WHERE category_id IS NULL ORDER BY updated_at DESC"
            )
        else:
            cursor.execute(
                "SELECT * FROM notes WHERE category_id = ? ORDER BY updated_at DESC",
                (category_id,)
            )
        return [Note(**dict(r)) for r in cursor.fetchall()]

    def get_all_notes(self) -> List[Note]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM notes ORDER BY updated_at DESC")
        return [Note(**dict(r)) for r in cursor.fetchall()]

    def search_notes(self, keyword: str) -> List[Note]:
        like = f"%{keyword}%"
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM notes WHERE title LIKE ? OR content LIKE ? ORDER BY updated_at DESC",
            (like, like)
        )
        return [Note(**dict(r)) for r in cursor.fetchall()]

    def update_note(self, note_id: int, title: Optional[str] = None,
                    content: Optional[str] = None,
                    category_id=_UNSET) -> Optional[Note]:
        note = self.get_note(note_id)
        if not note:
            return None
        now = self._now()
        new_title = title if title is not None else note.title
        new_content = content if content is not None else note.content
        new_cat = note.category_id if category_id is _UNSET else category_id
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE notes SET title = ?, content = ?, category_id = ?, updated_at = ? WHERE id = ?",
            (new_title, new_content, new_cat, now, note_id)
        )
        self.conn.commit()
        return self.get_note(note_id)

    def set_note_private(self, note_id: int, is_private: bool):
        """设置或取消笔记的私密状态。"""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE notes SET is_private = ? WHERE id = ?",
            (1 if is_private else 0, note_id)
        )
        self.conn.commit()

    def get_private_notes(self) -> List[Note]:
        """获取所有私密笔记。"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM notes WHERE is_private = 1 ORDER BY updated_at DESC")
        return [Note(**dict(r)) for r in cursor.fetchall()]

    def delete_note(self, note_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


def save_drawing_to_note_assets(note_id: int, pixmap) -> str:
    """将 QPixmap 保存到笔记的 assets 目录，返回相对路径用于 Markdown 引用。

    兼容 QPixmap / QImage 入参（二者均有 save() 方法）。
    """
    import uuid
    from datetime import datetime
    assets_dir = get_assets_dir(note_id)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_suffix = uuid.uuid4().hex[:6]
    filename = f"drawing_{timestamp}_{random_suffix}.png"
    filepath = os.path.join(assets_dir, filename)
    # 保存 pixmap 为 PNG（QPixmap / QImage 均支持 save）
    pixmap.save(filepath, "PNG")
    # 返回相对路径（用于笔记内引用）
    return f"./assets/note_{int(note_id)}_images/{filename}"
