

import pytest

from orderbook import (
    OrderBook, Order, Trade, MatchingStrategy,
    SIDE_BUY, SIDE_SELL,
    ORDER_LIMIT, ORDER_MARKET, ORDER_IOC, ORDER_FOK,
    STATUS_ACCEPTED, STATUS_PARTIALLY_FILLED, STATUS_FILLED, STATUS_CANCELLED,
)


@pytest.fixture
def book():
    return OrderBook()


class TestInputValidation:

    def test_invalid_side(self, book):
        with pytest.raises(ValueError):
            book.submit_order("LONG", 100, 1)

    def test_price_zero_boundary(self, book):
        with pytest.raises(ValueError):
            book.submit_order(SIDE_BUY, 0, 1)

    def test_price_negative(self, book):
        with pytest.raises(ValueError):
            book.submit_order(SIDE_BUY, -10, 1)

    def test_price_not_int(self, book):
        with pytest.raises(ValueError):
            book.submit_order(SIDE_BUY, 100.5, 1)

    def test_quantity_zero_boundary(self, book):
        with pytest.raises(ValueError):
            book.submit_order(SIDE_SELL, 100, 0)

    def test_quantity_negative(self, book):
        with pytest.raises(ValueError):
            book.submit_order(SIDE_SELL, 100, -5)

    def test_quantity_not_int(self, book):
        with pytest.raises(ValueError):
            book.submit_order(SIDE_SELL, 100, 1.5)

    def test_minimum_valid_order(self, book):
        order = book.submit_order(SIDE_BUY, 1, 1) 
        assert order.status == STATUS_ACCEPTED



class TestMatching:

    def test_no_match_when_price_gap(self, book):
        book.submit_order(SIDE_SELL, 10300, 5)
        order = book.submit_order(SIDE_BUY, 10200, 5)  
        assert order.remaining == 5
        assert order.status == STATUS_ACCEPTED

    def test_full_fill_exact_quantity(self, book):
        book.submit_order(SIDE_SELL, 10200, 5)
        order = book.submit_order(SIDE_BUY, 10200, 5)
        assert order.status == STATUS_FILLED
        assert order.remaining == 0
        assert len(book.get_trades()) == 1

    def test_execution_price_follows_resting_order(self, book):
      
        book.submit_order(SIDE_SELL, 10200, 5)
        book.submit_order(SIDE_BUY, 10500, 5)
        trade = book.get_trades()[0]
        assert trade.price == 10200  

    def test_partial_fill_incoming_larger(self, book):
        book.submit_order(SIDE_SELL, 10200, 5)
        order = book.submit_order(SIDE_BUY, 10200, 8)  
        assert order.status == STATUS_PARTIALLY_FILLED
        assert order.remaining == 3
        assert book.get_book()["bids"] == [(10200, 3)]

    def test_partial_fill_resting_larger(self, book):
        book.submit_order(SIDE_SELL, 10200, 8)
        book.submit_order(SIDE_BUY, 10200, 5) 
        assert book.get_book()["asks"] == [(10200, 3)]

    def test_sell_order_matches_bids(self, book):
        book.submit_order(SIDE_BUY, 10200, 5)
        order = book.submit_order(SIDE_SELL, 10200, 5)  
        assert order.status == STATUS_FILLED

    def test_sell_no_match_when_too_expensive(self, book):
        book.submit_order(SIDE_BUY, 10100, 5)
        order = book.submit_order(SIDE_SELL, 10200, 5)  
        assert order.status == STATUS_ACCEPTED



class TestPriority:

    def test_price_priority_buy_takes_cheapest_ask(self, book):
        book.submit_order(SIDE_SELL, 10300, 5)
        book.submit_order(SIDE_SELL, 10200, 5)  
        book.submit_order(SIDE_BUY, 10300, 5)
        trade = book.get_trades()[0]
        assert trade.price == 10200  

    def test_time_priority_same_price(self, book):
        first = book.submit_order(SIDE_SELL, 10200, 5)  
        book.submit_order(SIDE_SELL, 10200, 5)           
        book.submit_order(SIDE_BUY, 10200, 5)
        trade = book.get_trades()[0]
        assert trade.sell_order_id == first.order_id    

    def test_sell_takes_highest_bid_first(self, book):
        book.submit_order(SIDE_BUY, 10200, 5)
        book.submit_order(SIDE_BUY, 10300, 5)  
        book.submit_order(SIDE_SELL, 10200, 5)
        trade = book.get_trades()[0]
        assert trade.price == 10300  



