"""业务异常：HTTP 状态恒 200，靠 code 区分（与参考项目一致）。"""


class BizException(Exception):
    def __init__(self, msg: str = "操作失败", code: int = 500):
        self.msg = msg
        self.code = code
        super().__init__(msg)
