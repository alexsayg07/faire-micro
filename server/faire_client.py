import traceback

from config import BaseConfig
from typing import List
import requests
import json
from models.order import *
from pymongo import MongoClient
from dateutil import parser
from database import client, database
from odmantic import AIOEngine
from parameters import GetOrdersParams
import httpx

config = BaseConfig()
engine = AIOEngine(client=client, database=config.database)


class FaireClient:
    def __init__(self, brand: str):
        self.brand = brand
        # Update to brand object
        self.shop_url: str = config.faire_url  # brand.shop_url
        self.faire_admin_api_key: str = config.faire_api_key  # brand.shop_url
        self.auth_headers = config.faire_auth_headers
        self.version = "2023-06"

    async def get_all_orders(
        self, params: GetOrdersParams = GetOrdersParams()
    ) -> List[Order]:
        """
        Request all orders from faire client
        Parameters: Defaults are from faire API client
            "limit": 50
            "page": 1
        Returns: List of Order Models
        """
        order_models = []
        async with httpx.AsyncClient as faire_client:
            try:
                if not params.page:
                    response = faire_client.get(
                        f"{self.shop_url}/orders",
                        headers=self.auth_headers,
                        params=params.get_orders_params_dict(),
                    )
                    orders_json = response.json()
                    order_models = self.parse_orders_json(orders_json)
                else:
                    # TODO Handle page input differently?
                    response = requests.get(
                        f"{self.shop_url}/orders",
                        headers=self.auth_headers,
                        params=params.get_orders_params_dict(),
                    )
                    orders_json = response.json()
                    order_models = self.parse_orders_json(orders_json)

            except ConnectionError:
                raise Exception("Could not connect to API Endpoint")
            except Exception as e:
                raise Exception(
                    f"Exception trying to get orders: {e} "
                    f"\ntraceback:{traceback.format_exception(e)}"
                )

            return order_models

    async def get_order(self, brand_order_id: str) -> Order:
        async with httpx.AsyncClient as faire_client:
            try:
                response = faire_client.get(f"{self.shop_url}/orders/{brand_order_id}",
                                            headers=self.auth_headers)
                order_json = response.json()
                order_model = self.parse_order(order_json)

            except ConnectionError:
                raise Exception("Could not connect to API Endpoint")
            except Exception as e:
                raise Exception(
                    f"Exception trying to get orders: {e} "
                    f"\ntraceback:{traceback.format_exception(e)}"
                )

    def parse_order(self, order: {}) -> Order:
        """
        Go through an order dictionary and convert to an order model
        parameter: a single order dictionary to parse
        returns: a single Order model
        """
        # Extract relevant information from the order data
        order_id = order["id"]
        customer = Customer(
            first_name=order["customer"]["first_name"],
            last_name=order["customer"]["last_name"],
        )
        display_id = order["display_id"]
        created_at = parser.parse(order["created_at"])
        updated_at = parser.parse(order["updated_at"])
        state = order["state"]
        address = self.parse_address(order["address"])
        ship_after = parser.parse(order["ship_after"])
        payout_costs = self.parse_payout_costs(order["payout_costs"])
        payment_initiated_at = parser.parse(order.get("payment_initiated_at"))
        retailer_id = order["retailer_id"]
        source = order["source"]
        expected_ship_date = parser.parse(order.get("expected_ship_date"))
        processing_at = parser.parse(order["processing_at"])
        items_dict = order["items"]
        shipments_dict = order["shipments"]
        brand_discounts_dict = order["brand_discounts"]
        original_order_id = order.get("original_order_id")

        # Fields to reconfigure before making order model
        # Create an instance of your customer model and store the data
        item_id_list = []
        shipment_id_list = []

        brand_discounts_list = []  # TODO Get discount models and add to list
        item_list = []
        shipment_list = []

        # Parse through items
        if items_dict:
            item_list = self.parse_order_items(items_dict)
            for item in item_list:
                item_id_list.append(item.order_item_id)

        if shipments_dict:
            shipment_list = self.parse_order_shipments(shipments_dict)
            for shipment in shipment_list:
                shipment_id_list.append(shipment.shipment_id)

        if brand_discounts_dict:
            brand_discounts_list = self.parse_promotions(brand_discounts_dict)
        if payout_costs:
            new_payout_costs = self.parse_payout_costs(payout_costs)

        new_order = Order(
            provider_order_id=order_id,
            display_id=display_id,
            created_at=created_at,
            updated_at=updated_at,
            state=state,
            address=address,
            ship_after=ship_after,
            payout_costs=new_payout_costs,
            payment_initiated_at=payment_initiated_at,
            original_order_id=original_order_id,
            retailer_id=retailer_id,
            expected_ship_date=expected_ship_date,
            processing_at=processing_at,
            customer=customer,
            item_ids=item_id_list,
            shipment_ids=shipment_id_list,
            brand_discounts=brand_discounts_list,
            source=source,
        )
        order_in_db = await engine.save(new_order, insert=False)
        return new_order

    async def parse_orders_json(self, orders_json: json) -> List[Order]:
        # Parse the response JSON
        # Process the order data as needed
        for order in orders_json["orders"]:
            self.parse_order(order)

    def parse_promotions(self, brand_discounts: [{}]) -> Optional[List[Discounts]]:
        """
        Parsing through a brand discount list in dictionary format to convert to
        list of Discount Models
        parameter: List of Dictionary
        return: List of Discounts Models
        """
        brand_discount_list = []
        if brand_discounts:
            for discount in brand_discounts:
                new_discount = Discounts(
                    discount_id=discount["id"],
                    code=discount["code"],
                    discount_type=discount.get("discount_type"),
                    includes_free_shipping=discount.get("includes_free_shipping"),
                    discount_amount=Cost(
                        amount_minor=discount["discount_amount"]["amount_minor"],
                        currency=discount["discount_amount"]["amount_minor"],
                    ),
                    discount_percentage=discount.get("discount_percentage"),
                )
                brand_discount_list.append(new_discount)
            return brand_discount_list
        else:
            return None

    def parse_order_items(self, items: [{}]) -> List[OrderItem]:
        """
        Parsing list of dictionaries to return list of OrderItem Models
        parameter: list of dictionaries
        return: List of OrderItem Models
        """
        item_list = []
        # Iterate through items and add to item collection
        # get list of item id and add to order list
        if len(items) > 0:
            for item in items:
                new_item = OrderItem(
                    order_item_id=item["id"],
                    order_id=item["order_id"],
                    state=item["state"],
                    product_id=item["product_id"],
                    variant_id=item["variant_id"],
                    quantity=item["quantity"],
                    sku=item["id"],  # TODO Update key from id to sku, or merge values?
                    price=item["price"],  # TODO Make price cost model
                    product_name=item["product_name"],
                    variant_name=item["variant_name"],
                    includes_tester=item["includes_tester"],
                    tester_price=item.get("tester_price"),
                    created_at=item["created_at"],
                    updated_at=item["updated_at"],
                    discounts=item["discounts"],
                )
            item_list.append(new_item)
        return item_list

    def parse_order_shipments(self, shipments: [{}]) -> List[Shipment]:
        """
        Parsing a list of dictionaries to return a list of Shipment models
        parameter: List of dictionary
        return: List of Shipment Models
        """
        shipment_list = []
        for shipment in shipments:
            new_shipment = Shipment(
                shipment_id=shipment["id"],
                order_id=shipment["order_id"],
                maker_cost_cents=shipment["maker_cost_cents"],
                carrier=shipment.get("carrier"),
                tracking_code=shipment.get("tracking_code"),
                created_at=shipment["created_at"],
                updated_at=shipment["updated_at"],
            )
            shipment_list.append(new_shipment)
        return shipment_list

    def parse_address(self, address: {}) -> Optional[Address]:
        """
        parsing dictionary into a model to store in database
        parameter: an address dictionary
        return: Address Model
        """
        if not address:
            return None
        else:
            new_address = Address(
                address_id=address["id"],
                address_name=address["name"],
                address1=address["address1"],
                address2=address.get("address2"),
                postal_code=address["postal_code"],
                city=address["city"],
                address_state=address.get("state"),
                state_code=address.get("state_code"),
                phone_number=address["phone_number"],
                country=address["country"],
                country_code=address.get("country_code"),
                company_name=address.get("company_name"),
            )
            return new_address

    def parse_payout_costs(self, payout_costs: {}) -> Optional[PayoutCosts]:
        """
        parsing dictionary and making a PayoutCost model to store in database
        parameter: Payout_cost raw dictionary object to parse
        returns: PayoutCosts model
        """
        if payout_costs:
            taxes = []
            if payout_costs.get("taxes"):
                for tax in payout_costs.get("taxes"):
                    new_tax = Taxes(
                        value=Cost(
                            amount_minor=tax["value"]["amount_minor"],
                            currency=tax["value"]["currency"],
                        ),
                        taxable_item_type=tax["taxable_item_type"],
                        tax_type=tax["tax_type"],
                        effect=tax["effect"],
                    )
                    taxes.append(new_tax)

            payout = PayoutCosts(
                payout_fee_bps=payout_costs.get("payout_fee_bps"),
                commission_bps=payout_costs.get("commission_bps"),
                payout_fee=payout_costs.get("payout_fee"),
                commission=payout_costs.get("commission"),
                total_payout=payout_costs.get("total_payout"),
                payout_protection_fee=payout_costs.get("payout_protection_fee"),
                damaged_and_missing_items=payout_costs.get("damaged_and_missing_items"),
                net_tax=payout_costs.get("net_tax"),
                shipping_subsidy=payout_costs.get("shipping_subsidy"),
                taxes=taxes,
            )
            return payout
        else:
            return None

async def main():
    yate_client = FaireClient('yate')