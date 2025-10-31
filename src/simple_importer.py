import pandas as pd
import os
import sys
from sqlalchemy import create_engine, Column, Integer, String, Text, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID
import uuid
from geoalchemy2 import Geometry
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class Location(Base):
    __tablename__ = "locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    address = Column(Text, nullable=False)
    coordinate = Column(Geometry(geometry_type='POINT', srid=4326))
    description = Column(Text)
    title = Column(String(500), nullable=False)
    category_id = Column(Integer, nullable=False)
    url = Column(String(500))

    @property
    def longitude(self):
        """Долгота"""
        if self.coordinate:
            from sqlalchemy import text
            session = SessionLocal()
            result = session.execute(
                text("SELECT ST_X(coordinate) FROM locations WHERE id = :id"),
                {'id': self.id}
            ).fetchone()
            session.close()
            return result[0] if result else None
        return None

    @property
    def latitude(self):
        """Широта"""
        if self.coordinate:
            from sqlalchemy import text
            session = SessionLocal()
            result = session.execute(
                text("SELECT ST_Y(coordinate) FROM locations WHERE id = :id"),
                {'id': self.id}
            ).fetchone()
            session.close()
            return result[0] if result else None
        return None


def create_tables():
    """Создает таблицы в БД"""
    Base.metadata.create_all(bind=engine)
    print(" Таблицы созданы")


def parse_coordinate(coord_string):
    """Парсит координаты из строки"""
    try:
        # Извлекаем числа из строк типа "POINT (44.003277 56.331576)"
        import re
        numbers = re.findall(r'[\d\.-]+', coord_string)
        if len(numbers) >= 2:
            lon, lat = numbers[0], numbers[1]
            return f'POINT({lon} {lat})'
    except:
        pass
    return None


def import_from_excel(file_path):
    """Основная функция импорта"""

    # Читаем Excel
    df = pd.read_excel(file_path)
    print(f"📊 Прочитано {len(df)} строк из {file_path}")

    # Создаем таблицы
    create_tables()

    session = SessionLocal()
    imported_count = 0

    for index, row in df.iterrows():
        try:
            wkt_coord = parse_coordinate(str(row['coordinate']))
            if not wkt_coord:
                print(f" Пропуск строки {index + 2}: неверные координаты")
                continue

            # Создаем объект
            location = Location(
                address=str(row['address']),
                description=str(row.get('description', '')),
                title=str(row['title']),
                category_id=int(row['category_id']),
                url=str(row.get('url', ''))
            )

            # Сохраняем и обновляем координаты
            session.add(location)
            session.flush()  # Получаем ID

            # Обновляем геометрию
            session.execute(
                text("UPDATE locations SET coordinate = ST_GeomFromText(:wkt, 4326) WHERE id = :id"),
                {'wkt': wkt_coord, 'id': location.id}
            )

            imported_count += 1
            print(f" Импортировано: {row['title']}")

        except Exception as e:
            print(f" Ошибка в строке {index + 2}: {e}")
            continue

    session.commit()
    session.close()

    print(f"\n Импорт завершен! Успешно: {imported_count}/{len(df)}")


def get_locations_by_category(category_id):
    """Получить локации по категории"""
    session = SessionLocal()
    locations = session.query(Location).filter(Location.category_id == category_id).all()
    session.close()
    return locations


def get_locations_near_point(lat, lon, radius_km=10):
    """Получить локации в радиусе от точки (в километрах)"""
    session = SessionLocal()
    from sqlalchemy import text

    query = text("""
        SELECT * FROM locations 
        WHERE ST_DWithin(
            coordinate::geography, 
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            :radius * 1000
        )
        ORDER BY ST_Distance(
            coordinate::geography, 
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
        )
    """)

    results = session.execute(query, {
        'lat': lat,
        'lon': lon,
        'radius': radius_km
    }).fetchall()

    session.close()
    return results


def get_locations_by_category_and_coords(category_id, lat, lon, radius_km=10):
    """Фильтр по категории И координатам"""
    session = SessionLocal()
    from sqlalchemy import text

    query = text("""
        SELECT * FROM locations 
        WHERE category_id = :category_id
        AND ST_DWithin(
            coordinate::geography, 
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
            :radius * 1000
        )
        ORDER BY ST_Distance(
            coordinate::geography, 
            ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
        )
    """)

    results = session.execute(query, {
        'category_id': category_id,
        'lat': lat,
        'lon': lon,
        'radius': radius_km
    }).fetchall()

    session.close()
    return results

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "../data_/input.xlsx"

    if not os.path.exists(file_path):
        print(f" Файл {file_path} не найден!")
        print(f"Текущая директория: {os.getcwd()}")
        sys.exit(1)

    import_from_excel(file_path)