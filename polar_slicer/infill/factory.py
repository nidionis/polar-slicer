"""Selection of an infill strategy from configuration.

The factory is the single place that knows the mapping ``InfillType -> concrete
strategy``. Adding a new fill pattern means registering it here (or via
:meth:`register`); no existing strategy or the pipeline changes — Open/Closed in
practice. The factory returns abstractions (:class:`InfillStrategy`), so callers
stay decoupled from concrete classes (Dependency Inversion).
"""

from __future__ import annotations

from collections.abc import Callable

from polar_slicer.config import InfillType, SlicerConfig
from polar_slicer.infill.grid import GridInfill
from polar_slicer.infill.solid import SolidInfill
from polar_slicer.infill.strategy import InfillStrategy


class InfillStrategyFactory:
    """Create the :class:`InfillStrategy` requested by a configuration."""

    def __init__(
        self,
        registry: dict[InfillType, Callable[[], InfillStrategy]] | None = None,
    ) -> None:
        # Default registry; callers may inject their own to extend/override.
        self._registry: dict[InfillType, Callable[[], InfillStrategy]] = (
            registry
            if registry is not None
            else {
                InfillType.SOLID: SolidInfill,
                InfillType.GRID: GridInfill,
            }
        )

    def register(
        self, infill_type: InfillType, factory: Callable[[], InfillStrategy]
    ) -> None:
        """Register (or replace) the factory for an infill type."""
        self._registry[infill_type] = factory

    def create(self, config: SlicerConfig) -> InfillStrategy:
        """Instantiate the strategy selected by ``config.infill_type``."""
        try:
            factory = self._registry[config.infill_type]
        except KeyError as exc:
            raise ValueError(
                f"no infill strategy registered for {config.infill_type!r}"
            ) from exc
        return factory()
