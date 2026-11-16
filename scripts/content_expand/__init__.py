"""内容板块数据汇总"""

from data_brand import ITEMS as BRAND
from data_culture import ITEMS as CULTURE
from data_knowledge import ITEMS as KNOWLEDGE
from data_origin import ITEMS as ORIGIN
from data_teaware import ITEMS as TEAWARE

TYPE_ITEMS = {
    "teaware": TEAWARE,
    "origin": ORIGIN,
    "culture": CULTURE,
    "brand": BRAND,
    "knowledge": KNOWLEDGE,
}
