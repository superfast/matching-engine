from nose.tools import raises

from .. import market
from .. import order

class User(object):
    def __init__(self,id):
        self.id = id

alice = User("Alice")
bort = User("Bort")
carol = User("Carol")
dora = User("Dora")
erin = User("Erin")
farah = User("Farah")

class Asset(object):
    def __init__(self,name):
        self.name = name

latinum = Asset("LATINUM")
zorkmid = Asset("ZORKMID")

class Payment():
    def exchange_payment(self,*args):
        self.args = args

class Test_Market_Fill():
    def setup(self):
        self.payment = Payment()
        self.m = market.Market(self.payment.exchange_payment, latinum, zorkmid)

        # Simulated filled orders
        invariant_filled1 = order.MarketOrder(user=farah,buy_assetname="LATINUM",buy_amount=7,sell_assetname="ZORKMID")
        invariant_filled2 = order.LimitOrder(user=dora,buy_assetname="ZORKMID",buy_amount=3.5,sell_assetname="LATINUM",limit=1)
        invariant_filled3 = order.MarketOrder(user=erin,buy_assetname="ZORKMID",buy_amount=3.5,sell_assetname="LATINUM")
        self.m.filled_orders.extend([invariant_filled1,invariant_filled2,invariant_filled3])
        self.invariant_filled_orders = [invariant_filled1, invariant_filled2, invariant_filled3]

        # Cancelled orders
        invariant_cancelled1 = order.LimitOrder(user=carol,buy_assetname="LATINUM",buy_amount=7,sell_assetname="ZORKMID",limit=9)
        invariant_cancelled1.num = 1
        invariant_cancelled2 = order.MarketOrder(user=dora,buy_assetname="ZORKMID",buy_amount=70,sell_assetname="LATINUM")
        invariant_cancelled2.num = 2
        invariant_cancelled3 = order.LimitOrder(user=farah,buy_assetname="LATINUM",buy_amount=700,sell_assetname="ZORKMID",limit=11.5)
        invariant_cancelled3.num = 3
        self.m.submit_order(invariant_cancelled1)
        self.m.cancel_order(1,carol)
        self.m.submit_order(invariant_cancelled2)
        self.m.cancel_order(2,dora)
        self.m.submit_order(invariant_cancelled3)
        self.m.cancel_order(3,farah)
        self.invariant_cancelled_orders = [invariant_cancelled1, invariant_cancelled2, invariant_cancelled3]

        # Selling expensive zorkmids, a.k.a. trying to get cheap latinum - no takers
        invariant_limit_left1 = order.LimitOrder(user=alice,buy_assetname="LATINUM",buy_amount=.006,sell_assetname="ZORKMID",limit=.00001)
        invariant_limit_left2 = order.LimitOrder(user=bort,buy_assetname="LATINUM",buy_amount=1,sell_assetname="ZORKMID",limit=.00002)
        invariant_limit_left3 = order.LimitOrder(user=carol,buy_assetname="LATINUM",sell_amount=70000.23,sell_assetname="ZORKMID",limit=1100500)
        self.invariant_limit_left_orders = [invariant_limit_left1, invariant_limit_left2, invariant_limit_left3]

        # Selling expensive latinum, a.k.a. trying to get cheap zorkmids - no takers
        invariant_limit_right1 = order.LimitOrder(user=dora,buy_assetname="ZORKMID",buy_amount=.007,sell_assetname="LATINUM",limit=.00001)
        invariant_limit_right2 = order.LimitOrder(user=erin,buy_assetname="ZORKMID",sell_amount=1,sell_assetname="LATINUM",limit=1200001)
        invariant_limit_right3 = order.LimitOrder(user=farah,buy_assetname="ZORKMID",buy_amount=70,sell_assetname="LATINUM",limit=.00001)
        self.invariant_limit_right_orders = [invariant_limit_right1, invariant_limit_right2, invariant_limit_right3]

        for o in self.invariant_limit_left_orders + self.invariant_limit_right_orders:
            self.m.submit_order(o)

    def assert_invariants(self):
        for o in self.invariant_limit_left_orders:
            assert self.m.left_limitbook.count(o) == 1
        for o in self.invariant_limit_right_orders:
            assert self.m.right_limitbook.count(o) == 1
        for o in self.invariant_filled_orders:
            assert self.m.filled_orders.count(o) == 1
        for o in self.invariant_cancelled_orders:
            assert self.m.cancelled_orders.count(o) == 1

    def test_assert_invariants(self):
        """Invariant offers are correct""" 
        self.assert_invariants()
        self.m.match()
        self.assert_invariants()

    def test_print_market(self):
        """Market can be printed"""
        print self.m

    def test_submit_single_market_buy(self):
        """Submit a market BUY order"""
        self.assert_invariants()
        order1 = order.MarketOrder(user=alice,buy_assetname="LATINUM",buy_amount=7,sell_assetname="ZORKMID")
        order1.num = 100
        self.m.submit_order(order1)
        assert order1 in self.m.left_marketbook
        assert self.m.left_marketbook.count(order1) == 1
        assert order1 not in self.m.right_marketbook
        assert order1 not in self.m.left_limitbook
        assert order1 not in self.m.right_limitbook
        assert order1 not in self.m.filled_orders
        assert order1 not in self.m.cancelled_orders
        self.assert_invariants()

    def test_fill_two_limit_buys(self):
        """Fill two crossing limit buy orders"""
        self.assert_invariants()
        order1 = order.LimitOrder(user=alice,buy_assetname="LATINUM",buy_amount=7,sell_assetname="ZORKMID",limit=10.0)
        order2 = order.LimitOrder(user=bort,buy_assetname="ZORKMID",buy_amount=80,sell_assetname="LATINUM",limit=.10)
        order1.num = 100
        order2.num = 101
        self.m.submit_order(order1)
        self.m.submit_order(order2)
        assert order1 in self.m.left_limitbook
        assert order2 in self.m.right_limitbook
        assert self.m.left_limitbook.count(order1) == 1
        assert self.m.right_limitbook.count(order2) == 1
        assert order1 not in self.m.right_marketbook
        assert order1 not in self.m.left_marketbook
        assert order1 not in self.m.right_limitbook
        assert order1 not in self.m.filled_orders
        assert order1 not in self.m.cancelled_orders
        assert order2 not in self.m.left_marketbook
        assert order2 not in self.m.left_limitbook
        assert order2 not in self.m.right_marketbook
        assert order2 not in self.m.filled_orders
        assert order2 not in self.m.cancelled_orders
        self.m.match()
        assert order1 not in self.m.right_marketbook
        assert order1 not in self.m.left_marketbook
        assert order1 not in self.m.right_limitbook
        assert order1 not in self.m.left_limitbook
        assert order1 not in self.m.cancelled_orders
        assert order2 not in self.m.left_marketbook
        assert order2 not in self.m.left_limitbook
        assert order2 in self.m.right_limitbook
        assert order2 not in self.m.right_marketbook
        assert order2 not in self.m.cancelled_orders
        # Bort should get a partial order filled
        filled = [o for o in self.m.filled_orders if o.user==bort]
        assert len(filled) == 1
        partial = filled[0]
        assert partial.buy_amount == 70
        assert partial.limit == .10
        assert partial.num == 101
        assert order1 in self.m.filled_orders
        assert order1.buy_amount == 7
        assert order2.buy_amount == 10
        self.assert_invariants()
        # Alice sends Bort 70 zorkmid, Bort sends 7 latinum back
        assert self.payment.args == (bort,"LATINUM",7,alice,"ZORKMID",70) or self.payment.args==(alice,"ZORKMID",70,bort,"LATINUM",7)  

    def test_fill_two_limit_sells(self):
        """Fill two crossing limit sell orders"""
        self.assert_invariants()
        order1 = order.LimitOrder(user=alice,buy_assetname="LATINUM",sell_amount=7,sell_assetname="ZORKMID",limit=.1)
        order2 = order.LimitOrder(user=bort,buy_assetname="ZORKMID",sell_amount=80,sell_assetname="LATINUM",limit=10)
        order1.num = 100
        order2.num = 101
        self.m.submit_order(order1)
        self.m.submit_order(order2)
        assert order1 in self.m.left_limitbook
        assert order2 in self.m.right_limitbook
        assert self.m.left_limitbook.count(order1) == 1
        assert self.m.right_limitbook.count(order2) == 1
        assert order1 not in self.m.right_marketbook
        assert order1 not in self.m.left_marketbook
        assert order1 not in self.m.right_limitbook
        assert order1 not in self.m.filled_orders
        assert order1 not in self.m.cancelled_orders
        assert order2 not in self.m.left_marketbook
        assert order2 not in self.m.left_limitbook
        assert order2 not in self.m.right_marketbook
        assert order2 not in self.m.filled_orders
        assert order2 not in self.m.cancelled_orders
        self.m.match()
        assert order1 not in self.m.right_marketbook
        assert order1 not in self.m.left_marketbook
        assert order1 not in self.m.right_limitbook
        assert order1 not in self.m.left_limitbook
        assert order1 not in self.m.cancelled_orders
        assert order2 not in self.m.left_marketbook
        assert order2 not in self.m.left_limitbook
        assert order2 in self.m.right_limitbook
        assert order2 not in self.m.right_marketbook
        assert order2 not in self.m.cancelled_orders
        # Bort should get a partial order filled
        filled = [o for o in self.m.filled_orders if o.user==bort]
        assert len(filled) == 1
        partial = filled[0]
        assert partial.sell_amount == .7
        assert partial.limit == 10
        assert partial.num == 101
        assert order1 in self.m.filled_orders
        assert order1.sell_amount == 7
        assert order2.sell_amount == 79.3 
        self.assert_invariants()
        # Alice sends Bort 70 zorkmid, Bort sends 7 latinum back
        assert self.payment.args == (bort,"LATINUM",.7,alice,"ZORKMID",7) or self.payment.args==(alice,"ZORKMID",7,bort,"LATINUM",.7)  