class TestStateTransition:

    def test_accepted_to_filled(self, book):
        book.submit_order(SIDE_SELL, 10200, 5)
        order = book.submit_order(SIDE_BUY, 10200, 5)
        assert order.status == STATUS_FILLED

    def test_accepted_to_partial(self, book):
        book.submit_order(SIDE_SELL, 10200, 3)
        order = book.submit_order(SIDE_BUY, 10200, 5)
        assert order.status == STATUS_PARTIALLY_FILLED

    def test_accepted_to_cancelled(self, book):
        order = book.submit_order(SIDE_BUY, 10200, 5)
        assert book.cancel_order(order.order_id) is True
        assert order.status == STATUS_CANCELLED

    def test_cancel_nonexistent_returns_false(self, book):
        assert book.cancel_order(999) is False

    def test_cancel_removes_from_book(self, book):
        order = book.submit_order(SIDE_BUY, 10200, 5)
        book.cancel_order(order.order_id)
        assert book.get_book()["bids"] == []

    def test_partial_to_filled(self, book):
        
        resting = book.submit_order(SIDE_SELL, 10200, 10)
        book.submit_order(SIDE_BUY, 10200, 4)            
        assert resting.status == STATUS_PARTIALLY_FILLED
        book.submit_order(SIDE_BUY, 10200, 6)            
        assert resting.status == STATUS_FILLED

    def test_partial_to_cancelled(self, book):
        resting = book.submit_order(SIDE_SELL, 10200, 10)
        book.submit_order(SIDE_BUY, 10200, 4)            
        assert resting.status == STATUS_PARTIALLY_FILLED
        assert book.cancel_order(resting.order_id) is True
        assert resting.status == STATUS_CANCELLED


class TestOrderBookView:

    def test_empty_book(self, book):
        assert book.get_book() == {"bids": [], "asks": []}

    def test_aggregate_same_price(self, book):
        book.submit_order(SIDE_BUY, 10200, 5)
        book.submit_order(SIDE_BUY, 10200, 3)  
        assert book.get_book()["bids"] == [(10200, 8)]

    def test_bids_sorted_high_to_low(self, book):
        book.submit_order(SIDE_BUY, 10100, 1)
        book.submit_order(SIDE_BUY, 10300, 1)
        book.submit_order(SIDE_BUY, 10200, 1)
        prices = [p for p, _ in book.get_book()["bids"]]
        assert prices == [10300, 10200, 10100]

    def test_asks_sorted_low_to_high(self, book):
        book.submit_order(SIDE_SELL, 10300, 1)
        book.submit_order(SIDE_SELL, 10100, 1)
        book.submit_order(SIDE_SELL, 10200, 1)
        prices = [p for p, _ in book.get_book()["asks"]]
        assert prices == [10100, 10200, 10300]

class TestIntegration:

    def test_multi_level_sweep(self, book):
        book.submit_order(SIDE_SELL, 10200, 5)
        book.submit_order(SIDE_SELL, 10300, 5)
        order = book.submit_order(SIDE_BUY, 10300, 10)
        assert order.status == STATUS_FILLED
        trades = book.get_trades()
        assert len(trades) == 2
        assert trades[0].price == 10200  
        assert trades[1].price == 10300

    def test_partial_sweep_then_rest(self, book):
        book.submit_order(SIDE_SELL, 10200, 5)
        book.submit_order(SIDE_SELL, 10300, 5)
        order = book.submit_order(SIDE_BUY, 10300, 12) 
        assert order.remaining == 2
        assert book.get_book()["bids"] == [(10300, 2)]

    def test_repr_methods(self):
        o = Order(1, SIDE_BUY, 100, 5, 1)
        t = Trade(1, 1, 2, 100, 5)
        assert "Order" in repr(o)
        assert "Trade" in repr(t)

