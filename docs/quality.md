# 품질 관리 문서 (Quality Management)

**버전**: 0.4
**관련 문서**: [process.md](./process.md), [SRS.md](./SRS.md), [Design.md](./Design.md), [architecture.md](./architecture.md), [market_order_design.md](./market_order_design.md), [coding.md](./coding.md), [maintenance.md](./maintenance.md), [defect_log.md](./defect_log.md)

---

## 0. 본 문서의 범위

 앞 단계에서 만든 산출물(요구·설계·코드·테스트)을 **품질 속성**과 **품질 메트릭**으로 평가한다.

여기 나오는 메트릭은 추정값이 아니라 최종 코드(`orderbook.py`, 지정가·시장가·IOC·FOK 네 주문 유형 포함)에 대해 `radon`과 `pytest --cov`로 직접 잰 값이고, `measure_metrics.py`를 한 번 돌리면 전부 그대로 재현된다.

---

## 1. 품질 모델 선정

ISO/IEC 9126의 6대 품질 특성을 평가 기준으로 삼았다.

| 채택 | 근거 |
|---|---|
| ISO/IEC 9126 |  6개 특성(기능성·신뢰성·사용용이성·효율성·유지보수성·이식성)이 소규모 학습 시스템에도 빠짐없이 대응돼서 누락 없는 점검표가 된다. |

---

## 2. 품질 속성 평가 (정성 평가)

ISO/IEC 9126의 6대 특성을 기준으로, 각 특성을 어떤 산출물·결정으로 만족시켰는지 정리했다.

| 품질 특성 | 본 시스템에서의 실현 | 근거 산출물 |
|---|---|---|
| **기능성**  | 체결가가 "호가창에 먼저 있던 주문(수동 주문)의 가격"을 따르도록 정확히 구현. 지정가·시장가·IOC·FOK 네 주문 유형을 모두 지원. 초기 AI 코드의 체결가 오류(D-01)는 사람이 도메인 검토로 잡아 고침. | defect_log D-01, `_record_trade`, 전략 패턴 |
| **신뢰성** | 모든 입력을 `_validate_order_input`으로 검증해 잘못된 주문을 거부. 단위 테스트 50개·커버리지 100%로 동작 보장. 개발 중 결함 14건을 제거. | `test_orderbook.py`, defect_log |
| **사용용이성**  | Streamlit UI에 주문 폼·호가창·체결내역을 한 화면에 배치하고 색상·피드백을 일관되게 설계. | Design.md, `app.py`, 스크린샷 |
| **효율성**  | 메모리 기반 list 구조라 단순하지만 대량 주문엔 불리. 아키텍처 단계에서 list↔heap 트레이드오프를 명시적으로 따지고 벤치마크로 검증. | architecture.md (ATAM), benchmark.md |
| **유지보수성**  | 책임을 메서드 단위로 쪼개고, 주문 유형 차이를 전략 패턴으로 캡슐화(개방-폐쇄). 시장가·IOC·FOK를 더하면서도 `OrderBook` 본체는 거의 안 건드렸다. MI A등급, 커버리지 100%로 변경 시 회귀를 바로 잡아냄. | coding.md, market_order_design.md, §3 메트릭 |
| **이식성**  | 엔진(`orderbook.py`)은 외부 라이브러리 의존이 없는 순수 Python이라 어디서나 돌아간다. UI(Streamlit)와 엔진이 분리돼 엔진만 따로 재사용 가능. | architecture.md (계층 분리) |

---

## 3. 품질 메트릭 측정

### 3.1 구현 메트릭

| 메트릭 | 측정값 | 도구 |
|---|---|---|
| LOC (전체 줄 수) | 338 | radon raw |
| SLOC (순수 코드 줄) | 180 | radon raw |
| **사이클로매틱 복잡도(평균)** | **2.29 (A등급)** | radon cc |
| 최대 복잡도 메서드 | `_validate_order_input` = 9 (B), `_match` = 9 (B), `_fillable_quantity` = 6 (B), `submit_order`·`cancel_order` = 5 (A) | radon cc |

![메서드별 사이클로매틱 복잡도](../reports/quality_complexity.png)

사이클로매틱 복잡도는 "프로그램을 지나는 독립 경로의 수이자, 필요한 테스트 횟수"로 정의된다. 이 정의대로면 `_match`(복잡도 9)는 독립 경로가 9개라 최소 9개의 테스트가 필요하다. 실제로 체결 로직(`_match`)을 거치는 테스트는 체결·우선순위·상태·시장가·IOC/FOK·통합 클래스에 걸쳐 충분히 많아서 복잡도가 요구하는 테스트 수를 채운다. `_validate_order_input`은 주문 유형(지정가·시장가·IOC·FOK) 검증 분기가 늘면서 9까지 올랐고, `_fillable_quantity`(6)는 FOK가 "전량 체결 가능한지"를 미리 확인하려고 추가한 메서드다. 둘 다 입력 검증·IOC/FOK 테스트로 모두 커버된다.

