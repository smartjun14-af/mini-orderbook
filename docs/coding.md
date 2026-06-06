# Mini-OrderBook 코딩 (구현 단계)

**관련 문서**: [SRS.md](./SRS.md), [Design.md](./Design.md)

---

## 1. 코딩 작업 절차 

| 단계 | 본 프로젝트 적용 |
|---|---|
| ① 코딩 표준 만들기 | PEP 8 (Python 표준)을 기준으로 합의 |
| ② 패키지 결정 | 메인 엔진은 `orderbook.py` 단일 모듈, UI는 `app.py`로 분리 |
| ③ 클래스 구현 후 인스펙션 | 메서드마다 docstring + 정적 점검(§5) 후 커밋 |
| ④ 클래스 단위 테스트 | 별도 파일 `test_orderbook.py` (이후 단계에서 작성) |
| ⑤ 통합·릴리스 | Streamlit `app.py`에서 엔진 import → 통합 |

---

## 2. 코딩 표준

### 2.1 명명 규칙

| 대상 | 규칙 | 예시 |
|---|---|---|
| 클래스 | PascalCase, 명사 | `Order`, `OrderBook`, `Trade` |
| 함수·메서드·변수 | snake_case | `submit_order`, `cancel_order`, `next_order_id` |
| 상수 | UPPER_SNAKE_CASE | `SIDE_BUY`, `SIDE_SELL` |
| 비공개 멤버 | `_` 접두사 | `_bids`, `_asks`, `_match()`, `_insert_into_book()` |

### 2.2 간결성 원칙

- **단일 책임**: 한 함수는 한 가지 일만 한다.
  - `_match()` — 매칭만
  - `_record_trade()` — 체결 객체 생성만
  - `_insert_into_book()` — 정렬 위치에 삽입만
  - `_is_matchable()` — 체결 가능 여부만 판별
- **얕은 결합**: `Order`, `Trade`는 데이터만 담고, 로직은 `OrderBook`에 모은다
- **높은 응집**: 매칭 관련 로직은 전부 `OrderBook` 내부 비공개 메서드로 둔다

### 2.3 가독성 보조

- 모든 public API에 docstring을 단다
- 매직 넘버를 안 쓴다 (BUY/SELL은 상수로 뺀다)

---

## 3. 설계에서 코드 생성

| Design.md 산출물 | orderbook.py 대응 |
|---|---|
| §6 클래스 다이어그램 — Order | `class Order` |
| §6 클래스 다이어그램 — Trade | `class Trade` |
| §6 클래스 다이어그램 — OrderBook | `class OrderBook` |
| §7.1 완전 체결 시퀀스 | `submit_order()` → `_match()` → `_record_trade()` |
| §7.2 부분 체결 시퀀스 | `_match()` 루프 + `_insert_into_book()` 잔량 등록 |

### 3.1 연관의 코딩 


- **OrderBook 1 ── * Order**: `OrderBook._bids: list`, `OrderBook._asks: list` (1대N을 컬렉션으로 표현)
- **OrderBook 1 ── * Trade**: `OrderBook._trades: list`
- **Trade * ── 2 Order**: ID 참조(`buy_order_id`, `sell_order_id`)로 약결합 — 순환 참조를 피하려는 의도적 선택

---

## 4. 리팩토링 

| Before | After | 이유 |
|---|---|---|
| `submit_order()` 안에 매칭 로직을 통째로 넣음 | `_match()` 메서드로 분리 | 단일 책임, 테스트 용이성 |
| 매칭 가능 조건을 `submit_order` 안에 inline | `_is_matchable()`로 추출 | 가독성, 재사용성 |
| Trade 생성 코드 중복 | `_record_trade()`로 추출 | DRY 원칙 |
| 입력 검증 코드 인라인 | `_validate_order_input()`로 추출 | 진입점 검증 일원화 |
| 주문 유형별 매칭 규칙이 분기로 섞임 | `MatchingStrategy` + Limit/Market/IOC/FOK 전략으로 분리 | 개방-폐쇄(OCP) — 유형 추가 시 `OrderBook` 본체 불변 |

---

## 5. 코드 품질 향상 기법 

### 5.1 코드 인스펙션

| 결함 타입 | 점검 항목 | 본 코드 상태 |
|---|---|---|
| 로직 문제 | 매칭 조건의 부등호 방향 (BUY: ≥, SELL: ≤) | `_is_matchable()`에서 명시적 분기 |
| 컴퓨팅 문제 | 잔량 음수 가능성 | `min(들어온 잔량, 대기 잔량)`으로 방지 |
| 인터페이스 문제 | 잘못된 side 문자열 | `_validate_order_input()`이 `ValueError` raise |
| 데이터 처리 | 정렬 위치 오류 | `_insert_into_book()`의 가격 비교 부등호 검증 |

### 5.2 정적 분석

- 정의해 놓고 안 쓰는 **데드코드가 없다**
- **미사용 변수·임포트가 없다**
- 실제로 돌린 도구: `flake8`, `pylint`, `mypy` (자세한 결과는 정적 분석 문서 참고)

---

## 6. 패키지 의존성

```
streamlit>=1.30.0   # UI 레이어 (app.py에서 사용)
pandas>=2.0.0       # 호가창·체결내역 테이블 표시
pytest>=7.0.0       # 단위 테스트 (이후 단계에서 진행)
```

`orderbook.py` 자체는 외부 라이브러리 없이 표준 라이브러리만으로 돌아간다. 의존성을 최소화해서 테스트랑 재사용을 쉽게 만들었다.
