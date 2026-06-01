#!/usr/bin/env python3
"""Mini-OrderBook 품질 메트릭 일괄 측정 스크립트."""
import ast
import os
import re
import subprocess
import sys

# 어디서 실행하든 스크립트(=코드) 폴더 기준으로 동작하게 한다.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

SRC = "orderbook.py"
TEST = "test_orderbook.py"


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def section(title):
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def main():
    # 1) 테스트 커버리지
    section("1. 단위 테스트 + 커버리지  (pytest --cov)")
    cov = run([sys.executable, "-m", "pytest", TEST, f"--cov={SRC[:-3]}",
               "--cov-report=term-missing", "-q"])
    for line in cov.splitlines():
        if SRC in line or "TOTAL" in line or "passed" in line or "no tests" in line:
            print(line)

    # 2) 사이클로매틱 복잡도
    section("2. 사이클로매틱 복잡도  (radon cc)")
    cc_out = run([sys.executable, "-m", "radon", "cc", SRC, "-s", "-a"])
    print(cc_out.strip())

    # 3) 유지보수성 지수
    section("3. 유지보수성 지수  (radon mi)")
    print(run([sys.executable, "-m", "radon", "mi", SRC, "-s"]).strip())

    # 4) 코드 줄 수
    section("4. 코드 줄 수  (radon raw)")
    for line in run([sys.executable, "-m", "radon", "raw", SRC]).splitlines():
        if any(k in line for k in ("LOC", "SLOC", "Comment", "Multi")):
            print(line)

    # 5) 정적 분석  (flake8 는 --jobs=1 로 Windows 멈춤 방지)
    section("5. 정적 분석  (flake8 / pylint)")
    fl = run([sys.executable, "-m", "flake8", SRC,
              "--max-line-length=100", "--count", "--jobs=1"]).strip()
    print(f"flake8 위반 건수: {fl.splitlines()[-1] if fl else '0'}")
    pl = run([sys.executable, "-m", "pylint", SRC, "--disable=R0902,R0913"])
    score = re.search(r"rated at ([\d.]+)/10", pl)
    print(f"pylint 점수: {score.group(1) if score else '?'}/10")

    # 6) 객체지향 메트릭 (WMC / CBO)
    section("6. 객체지향 메트릭 (WMC / CBO)  [radon 복잡도 합산 + AST 참조 분석]")
    cc_map = {}
    for line in cc_out.splitlines():
        m = re.search(r"(Order|Trade|OrderBook)\.(\w+).*\((\d+)\)", line)
        if m:
            cc_map[(m.group(1), m.group(2))] = int(m.group(3))
    tree = ast.parse(open(SRC, encoding="utf-8").read())
    classes = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    cnames = set(classes)
    for cn, node in classes.items():
        methods = [m for m in node.body if isinstance(m, ast.FunctionDef)]
        wmc = sum(cc_map.get((cn, m.name), 1) for m in methods)
        refs = {s.id for s in ast.walk(node)
                if isinstance(s, ast.Name) and s.id in cnames and s.id != cn}
        print(f"  {cn:12s}  WMC={wmc:3d}  CBO={len(refs)}  (참조: {sorted(refs) or '없음'})")

    print("\n측정 완료. 위 수치는 모두 동일 환경에서 재현 가능합니다.")


if __name__ == "__main__":
    main()
