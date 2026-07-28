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


class FactIdentityError(FactPersistenceError):
    """事实 fact_id 与 canonical 身份不一致，或 fact_id 缺失。

    由 Service 边界和 Repository 边界共同强制：Provider 返回事实后、
    以及持久化写入前，都会校验 fact_id == build_fact_id(fact)。
    """
    pass


class LineagePersistenceError(AshareDataError):
    """运行 Manifest 写入失败。

    只有 write_manifest 成功返回后才能将运行标记为 finalized；
    底层 OSError/PermissionError/JSON 序列化/os.replace 失败统一
    转换为此异常，避免把运行错误地汇报为成功。
    """
    pass


class VersionChainCycleError(FactValidationError):
    """事实版本链形成循环（A supersedes B, B supersedes A ...）。"""
    pass


class FactSchemaMigrationError(AshareDataError):
    """Fact schema 迁移失败。"""
    pass


class FactCheckpointError(AshareDataError):
    """事实构建 checkpoint 校验失败。"""
    pass


class FactVersionConflictError(AshareDataError):
    """事实版本冲突：已有不同内容的同 fact_id 事实存在，拒绝覆盖。"""
    pass


class ContextVersionConflictError(AshareDataError):
    """上下文版本冲突：已有不同内容的同 context_id 上下文存在，拒绝覆盖。"""
    pass


class ConceptVersionConflictError(AshareDataError):
    """概念版本冲突：已有不同内容的同 (concept_id, version) 概念存在，拒绝覆盖。"""
    pass
