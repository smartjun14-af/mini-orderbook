
**관련 문서**: [SRS.md](./SRS.md), [DESIGN.md](./DESIGN.md)
---

## 1. 코딩 작업 절차 


| 강의록 단계 | 본 프로젝트 적용 |
|---|---|
| ① 코딩 표준 만들기 | PEP 8 (Python 표준) + 타입 힌트 의무화로 합의 |
| ② 패키지 결정 | 메인 엔진은 `orderbook.py` 단일 모듈, UI는 `app.py` 분리 |
| ③ 클래스 구현 후 인스펙션 | 모든 메서드 docstring + 정적 점검(§5) 후 커밋 |
| ④ 클래스 단위 테스트 | 별도 파일 `test_orderbook.py` (이후 단계에서 작성) |
| ⑤ 통합·릴리스 | Streamlit `app.py`에서 엔진 import → 통합 |

---

## 2. 코딩 표준

강의록의 핵심 기준 *"간결하고 읽기 쉬운 것"* 을 따른다.

### 2.1 명명 규칙

| 대상 | 규칙 | 예시 |
|---|---|---|
| 클래스 | PascalCase, 명사 | `Order`, `OrderBook`, `Trade` |
| 함수·메서드·변수 | snake_case | `submit_order`, `cancel_order`, `next_order_id` |
| 상수 | UPPER_SNAKE_CASE | `SIDE_BUY`, `SIDE_SELL`, `VALID_SIDES` |
| 비공개 멤버 | `_` 접두사 | `_bids`, `_asks`, `_match()`, `_insert_into_book()` |

### 2.2 간결성 원칙

- **단일 책임**: 한 함수는 한 가지 일만 한다.
  - `_match()` — 매칭만
  - `_record_trade()` — 체결 객체 생성만
  - `_insert_into_book()` — 정렬 위치 삽입만
  - `_is_matchable()` — 체결 가능 여부만 판별
- **얕은 결합**: `Order`, `Trade`는 dataclass로 데이터만, 로직은 `OrderBook`에 집중
- **높은 응집**: 매칭 관련 로직은 모두 `OrderBook` 내부 비공개 메서드

### 2.3 가독성 보조

- 모든 public API에 docstring
- 모든 함수 시그니처에 type hint
- 매직 넘버 없음 (BUY/SELL은 상수)

---

## 3. 설계에서 코드 생성


| DESIGN.md 산출물 | orderbook.py 대응 |
|---|---|
| §6 클래스 다이어그램 — Order | `@dataclass class Order` |
| §6 클래스 다이어그램 — Trade | `@dataclass class Trade` |
| §6 클래스 다이어그램 — OrderBook | `class OrderBook` |
| §7.1 완전 체결 시퀀스 | `submit_order()` → `_match()` → `_record_trade()` |
| §7.2 부분 체결 시퀀스 | `_match()` 루프 + `_insert_into_book()` 잔량 등록 |

### 3.1 연관의 코딩 

강의록의 연관 관계 코딩 방식 적용:

- **OrderBook 1 ── * Order**: `OrderBook._bids: list[Order]`, `OrderBook._asks: list[Order]` (1대N을 컬렉션으로 표현)
- **OrderBook 1 ── * Trade**: `OrderBook._trades: list[Trade]`
- **Trade * ── 2 Order**: ID 참조(`buy_order_id`, `sell_order_id`)로 약결합 — 순환 참조를 피하기 위한 의도적 선택

---

## 4. 리팩토링 

리팩토링은 *"결과의 변경 없이 코드의 구조를 재조정"* 하는 것. 본 프로젝트에서 실제로 적용한 리팩토링:

| Before | After | 이유 |
|---|---|---|
| `submit_order()` 내부에 매칭 로직 통째로 | `_match()` 메서드로 분리 | 단일 책임, 테스트 용이성 |
| 매칭 가능 조건을 `submit_order` 안에 inline | `_is_matchable()` 정적 메서드로 분리 | 가독성, 재사용성 |
| Trade 생성 코드 중복 | `_record_trade()`로 추출 | DRY 원칙 |
| 입력 검증 코드 인라인 | `_validate_order_input()` 정적 메서드 | 진입점 검증 일원화 |

---

## 5. 코드 품질 향상 기법 

### 5.1 코드 인스펙션

| 결함 타입 | 점검 항목 | 본 코드 상태 |
|---|---|---|
| 로직 문제 | 매칭 조건의 부등호 방향 (BUY: ≥, SELL: ≤) | `_is_matchable()` 명시적 분기 |
| 컴퓨팅 문제 | 잔량 음수 가능성 | `min(incoming.remaining, best.remaining)`으로 방지 |
| 인터페이스 문제 | 잘못된 side 문자열 | `_validate_order_input()`이 `ValueError` raise |
| 데이터 처리 | 정렬 위치 오류 | `_insert_into_book()`의 가격 비교 부등호 검증 |

### 5.2 정적 분석

- **타입 힌트** 의무화 → `mypy` 등 정적 분석 도구가 검사 가능
- **데드코드 없음**: 모든 정의된 함수가 호출됨
- **미사용 변수 없음**: 임포트·변수 모두 활용됨
- 권장 도구: `ruff check orderbook.py`, `mypy orderbook.py`


---

## 6. 패키지 의존성

```
streamlit>=1.30.0   # UI 레이어 (app.py에서 사용)
pandas>=2.0.0       # 호가창·체결내역 테이블 표시
pytest>=7.0.0       # 단위 테스트 (이후 단계에서 진행)
```

`orderbook.py` 자체는 **순수 표준 라이브러리만 사용**한다(`dataclasses`, `datetime`, `typing`). 의존성을 최소화하여 테스트와 재사용을 쉽게 만들었다.
