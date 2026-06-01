"""Mini-OrderBook 데모 UI (Streamlit).

docs/Design.md 의 화면 설계 / UI 설계 원리를 구현한다.
설계 → 구현 추적성을 위해 적용한 UI 원리를 주석으로 명시한다.

실행:
    streamlit run app.py
"""

import pandas as pd
import streamlit as st

from orderbook import (
    SIDE_BUY,
    SIDE_SELL,
    STATUS_FILLED,
    STATUS_PARTIALLY_FILLED,
    OrderBook,
)

# --- 색상 상수: 매수/매도 색상 일관성 (UI 원리: 일관성) ----------------------
# 도메인(국내 코인 거래소) 관행을 따른다: 매수=빨강, 매도=파랑.
# 단, 색에만 의존하지 않도록 텍스트 라벨("매수"/"매도")을 항상 병기한다.
COLOR_BUY = "#e74c3c"
COLOR_SELL = "#2e86de"

st.set_page_config(page_title="Mini-OrderBook", page_icon="📈", layout="wide")


# --- 상태 초기화: 세션 동안 단일 OrderBook 인스턴스 유지 --------------------
def get_book() -> OrderBook:
    if "book" not in st.session_state:
        st.session_state.book = OrderBook()
    return st.session_state.book


def seed_sample_orders() -> None:
    """데모용 샘플 호가를 주입한다 (학습성: 첫 화면에서 바로 체험)."""
    book = OrderBook()
    book.submit_order(SIDE_SELL, 10300, 3)
    book.submit_order(SIDE_SELL, 10200, 2)
    book.submit_order(SIDE_SELL, 10100, 4)
    book.submit_order(SIDE_BUY, 9900, 5)
    book.submit_order(SIDE_BUY, 9800, 3)
    book.submit_order(SIDE_BUY, 9700, 2)
    st.session_state.book = book


book = get_book()

# --- 헤더 -------------------------------------------------------------------
st.title("📈 Mini-OrderBook")
st.caption(
    "단일 종목 지정가 주문을 **가격-시간 우선**으로 매칭하는 학습용 매칭 엔진 "
    "(코인 자동매매에서 백엔드가 다루지 않는 호가창/체결 영역)"
)

# --- 사이드바: 주문 입력 폼 (UI 원리: 사용자 제어, 입력 최소화) -------------
with st.sidebar:
    st.header("주문 입력")
    side_label = st.radio("구분", ["매수 (BUY)", "매도 (SELL)"], horizontal=True)
    side = SIDE_BUY if side_label.startswith("매수") else SIDE_SELL

    # 엔진이 정수 가격/수량을 받으므로 정수 위젯으로 입력받는다.
    price = st.number_input("가격", min_value=1, value=10000, step=100)
    quantity = st.number_input("수량", min_value=1, value=1, step=1)

    submitted = st.button("주문 제출", type="primary", use_container_width=True)

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("샘플 주입", use_container_width=True):
            seed_sample_orders()
            st.rerun()
    with col_b:
        if st.button("초기화", use_container_width=True):
            st.session_state.book = OrderBook()
            st.rerun()

    # --- 주문 취소 (FR-07): 제출 시 안내된 주문 번호로 취소 -----------------
    st.divider()
    st.subheader("주문 취소")
    cancel_id = st.number_input("취소할 주문 번호", min_value=1, value=1, step=1)
    if st.button("취소", use_container_width=True):
        if book.cancel_order(int(cancel_id)):
            st.success(f"주문 #{int(cancel_id)} 취소됨")
        else:
            st.error(f"주문 #{int(cancel_id)} 없음 (이미 체결/취소되었거나 미존재)")
        st.rerun()

