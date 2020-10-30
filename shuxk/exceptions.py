class PasswordError(ValueError):
    """密码错误
    """
    pass


class CannotJudgeError(RuntimeError):
    """无法判断结果错误。一般出现在选课系统改版之后。
    """
    pass
