# 추적성 매트릭스 (Traceability Matrix)

**버전**: 0.4
**관련 문서**: [SRS.md](./SRS.md), [requirements_model.md](./requirements_model.md), [quality.md](./quality.md)

---

## 0. 문서의 목적
SRS의 기능 요구사항(FR) → 유저 스토리(US) → 테스트 → 코드 함수를 한 줄로 엮어서, 요구는 했는데 구현이 없는 항목(고아 요구)이나 테스트가 없는 기능(검증 누락)을 한눈에 잡아낸다.

---

## 1. 기능 요구사항 추적 매트릭스 (FR → US → 테스트 → 코드)

| FR | 요구 내용(요약) | US | 테스트 (test_orderbook.py) | 코드 (orderbook.py) |
|---|---|---|---|---|
| FR-01 | 지정가 주문 접수 + 고유 ID 할당 | US-01, US-02 | `TestInputValidation` 8개, `test_minimum_valid_order` | `submit_order`, `Order.__init__` |
| FR-02 | 매수가 ≥ 최우선 매도가일 때 자동 매칭 | US-03 | `test_full_fill_exact_quantity`, `test_no_match_when_price_gap`, `test_sell_order_matches_bids`, `test_sell_no_match_when_too_expensive` | `_match`, `LimitStrategy.is_matchable` |
| FR-03 | 동일 가격 시간 우선 매칭 | US-03 | `test_time_priority_same_price`, `test_price_priority_buy_takes_cheapest_ask`, `test_sell_takes_highest_bid_first` | `_match` (정렬 키 `seq`) |
| FR-04 | 부분 체결 시 잔량 호가창 유지 | US-04 | `test_partial_fill_incoming_larger`, `test_partial_fill_resting_larger`, `test_partial_sweep_then_rest`, `test_partial_to_filled` | `_match`, `_insert_into_book` |
| FR-05 | 호가창 가격순 정렬 반환 | US-05 | `test_bids_sorted_high_to_low`, `test_asks_sorted_low_to_high`, `test_aggregate_same_price`, `test_empty_book` | `get_book`, `_aggregate` |
| FR-06 | 체결 내역 시간순 저장·조회 | US-06 | `test_multi_level_sweep`, `test_full_fill_exact_quantity` | `get_trades`, `_record_trade`, `Trade` |
| FR-07 | 미체결 주문 취소 + 호가창 제거 | US-07 | `test_accepted_to_cancelled`, `test_cancel_removes_from_book`, `test_partial_to_cancelled` | `cancel_order` |
| FR-08 | 이미 체결/취소된 주문 취소 거부 | US-07 | `test_cancel_nonexistent_returns_false` | `cancel_order` (False 반환) |
| FR-09 | 시장가 주문 즉시 체결(가격 무시, 최우선부터) | US-08 | `test_market_buy_full_fill`, `test_market_buy_ignores_price_takes_best`, `test_market_sell_full_fill`, `test_invalid_order_type` | `submit_order(order_type)`, `MarketStrategy.is_matchable`, `_match` |
| FR-10 | 시장가 미체결 잔량 취소(호가창에 안 남김) | US-08 | `test_market_buy_partial_then_cancel`, `test_market_buy_empty_book_cancelled`, `test_market_with_price_rejected` | `MarketStrategy.rests_remainder`, `submit_order` (잔량 취소) |
| FR-11 | IOC 주문: 즉시 체결 가능한 만큼만 체결, 잔량 취소 | US-09 | `test_ioc_full_fill`, `test_ioc_partial_then_cancel`, `test_ioc_no_cross_cancelled` | `IOCStrategy.rests_remainder`, `submit_order` (잔량 취소) |
| FR-12 | FOK 주문: 전량 체결 가능할 때만 체결, 아니면 전량 취소 | US-10 | `test_fok_full_fill`, `test_fok_insufficient_cancelled`, `test_fok_exact_boundary_multi_level`, `test_fok_no_cross_cancelled`, `test_fok_empty_book_cancelled`, `test_fok_sell_full_fill` | `FOKStrategy.requires_full_fill`, `_fillable_quantity`(사전검사), `submit_order` |

**확인 결과**: 12개 FR 전부 짝이 되는 코드와 테스트가 있다. 구현이 없는 요구(고아 요구)도, 검증이 없는 기능도 없다 → **요구 커버리지 100%**(총 50개 테스트). 시장가·IOC·FOK(FR-09~12)는 전략 패턴으로 추가했는데, 아키텍처에서 미리 잡아 둔 확장점이 실제로 쓰인 경우다. 전략 인터페이스 자체의 계약(미구현 메서드 호출 시 예외)은 `test_base_strategy_requires_implementation`으로 검증한다.

---

## 2. 주요 비기능 요구사항(NFR) 추적

측정 가능한 NFR이 실제로 충족됐는지 증거 문서와 연결했다.

| NFR | 기준 | 측정/증거 |
|---|---|---|
| NFR-T-01 | 코어 단위 테스트 커버리지 ≥ 70% | 100% (quality.md §3.1) |
| NFR-T-03 | 상태 기반 테스트로 상태 전이 검증 | `TestStateTransition` 7개 (모든 전이, state_diagram.md §3) |
| NFR-M-01 | PEP8 준수 | flake8 위반 0건 (정적 분석 문서) |
| NFR-M-03 | 함수당 사이클로매틱 복잡도 ≤ 10 | 최대 9 (`_match`·`_validate_order_input`, quality.md §3.1) |
| NFR-P-01 | 단일 주문 매칭 ≤ 100ms | N=1000에서 0.268ms (benchmark.md) |
| NFR-P-02 | 미체결 주문 ≥ 1,000건 보관 | N=5,000까지 정상 동작 (benchmark.md) |

---

## 3. 명세-구현 차이 (추적성으로 드러난 점을 기술한다.)

추적성 매트릭스의 원래 목적이 "명세와 구현이 어긋난 데를 찾는 것"이라, 점검하다 발견한 차이를 적어 둔다.

1. **주문 ID 형식**: SRS 수락 기준은 UUID를 명시하지만, 구현은 **순번 정수**를 쓴다. 단점이라기보다, 정수 순번이 시간 우선순위(`seq`) 계산까지 겸할 수 있어서 단일 사용자 시뮬레이터엔 더 단순하기 때문에 택한 설계다. 다만 SRS 문구와는 다르니, 추후 SRS를 "고유 ID(순번 또는 UUID)"로 완화하거나 구현을 UUID로 바꿔 맞추면 된다.
2. **가격·수량 자료형**: SRS는 "정수 또는 소수"를 허용하지만, 구현은 **정수만** 받는다. 호가 단위가 정수라는 단순화 가정에 따른 것이고, 소수 호가가 필요해지면 검증 함수만 손보면 된다.

