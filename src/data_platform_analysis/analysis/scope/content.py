"""Content 事实状态：先决定是否检查，再给出检查后的具体状态。

Content 检查由 ``config/analysis-scope-rules.yaml`` 的 ``content_check`` 控制：

- 启用且 ``content_format`` 命中 ``enabled_formats`` → 读 Snapshot 判定为
  ``present`` / ``empty_text`` / ``not_collected`` / ``path_missing`` / ``read_error``；
- 未启用或格式不在 ``enabled_formats`` 内 → ``not_checked``（未启用 Content 检查）：
  不读 Snapshot、不计为 Content 缺口、不阻断分析资格，也不推断内容期望。

文件系统读取只发生在状态计算这一处，规则匹配阶段不访问文件系统。
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import FileInventory
from ..snapshot import SnapshotReader

CONTENT_STATE_NOT_CHECKED = "not_checked"
CONTENT_STATE_PRESENT = "present"
CONTENT_STATE_EMPTY_TEXT = "empty_text"
CONTENT_STATE_NOT_COLLECTED = "not_collected"
CONTENT_STATE_PATH_MISSING = "path_missing"
CONTENT_STATE_READ_ERROR = "read_error"

CONTENT_STATES: tuple[str, ...] = (
    CONTENT_STATE_NOT_CHECKED,
    CONTENT_STATE_PRESENT,
    CONTENT_STATE_EMPTY_TEXT,
    CONTENT_STATE_NOT_COLLECTED,
    CONTENT_STATE_PATH_MISSING,
    CONTENT_STATE_READ_ERROR,
)
"""全部合法 Content 状态；condition.states 只能取其中的值。"""

CONTENT_GAP_STATES: frozenset[str] = frozenset(
    {
        CONTENT_STATE_EMPTY_TEXT,
        CONTENT_STATE_NOT_COLLECTED,
        CONTENT_STATE_PATH_MISSING,
        CONTENT_STATE_READ_ERROR,
    }
)
"""已检查且确实存在内容缺口的状态：既不含 present，也不含 not_checked。"""

EXPECTATION_REQUIRED = "required"
EXPECTATION_NOT_REQUIRED = "not_required"
EXPECTATION_UNKNOWN = "unknown"

EXPECTATIONS: tuple[str, ...] = (
    EXPECTATION_REQUIRED,
    EXPECTATION_NOT_REQUIRED,
    EXPECTATION_UNKNOWN,
)
"""全部合法内容期望取值。"""

CONTENT_READ_LIMIT = 1 << 20
"""判断 Content 是否空白时读取的最大字节数（超出按有内容处理）。"""


@dataclass(frozen=True)
class ContentCheckConfig:
    """Content 检查开关：启用状态下哪些 content_format 才会被实际读取。"""

    enabled: bool
    enabled_formats: frozenset[str]

    def is_enabled(self, content_format: str) -> bool:
        """该文件是否执行 Content 检查；未启用或格式不匹配 → 不检查。"""

        if not self.enabled:
            return False

        return (content_format or "").strip().upper() in self.enabled_formats


def content_state_of(
    reader: SnapshotReader,
    file: FileInventory,
    *,
    content_check: ContentCheckConfig,
) -> str:
    """Content 事实状态；未启用检查的格式直接返回 ``not_checked``。

    已检查格式区分四种不同语义（绝不混为一谈）：
    - not_collected：content_file 为空，采集结果事实（API 未返回内容）；
    - path_missing ：content_file 指向的 Snapshot 文件不存在，技术异常；
    - empty_text   ：文件存在但内容为空白；
    - present      ：文件存在且有内容。
    """

    if not content_check.is_enabled(file.content_format):
        return CONTENT_STATE_NOT_CHECKED

    if not file.content_file:
        return CONTENT_STATE_NOT_COLLECTED

    path = reader.resolve(file.content_file)

    if not path.exists():
        return CONTENT_STATE_PATH_MISSING

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return CONTENT_STATE_READ_ERROR

    if len(text) > CONTENT_READ_LIMIT:
        return CONTENT_STATE_PRESENT

    return CONTENT_STATE_PRESENT if text.strip() else CONTENT_STATE_EMPTY_TEXT
