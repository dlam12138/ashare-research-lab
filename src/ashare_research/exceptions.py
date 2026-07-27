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


# ── M2 Stage 1 异常 ──────────────────────────────────────


class FactValidationError(AshareDataError):
    """财务事实校验失败。"""
    pass


class ConceptNotFoundError(AshareDataError):
    """概念ID未在注册表中找到。"""
    pass


class UnitConversionError(AshareDataError):
    """单位转换不支持。"""
    pass


class DerivationError(AshareDataError):
    """派生事实计算失败。"""
    pass


class PointInTimeError(AshareDataError):
    """PIT查询违反时序约束。"""
    pass


class SourceDocumentError(AshareDataError):
    """官方来源文档不可访问或不可解析。"""
    pass


class ReconciliationError(AshareDataError):
    """交叉核验发现无法解释的不一致。"""
    pass


class FactPersistenceError(AshareDataError):
    """事实持久化失败，事务已回滚。"""
    pass


class FactSchemaMigrationError(AshareDataError):
    """Fact schema 迁移失败。"""
    pass


class FactCheckpointError(AshareDataError):
    """事实构建 checkpoint 校验失败。"""
    pass
