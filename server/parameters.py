import datetime
from typing import Optional, List


class GetOrdersParams:
    def __init__(
        self,
        limit: Optional[int] = 50,
        page: Optional[int] = 1,
        updated_at_min: Optional[str] = None,
        created_at_min: Optional[str] = None,
        excluded_states: Optional[List] = None,
        ship_after_max: Optional[str] = None,
        cursor: Optional[int] = None,
    ):
        self.limit = limit
        self.page = page
        self.updated_at_min = updated_at_min
        self.created_at_min = created_at_min
        self.excluded_states = excluded_states
        self.ship_after_max = ship_after_max
        self.cursor = cursor

    def get_orders_params_dict(self):
        return {
            "limit": self.limit,
            "page": self.page,
            "updated_at_min": self.updated_at_min,
            "created_at_min": self.created_at_min,
            "excluded_states": self.excluded_states,
            "ship_after_max": self.ship_after_max,
            "cursor": self.cursor,
        }
