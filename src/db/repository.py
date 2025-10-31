from typing import Iterable, Optional

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session


def fetch_locations_df(
    session: Session,
    categories: Optional[Iterable[int]] = None,
) -> pd.DataFrame:
    """
    Возвращает DataFrame с колонками:
    id, title, description, category_id, address, url, lat, lon
    """
    base_sql = """
        SELECT
            id,
            title,
            description,
            category_id,
            address,
            url,
            ST_Y(coordinate) AS lat,
            ST_X(coordinate) AS lon
        FROM locations
    """
    params = {}
    if categories:
        base_sql += " WHERE category_id = ANY(:cats)"
        params["cats"] = list(categories)

    base_sql += " ORDER BY title"

    result = session.execute(text(base_sql), params)
    rows = [dict(r._mapping) for r in result]
    df = pd.DataFrame(rows)

    if not df.empty:
        if "category_id" in df.columns:
            df["category_id"] = pd.to_numeric(df["category_id"], errors="coerce")
        for col in ("lat", "lon"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
    return df
