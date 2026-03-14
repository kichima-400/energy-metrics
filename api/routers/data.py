"""
データ取得エンドポイント
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, HTTPException

from api.services.loader import get_chart_data, get_indicators, get_summary

router = APIRouter(prefix="/api")


@router.get("/indicators")
def indicators():
    """利用可能な指標の一覧を返す。"""
    return get_indicators()


@router.get("/chart")
def chart(
    ids: Annotated[list[str], Query()] = [],
    start: date | None = None,
    end: date | None = None,
):
    """
    チャート用の時系列データを返す。

    - **ids**: 取得する指標ID（複数指定可）例: `?ids=wti_crude&ids=usd_jpy`
    - **start**: 開始日 (YYYY-MM-DD)
    - **end**: 終了日 (YYYY-MM-DD)
    """
    if not ids:
        raise HTTPException(status_code=400, detail="ids パラメータを1つ以上指定してください")
    return get_chart_data(ids, start, end)


@router.get("/summary")
def summary():
    """各指標の最新値・前の値との差分を返す。"""
    return get_summary()
