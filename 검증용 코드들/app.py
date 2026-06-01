"""Mini-OrderBook 데모 UI (Streamlit).

docs/DESIGN.md 의 §화면 설계 / UI 설계 원리를 구현한다.
설계 → 구현 추적성을 위해 적용한 UI 원리를 주석으로 명시한다.

실행:
    streamlit run app.py
"""

import pandas as pd
import streamlit as st

from orderbook import SIDE_BUY, SIDE_SELL, OrderBook

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

# --- 주문 처리 + 즉각 피드백 (UI 원리: 가시성, 즉각적 피드백) ---------------
if submitted:
    try:
        order = book.submit_order(side, float(price), int(quantity))
        if order.is_filled():
            st.success(
                f"주문 #{order.order_id} ({side}) 전량 체결 완료 "
                f"— {quantity}계약 @ {price:,}"
            )
        elif order.remaining < order.quantity:
            filled = order.quantity - order.remaining
            st.warning(
                f"주문 #{order.order_id} ({side}) 부분 체결 "
                f"— 체결 {filled} / 잔량 {order.remaining} 호가창 등록"
            )
        else:
            st.info(
                f"주문 #{order.order_id} ({side}) 미체결 "
                f"— {quantity}계약 @ {price:,} 호가창 등록"
            )
    except ValueError as exc:
        # UI 원리: 오류 메시지는 입력부 근처에서 명확하게
        st.error(f"입력 오류: {exc}")


# --- 호가창 렌더링 (거래소 관행: 매도 위 / 매수 아래) -----------------------
def render_orderbook(book: OrderBook) -> None:
    snapshot = book.get_book()
    asks = snapshot["asks"]
    bids = snapshot["bids"]

    # 가격대별 잔량 집계
    def aggregate(orders):
        agg: dict[float, int] = {}
        for o in orders:
            agg[o.price] = agg.get(o.price, 0) + o.remaining
        return agg

    ask_levels = sorted(aggregate(asks).items(), reverse=True)  # 위에서 높은가
    bid_levels = sorted(aggregate(bids).items(), reverse=True)  # 높은가 먼저

    rows = []
    for p, q in ask_levels:
        rows.append(
            f"<tr><td style='color:{COLOR_SELL};text-align:right;padding:2px 12px'>"
            f"{q}</td>"
            f"<td style='color:{COLOR_SELL};font-weight:600;text-align:center;"
            f"padding:2px 12px'>{p:,.0f}</td>"
            f"<td style='padding:2px 12px'></td></tr>"
        )
    rows.append(
        "<tr><td colspan='3' style='border-top:1px solid #888;"
        "text-align:center;color:#888;font-size:12px;padding:4px'>"
        "── 스프레드 ──</td></tr>"
    )
    for p, q in bid_levels:
        rows.append(
            f"<tr><td style='padding:2px 12px'></td>"
            f"<td style='color:{COLOR_BUY};font-weight:600;text-align:center;"
            f"padding:2px 12px'>{p:,.0f}</td>"
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
    if not ask_levels and not bid_levels:
        st.info("호가창이 비어 있습니다. 왼쪽에서 주문을 제출하거나 '샘플 주입'을 눌러보세요.")
    else:
        st.markdown(table, unsafe_allow_html=True)


# --- 메인 레이아웃 ----------------------------------------------------------
left, right = st.columns([1, 1])

with left:
    st.subheader("호가창 (Order Book)")
    render_orderbook(book)

    st.subheader("미체결 주문")
    snapshot = book.get_book()
    open_orders = snapshot["bids"] + snapshot["asks"]
    if open_orders:
        for o in sorted(open_orders, key=lambda x: x.order_id):
            label = "매수" if o.side == SIDE_BUY else "매도"
            color = COLOR_BUY if o.side == SIDE_BUY else COLOR_SELL
            c1, c2 = st.columns([3, 1])
            c1.markdown(
                f"<span style='color:{color};font-weight:600'>#{o.order_id} "
                f"{label}</span> {o.price:,.0f} × {o.remaining}",
                unsafe_allow_html=True,
            )
            if c2.button("취소", key=f"cancel_{o.order_id}"):
                book.cancel_order(o.order_id)
                st.rerun()
    else:
        st.caption("미체결 주문이 없습니다.")

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
                    "체결가": f"{t.price:,.0f}",
                    "수량": t.quantity,
                    "시각": t.timestamp.strftime("%H:%M:%S"),
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
