"""测试包：统一测试环境，并在每次测试进程启动时使用全新的临时数据库。"""

import os
import tempfile

os.environ.setdefault("DEEPSEEK_API_KEY", "sk-test")

_DB_PATH = os.path.join(tempfile.gettempdir(), "xdwe-tests.db")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_DB_PATH}")

try:
    if os.path.exists(_DB_PATH):
        os.remove(_DB_PATH)
except OSError:  # 极端情况下文件被占用时忽略，保持测试可运行
    pass
