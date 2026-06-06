# 정적 분석 결과 (Static Analysis)

**버전**: 0.4
**관련 문서**: [coding.md](./coding.md), [quality.md](./quality.md), [defect_log.md](./defect_log.md)

---

## 0. 문서의 목적

코드를 실행하지 않고 검사하는 정적 분석을 코드 품질 활동으로 다룬다. 매칭 엔진(`orderbook.py`)에 정적 분석 도구 3종을 돌린 현재 결과와, 엔진을 정비하는 과정에서 정적 분석이 뭘 잡아서 어떻게 고쳤는지를 적는다.

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
| pylint | **9.75 / 10** | 양호 |
| mypy | 오류 0건 (Success) | 통과 |

단위 테스트 50개도 전부 통과하고 커버리지 100%를 유지한다(지정가 → 시장가 → IOC/FOK까지 추가한 뒤 다시 측정).

---

## 2. 정비 과정에서 정적 분석이 잡은 것

### 2.1 cancel_order의 위험 패턴 (발견 → 수정)

엔진을 정비하던 중, `cancel_order`의 초안은 호가창 리스트를 순회하는 도중에 그 리스트에서 원소를 제거하는 형태였다.

```python
# 초안 — 순회 중 리스트 수정 (위험 패턴)
for order in book:
    if order.order_id == order_id:
        book.remove(order)   # ← 순회 중 제거
        return True
```

이 코드는 제거하자마자 바로 `return` 하니까 **결과적으로는 동작**했고, 단위 테스트도 다 통과했다. 그런데 pylint가 **W4701(modified-iterating-list)** 경고로 이걸 짚었다. 여러 주문을 한 번에 취소하도록 바뀌는 순간 바로 버그가 될 수 있다.

```python
# 수정본 — 대상을 먼저 찾고 나서 제거
target = next((o for o in book if o.order_id == order_id), None)
if target is not None:
    book.remove(target)
    target.status = STATUS_CANCELLED
    return True
```

**수정 효과**: W4701 경고가 사라지고(현재 코드엔 없다) 점수도 올랐다. 이후 시장가·IOC·FOK 주문을 차례로 추가하며 다시 잰 pylint는 **9.75**, 테스트 50개 전부 통과(커버리지 100% 유지, 회귀 없음).

### 2.2 남겨 둔 경고 

| 경고 | 위치 | 판단 |
|---|---|---|
| R0903 (public 메서드 너무 적음) | Order, Trade | 두 클래스는 데이터를 담는 용도라 메서드가 적은 게 정상. 유지. |
| R0917 (위치 인자 너무 많음) | Trade 생성자 | 체결의 필수 필드라 줄이면 의미가 흐려진다. 유지. |
| W0613 (미사용 인자) | MarketStrategy.is_matchable | 전략 인터페이스 시그니처상 인자를 받지만 시장가는 가격을 안 본다. 인터페이스 일관성을 위해 시그니처는 그대로 두고 이 경고만 명시적으로 억제(`# pylint: disable=unused-argument`). |

> IOC/FOK는 `LimitStrategy`를 상속해 다른 부분(잔량 처리·전량 조건)만 override하므로 새로운 경고를 만들지 않았다.

---
