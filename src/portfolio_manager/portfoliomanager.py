import pickle
from copy import deepcopy
from collections import OrderedDict
import random
import time
class ConfigManager():
    def __init__(self, crypto_list, initial_orders, volume_dict):
        self.crypto_list = crypto_list
        self.initial_orders = initial_orders
        self.volume_dict = volume_dict

class Order():
    def __init__(self, pair:str, volume: float, limit_price: float, order_type: str, status:str):
        self.pair = pair
        self.volume = volume
        self.limit_price = limit_price
        self.order_type = order_type
        self.status = status
        self.id = None
        self.output = None
    def __repr__(self,):
        return f"{self.pair}, {self.volume}, {self.limit_price}, {self.order_type}, {self.status}, {self.id}"

    def update_id(self, id):
        self.id = id
        return self

    def update_status(self, status: str):
        self.status = status
        return self

    def update_output(self, output: str):
        self.output = output
        return self

    @staticmethod
    def get_id_order(output):
        id_order = eval(output)["result"]["txid"][0]
        return id_order




class PortfolioManager:
    """
    Base class for an active portfolio manager. 
    We want the following functionalities:
    - Place and execute orders base on a algorithm selector (other class)
    - Being able to keep track of placed and executed orders
    - Being able to do that for different crypto coins
    To avoid extra fees we want to use only limit orders
    """
    def __init__(self, config: ConfigManager, fresh_start: bool, kraken_client):
        self.config = config
        self.finalized_orders = {}
        self.placed_orders = {}
        self.cryptos = self.config.crypto_list
        self.incoming_orders = {} 
        self.kraken_client = kraken_client
        self.fresh_start = fresh_start
    
    def initialize_first_orders(self,):
        self.incoming_orders = self.config.initial_orders


    def place_limit_orders(self,):
        """Place orders from incoming_orders"""
        # make copy to avoid issue when changing size
        incoming_orders_dict = self.incoming_orders.copy()
        for key, order in incoming_orders_dict.items():
            output = self.kraken_client.execute_limit_order(
                pair=order.pair,
                order_type=order.order_type,
                volume=order.volume,
                limit_price=order.limit_price
                )
            # delete from incoming_orders 
            del self.incoming_orders[key]
            # update order
            order_id = order.get_id_order(output)
            order = order.update_id(id=order_id)
            order = order.update_status(status="placed")
            order = order.update_output(output=output)
            # pass to placed orders
            self.placed_orders[order_id] = order
            print(output, order.id)

    def check_closed_orders_and_update(self,):
        closed_orders=self.kraken_client.get_closed_order()
        # make copy
        placed_order_dict = self.placed_orders.copy()
        for key_id, order in placed_order_dict.items():
            if key_id in closed_orders:
                # delete from placed_orders 
                del self.placed_orders[key_id]
                order = order.update_status(status="finalized")
                self.finalized_orders[key_id] = order
                print(key_id, order, "has been finalized")
            else:
                print(key_id, order, "has not been finalized yet")

    def select_next_incoming_orders(self,):
        """Decide which orders are going to incoming orders. 
        Based on completed orders, available balance and so on"""
        # We only allow one buy followed by one sell
        # we have to check in placed orders and finalized
        list_attr = self.get_list_attr_from_dict_orders(self.placed_orders, "pair")
        for crypto in self.cryptos:
            if crypto in list_attr:
                print(f"Already placed orders for {crypto}")
                continue
            else:
                order_type = self.select_order_type(pair=crypto)
                # add order for this crypto
                self.add_incoming_order(pair=crypto, order_type=order_type) 

    def select_order_type(self, pair):
        """Check if there is finalized order (choose opposite order type), if not, buy """
        #### what about if there are many for the same pair TODO
        next_order_type = None
        for key_id, order in OrderedDict(self.finalized_orders).items():
            print("here",key_id)
            if (order.pair == pair) and (order.order_type=="buy"):
                next_order_type = "sell"
            elif (order.pair == pair) and (order.order_type=="sell"):  
                next_order_type = "buy"  
        return next_order_type

    def add_incoming_order(self, pair, order_type):
        limit = self.get_limit_price(pair, order_type)
        self.incoming_orders.update(
            {
                f"id{random.randint(0,100)}": Order(
                    pair=pair,
                    order_type=order_type,
                    volume=self.config.volume_dict[pair]["volume"],
                    limit_price = limit,
                    status="incoming")
            }
            )


    def get_limit_price(self, pair, order_type):
        # mean +- std in 30 interval
        df = self.kraken_client.get_last_info_and_preproces(pair, 30)
        if order_type=="buy":
            limit_price = df.tail(1).low.mean() - df.open.std()
        else:
            limit_price = df.tail(1).high.mean() + df.open.std()

        return round(limit_price, self.config.volume_dict[pair]["precission"])

            
    @staticmethod
    def get_list_attr_from_dict_orders(orders_dict, attr):
        list_attr = []
        for key, order in orders_dict.items():
            list_attr.append(getattr(order, attr))
        return list_attr

    def run_loop(self,):
        """Run the manager for the selected crypto in the config file"""
        # available balance?

        if self.fresh_start:
            self.initialize_first_orders()
            self.fresh_start = False
        else:
            #check if any order has been finalized
            self = self.deserialize("", "test")
            self.check_closed_orders_and_update()
            # logic of when and if place an order
            self.select_next_incoming_orders()

        self.place_limit_orders()
        self.serialize("", "test")
        #print(self.kraken_client.get_balance())

    def run(self,):
        self.run_count = 0
        while True:

            self.run_loop()
            time.sleep(10)
            self.run_count += 1
            print("info")
            print("incoming orders")
            print(self.incoming_orders)
            print("placed orders")
            print(self.placed_orders)
            print("finalized orders")
            print(self.finalized_orders)
            



    def serialize(self, path, name):
        with open(path+f"{name}.pickle", "wb") as f:
            # avoid api key to be serialized
            agent=deepcopy(self)
            agent.kraken_client = None
            pickle.dump(agent, f)

    def deserialize(self, path, name):
        with open(path+f"{name}.pickle", "rb") as f:
            agent = pickle.load(f)
            agent.kraken_client = self.kraken_client
        return agent










