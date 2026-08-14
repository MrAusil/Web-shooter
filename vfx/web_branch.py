"""Branch data structure re-exported for external modules that only need the shape.

Kept as its own module per the project's architecture; the canonical
implementation lives alongside WebProjectile in vfx/web.py since branch
geometry is tightly coupled to the parent curve's parametrization.
"""
from vfx.web import Branch  # noqa: F401
