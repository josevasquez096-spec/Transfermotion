"""Modelo de datos de MailPilot, independiente de Outlook."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Store:
    id: str
    name: str
    kind: str = "primary"  # primary, shared, pst, demo
    address: str = ""


@dataclass
class Folder:
    id: str
    store_id: str
    name: str
    path: str
    parent_id: str = ""
    depth: int = 0
    unread: int = 0
    total: int = 0
    special: str = ""  # inbox, sent, drafts, deleted, junk, outbox, sync o vacío


@dataclass
class Message:
    id: str
    store_id: str
    folder_id: str
    folder_path: str
    subject: str = ""
    sender_name: str = ""
    sender_email: str = ""
    to: str = ""
    cc: str = ""
    received: datetime | None = None
    categories: list = field(default_factory=list)
    unread: bool = False
    flagged: bool = False
    importance: int = 1  # 0 baja, 1 normal, 2 alta
    has_attachments: bool = False
    size: int = 0
    body: str | None = None  # se carga bajo demanda
    html: str | None = None
    attachments: list = field(default_factory=list)
    reply_to: str = ""

    @property
    def domain(self):
        email = (self.sender_email or "").lower()
        return email.rsplit("@", 1)[1] if "@" in email else ""


@dataclass
class Category:
    name: str
    color: int = 0  # OlCategoryColor (0 = sin color, 1-25)


# Colores de categoría de Outlook (OlCategoryColor) para mostrarlos en la app.
CATEGORY_HEX = {
    0: "#C8C8C8", -1: "#C8C8C8", 1: "#E74856", 2: "#F7630C", 3: "#FFAA44", 4: "#FFD335", 5: "#4CAF50",
    6: "#00B7C3", 7: "#8BAE3A", 8: "#0078D4", 9: "#8764B8", 10: "#A4262C", 11: "#69797E", 12: "#374649",
    13: "#A0AEB2", 14: "#6E6E6E", 15: "#000000", 16: "#750B1C", 17: "#CA5010", 18: "#C46A2D", 19: "#C19C00",
    20: "#0B6A0B", 21: "#005B70", 22: "#5C6F1A", 23: "#003966", 24: "#401B6C", 25: "#5C0A16",
}
# Colores que se ofrecen al crear una categoría (clave de traducción, índice de Outlook).
PICKER_COLORS = [("c_red", 1), ("c_orange", 2), ("c_yellow", 4), ("c_green", 5), ("c_teal", 6), ("c_blue", 8),
                 ("c_purple", 9), ("c_maroon", 10), ("c_steel", 11), ("c_gray", 13), ("c_darkgreen", 20),
                 ("c_darkblue", 23)]
