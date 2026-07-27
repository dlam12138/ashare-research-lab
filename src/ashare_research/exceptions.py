"""项目自定义异常类。

所有数据层异常继承自 AshareDataError，便于上层统一捕获。
"""


class AshareDataError(Exception):
    """项目数据层基础异常。"""
    pass


class AuthenticationError(AshareDataError):
    """数据源认证失败。"""
    pass


class NetworkError(AshareDataError):
    """网络请求失败。"""
    pass


class FieldMissingError(AshareDataError):
    """必需字段缺失。"""

    def __init__(self, missing_fields: list[str], source: str = ""):
        self.missing_fields = missing_fields
        self.source = source
        msg = f"Missing required fields: {missing_fields}"
        if source:
            msg += f" (source: {source})"
        super().__init__(msg)


class SchemaValidationError(AshareDataError):
    """数据模式验证失败。"""
    pass


class QualityCheckError(AshareDataError):
    """数据质量检查失败。"""
    pass


class EmptyResultError(AshareDataError):
    """合法空结果（与请求失败不同）。"""

    def __init__(self, reason: str = ""):
        self.reason = reason
        super().__init__(f"Empty result: {reason}" if reason else "Empty result")


class DuplicateKeyError(AshareDataError):
    """主键重复。"""
    pass


class CodeFormatError(AshareDataError):
    """股票代码格式错误。"""
    pass


class DateRangeError(AshareDataError):
    """日期范围无效。"""
    pass


class RawPersistenceError(AshareDataError):
    """原始响应保存失败。"""
    pass
