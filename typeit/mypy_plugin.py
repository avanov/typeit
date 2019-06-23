from typing import Optional, Callable
from mypy.types import Type
from mypy.plugin import Plugin, AnalyzeTypeContext
from mypy.nodes import TypeInfo


class TypeitPlugin(Plugin):
    def get_type_analyze_hook(self, fullname: str) -> Optional[Callable[[AnalyzeTypeContext], Type]]:
        def analyze(type_context: AnalyzeTypeContext) -> Type:
            api = type_context.api
            ctx = type_context.context
            typ = type_context.type
            return typ

        return analyze


def plugin(version: str):
    # ignore version argument if the plugin works with all mypy versions.
    return TypeitPlugin