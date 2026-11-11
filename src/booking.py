"""会議室の予約と、2つの予約が重なるかの判定。"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Booking:
    """会議室の予約。開始を含み、終了を含まない区間として扱う。"""

    start: datetime
    end: datetime


def overlaps(a: Booking, b: Booking) -> bool:
    """2つの予約が重なるかを返す。

    終了を含まないので、10:00〜11:00 と 11:00〜12:00 のように
    片方の終了ともう片方の開始がちょうど同じなら、重ならない。
    """
    return a.start <= b.end and b.start <= a.end
