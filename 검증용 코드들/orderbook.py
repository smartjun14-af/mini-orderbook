"""Mini-OrderBook 매칭 엔진.

단일 종목에 대한 지정가(limit)·시장가(market) 주문을 가격-시간 우선
(Price-Time Priority) 원칙으로 매칭하는 메모리 기반 엔진이다.

관련 문서:
    - docs/SRS.md                  : 요구사항 명세 (FR-01 ~ FR-10)
    - docs/Design.md               : UI/상세 설계
    - docs/architecture.md         : 계층형 아키텍처, 설계 원리
    - docs/market_order_design.md  : 시장가 주문 요구·설계(전략 패턴)
    - docs/CODING.md               : 코딩 표준(PEP 8), 리팩토링 내역

설계 결정 요약:
    - 체결가는 호가창에 "먼저 있던" 수동 주문(passive order)의 가격을 따른다.
    - 지정가 주문의 미체결 잔량은 자기 가격으로 호가창에 등록된다.
    - 시장가 주문은 가격 조건 없이 즉시 체결하고, 미체결 잔량은 취소한다.
    - 지정가/시장가의 차이(체결 조건·잔량 처리)는 전략 패턴으로 분리한다.
    - Trade 는 주문을 객체가 아니라 주문 ID로만 참조한다(약결합).
"""

# 주문 방향 상수
SIDE_BUY = "BUY"
SIDE_SELL = "SELL"

# 주문 유형 상수
ORDER_LIMIT = "LIMIT"
ORDER_MARKET = "MARKET"

# 주문 상태 상수
STATUS_ACCEPTED = "ACCEPTED"            # 접수(미체결)
STATUS_PARTIALLY_FILLED = "PARTIAL"     # 부분 체결
STATUS_FILLED = "FILLED"                # 완전 체결
STATUS_CANCELLED = "CANCELLED"          # 취소됨


class Order:
    """하나의 주문을 표현하는 데이터 객체.

    Attributes:
        order_id (int): 주문 고유 번호.
        side (str): SIDE_BUY 또는 SIDE_SELL.
        price (int | None): 지정가. 시장가 주문은 None.
        quantity (int): 최초 주문 수량.
        remaining (int): 미체결 잔량.
        seq (int): 접수 순번(시간 우선순위 비교용).
        status (str): 현재 주문 상태.
    """

    def __init__(self, order_id, side, price, quantity, seq):
        self.order_id = order_id
        self.side = side
        self.price = price
        self.quantity = quantity
        self.remaining = quantity
        self.seq = seq
        self.status = STATUS_ACCEPTED

    def __repr__(self):
        return (
            f"Order(id={self.order_id}, side={self.side}, "
            f"price={self.price}, remaining={self.remaining}, "
            f"status={self.status})"
        )


class Trade:
    """한 번의 체결 기록.

    주문을 객체가 아니라 ID로만 참조해 OrderBook 과의 결합도를 낮춘다.
    """

    def __init__(self, trade_id, buy_order_id, sell_order_id, price, quantity):
        self.trade_id = trade_id
        self.buy_order_id = buy_order_id
        self.sell_order_id = sell_order_id
        self.price = price
        self.quantity = quantity

    def __repr__(self):
        return (
            f"Trade(id={self.trade_id}, buy={self.buy_order_id}, "
            f"sell={self.sell_order_id}, price={self.price}, qty={self.quantity})"
        )


# --------------------------------------------------------------------------- #
# 매칭 전략 (전략 패턴) — 지정가/시장가의 차이만 캡슐화
# --------------------------------------------------------------------------- #
class MatchingStrategy:
    """주문 유형별 매칭 전략 인터페이스.

    지정가와 시장가는 (1) 체결 조건과 (2) 잔량 처리만 다르다. 이 두 가지를
    전략으로 캡슐화해, OrderBook 의 핵심 흐름을 바꾸지 않고 주문 유형을
    추가할 수 있게 한다(전략 패턴, 개방-폐쇄 원칙).
    """

    def is_matchable(self, incoming, resting):
        """들어온 주문이 대기 주문과 체결될 수 있는지 판단한다."""
        raise NotImplementedError

    def rests_remainder(self):
        """미체결 잔량을 호가창에 남기는지 여부."""
        raise NotImplementedError


class LimitStrategy(MatchingStrategy):
    """지정가 전략: 가격이 교차할 때만 체결하고, 잔량은 호가창에 남긴다."""

    def is_matchable(self, incoming, resting):
        if incoming.side == SIDE_BUY:
            return incoming.price >= resting.price
        return incoming.price <= resting.price

    def rests_remainder(self):
        return True


class MarketStrategy(MatchingStrategy):
    """시장가 전략: 가격 조건 없이 즉시 체결하고, 잔량은 취소한다."""

    def is_matchable(self, incoming, resting):  # pylint: disable=unused-argument
        return True  # 반대편 호가가 있으면 가격을 무시하고 체결

    def rests_remainder(self):
        return False


# 전략은 상태가 없으므로 단일 인스턴스를 재사용한다.
_STRATEGIES = {
    ORDER_LIMIT: LimitStrategy(),
    ORDER_MARKET: MarketStrategy(),
}


