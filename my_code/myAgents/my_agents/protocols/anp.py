"""ANP（Agent Network Protocol）：纯内存的智能体服务发现与调度。

这是教学用的轻量模拟，零外部依赖：
- ANPRegistry 维护「服务名 -> 提供者(callable) + 元数据」的注册表
- register_service / discover_service / invoke_service
- ANPNetwork 可聚合多个 registry，做简单的负载/轮询调度
"""

from itertools import cycle
from typing import Any, Callable, Dict, List, Optional


class ANPRegistry:
    """单节点服务注册表。"""

    def __init__(self):
        # name -> list of {"func": callable, "meta": dict}
        self._services: Dict[str, List[Dict[str, Any]]] = {}

    def register_service(
        self, name: str, func: Callable[[str], str], meta: Optional[Dict] = None
    ) -> None:
        self._services.setdefault(name, []).append({"func": func, "meta": meta or {}})

    def discover_service(self, name: str) -> List[Dict[str, Any]]:
        """返回某服务的所有提供者（仅元数据）。"""
        return [{"name": name, "meta": p["meta"]} for p in self._services.get(name, [])]

    def list_services(self) -> List[str]:
        return list(self._services.keys())

    def invoke_service(self, name: str, payload: str, index: int = 0) -> str:
        providers = self._services.get(name)
        if not providers:
            return f"错误：未发现服务 '{name}'。"
        if index >= len(providers):
            index = 0
        return providers[index]["func"](payload)


class ANPNetwork:
    """多提供者负载调度（轮询）。"""

    def __init__(self):
        self.registry = ANPRegistry()
        self._round_robin: Dict[str, Any] = {}

    def register_service(self, name, func, meta=None) -> None:
        self.registry.register_service(name, func, meta)
        # 重置该服务的轮询迭代器
        providers = self.registry._services[name]
        self._round_robin[name] = cycle(range(len(providers)))

    def invoke_balanced(self, name: str, payload: str) -> str:
        """轮询选择一个提供者执行。"""
        if name not in self._round_robin:
            return f"错误：未发现服务 '{name}'。"
        idx = next(self._round_robin[name])
        return self.registry.invoke_service(name, payload, index=idx)

    def list_services(self) -> List[str]:
        return self.registry.list_services()
