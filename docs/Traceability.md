# 추적성 매트릭스 (Traceability Matrix)


**관련 문서**: [SRS.md](./SRS.md), [requirements_model.md](./requirements_model.md), [TESTING.md](./TESTING.md), [state_diagram.md](./state_diagram.md), [quality.md](./quality.md)

---

## 0. 본 문서의 목적

추적성 매트릭스는 **요구사항이 빠짐없이 코드와 테스트로 이어졌는지**를 표 하나로 확인하는 도구다. SRS의 기능 요구사항(FR) → 유저 스토리(US) → 테스트 → 코드 함수를 한 줄로 연결해, "요구했는데 구현이 없는 항목(고아 요구)"이나 "테스트가 없는 기능(검증 누락)"을 한눈에 잡는다.

---

## 1. 기능 요구사항 추적 매트릭스 (FR → US → 테스트 → 코드)

| FR | 요구 내용(요약) | US | 테스트 (test_orderbook.py) | 코드 (orderbook.py) |
|---|---|---|---|---|
| FR-01 | 지정가 주문 접수 + 고유 ID 할당 | US-01, US-02 | `TestInputValidation` 8개, `test_minimum_valid_order` | `submit_order`, `Order.__init__` |
| FR-02 | 매수가 ≥ 최우선 매도가일 때 자동 매칭 | US-03 | `test_full_fill_exact_quantity`, `test_no_match_when_price_gap`, `test_sell_order_matches_bids`, `test_sell_no_match_when_too_expensive` | `_match`, `_is_matchable` |
| FR-03 | 동일 가격 시간 우선 매칭 | US-03 | `test_time_priority_same_price`, `test_price_priority_buy_takes_cheapest_ask`, `test_sell_takes_highest_bid_first` | `_match` (정렬 키 `seq`) |
| FR-04 | 부분 체결 시 잔량 호가창 유지 | US-04 | `test_partial_fill_incoming_larger`, `test_partial_fill_resting_larger`, `test_partial_sweep_then_rest`, `test_partial_to_filled` | `_match`, `_insert_into_book` |
| FR-05 | 호가창 가격순 정렬 반환 | US-05 | `test_bids_sorted_high_to_low`, `test_asks_sorted_low_to_high`, `test_aggregate_same_price`, `test_empty_book` | `get_book`, `_aggregate` |
| FR-06 | 체결 내역 시간순 저장·조회 | US-06 | `test_multi_level_sweep`, `test_full_fill_exact_quantity` | `get_trades`, `_record_trade`, `Trade` |
| FR-07 | 미체결 주문 취소 + 호가창 제거 | US-07 | `test_accepted_to_cancelled`, `test_cancel_removes_from_book`, `test_partial_to_cancelled` | `cancel_order` |
| FR-08 | 이미 체결/취소된 주문 취소 거부 | US-07 | `test_cancel_nonexistent_returns_false` | `cancel_order` (False 반환) |

**확인 결과**: 8개 FR 전부 대응하는 코드와 테스트가 존재한다. 구현이 없는 요구(고아 요구)도, 검증이 없는 기능도 없다. → **요구 커버리지 100%** (총 32개 테스트).

---

## 2. 주요 비기능 요구사항(NFR) 추적

측정 가능한 NFR이 실제로 충족됐는지 증거 문서와 연결한다.

| NFR | 기준 | 측정/증거 | 
|---|---|---|---|
| NFR-T-01 | 코어 단위 테스트 커버리지 ≥ 80% | 100% (quality.md §3.1) | 
| NFR-T-03 | 상태 기반 테스트로 상태 전이 검증 | `TestStateTransition` 7개 (모든 전이, state_diagram.md §3) | 
| NFR-M-01 | PEP8 준수 | flake8 위반 0건 (static_analysis.md) | 
| NFR-M-03 | 함수당 사이클로매틱 복잡도 ≤ 10 | 최대 9 (quality.md §3.1) | 
| NFR-P-01 | 단일 주문 매칭 ≤ 100ms | N=1000에서 0.099ms (benchmark.md) | 
| NFR-P-02 | 미체결 주문 ≥ 1,000건 보관 | N=5,000까지 정상 동작 (benchmark.md) | 

---

## 3. 명세-구현 차이 (추적성으로 드러난 점)

추적성 매트릭스의 본래 목적이 "명세와 구현의 어긋남을 찾는 것"이므로, 점검 중 발견한 차이를 솔직히 기록한다.

1. **주문 ID 형식**: SRS 수락 기준은 UUID를 명시하나, 본 구현은 **순번 정수**를 쓴다. 이는 단점이 아니라, 정수 순번이 시간 우선순위(`seq`) 계산을 겸할 수 있어 단일 사용자 시뮬레이터에 더 단순하기 때문에 택한 설계다. 다만 SRS 문구와는 다르므로, 추후 SRS를 "고유 ID(순번 또는 UUID)"로 완화하거나 구현을 UUID로 바꿔 일치시킨다.
2. **가격·수량 자료형**: SRS는 "정수 또는 소수"를 허용하나, 본 구현은 **정수만** 허용한다. 호가 단위가 정수인 단순화 가정에 따른 것이며, 소수 호가가 필요해지면 검증 함수만 확장하면 된다.


---