class OrderBook:
    """단일 종목 호가창 + 매칭 엔진.

    매수 호가(bids)는 가격 높은 순, 매도 호가(asks)는 가격 낮은 순으로
    정렬해 보관한다. 같은 가격이면 먼저 접수된 주문(seq 작은 순)이 우선한다.
    """

    def __init__(self):
        self._bids = []          # 매수 대기 주문
        self._asks = []          # 매도 대기 주문
        self._trades = []        # 체결 내역
        self._next_order_id = 1
        self._next_trade_id = 1
        self._next_seq = 1

    # ------------------------------------------------------------------ #
    # 공개 인터페이스
    # ------------------------------------------------------------------ #
    def submit_order(self, side, price, quantity, order_type=ORDER_LIMIT):
        """주문을 접수하고 즉시 매칭한 뒤, 유형에 따라 잔량을 처리한다.

        지정가(order_type=ORDER_LIMIT)는 잔량을 호가창에 등록하고,
        시장가(order_type=ORDER_MARKET)는 잔량을 취소한다. 시장가 주문은
        price 를 지정하지 않는다(None).

        Returns:
            Order: 접수된 주문 객체(체결 후 상태가 갱신되어 있음).
        """
        self._validate_order_input(side, price, quantity, order_type)
        strategy = _STRATEGIES[order_type]

        order = Order(self._next_order_id, side, price, quantity, self._next_seq)
        self._next_order_id += 1
        self._next_seq += 1

        self._match(order, strategy)

        if order.remaining > 0:
            if strategy.rests_remainder():
                self._insert_into_book(order)
            else:
                # 시장가 잔량은 호가창에 남기지 않고 취소한다(FR-10).
                order.status = STATUS_CANCELLED
        return order

    def cancel_order(self, order_id):
        """미체결 주문을 호가창에서 제거하고 상태를 CANCELLED 로 바꾼다.

        Returns:
            bool: 취소에 성공하면 True, 해당 미체결 주문이 없으면 False.
        """
        for book in (self._bids, self._asks):
            target = next((o for o in book if o.order_id == order_id), None)
            if target is not None:
                book.remove(target)        # 대상을 먼저 찾은 뒤 제거(순회 중 수정 회피)
                target.status = STATUS_CANCELLED
                return True
        return False

    def get_book(self):
        """호가창 스냅샷을 가격대별 집계로 반환한다.

        Returns:
            dict: {"bids": [(price, qty), ...], "asks": [(price, qty), ...]}
                  bids 는 가격 높은 순, asks 는 가격 낮은 순.
        """
        return {
            "bids": self._aggregate(self._bids, reverse=True),
            "asks": self._aggregate(self._asks, reverse=False),
        }

    def get_trades(self):
        """지금까지의 체결 내역 리스트를 반환한다."""
        return list(self._trades)

    # ------------------------------------------------------------------ #
    # 내부 헬퍼 (단일 책임으로 분리)
    # ------------------------------------------------------------------ #
    def _validate_order_input(self, side, price, quantity, order_type):
        """주문 입력값을 검증한다. 잘못된 값이면 ValueError 를 던진다."""
        if side not in (SIDE_BUY, SIDE_SELL):
            raise ValueError(f"잘못된 주문 방향: {side}")
        if order_type not in (ORDER_LIMIT, ORDER_MARKET):
            raise ValueError(f"잘못된 주문 유형: {order_type}")
        if order_type == ORDER_LIMIT:
            if not isinstance(price, int) or price <= 0:
                raise ValueError(f"지정가 주문의 가격은 양의 정수여야 함: {price}")
        elif price is not None:
            raise ValueError("시장가 주문은 가격을 지정하지 않는다(None)")
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError(f"수량은 양의 정수여야 함: {quantity}")

    def _match(self, order, strategy):
        """들어온 주문을 반대편 호가와 가격-시간 우선으로 체결한다.

        체결 가능 여부 판단은 전략(strategy)에 위임한다.
        """
        book = self._asks if order.side == SIDE_BUY else self._bids
        # 반대편을 우선순위 순으로 정렬: 매수면 싼 매도부터, 매도면 비싼 매수부터
        book.sort(key=lambda o: (o.price, o.seq))
        if order.side == SIDE_SELL:
            book.sort(key=lambda o: (-o.price, o.seq))

        i = 0
        while i < len(book) and order.remaining > 0:
            resting = book[i]
            if not strategy.is_matchable(order, resting):
                break
            traded_qty = min(order.remaining, resting.remaining)
            self._record_trade(order, resting, resting.price, traded_qty)
            order.remaining -= traded_qty
            resting.remaining -= traded_qty
            if resting.remaining == 0:
                resting.status = STATUS_FILLED
                book.pop(i)
            else:
                resting.status = STATUS_PARTIALLY_FILLED
                i += 1

        if order.remaining == 0:
            order.status = STATUS_FILLED
        elif order.remaining < order.quantity:
            order.status = STATUS_PARTIALLY_FILLED

    def _record_trade(self, incoming, resting, price, quantity):
        """체결을 Trade 로 기록한다. 체결가는 대기 주문 가격을 따른다."""
        if incoming.side == SIDE_BUY:
            buy_id, sell_id = incoming.order_id, resting.order_id
        else:
            buy_id, sell_id = resting.order_id, incoming.order_id
        trade = Trade(self._next_trade_id, buy_id, sell_id, price, quantity)
        self._next_trade_id += 1
        self._trades.append(trade)

    def _insert_into_book(self, order):
        """미체결 잔량 주문을 해당 방향 호가창에 등록한다."""
        if order.side == SIDE_BUY:
            self._bids.append(order)
        else:
            self._asks.append(order)

    @staticmethod
    def _aggregate(book, reverse):
        """같은 가격의 잔량을 합쳐 (가격, 수량) 목록으로 만든다."""
        totals = {}
        for order in book:
            totals[order.price] = totals.get(order.price, 0) + order.remaining
        return sorted(totals.items(), key=lambda x: x[0], reverse=reverse)
