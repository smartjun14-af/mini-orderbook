
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


SIDE_BUY = "BUY"
SIDE_SELL = "SELL"
VALID_SIDES = (SIDE_BUY, SIDE_SELL)


@dataclass
class Order:
    """단일 지정가 주문.
    Attributes:
        order_id: 시스템 내 유일 식별자.
        side: 'BUY' 또는 'SELL'.
        price: 주문 가격 (>0).
        quantity: 최초 주문 수량 (>0).
        remaining: 미체결 잔량.
        timestamp: 접수 시각 (시간 우선 매칭 기준).
    """
    order_id: int
    side: str
    price: float
    quantity: int
    remaining: int
    timestamp: datetime

    def is_filled(self) -> bool:
        """완전 체결 여부."""
        return self.remaining == 0


@dataclass
class Trade:
    """체결 1건. 매수/매도 주문 한 쌍 사이의 거래 성립을 표현."""
    trade_id: int
    buy_order_id: int
    sell_order_id: int
    price: float
    quantity: int
    timestamp: datetime


class OrderBook:
    """호가창 + 매칭 엔진.

    가격-시간 우선(Price-Time Priority) 원칙으로 매칭한다.
    - bids: 매수 호가, 가격 내림차순 + 시간 오름차순
    - asks: 매도 호가, 가격 오름차순 + 시간 오름차순
    - trades: 체결 내역, 시간 오름차순
    """

    def __init__(self) -> None:
        self._bids: list[Order] = []
        self._asks: list[Order] = []
        self._trades: list[Trade] = []
        self._next_order_id: int = 1
        self._next_trade_id: int = 1

    # ----- Public API -----

    def submit_order(self, side: str, price: float, quantity: int) -> Order:
        """주문을 접수하고 즉시 매칭을 시도한다.

        Args:
            side: 'BUY' 또는 'SELL'.
            price: 양수 가격.
            quantity: 양수 수량.

        Returns:
            생성된 Order 객체 (잔량은 매칭 후 값).

        Raises:
            ValueError: side가 잘못되었거나 price/quantity가 양수가 아닐 때.
        """
        self._validate_order_input(side, price, quantity)

        order = Order(
            order_id=self._next_order_id,
            side=side,
            price=price,
            quantity=quantity,
            remaining=quantity,
            timestamp=datetime.now(),
        )
        self._next_order_id += 1

        self._match(order)

        if order.remaining > 0:
            self._insert_into_book(order)
        return order

    def cancel_order(self, order_id: int) -> bool:
        """미체결 주문을 취소한다.

        Returns:
            True: 호가창에서 찾아 제거 성공.
            False: 해당 ID 주문이 호가창에 없음(이미 체결됐거나 존재하지 않음).
        """
        for book in (self._bids, self._asks):
            for i, order in enumerate(book):
                if order.order_id == order_id:
                    del book[i]
                    return True
        return False

    def get_book(self) -> dict[str, list[Order]]:
        """현재 호가창의 스냅샷을 반환한다 (얕은 복사)."""
        return {"bids": list(self._bids), "asks": list(self._asks)}

    def get_trades(self) -> list[Trade]:
        """전체 체결 내역을 시간순으로 반환한다 (얕은 복사)."""
        return list(self._trades)

    # ----- Private helpers  -----

    @staticmethod
    def _validate_order_input(side: str, price: float, quantity: int) -> None:
        """주문 입력 유효성 검증."""
        if side not in VALID_SIDES:
            raise ValueError(f"side must be one of {VALID_SIDES}, got {side!r}")
        if price <= 0:
            raise ValueError(f"price must be positive, got {price}")
        if quantity <= 0:
            raise ValueError(f"quantity must be positive, got {quantity}")

    def _match(self, incoming: Order) -> None:
        """들어온 주문을 반대편 호가창과 매칭한다.

        매칭 가능 조건: 매수가 >= 매도가.
        체결 가격은 호가창에 먼저 들어와 있던 주문의 가격(시간 우선).
        잔량이 남으면 호출자가 _insert_into_book으로 등록한다.
        """
        opposite_book = self._asks if incoming.side == SIDE_BUY else self._bids

        while incoming.remaining > 0 and opposite_book:
            best = opposite_book[0]
            if not self._is_matchable(incoming, best):
                break

            trade_qty = min(incoming.remaining, best.remaining)
            self._record_trade(incoming, best, best.price, trade_qty)

            incoming.remaining -= trade_qty
            best.remaining -= trade_qty
            if best.is_filled():
                opposite_book.pop(0)

    @staticmethod
    def _is_matchable(incoming: Order, resting: Order) -> bool:
        """incoming 주문이 resting(호가창 대기) 주문과 체결 가능한가?"""
        if incoming.side == SIDE_BUY:
            return incoming.price >= resting.price
        return incoming.price <= resting.price

    def _record_trade(
        self,
        incoming: Order,
        resting: Order,
        price: float,
        quantity: int,
    ) -> None:
        """체결을 기록한다."""
        if incoming.side == SIDE_BUY:
            buy_id, sell_id = incoming.order_id, resting.order_id
        else:
            buy_id, sell_id = resting.order_id, incoming.order_id

        trade = Trade(
            trade_id=self._next_trade_id,
            buy_order_id=buy_id,
            sell_order_id=sell_id,
            price=price,
            quantity=quantity,
            timestamp=datetime.now(),
        )
        self._next_trade_id += 1
        self._trades.append(trade)

    def _insert_into_book(self, order: Order) -> None:
        """잔량이 남은 주문을 호가창에 정렬 위치에 삽입한다.

        - bids: 가격 내림차순, 동가 시 시간 오름차순
        - asks: 가격 오름차순, 동가 시 시간 오름차순
        """
        if order.side == SIDE_BUY:
            book = self._bids
            # 가격이 더 낮은 첫 위치 앞에 삽입 (내림차순 유지)
            i = 0
            while i < len(book) and book[i].price >= order.price:
                i += 1
        else:
            book = self._asks
            # 가격이 더 높은 첫 위치 앞에 삽입 (오름차순 유지)
            i = 0
            while i < len(book) and book[i].price <= order.price:
                i += 1


                
        book.insert(i, order)
