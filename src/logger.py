import logging
import socket

import streamlit as st

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("user_actions.log", encoding="utf-8"),
    ],
)

def get_user_ip() -> str:
    try:
        if hasattr(st, "server") and hasattr(st.server, "_runtime"):
            headers = st.server._runtime._get_websocket_headers()  # type: ignore
            if headers and "X-Forwarded-For" in headers:
                return headers["X-Forwarded-For"].split(",")[0].strip()
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except Exception:
        return "unknown"

def log_user_action(action: str, **kwargs):
    user_ip = get_user_ip()
    extra = " ".join([f"{k}={v}" for k, v in kwargs.items()])
    logging.info(f"[USER] {action.upper()} ip={user_ip} {extra}")