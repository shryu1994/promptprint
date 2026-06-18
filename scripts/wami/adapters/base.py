from abc import ABC, abstractmethod
from typing import Iterable, Iterator, List
from wami.model import QuestionRecord


class Adapter(ABC):
    """도구별 로그 → QuestionRecord 변환기."""

    tool: str = ""  # 하위 클래스가 "claude" / "codex" 등으로 지정

    @abstractmethod
    def default_roots(self) -> List[str]:
        """이 도구의 기본 로그 경로 목록(존재하지 않을 수 있음)."""
        raise NotImplementedError

    @abstractmethod
    def iter_records(self, roots: Iterable[str]) -> Iterator[QuestionRecord]:
        """주어진 루트들에서 '진짜 질문' 레코드를 순회 생성한다."""
        raise NotImplementedError
