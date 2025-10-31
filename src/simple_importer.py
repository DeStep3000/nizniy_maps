import os
import sys
import uuid
import re
from typing import Optional, Tuple

import pandas as pd
from sqlalchemy import text
from dotenv import load_dotenv

from src.db.session import SessionLocal, engine
from src.db.models import Base, Location

load_dotenv()

def _norm(s: Optional[str]) -> str:
    return "" if s is None else " ".join(str(s).strip().lower().split())

def _pick_sheet(file_path: str, sheet_name: Optional[str | int]) -> str | int:
    """
    Возвращает корректный идентификатор листа для pd.read_excel:
      1) Явно переданный sheet_name
      2) Лист 'cultural_sites_202509191434', если есть
      3) Первый лист в книге
    """
    if sheet_name is not None:
        return sheet_name

    xls = pd.ExcelFile(file_path)
    preferred = "cultural_sites_202509191434"
    if preferred in xls.sheet_names:
        return preferred
    return xls.sheet_names[0]


def _parse_lat_lon_from_string(coord_str: str) -> Tuple[float | None, float | None]:
    """
    Полная копия логики из рабочего Excel-лоадера:

    matches = re.findall(r"[-+]?\d*\.\d+|\d+", str(coord_str))
    if len(matches) >= 2:
        return float(matches[1]), float(matches[0])  # lat, lon
    return None, None

    Т.е. строка содержит два числа, первое — lon, второе — lat.
    Мы возвращаем (lat, lon).
    """
    if coord_str is None:
        return None, None
    matches = re.findall(r"[-+]?\d*\.\d+|\d+", str(coord_str))
    if len(matches) >= 2:
        try:
            lon = float(matches[0])
            lat = float(matches[1])
            return lat, lon
        except Exception:
            return None, None
    return None, None


def _parse_lat_lon(row: dict) -> Tuple[float | None, float | None]:
    """
    Унифицированный парсер:
    - сначала пробуем явные 'lat'/'lon'
    - затем строковые поля 'coordinate'/'coordinates'/'coords' согласно логике из Excel-лоадера
    """
    lat = row.get("lat")
    lon = row.get("lon")
    if pd.notna(lat) and pd.notna(lon):
        try:
            return float(lat), float(lon)
        except Exception:
            pass

    coord_str = row.get("coordinate") or row.get("coordinates") or row.get("coords")
    if coord_str is not None and not (isinstance(coord_str, float) and pd.isna(coord_str)):
        return _parse_lat_lon_from_string(coord_str)

    return None, None


def create_schema_if_not_exists():
    """Создает таблицы, если они еще не созданы."""
    Base.metadata.create_all(bind=engine)


def create_indexes(session):
    """Индексы для ускорения гео-запросов."""
    session.execute(
        text(
            """
        CREATE INDEX IF NOT EXISTS idx_locations_coordinate
        ON locations
        USING GIST (coordinate)
        """
        )
    )
    session.execute(
        text(
            """
        CREATE INDEX IF NOT EXISTS idx_locations_category
        ON locations (category_id)
        """
        )
    )
    session.execute(
        text(
                       """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_locations_title_addr_xy6
            ON locations (
                lower(coalesce(title,'')),
                lower(coalesce(address,'')),
                round(CAST(ST_Y(coordinate) AS numeric), 6),
                round(CAST(ST_X(coordinate) AS numeric), 6)
            )
            """
            )
        )


def import_from_excel(file_path: str, sheet_name: str | int | None = None):
    """
    Импортирует данные из Excel в таблицу locations.
    Ожидаемые поля: title, description, category_id, address, url, coordinate (или lat/lon).
    """
    if not os.path.exists(file_path):
        print(f"Файл {file_path} не найден")
        sys.exit(1)

    create_schema_if_not_exists()

    sheet_to_use = _pick_sheet(file_path, sheet_name)
    print(f"[import] читаем Excel: {file_path}, лист: {sheet_to_use}")
    df = pd.read_excel(file_path, sheet_name=sheet_to_use)

    df.columns = [str(c).strip().lower() for c in df.columns]

    required = ["title", "category_id"]
    for col in required:
        if col not in df.columns:
            print(f"В Excel не найден обязательный столбец: {col}")
            sys.exit(1)

    inserted, skipped, with_geom = 0, 0, 0

    with SessionLocal() as session:
        has_any = session.execute(text("SELECT 1 FROM locations LIMIT 1")).first() is not None
        if has_any:
            print("[import] В таблице уже есть данные — импорт пропущен (одноразовая загрузка).")
            return

        sheet_to_use = _pick_sheet(file_path, sheet_name)
        print(f"[import] читаем Excel: {file_path}, лист: {sheet_to_use}")
        df = pd.read_excel(file_path, sheet_name=sheet_to_use)

        df.columns = [str(c).strip().lower() for c in df.columns]

        required = ["title", "category_id"]

        for col in required:
            if col not in df.columns:
                print(f"В Excel не найден обязательный столбец: {col}")
                sys.exit(1)

        inserted, skipped, with_geom = 0, 0, 0
        for _, row in df.iterrows():
            rowd = row.to_dict()


            try:
                category_id = int(rowd.get("category_id"))
            except Exception:
                skipped += 1
                continue

            title = str(rowd.get("title", "")).strip()
            if not title:
                skipped += 1
                continue

            description = None if pd.isna(rowd.get("description")) else str(rowd.get("description"))
            address = None if pd.isna(rowd.get("address")) else str(rowd.get("address"))
            url = None if pd.isna(rowd.get("url")) else str(rowd.get("url"))

            lat, lon = _parse_lat_lon(rowd)
            if lat is None or lon is None:
                skipped += 1
                continue

            loc = Location(
                id=uuid.uuid4(),
                title=title,
                description=description,
                category_id=category_id,
                address=address or "",
                url=url,
            )
            session.add(loc)
            session.flush()

            wkt_point = f"POINT({lon} {lat})"
            session.execute(
                text(
                    """
                    UPDATE locations
                    SET coordinate = ST_GeomFromText(:wkt, 4326)
                    WHERE id = :id
                    """
                ),
                {"wkt": wkt_point, "id": loc.id},
            )
            with_geom += 1
            inserted += 1

        create_indexes(session)

        session.commit()

    print(f"Импорт завершен. Добавлено: {inserted}, с геометрией: {with_geom}, пропущено: {skipped}")


if __name__ == "__main__":
    if len(sys.argv) > 2:
        path = sys.argv[1]
        sheet = sys.argv[2]
    elif len(sys.argv) > 1:
        path = sys.argv[1]
        sheet = None
    else:
        path = "data_/cultural_objects_mnn.xlsx"
        sheet = None

    import_from_excel(path, sheet_name=sheet)
