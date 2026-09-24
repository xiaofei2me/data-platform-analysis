"""日志配置。"""

import logging

from rich.logging import RichHandler


def setup_logging(level: str = "INFO") -> None:
    """初始化项目日志。"""

    numeric_level = getattr(
        logging,
        level.upper(),
        logging.INFO,
    )

    logging.basicConfig(
        level=numeric_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                rich_tracebacks=True,
                markup=True,
            )
        ],
        force=True,
    )

    # 第三方 HTTP 库的 DEBUG 日志通常没有分析价值，
    # 将它们的日志级别提高，避免终端输出过于冗长。
    logging.getLogger("httpx").setLevel(
        logging.WARNING
    )

    logging.getLogger("urllib3").setLevel(
        logging.WARNING
    )