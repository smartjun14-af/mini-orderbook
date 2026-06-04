
SIDE_BUY = "BUY"
SIDE_SELL = "SELL"


ORDER_LIMIT = "LIMIT"
ORDER_MARKET = "MARKET"
ORDER_IOC = "IOC"      
ORDER_FOK = "FOK"      


STATUS_ACCEPTED = "ACCEPTED"            
STATUS_PARTIALLY_FILLED = "PARTIAL"     
STATUS_FILLED = "FILLED"                
STATUS_CANCELLED = "CANCELLED"          


class Order:

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



class MatchingStrategy:

    def is_matchable(self, incoming, resting):
        raise NotImplementedError

    def rests_remainder(self):
        raise NotImplementedError

    def requires_full_fill(self):   
        raise NotImplementedError


class LimitStrategy(MatchingStrategy):

    def is_matchable(self, incoming, resting):
        if incoming.side == SIDE_BUY:
            return incoming.price >= resting.price
        return incoming.price <= resting.price

    def rests_remainder(self):
        return True

    def requires_full_fill(self):
        return False


class MarketStrategy(MatchingStrategy):
   

    def is_matchable(self, incoming, resting): 
        return True 

    def rests_remainder(self):
        return False

    def requires_full_fill(self):
        return False


class IOCStrategy(LimitStrategy):

    def rests_remainder(self):
        return False


class FOKStrategy(LimitStrategy):
    

    def requires_full_fill(self):
        return True


_STRATEGIES = {
    ORDER_LIMIT: LimitStrategy(),
    ORDER_MARKET: MarketStrategy(),
    ORDER_IOC: IOCStrategy(),
    ORDER_FOK: FOKStrategy(),
}


class OrderBook:

    def __init__(self):
        self._bids = []          
        self._asks = []          
        self._trades = []       
        self._next_order_id = 1
        self._next_trade_id = 1
        self._next_seq = 1

    
    def submit_order(self, side, price, quantity, order_type=ORDER_LIMIT):
        
        self._validate_order_input(side, price, quantity, order_type)
        strategy = _STRATEGIES[order_type]

        order = Order(self._next_order_id, side, price, quantity, self._next_seq)
        self._next_order_id += 1
        self._next_seq += 1

        if (strategy.requires_full_fill()
                and self._fillable_quantity(order, strategy) < order.quantity):
            order.status = STATUS_CANCELLED
            return order

        self._match(order, strategy)

        if order.remaining > 0:
            if strategy.rests_remainder():
                self._insert_into_book(order)
            else:

                order.status = STATUS_CANCELLED
        return order

    def cancel_order(self, order_id):
        
        for book in (self._bids, self._asks):
            target = next((o for o in book if o.order_id == order_id), None)
            if target is not None:
                book.remove(target)        
                target.status = STATUS_CANCELLED
                return True
        return False

    def get_book(self):
        return {
            "bids": self._aggregate(self._bids, reverse=True),
            "asks": self._aggregate(self._asks, reverse=False),
        }

    def get_trades(self):
        return list(self._trades)

   
    def _validate_order_input(self, side, price, quantity, order_type):
        if side not in (SIDE_BUY, SIDE_SELL):
            raise ValueError(f"잘못된 주문 방향: {side}")
        if order_type not in (ORDER_LIMIT, ORDER_MARKET, ORDER_IOC, ORDER_FOK):
            raise ValueError(f"잘못된 주문 유형: {order_type}")
        if order_type == ORDER_MARKET:
            if price is not None:
                raise ValueError("시장가 주문은 가격을 지정하지 않는다(None)")
        elif not isinstance(price, int) or price <= 0:
            # 지정가·IOC·FOK 는 가격이 필요하다
            raise ValueError(f"가격은 양의 정수여야 함: {price}")
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError(f"수량은 양의 정수여야 함: {quantity}")

    def _fillable_quantity(self, order, strategy):
        book = self._asks if order.side == SIDE_BUY else self._bids
        book.sort(key=lambda o: (o.price, o.seq))
        if order.side == SIDE_SELL:
            book.sort(key=lambda o: (-o.price, o.seq))
        total = 0
        for resting in book:
            if not strategy.is_matchable(order, resting):
                break
            total += resting.remaining
            if total >= order.quantity:
                break
        return total

    def _match(self, order, strategy):
        book = self._asks if order.side == SIDE_BUY else self._bids
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
        if incoming.side == SIDE_BUY:
            buy_id, sell_id = incoming.order_id, resting.order_id
        else:
            buy_id, sell_id = resting.order_id, incoming.order_id
        trade = Trade(self._next_trade_id, buy_id, sell_id, price, quantity)
        self._next_trade_id += 1
        self._trades.append(trade)

    def _insert_into_book(self, order):
        if order.side == SIDE_BUY:
            self._bids.append(order)
        else:
            self._asks.append(order)

    @staticmethod
    def _aggregate(book, reverse):
        totals = {}
        for order in book:
            totals[order.price] = totals.get(order.price, 0) + order.remaining
        return sorted(totals.items(), key=lambda x: x[0], reverse=reverse)
