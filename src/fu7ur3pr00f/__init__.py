"""FutureProof - Career Intelligence System."""

from importlib.metadata import PackageNotFoundError, version as _version

try:
    __version__ = _version("fu7ur3pr00f")
except PackageNotFoundError:
    __version__ = "0.0.0"
