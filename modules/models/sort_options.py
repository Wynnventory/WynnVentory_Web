from enum import Enum


class SortOption(str, Enum):
    TIMESTAMP_DESC = "timestamp_desc"
    TIMESTAMP_ASC = "timestamp_asc"
    LISTING_PRICE_DESC = "listing_price_desc"
    LISTING_PRICE_ASC = "listing_price_asc",
    OVERALL_ROLL_DESC = "overall_roll_desc"
    OVERALL_ROLL_ASC = "overall_roll_asc"

    def to_mongo_sort(self) -> tuple[str, int]:
        """Return (field, direction) for Mongo sort."""
        return {
            SortOption.TIMESTAMP_DESC: ("timestamp", -1),
            SortOption.TIMESTAMP_ASC: ("timestamp", 1),
            SortOption.LISTING_PRICE_DESC: ("listing_price", -1),
            SortOption.LISTING_PRICE_ASC: ("listing_price", 1),
            SortOption.OVERALL_ROLL_DESC: ("overall_roll", -1),
            SortOption.OVERALL_ROLL_ASC: ("overall_roll", 1),
        }[self]

    def label(self) -> str:
        return {
            SortOption.TIMESTAMP_DESC: "Newest First",
            SortOption.TIMESTAMP_ASC: "Oldest First",
            SortOption.LISTING_PRICE_DESC: "Highest Price",
            SortOption.LISTING_PRICE_ASC: "Lowest Price",
            SortOption.OVERALL_ROLL_DESC: "Highest Overall Roll",
            SortOption.OVERALL_ROLL_ASC: "Lowest Overall Roll",
        }[self]

    def __str__(self) -> str:
        return self.value
