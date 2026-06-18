"""National tender portal adapters."""
from .guyana_eprocure import GuyanaEprocureAdapter
from .jamaica_gojep import JamaicaGojepAdapter

ADAPTERS = [
    GuyanaEprocureAdapter(),
    JamaicaGojepAdapter(),
]

__all__ = ["ADAPTERS", "GuyanaEprocureAdapter", "JamaicaGojepAdapter"]
