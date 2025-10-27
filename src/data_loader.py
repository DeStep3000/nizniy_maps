import re

import pandas as pd
import streamlit as st

from src.constants import FILE_PATH


@st.cache_data(show_spinner=False)
def load_data():
    try:
        df = pd.read_excel(FILE_PATH, sheet_name="cultural_sites_202509191434")

        def parse_coordinates(coord_str):
            if pd.isna(coord_str):
                return None, None
            matches = re.findall(r"[-+]?\d*\.\d+|\d+", str(coord_str))
            if len(matches) >= 2:
                return float(matches[1]), float(matches[0])
            return None, None

        coords = df["coordinate"].apply(parse_coordinates)
        df["lat"] = coords.apply(lambda x: x[0] if x[0] is not None else None)
        df["lon"] = coords.apply(lambda x: x[1] if x[1] is not None else None)
        df = df.dropna(subset=["lat", "lon"])
        df["description"] = df["description"].fillna("Описание отсутствует")
        return df
    except Exception as e:
        st.error(f"Ошибка загрузки данных: {e}")
        return pd.DataFrame()
