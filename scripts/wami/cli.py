import argparse
import json
import os
import sys
from typing import Dict, List, Optional

from wami.extract import extract_records
from wami.aggregate import build_aggregates
from wami.insights import validate_insights
from wami.render import build_report_html


def run_aggregate(roots_by_tool: Optional[Dict[str, List[str]]], out_path: str) -> dict:
    records = extract_records(roots_by_tool)
    agg = build_aggregates(records)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(agg, fh, ensure_ascii=False, indent=2, sort_keys=True)
    return agg


def main(argv=None):
    p = argparse.ArgumentParser(prog="wami", description="where-am-i: 질문 로그 추출·집계")
    sub = p.add_subparsers(dest="cmd", required=True)

    pa = sub.add_parser("aggregate", help="로그를 집계해 aggregates.json 생성")
    pa.add_argument("--out", default="aggregates.json", help="출력 경로")
    pa.add_argument("--claude", nargs="*", default=None, help="Claude 로그 루트(생략 시 기본 경로)")
    pa.add_argument("--codex", nargs="*", default=None, help="Codex 로그 루트(생략 시 기본 경로)")

    pv = sub.add_parser("validate-insights", help="insights.json 구조 검증")
    pv.add_argument("path", help="검증할 insights.json 경로")

    pr = sub.add_parser("render", help="insights+aggregates → HTML 리포트")
    pr.add_argument("--insights", required=True, help="insights.json 경로")
    pr.add_argument("--aggregates", required=True, help="aggregates.json 경로")
    pr.add_argument("--out", default="report.html", help="출력 HTML 경로")

    args = p.parse_args(argv)
    if args.cmd == "aggregate":
        print("Network: DISABLED · reading ~/.claude, ~/.codex (read-only) · output stays local", file=sys.stderr)
        # Normalize empty list (flag given with no values) to None → use default paths
        if args.claude == []:
            args.claude = None
        if args.codex == []:
            args.codex = None

        roots = None
        if args.claude is not None or args.codex is not None:
            roots = {}
            if args.claude is not None:
                roots["claude"] = args.claude
            if args.codex is not None:
                roots["codex"] = args.codex

        # Stage 1: extract
        print("로그를 스캔하는 중…", file=sys.stderr)
        records = extract_records(roots)
        n = len(records)
        print(f"질문 {n}개 발견 — 분석 준비 중…", file=sys.stderr)

        # Graceful empty handling
        if n == 0:
            print(
                "\n로그를 찾지 못했습니다.\n"
                "  · Claude Code 또는 Codex를 사용하고 있는지 확인해 주세요.\n"
                "  · 기본 경로: ~/.claude/projects  /  ~/.codex\n"
                "  · 직접 경로를 지정하려면: --claude <경로>  /  --codex <경로>",
                file=sys.stderr,
            )
            # Still write an aggregates.json with total_questions:0 so downstream tools
            # don't break, but clearly report nothing was found.
            agg = build_aggregates(records)
            os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
            with open(args.out, "w", encoding="utf-8") as fh:
                json.dump(agg, fh, ensure_ascii=False, indent=2, sort_keys=True)
            print(f"빈 집계 파일 저장 → {args.out}", file=sys.stderr)
            return 0

        # Stage 2: build aggregates
        print("집계하는 중…", file=sys.stderr)
        agg = build_aggregates(records)
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(agg, fh, ensure_ascii=False, indent=2, sort_keys=True)

        m = agg["meta"]
        print(f"질문 {m['total_questions']}개 집계 완료 → {args.out}", file=sys.stderr)
        print(f"  도구별: {m['by_tool']}", file=sys.stderr)
        dr = m["date_range"]
        if dr[0] is not None:
            print(f"  기간: {dr[0]} ~ {dr[1]}", file=sys.stderr)
        else:
            print("  기간: (레코드 없음)", file=sys.stderr)
        return 0

    if args.cmd == "validate-insights":
        try:
            with open(args.path, encoding="utf-8") as fh:
                obj = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"파일 읽기 실패: {exc}", file=sys.stderr)
            return 1
        errs = validate_insights(obj)
        if errs:
            for e in errs:
                print(f"  ✗ {e}", file=sys.stderr)
            print(f"insights 검증 실패: {len(errs)}건", file=sys.stderr)
            return 1
        print("insights 검증 통과 ✓", file=sys.stderr)
        return 0

    if args.cmd == "render":
        try:
            with open(args.insights, encoding="utf-8") as fh:
                insights = json.load(fh)
            with open(args.aggregates, encoding="utf-8") as fh:
                aggregates = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"파일 읽기 실패: {exc}", file=sys.stderr)
            return 1
        errs = validate_insights(insights)
        if errs:
            print(f"insights 구조 오류 {len(errs)}건 — render 중단", file=sys.stderr)
            for e in errs:
                print(f"  ✗ {e}", file=sys.stderr)
            return 1
        html = build_report_html(insights, aggregates)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(html)
        print(f"리포트 생성 완료 → {args.out}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
