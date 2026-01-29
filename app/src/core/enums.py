from enum import Enum


class LoadMode(str, Enum):
    JSON = "json"
    EXTRACTED = "extracted"
    IPK = "ipk"
