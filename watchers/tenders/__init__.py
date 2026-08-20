"""Tender adapters — national procurement portals plus multilateral funders.

A second publisher is what makes independent outcome resolution possible:
a portal that announces a tender cannot also be the source that proves
what happened to it.
"""
from .guyana_eprocure import GuyanaEprocureAdapter
from .idb_procurement import IdbProcurementAdapter
from .jamaica_gojep import JamaicaGojepAdapter

ADAPTERS = [
    GuyanaEprocureAdapter(),
    JamaicaGojepAdapter(),
    IdbProcurementAdapter(),
]

__all__ = ["ADAPTERS", "GuyanaEprocureAdapter", "IdbProcurementAdapter", "JamaicaGojepAdapter"]
