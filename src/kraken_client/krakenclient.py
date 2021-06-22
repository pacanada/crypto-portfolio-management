import pandas as pd
from src.kraken_client.krakenapi_func import krakenapi_func
import json
import time
import pickle
class KrakenClient():
    def __init__(self, api_private_key=None, api_public_key=None):
        self.api_private_key=api_private_key
        self.api_public_key=api_public_key
        
    def get_last_info_and_preproces(self, pair_name: str, interval: int):
        
        assert interval in [1, 5, 15, 30, 60, 240, 1440, 10080, 21600], "interval is not supported"
        data = self.get_historical_data_from_crypto(pair_name=pair_name, interval=interval)
        df = self.from_dict_to_df(data=data)
        df = self.fix_columns_type(df)
        df = self.set_datetime_as_index(df)
        return df
    
    def get_historical_data_from_crypto(self, pair_name: str, interval: int):
        output=krakenapi_func(
            ["","OHLC", f"pair={pair_name.lower()}", f"interval={interval}"],
            api_private_key=None,
            api_public_key=None
            
        )
        output_dict = eval(output)
        return output_dict
    
    def from_dict_to_df(self, data: dict):
        result_name = list(data["result"].keys())[0]
        df_raw = pd.DataFrame.from_dict(data=data["result"][result_name])
        df = pd.DataFrame()
        df[["time", "open", "high", "low", "close", "vwap", "volume", "count"]] = df_raw.copy()
        return df
    def fix_columns_type(self, df: pd.DataFrame):
        df = df.astype(float).copy()
        df[["time", "count"]] = df[["time", "count"]].astype(int).copy()
        return df
    def set_datetime_as_index(self, df: pd.DataFrame):
        df["date"] = pd.to_datetime(df['time'], unit='s')
        df = df.set_index(pd.DatetimeIndex(df["date"])).copy()
        return df

    def execute_limit_order(self, order_type, volume, pair, limit_price):
        assert order_type in ["sell", "buy"], "Unknown order_type"
        output=krakenapi_func(
            sysargs=[
                        "",
                        "AddOrder",
                        f"pair={pair.lower()}",
                        f"type={order_type.lower()}",
                        "ordertype=limit",
                        f"volume={volume}",
                        f"price={limit_price}"
            ],
            api_private_key=self.api_private_key,
            api_public_key=self.api_public_key
            )

        return output

    def get_balance(self):
        output=krakenapi_func(
            sysargs=[
                        "",
                        "Balance",
            ],
            api_private_key=self.api_private_key,
            api_public_key=self.api_public_key
            )

        return output

        
        
    def execute_order(self, order_type, volume, pair_name):
        assert order_type in ["Sell", "Buy"], "Unknown order_type"
        output=krakenapi_func(
            sysargs=[
                        "",
                        "AddOrder",
                        f"pair={pair_name.lower()}",
                        f"type={order_type.lower()}",
                        "ordertype=market",
                        f"volume={volume}"
            ],
            api_private_key=self.api_private_key,
            api_public_key=self.api_public_key
            )
        
        print(output)
        id_order = self.get_id_order(output)
        finalized_order = self.wait_until_fulfilled(id_order, order_type, pair_name)
        assert finalized_order["Id"] == id_order
        return finalized_order

    def execute_order_leverage(self, trade_type, volume, pair_name, order_type, leverage, price=None ):
        assert trade_type in ["Sell", "Buy"], "Unknown order_type"
        sysargs = [
                        "",
                        "AddOrder",
                        f"pair={pair_name.lower()}",
                        f"type={trade_type.lower()}",
                        f"ordertype={order_type}",
                        f"volume={volume}",
                        f"leverage={leverage}"
            ]
        if price is not None:
            # for market type limit or stoploss or takeprofit
            sysargs = sysargs + [f"price={price}"]
        
        output=krakenapi_func(
            sysargs=sysargs,
            api_private_key=self.api_private_key,
            api_public_key=self.api_public_key
            )
        
        print(output)
        id_order = self.get_id_order(output)
        if order_type not in ["take-profit", "stop-loss"]:
            finalized_order = self.wait_until_fulfilled(id_order, order_type, pair_name)
        else:
            print("We dont have to wait until fulfilled")
            finalized_order = {"Id": id_order,
                                "Price": price}
        assert finalized_order["Id"] == id_order
        return finalized_order

    def cancel_order(self, txid):
        output=krakenapi_func(
            sysargs=[
                        "",
                        "CancelOrder",
                        f"txid={txid}",
            ],
            api_private_key=self.api_private_key,
            api_public_key=self.api_public_key
            )
        return output

    def get_closed_order(self,):
        output=krakenapi_func(
            sysargs=[
                        "",
                        "ClosedOrders",
            ],
            api_private_key=self.api_private_key,
            api_public_key=self.api_public_key
            )
        output = eval(output.replace("null", "None"))
        # list of closed, not cancelled
        output_list = [idclosed for idclosed,v in output["result"]["closed"].items() if v["status"]=="closed"]

        return output_list

    def get_trades_history(self,):
        output=krakenapi_func(
            sysargs=[
                        "",
                        "TradesHistory",
            ],
            api_private_key=self.api_private_key,
            api_public_key=self.api_public_key
            )
        output = eval(output.replace("null", "None"))
        output_list = list(output["result"]["trades"].keys())
        return output_list

    
    def execute_mock_order(self, order_type, volume, pair_name):
        """mock order to simulate and not have to make a trade"""
        assert order_type in ["Sell", "Buy"], "Unknown order_type"
        finalized_order = {'Id': 'OPJZJL-V76CB-ZWOYJK', 'Price': 0.331511, 'Action': 'Sell'}
        return finalized_order
        
    def get_id_order(self, output):
        id_order = eval(output)["result"]["txid"][0]
        return id_order
    def wait_until_fulfilled(self, id_order, order_type, pair_name ):
        while True:
            # Get last closed order
            output_closedorders = krakenapi_func(
                sysargs=[" ","ClosedOrders"],
                api_private_key=self.api_private_key,
                api_public_key=self.api_public_key)
            output_closeorders_json=json.loads(output_closedorders)
            finalized_id = list(output_closeorders_json["result"]["closed"].keys())[0]
            finalized_price = eval(output_closeorders_json["result"]["closed"][finalized_id]["price"])

            print("checking id",id_order,finalized_id)
            # Wait until id of last trade is recognized
            time.sleep(3)
            if id_order==finalized_id:
                finalized_order = {
                    "Id": id_order,
                    "Price": finalized_price,
                    "Action": order_type,
                    "Pair_Name": pair_name
                    }   
                #send_slack_message(text=str(finalized_order), channel=CHANNEL_NAME)
                #save_order(finalized_order, dir_data=dir_finalized_order, name_file=finalized_orders_file)
                break
        return finalized_order