class TestMarketOrder:

    def test_explicit_limit_order_type(self, book):
        book.submit_order(SIDE_SELL, 10200, 5)
        order = book.submit_order(SIDE_BUY, 10200, 5, ORDER_LIMIT)
        assert order.status == STATUS_FILLED

    def test_market_buy_full_fill(self, book):
        book.submit_order(SIDE_SELL, 10200, 5)
        order = book.submit_order(SIDE_BUY, None, 5, ORDER_MARKET)
        assert order.status == STATUS_FILLED
        assert order.remaining == 0
        assert book.get_trades()[0].price == 10200     

    def test_market_buy_ignores_price_takes_best(self, book):
        book.submit_order(SIDE_SELL, 10500, 5)
        book.submit_order(SIDE_SELL, 10200, 5)
        order = book.submit_order(SIDE_BUY, None, 10, ORDER_MARKET)
        assert order.status == STATUS_FILLED
        trades = book.get_trades()
        assert trades[0].price == 10200                 
        assert trades[1].price == 10500

    def test_market_buy_partial_then_cancel(self, book):
        book.submit_order(SIDE_SELL, 10200, 5)
        order = book.submit_order(SIDE_BUY, None, 8, ORDER_MARKET)  
        assert order.remaining == 3
        assert order.status == STATUS_CANCELLED        
        assert book.get_book()["bids"] == []            
        assert len(book.get_trades()) == 1

    def test_market_buy_empty_book_cancelled(self, book):
        order = book.submit_order(SIDE_BUY, None, 5, ORDER_MARKET)  
        assert order.status == STATUS_CANCELLED
        assert order.remaining == 5
        assert book.get_trades() == []

    def test_market_sell_full_fill(self, book):
        book.submit_order(SIDE_BUY, 10200, 5)
        order = book.submit_order(SIDE_SELL, None, 5, ORDER_MARKET)
        assert order.status == STATUS_FILLED

    def test_market_with_price_rejected(self, book):
        with pytest.raises(ValueError):
            book.submit_order(SIDE_BUY, 10200, 5, ORDER_MARKET)    

    def test_invalid_order_type(self, book):
        with pytest.raises(ValueError):
            book.submit_order(SIDE_BUY, 10200, 5, "STOP")


class TestMatchingStrategy:

    def test_base_strategy_requires_implementation(self):
        strategy = MatchingStrategy()
        with pytest.raises(NotImplementedError):
            strategy.is_matchable(None, None)
        with pytest.raises(NotImplementedError):
            strategy.rests_remainder()
        with pytest.raises(NotImplementedError):
            strategy.requires_full_fill()



class TestIOCFOK:

    
    def test_ioc_full_fill(self, book):
        book.submit_order(SIDE_SELL, 10200, 5)
        order = book.submit_order(SIDE_BUY, 10200, 5, ORDER_IOC)
        assert order.status == STATUS_FILLED
        assert len(book.get_trades()) == 1

    def test_ioc_partial_then_cancel(self, book):
        book.submit_order(SIDE_SELL, 10200, 5)
        order = book.submit_order(SIDE_BUY, 10200, 8, ORDER_IOC)  
        assert order.remaining == 3
        assert order.status == STATUS_CANCELLED       
        assert book.get_book()["bids"] == []           
        assert len(book.get_trades()) == 1

    def test_ioc_no_cross_cancelled(self, book):
        book.submit_order(SIDE_SELL, 10300, 5)
        order = book.submit_order(SIDE_BUY, 10200, 5, ORDER_IOC)  
        assert order.status == STATUS_CANCELLED        
        assert book.get_trades() == []
        assert book.get_book()["bids"] == []

    
    def test_fok_full_fill(self, book):
        book.submit_order(SIDE_SELL, 10200, 5)
        order = book.submit_order(SIDE_BUY, 10200, 5, ORDER_FOK)
        assert order.status == STATUS_FILLED
        assert len(book.get_trades()) == 1

    def test_fok_insufficient_cancelled(self, book):
        book.submit_order(SIDE_SELL, 10200, 3)
        order = book.submit_order(SIDE_BUY, 10200, 5, ORDER_FOK)  
        assert order.status == STATUS_CANCELLED
        assert book.get_trades() == []                 
        assert book.get_book()["asks"] == [(10200, 3)]  

    def test_fok_exact_boundary_multi_level(self, book):
        book.submit_order(SIDE_SELL, 10200, 3)
        book.submit_order(SIDE_SELL, 10250, 2)
        order = book.submit_order(SIDE_BUY, 10300, 5, ORDER_FOK)
        assert order.status == STATUS_FILLED
        assert len(book.get_trades()) == 2

    def test_fok_no_cross_cancelled(self, book):
        book.submit_order(SIDE_SELL, 10300, 5)
        order = book.submit_order(SIDE_BUY, 10200, 5, ORDER_FOK)  
        assert order.status == STATUS_CANCELLED
        assert book.get_trades() == []

    def test_fok_empty_book_cancelled(self, book):
        order = book.submit_order(SIDE_BUY, 10200, 5, ORDER_FOK) 
        assert order.status == STATUS_CANCELLED
        assert book.get_trades() == []

    def test_fok_sell_full_fill(self, book):
        book.submit_order(SIDE_BUY, 10200, 5)
        order = book.submit_order(SIDE_SELL, 10200, 5, ORDER_FOK)
        assert order.status == STATUS_FILLED
        assert len(book.get_trades()) == 1