# --- 주문 처리 + 즉각 피드백 (UI 원리: 가시성, 즉각적 피드백) ---------------
if submitted:
    try:
        order = book.submit_order(side, int(price), int(quantity))
        if order.status == STATUS_FILLED:
            st.success(
                f"주문 #{order.order_id} ({side}) 전량 체결 완료 "
                f"— {int(quantity)}계약 @ {int(price):,}"
            )
        elif order.status == STATUS_PARTIALLY_FILLED:
            filled = order.quantity - order.remaining
            st.warning(
                f"주문 #{order.order_id} ({side}) 부분 체결 "
                f"— 체결 {filled} / 잔량 {order.remaining} 호가창 등록"
            )
        else:
            st.info(
                f"주문 #{order.order_id} ({side}) 미체결 "
                f"— {int(quantity)}계약 @ {int(price):,} 호가창 등록"
            )
    except ValueError as exc:
        # UI 원리: 오류 메시지는 입력부 근처에서 명확하게
        st.error(f"입력 오류: {exc}")


# --- 호가창 렌더링 (거래소 관행: 매도 위 / 매수 아래) -----------------------
def render_orderbook(book: OrderBook) -> None:
    snapshot = book.get_book()
    asks = snapshot["asks"]  # [(가격, 잔량)] 가격 오름차순
    bids = snapshot["bids"]  # [(가격, 잔량)] 가격 내림차순

    if not asks and not bids:
        st.info("호가창이 비어 있습니다. 왼쪽에서 주문을 제출하거나 '샘플 주입'을 눌러보세요.")
        return

    rows = []
    for p, q in reversed(asks):  # 높은 매도가 위로
        rows.append(
            f"<tr><td style='color:{COLOR_SELL};text-align:right;padding:2px 12px'>"
            f"{q}</td>"
            f"<td style='color:{COLOR_SELL};font-weight:600;text-align:center;"
            f"padding:2px 12px'>{p:,}</td>"
            f"<td style='padding:2px 12px'></td></tr>"
        )
    rows.append(
        "<tr><td colspan='3' style='border-top:1px solid #888;"
        "text-align:center;color:#888;font-size:12px;padding:4px'>"
        "── 스프레드 ──</td></tr>"
    )
    for p, q in bids:  # 높은 매수가 위로 (이미 내림차순)
        rows.append(
            f"<tr><td style='padding:2px 12px'></td>"
            f"<td style='color:{COLOR_BUY};font-weight:600;text-align:center;"
            f"padding:2px 12px'>{p:,}</td>"
            f"<td style='color:{COLOR_BUY};text-align:left;padding:2px 12px'>"
            f"{q}</td></tr>"
        )

    header = (
        f"<tr><th style='color:{COLOR_SELL};padding:4px 12px'>매도잔량</th>"
        f"<th style='padding:4px 12px'>호가</th>"
        f"<th style='color:{COLOR_BUY};padding:4px 12px'>매수잔량</th></tr>"
    )
    table = (
        "<table style='width:100%;border-collapse:collapse;font-size:15px'>"
        f"{header}{''.join(rows)}</table>"
    )
    st.markdown(table, unsafe_allow_html=True)


# --- 메인 레이아웃 ----------------------------------------------------------
left, right = st.columns([1, 1])

with left:
    st.subheader("호가창 (Order Book)")
    render_orderbook(book)
    st.caption("미체결 주문은 위 호가창에 가격대별로 집계되어 표시됩니다. "
               "취소는 왼쪽 '주문 취소'에서 주문 번호로 할 수 있습니다.")

with right:
    st.subheader("체결 내역 (Trades)")
    trades = book.get_trades()
    if trades:
        df = pd.DataFrame(
            [
                {
                    "체결#": t.trade_id,
                    "매수주문": t.buy_order_id,
                    "매도주문": t.sell_order_id,
                    "체결가": f"{t.price:,}",
                    "수량": t.quantity,
                }
                for t in trades
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True)
        total_qty = sum(t.quantity for t in trades)
        st.metric("총 체결 건수 / 수량", f"{len(trades)}건 / {total_qty}계약")
    else:
        st.caption("아직 체결된 거래가 없습니다.")

st.divider()
st.caption(
    "엔진: orderbook.py · 가격-시간 우선 매칭 · 메모리 기반 · "
    "체결가는 호가창에 먼저 있던(수동) 주문 가격을 따름"
)
