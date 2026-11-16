# 茶品批量扩充数据入口

from data_green import TEAS_GREEN
from data_red import TEAS_RED
from data_oolong import TEAS_OOLONG
from data_dark import TEAS_DARK
from data_white import TEAS_WHITE
from data_yellow import TEAS_YELLOW
from data_reprocessed import TEAS_REPROCESSED

ALL_TEAS = (
    TEAS_GREEN
    + TEAS_RED
    + TEAS_OOLONG
    + TEAS_DARK
    + TEAS_WHITE
    + TEAS_YELLOW
    + TEAS_REPROCESSED
)

if __name__ == "__main__":
    print(f"绿茶 {len(TEAS_GREEN)} 款")
    print(f"红茶 {len(TEAS_RED)} 款")
    print(f"乌龙 {len(TEAS_OOLONG)} 款")
    print(f"黑茶 {len(TEAS_DARK)} 款")
    print(f"白茶 {len(TEAS_WHITE)} 款")
    print(f"黄茶 {len(TEAS_YELLOW)} 款")
    print(f"再加工茶 {len(TEAS_REPROCESSED)} 款")
    print(f"合计 {len(ALL_TEAS)} 款")
