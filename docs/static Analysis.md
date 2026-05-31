# 정적 분석 결과 (Static Analysis)


**관련 문서**: [CODING.md](./CODING.md), [quality.md](./quality.md), [defect_log.md](./defect_log.md)

---

## 0. 본 문서의 목적

코드를 실행하지 않고 검사하는 **정적 분석**을 코드 품질 활동으로 다룬다. 본 문서는 매칭 엔진(`orderbook.py`)에 정적 분석 도구 3종을 돌린 **현재 결과**와, 엔진 정비 과정에서 정적 분석이 무엇을 잡아 어떻게 고쳤는지를 기록한다. 모든 수치는 실제 도구 실행값이다.

| 도구 | 검사 항목 |
|---|---|
| flake8 | PEP8 스타일 위반 (NFR-M-01 검증) |
| pylint | 코드 품질 종합 점수 + 설계 경고 |
| mypy | 타입 정합성 |

---

## 1. 측정 결과 (현재 코드)

| 도구 | 결과 | 판정 |
|---|---|---|
| flake8 (line-length 100) | 위반 **0건** | PEP8 충족 → NFR-M-01  |
| pylint | **9.62 / 10** | 양호 |
| mypy | 오류 0건 (Success) | 통과 |

단위 테스트 32개도 모두 통과하며 커버리지 100%를 유지한다.

---

## 2. 정비 과정에서 정적 분석이 잡은 것

### 2.1 cancel_order의 위험 패턴 (발견 → 수정)

엔진 정비 중 `cancel_order`의 초안은 호가창 리스트를 순회하는 도중에 그 리스트에서 원소를 제거하는 형태였다.

```python
# 초안 — 순회 중 리스트 수정 (위험 패턴)
for order in book:
    if order.order_id == order_id:
        book.remove(order)   # ← 순회 중 제거
        return True
```

이 코드는 제거 직후 곧바로 `return` 하므로 **결과적으로는 동작**했고 단위 테스트도 모두 통과했다. 즉 사람 눈으로도, 테스트로도 드러나지 않던 잠재 위험이다. 그러나 정적 분석(pylint)이 **W4701(modified-iterating-list)** 경고로 이를 지적했다. "여러 주문을 한 번에 취소"하도록 바뀌면 곧장 버그가 될 패턴이다.

```python
# 수정본 — 대상을 먼저 찾고 나서 제거
target = next((o for o in book if o.order_id == order_id), None)
if target is not None:
    book.remove(target)
    target.status = STATUS_CANCELLED
    return True
```

**수정 효과**: W4701 경고 해소(현재 코드엔 없음), pylint 9.52 → **9.62**, 테스트 32개 여전히 전부 통과(커버리지 100% 유지, 회귀 없음).



### 2.2 남겨 둔 경고 (의도된 설계)

| 경고 | 위치 | 판단 |
|---|---|---|
| R0903 (public 메서드 너무 적음) | Order, Trade | 두 클래스는 데이터를 담는 용도라 메서드가 적은 것이 정상. 유지. |
| R0917 (위치 인자 너무 많음) | Trade 생성자 | 체결의 필수 필드라 줄이면 의미가 흐려짐. 유지. |

---
