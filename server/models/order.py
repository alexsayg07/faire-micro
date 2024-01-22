from odmantic import Field, EmbeddedModel, Model, Reference, Index
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from faire.server.models.enums import OrderState


class Address(EmbeddedModel):
    address_id: str
    name: Optional[str]
    address1: str
    address2: Optional[str] = None
    postal_code: str
    city: str
    state: Optional[str]
    state_code: Optional[str]
    phone_number: str
    country: str
    country_code: Optional[str] = None
    company_name: Optional[str] = None


class Cost(EmbeddedModel):
    amount_minor: int = Field(default=None)
    currency: str = Field(default=None)


class Customer(EmbeddedModel):
    first_name: str = Field(default=None)
    last_name: str = Field(default=None)


class Taxes(EmbeddedModel):
    value: Cost
    taxable_item_type: str = Field(default=None)
    tax_type: str
    effect: str


class PayoutCosts(EmbeddedModel):
    payout_fee_bps: int
    commission_bps: int
    payout_fee: Cost
    commission: Cost
    total_payout: Cost
    payout_protection_fee: Optional[Cost]
    damaged_and_missing_items: Optional[Cost]
    net_tax: Optional[Cost]
    shipping_subsidy: Optional[Cost]
    taxes: Optional[List[Taxes]]


class Shipment(Model):
    shipment_id: str = Field(unique=True)
    order_id: str
    maker_cost_cents: int
    carrier: Optional[str]  # TODO MAKE ENUM
    tracking_code: Optional[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Discounts(EmbeddedModel):
    discount_id: Optional[str]
    code: Optional[str]
    discount_type: Optional[str]
    includes_free_shipping: bool = Field(default=False)
    discount_amount: Optional[Cost]
    discount_percentage: Optional[int]


class OrderItem(Model):
    order_item_id: str = Field(unique=True)
    order_id: str
    state: OrderState = Field(default=OrderState.NEW)
    product_id: str
    variant_id: Optional[str] = None
    quantity: int
    sku: str = Field(unique=True)
    price: Cost
    product_name: str
    variant_name: Optional[str] = None
    includes_tester: bool = Field(default=False)
    tester_price: Optional[Cost] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    discounts: Optional[Discounts] = None


class Order(Model):
    provider_order_id: str = Field(required=True)
    display_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    state: OrderState = Field(default=OrderState.NEW)
    address: Address
    ship_after: datetime = Field(default=None)
    payout_costs: Cost = Field(default=None)
    payment_initiated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    original_order_id: Optional[str] = None
    retailer_id: str
    source: str
    expected_ship_date: Optional[datetime] = None
    customer: Customer
    processing_at: Optional[datetime] = None
    # Reference item_id
    order_item_ids: List[str] = Field(default=None)
    # Reference shipment_id
    shipment_ids: Optional[List[str]] = Field(default=None)
    brand_discounts: Optional[List[Discounts]] = None

    class Index:
        provider_order_id = Index(unique=True)