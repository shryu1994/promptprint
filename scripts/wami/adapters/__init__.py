# 어댑터 레지스트리. 각 어댑터 모듈이 import 시 자신을 등록한다.
ADAPTERS = {}


def register(adapter_cls):
    if not adapter_cls.tool:
        raise ValueError("Adapter.tool must be a non-empty string")
    ADAPTERS[adapter_cls.tool] = adapter_cls
    return adapter_cls
