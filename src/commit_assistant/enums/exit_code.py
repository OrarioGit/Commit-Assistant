from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0  # 成功生成並確認使用 AI message
    CANCEL = 1  # 使用者取消操作
    ERROR = 2  # 發生錯誤
