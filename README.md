## 작성자

- 이름: 김동준
- 학번: B982007
- 과목: 소프트웨어공학(4분반)

## Mini-OrderBook

> 미니 호가창 및 매칭 엔진 시뮬레이터  
> 소프트웨어공학 과제: 프로세스에 입각한 바이브코딩의 효과 분석

## 프로젝트 개요

본 프로젝트는 단일 종목에 대한 미니 호가창과 매칭 엔진을 직접 구현하면서,
바이브코딩(AI 기반 코딩)에 정통 소프트웨어 공학 프로세스를 어떻게 적용할 때
어떤 효과와 한계가 있는지를 분석하는 것을 목표로 한다.

## 동기

졸업 프로젝트로 진행 중인 암호화폐 자동매매 시스템에서 거래소 API를 클라이언트 관점으로 다뤄보며,
"이 가격 데이터는 거래소 내부에서 어떻게 만들어지는가?"에 대한 호기심이 생겼다.
호가창의 가격-시간 우선 원칙과 매칭 엔진의 작동 방식을 직접 구현해보며
시장 미시구조(market microstructure)를 이해하고자 한다.

## 기술 스택

**Language**: Python 3.11+
**Backend/API**: FastAPI
**Frontend/UI**: Streamlit
**Testing**: pytest, pytest-cov
**Static Analysis**: pylint, mypy
**AI Tools**: Claude Code (주), Cursor (보조)

## 핵심 기능 (Scope)

## 기능 및 구현
- 지정가(Limit) 주문 접수/취소
- 가격-시간 우선(Price-Time Priority) 매칭
- 부분 체결(Partial Fill) 처리
- 호가창 실시간 표시
- 체결 내역 조회

## 일정

2주 압축 일정. 자세한 진행 상황은 [Project Board](../../projects)와 
[Discussions](../../discussions)에서 확인.

| 주차 | 단계 |
|---|---|
| Week 1 | 요구사항 분석, 설계, 매칭 엔진 코어 구현, 단위 테스트 |
| Week 2 | UI 구현, 통합 테스트, 품질 측정, 보고서 작성 |

## 디렉토리 구조
mini-orderbook/
├── docs/              # SRS, 설계 문서, 와이어프레임, 회고록
├── core/              # 매칭 엔진 코어 모듈
├── api/               # FastAPI 백엔드
├── ui/                # Streamlit 프론트엔드
├── tests/             # 단위/통합/상태 기반 테스트
└── reports/           # 품질 메트릭, lessons learned

## 개발 원칙

- **바이브코딩 + 프로세스 결합**: AI 생성 코드는 100% 사람이 라인 단위 리뷰 후 merge하기
- **한 PR = 한 기능**: 작은 단위 커밋
- **테스트 우선**: 핵심 로직은 반드시 테스트 후 merge
- **회고 의무**: 매주 1회 Discussion에 회고록 작성




