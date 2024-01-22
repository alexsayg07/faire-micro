import requests
import json

from odmantic import AIOEngine

from faire.server.config import BaseConfig
from faire.server.models.order import *
from pymongo import MongoClient
from dateutil import parser
import httpx
import asyncio

config = BaseConfig()
client = MongoClient(config.mongo_details)
db = client[config.database]
collection = db["orders"]
engine = AIOEngine(client=client, database='faire-data')


# Request FaireAPI for Orders
def get_orders(file_function: str):
    """
    (temp) parameter: file_function determines whether to create 'x' or overwrite 'w' in file directory
    return: returns a JSON Order_Data, or empty list if fail to request from API
    Request order data from faire API and store information in a file orders.json
    """

    response = requests.get(
        f"{config.faire_url}/orders", headers=config.faire_auth_headers
    )
    if response.status_code == 404:
        order_data = []
        raise Exception("Could not connect to API Endpoint")

    elif response.status_code == 200:
        order_data = response.json()
        # For development purposes, keep information locally stored
        f = open("orders.json", file_function)
        f.write(json.dumps(order_data, indent=4))
        f.close()
    else:
        order_data = []
    raise Exception(response.reason)

    return order_data


# Takes in Items from Orders
# Returns a list of Item Objects
def parse_order_items(items: [{}]) -> List[OrderItem]:
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


def parse_order_shipments(shipments: [{}]) -> List[Shipment]:
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
        # TODO SAVE
        shipment_list.append(new_shipment)
    return shipment_list


def parse_promotions(brand_discounts: [{}]) -> Optional[List[Discounts]]:
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


# Takes an address dictionary
# Returns an address model
def parse_address(address: {}) -> Address:
    if address:
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


def parse_payout_costs(payout_costs: {}) -> PayoutCosts:
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


async def parse_orders(order_data) -> List[Order]:
    order_list = []
    # Parse the response JSON
    # Process the order data as needed
    for order in order_data["orders"]:
        print()
        # Extract relevant information from the order data
        order_id = order["id"]
        display_id = order["display_id"]
        created_at = parser.parse(order["created_at"])
        updated_at = parser.parse(order["updated_at"])
        state = order["state"]
        address = order["address"]
        ship_after = order["ship_after"]
        payout_costs = order["payout_costs"]
        payment_initiated_at = parser.parse(order.get("payment_initiated_at"))
        retailer_id = order["retailer_id"]
        source = order["source"]
        expected_ship_date = parser.parse(order.get("expected_ship_date"))
        cust = order["customer"]
        processing_at = order["processing_at"]
        items = order["items"]  # TODO Instantiate each item model and make a list of id
        shipments = order[
            "shipments"
        ]  # TODO Instantiate shipment model and add shipment id
        brand_discounts = order[
            "brand_discounts"
        ]  # TODO Instantiate discount Promotion model and add promotion_id
        original_order_id = order.get("original_order_id")

        # Fields to reconfigure before making order model
        # Create an instance of your customer model and store the data
        new_cust = Customer(
            first_name=order["customer"]["first_name"], last_name=cust["last_name"]
        )
        new_address = None
        item_id_list = []
        shipment_id_list = []
        brand_discounts_list = []  # TODO Get discount models and add to list
        item_list = []
        shipment_list = []

        # Parse through items
        if items:
            item_list = parse_order_items(items)
            for item in item_list:
                item_id_list.append(item.order_item_id)
            # TODO Add item_list to MONGODB COLLECTIONS

        if shipments:
            shipment_list = parse_order_shipments(shipments)
            for shipment in shipment_list:
                shipment_id_list.append(shipment.shipment_id)
            # print(shipment_id_list)
            # TODO Add shipment_list to MONGODB COLLECTIONS

        if address:
            new_address = parse_address(address)

        if brand_discounts:
            brand_discounts_list = parse_promotions(brand_discounts)
        if payout_costs:
            new_payout_costs = parse_payout_costs(payout_costs)

        # Create a new Order instance and save it to MongoDB
        new_order = Order(
            provider_order_id=order_id,
            display_id=display_id,
            created_at=created_at,
            updated_at=updated_at,
            state=state,
            address=new_address,
            ship_after=ship_after,
            payout_costs=Cost(
                amount_minor=payout_costs.get("amount_minor"),
                currency=payout_costs.get("currency"),
            ),
            payment_initiated_at=payment_initiated_at,
            original_order_id=original_order_id,
            retailer_id=retailer_id,
            expected_ship_date=expected_ship_date,
            processing_at=processing_at,
            customer=new_cust,
            order_item_ids=item_id_list,
            shipment_ids=shipment_id_list,
            brand_discounts=brand_discounts_list,
            source=source,
        )
        order_list.append(new_order)

    return order_list


async def run_orders():
    order_data = None

    # Load existing data to not keep requesting API
    # Storing data locally to orders.json for now
    try:
        f = open("orders.json", "r")
        print("Orders.json exists")  # TODO Check if file empty or has data
        try:
            order_data = json.load(f)
            print("Loading data...")
        except json.decoder.JSONDecodeError:
            print("No order data in JSON, rewriting file with new request")
            order_data = get_orders("w")
        f.close()
    except FileNotFoundError:
        order_data = get_orders("x")
        print("File not found...\nCreating file...Requested orders")

    orders = await parse_orders(order_data)
    return orders


async def save_orders(orders):
    await engine.save_all(orders)


orders = asyncio.run(run_orders())
save_orders(orders)