from abc import ABC, abstractmethod
from collections import Counter
from typing import Iterable, Iterator, List
from wami.model import QuestionRecord


class Adapter(ABC):
    """도구별 로그 → QuestionRecord 변환기."""

    tool: str = ""  # 하위 클래스가 "claude" / "codex" 등으로 지정

    def __init__(self):
        # 신뢰 영수증용 스캔 통계(어댑터가 순회하며 채운다).
        #   scanned          : 검사한 user 텍스트 블록 수
        #   dropped_noise    : 주입/명령/시스템 마커로 제외
        #   dropped_subagent : 서브에이전트·워크플로 턴(isSidechain/agentId)으로 제외
        #   kept             : QuestionRecord로 산출(이후 extract 단계서 dedup/중복제거로 더 줄 수 있음)
        self.stats: Counter = Counter()

    @abstractmethod
    def default_roots(self) -> List[str]:
        """이 도구의 기본 로그 경로 목록(존재하지 않을 수 있음)."""
        raise NotImplementedError

    @abstractmethod
    def iter_records(self, roots: Iterable[str]) -> Iterator[QuestionRecord]:
        """주어진 루트들에서 '진짜 질문' 레코드를 순회 생성한다."""
        raise NotImplementedError