### 3.2 설계 메트릭 (객체지향)

복잡도·결합도·응집도를 객체지향 형태로 구체화해서 클래스별로 쟀다(measure_metrics.py의 WMC/CBO 출력 기준).

| 클래스 | WMC (메서드 복잡도 합) | CBO (결합 클래스 수) | 응집도(LCOM) |
|---|---|---|---|
| Order | 2 | 0 | 단일 책임(데이터) |
| Trade | 2 | 0 | 단일 책임(데이터) |
| MatchingStrategy | 3 | 0 | 인터페이스 |
| LimitStrategy | 3 | 1 (MatchingStrategy) | 단일 책임(지정가 규칙) |
| MarketStrategy | 3 | 1 (MatchingStrategy) | 단일 책임(시장가 규칙) |
| IOCStrategy | 1 | 1 (LimitStrategy) | 지정가에서 잔량 처리만 다름 |
| FOKStrategy | 1 | 1 (LimitStrategy) | 지정가에서 전량 조건만 다름 |
| OrderBook | 43 | 2 (Order, Trade) | 단일 연결(높음) |

해석:
- **WMC**: 복잡도가 `OrderBook`에 몰리고(43) 데이터·전략 클래스는 1~3으로 낮다. 매칭 엔진이 핵심 책임이라 의도된 분포다. 시장가에 이어 IOC/FOK를 더했는데도 OrderBook의 WMC는 크게 안 튀었다(전략으로 분리한 효과). 특히 IOCStrategy·FOKStrategy는 LimitStrategy를 상속해 다른 점(잔량 처리/전량 조건)만 override하므로 WMC가 1로 가장 작다.
- **CBO(결합도)**: 전략 클래스들이 부모(MatchingStrategy 또는 LimitStrategy)에 결합(1)된 건 **상속 관계**라 의도된 거다. `OrderBook`은 Order·Trade 둘에만 결합되고, `Trade`는 여전히 **0**(주문을 ID로만 참조하는 약결합)이다.
- **응집도(LCOM)**: 각 전략 클래스는 한 가지 주문 유형의 규칙만 담아서 응집도가 높다. `OrderBook`의 메서드들은 호가창 상태나 메서드 호출 관계로 엮여 한 덩어리를 이룬다.

### 3.3 시스템 메트릭 (신뢰도)

강의록의 신뢰도 메트릭은 **MTBF = MTTF + MTTR**(고장 사이 평균 시간)이다. 그런데 MTBF는 **운영 중 실제 고장 데이터**가 있어야 계산할 수 있는데, 이 시스템은 운영 이력이 없는 학습용 시뮬레이터라 직접 잴 수가 없다.

그래서 무리하게 만들지 않고 **대리 지표**로 신뢰도를 평가했다.

| 대리 지표 | 값 | 의미 |
|---|---|---|
| 개발 중 발견·제거 결함 | 14건 | 출하 전에 잡아낸 결함의 양 |
| 테스트 통과율 / 커버리지 | 50개 전부 통과 / 100% | 잔존 결함이 억제됨 |
| 입력 검증으로 거부되는 비정상 입력 | 음수·0 수량 등 + 잘못된 주문 유형 + 시장가 가격 지정 | 오류 허용성 확보 |

### 3.4 유지보수성 지수 (MI)

`radon`이 내주는 종합 유지보수성 지수(Maintainability Index)는 **51.02 (A등급)**이다. 주문 유형을 늘리면서 코드가 길어져 지정가만 있던 때의 58.98 → 시장가 추가 후 55.56 → IOC/FOK 추가 후 51.02로 조금씩 내렸지만, 여전히 A등급("유지보수가 용이함")을 유지한다.

---

## 4. 메트릭 종합 해석

| 항목 | 측정값 | 일반 권장 기준 |
|---|---|---|
| 사이클로매틱 복잡도(평균) | 2.29 | 10 이하 권장 |
| 최대 복잡도(`_validate_order_input`·`_match`) | 9 | 10 초과 시 분리 권장 |
| 테스트 커버리지 | 100% (50개) | 80% 이상 권장 |
| CBO(최대) | 2 | 낮을수록 좋음 |
| 유지보수성 지수 | 51.02 (A) | A등급 양호 |

지금은 `_validate_order_input`과 `_match` 두 메서드가 복잡도 9로 권장 상한(10)에 바짝 붙은 경계 항목이다. 특히 `_validate_order_input`은 주문 유형이 네 가지로 늘면서 검증 분기가 많아졌다. 지금 당장 쪼개지는 않되, 주문 유형이 더 늘어 둘 중 하나라도 10을 넘으면 헬퍼로 분리하기로 했다(유지보수 문서의 개선 항목과 연결).

---
