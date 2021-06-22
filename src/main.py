from portfolio_manager.portfoliomanager import PortfolioManager, ConfigManager, Order
from kraken_client.krakenclient import KrakenClient
from slack_client.slackclient import SlackClient
import copy
import os
from pathlib import Path
from os.path import join, dirname
from dotenv import load_dotenv


dotenv_path = join(Path(__file__).parent.parent, '.env')
load_dotenv(dotenv_path)

API_PRIVATE_KEY = os.environ.get("API_PRIVATE_KEY")
API_PUBLIC_KEY = os.environ.get("API_PUBLIC_KEY")


slack_client = SlackClient()


kraken_client=KrakenClient(api_private_key=API_PRIVATE_KEY, api_public_key=API_PUBLIC_KEY)

crypto_list = ["xlmeur", "adaeur"]
volume_dict = {
    "xlmeur": {"volume": 30, "precission": 6},
    "adaeur": {"volume": 5, "precission": 6}
    }

precission_dict = {}
initial_orders = {
    "id0": Order(pair="xlmeur", order_type="sell", volume=volume_dict["xlmeur"]["volume"], limit_price = 0.2015, status="incoming"),
    "id1": Order(pair="adaeur", order_type="buy", volume=volume_dict["adaeur"]["volume"], limit_price = 1.012, status="incoming"),
}



cm = ConfigManager(crypto_list=crypto_list, initial_orders=initial_orders, volume_dict=volume_dict )


pm = PortfolioManager(config=cm, fresh_start=True, kraken_client=kraken_client)

pm.run()
