#!/usr/bin/python

import datetime
import copy

from order import *

class Orderbook(list):
    def __str__(self):
        s = "{} with {} order(s):\n".format(type(self).__name__, len(self))
        for order in self:
            s = s + str(order) + "\n"
        return s

class LeftLimitOrderbook(Orderbook):
    def add(self,order):
        if order not in self:
            self.append(order)
            self.sort(key=lambda k: k.unitprice)
            order.submitted_time = int(datetime.datetime.now().strftime('%s%f'))
            order.status = "Open Submitted"

class RightLimitOrderbook(Orderbook):
    def add(self,order):
        if order not in self:
            self.append(order)
            self.sort(key=lambda k: k.unitprice, reverse=True)
            order.submitted_time = int(datetime.datetime.now().strftime('%s%f'))
            order.status = "Open Submitted"
    
class MarketOrderbook(Orderbook):
    """This class implements both Right and Left orederbooks for market orders. Market orders are ordered by time of submission"""

    def add(self,order):
        if order not in self:
            self.insert(0,order)
            order.submitted_time = int(datetime.datetime.now().strftime('%s%f'))
            order.status = "Open Submitted"

class Market(object):
    def __init__(self,exchange_payment,asset1,asset2):
        self.asset1 = asset1
        self.asset2 = asset2
        self.exchange_payment = exchange_payment    # Function to exchange assets between users when filling orders

        self.left_limitbook = LeftLimitOrderbook()
        self.right_limitbook = RightLimitOrderbook()
        self.left_marketbook = MarketOrderbook()
        self.right_marketbook = MarketOrderbook()
        self.filled_orders = []
        self.cancelled_orders = []

        self.preset_price = None
        self.last_price = None

    def __str__(self):
        x = "Filled Orders:\n"
        for order in self.filled_orders:
            x +=  str(order) + "\n"
        x += "Cancelled Orders:\n"
        for order in self.cancelled_orders:
            x +=  str(order) + "\n"
        return str(self.left_marketbook) + str(self.right_marketbook) + str(self.left_limitbook) + str(self.right_limitbook) + x

    def get_orders_by_user(self,user):
        result = []
        for orderbook in [self.left_limitbook, self.right_limitbook, self.left_marketbook, self.right_marketbook, self.filled_orders, self.cancelled_orders]:
            result.extend([order for order in orderbook if order.user == user])
        return result

    def get_reference_price(self):
        if self.right_limitbook:
            return self.right_limitbook[-1].limit
        elif self.last_price:
            return self.last_price
        elif self.preset_price:
            return self.preset_price
        else:
            return None

    def submit_market_left(self,order):
        self.left_marketbook.add(order)

    def submit_market_right(self,order):
        self.right_marketbook.add(order)

    def submit_limit_left(self,order):
        self.left_limitbook.add(order)

    def submit_limit_right(self,order):
        self.right_limitbook.add(order)

    def submit_order(self,order):
        if order.buy_assetname == self.asset1.name and order.sell_assetname == self.asset2.name:
            if isinstance(order,LimitOrder):
                if order.ordertype == "BUY":
                    order.unitprice = order.limit
                elif order.ordertype == "SELL":
                    order.unitprice = 1.0 / order.limit
                self.submit_limit_left(order)
            elif isinstance(order,MarketOrder):
                self.submit_market_left(order)
            else:
                raise TypeError("Unsupported Order Type: {}".format(type(order)))
        elif order.buy_assetname == self.asset2.name and order.sell_assetname == self.asset1.name:
            if isinstance(order,LimitOrder):
                if order.ordertype == "SELL":
                    order.unitprice = order.limit
                elif order.ordertype == "BUY":
                    order.unitprice = 1.0 / order.limit
                self.submit_limit_right(order)
            elif isinstance(order,MarketOrder):
                self.submit_market_right(order)
            else:
                raise TypeError("Unsupported Order Type: {}".format(type(order)))
        else:
            order.status = "Misrouted"
            self.cancelled_orders.append(order)
 
    def cancel_order(self,order_num,user):
        for orderbook in [self.left_limitbook, self.right_limitbook, self.left_marketbook, self.right_marketbook]:
            orders_to_cancel = [order for order in orderbook if order.user == user and order.num == order_num]
            if orders_to_cancel:
                for order in orders_to_cancel:
                    orderbook.remove(order)
                    self.cancelled_orders.append(order)
                    order.status = "Cancelled by User"
                return True

    def insufficient_funds(self,left_order,right_order,left_orderbook,right_orderbook,insufficient_funds_list):
        if left_order.user in insufficient_funds_list:
            left_order.status = "Insufficient Funds"
            left_orderbook.remove(left_order)
            self.cancelled_orders.append(left_order)
        elif right_order.user in insufficient_funds_list:
            right_order.status = "Insufficient Funds"
            right_orderbook.remove(right_order)
            self.cancelled_orders.append(right_order)

    def fill(self,left_orderbook,right_orderbook,unitprice):
        left_order = left_orderbook[-1]
        right_order = right_orderbook[-1]
        if not left_order.buy_amount: 
            left_order.buy_amount = left_order.sell_amount / unitprice 
        if not left_order.sell_amount: 
            left_order.sell_amount = left_order.buy_amount * unitprice 
            left_order.sell_amount
        if not right_order.buy_amount: 
            right_order.buy_amount = right_order.sell_amount * unitprice 
        if not right_order.sell_amount: 
            right_order.sell_amount = right_order.buy_amount / unitprice 

        if left_order.buy_amount == right_order.sell_amount:
            insufficient_funds_list = self.exchange_payment(left_order.user,self.asset2.name,unitprice*left_order.buy_amount,right_order.user,self.asset1.name,left_order.buy_amount)
            if insufficient_funds_list: self.insufficient_funds(left_order,right_order,left_orderbook,right_orderbook,insufficient_funds_list); return
            left_orderbook.remove(left_order)
            right_orderbook.remove(right_order)
            left_order.status = "Filled"
            right_order.status = "Filled"
            self.filled_orders.append(left_order)
            self.filled_orders.append(right_order)
            left_order.filled_time = right_order.filled_time = int(datetime.datetime.now().strftime('%s%f'))
            left_order.filled_by = right_order
            right_order.filled_by = left_order
            self.last_price = left_order.filled_price = right_order.filled_price = unitprice
        else:
            if left_order.buy_amount < right_order.sell_amount:
                smaller_order = left_order
                smaller_order_orderbook = left_orderbook
                bigger_order = right_order
                bigger_order_orderbook = right_orderbook
            elif left_order.buy_amount > right_order.sell_amount:
                smaller_order = right_order
                smaller_order_orderbook = right_orderbook
                bigger_order = left_order
                bigger_order_orderbook = left_orderbook

            insufficient_funds_list = self.exchange_payment(bigger_order.user,bigger_order.sell_assetname,smaller_order.buy_amount,smaller_order.user,smaller_order.sell_assetname,smaller_order.sell_amount)
            if insufficient_funds_list: self.insufficient_funds(left_order,right_order,left_orderbook,right_orderbook,insufficient_funds_list); return

            smaller_order_orderbook.remove(smaller_order)
            bigger_order_filled = copy.copy(bigger_order)
            bigger_order_filled.buy_amount = smaller_order.sell_amount
            bigger_order_filled.sell_amount = smaller_order.buy_amount
            if bigger_order.ordertype == "BUY":
                bigger_order.buy_amount -= smaller_order.sell_amount
                bigger_order.sell_amount = None
            elif bigger_order.ordertype == "SELL":
                bigger_order.sell_amount -= smaller_order.buy_amount
                bigger_order.buy_amount = None
            smaller_order.status = "Filled"
            bigger_order_filled.status = "Filled Partial"
            bigger_order.status = "Open Partial"
            self.filled_orders.append(smaller_order)
            self.filled_orders.append(bigger_order_filled)
            bigger_order_filled.filled_time = smaller_order.filled_time = int(datetime.datetime.now().strftime('%s%f'))
            smaller_order.filled_by = bigger_order_filled
            bigger_order_filled.filled_by = smaller_order
            self.last_price = smaller_order.filled_price = bigger_order_filled.filled_price = unitprice

    def match(self):
        ref_price = self.get_reference_price()
        if self.left_marketbook and not ref_price:
            return
        # Market orders on the LEFT side get processed first
        if self.left_marketbook:
            if self.right_marketbook: 
                self.fill(self.left_marketbook,self.right_marketbook,ref_price)
            elif self.right_limitbook:
                self.fill(self.left_marketbook,self.right_limitbook,self.right_limitbook[-1].unitprice)
        elif self.left_limitbook:
            if self.right_marketbook:
                self.fill(self.left_limitbook,self.right_marketbook,self.left_limitbook[-1].unitprice)
            elif self.right_limitbook and (self.left_limitbook[-1].unitprice >= self.right_limitbook[-1].unitprice):
                if self.left_limitbook[-1].submitted_time <= self.right_limitbook[-1].submitted_time:
                    unitprice = self.left_limitbook[-1].unitprice
                else:
                    unitprice = self.right_limitbook[-1].unitprice 
                self.fill(self.left_limitbook,self.right_limitbook,unitprice)


