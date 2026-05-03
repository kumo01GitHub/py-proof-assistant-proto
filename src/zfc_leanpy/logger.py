"""Shared logging utilities for zfc_leanpy.

ライブラリとして NullHandler のみ登録し、ハンドラ設定はアプリ側に委ねる。
アプリ側で出力したい場合は以下のように設定する::

    import logging
    logging.getLogger("zfc_leanpy").setLevel(logging.DEBUG)
    logging.basicConfig()
"""

from __future__ import annotations

import logging

logging.getLogger("zfc_leanpy").addHandler(logging.NullHandler())


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the zfc_leanpy namespace."""
    return logging.getLogger(name)
