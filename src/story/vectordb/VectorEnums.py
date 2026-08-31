from enum import Enum


class VectorDBProvider(str, Enum):
    CHROMA  = "chroma"
    MOCK    = "mock"
