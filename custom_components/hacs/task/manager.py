"""Hacs task manager."""
from __future__ import annotations

import asyncio
from importlib import import_module
from pathlib import Path

from custom_components.hacs.base import HacsBase
from custom_components.hacs.task.const import HacsTaskType
from custom_components.hacs.task.tasks.base import HacsTaskBase


class HacsTaskManager(HacsBase):
    """Hacs task manager."""

    def __init__(self) -> None:
        """Initialize the setup manager class."""
        self.__tasks: dict[str, HacsTaskBase] = {}

    @property
    def tasks(self) -> list[HacsTaskBase]:
        """Return all list of all tasks."""
        return list(self.__tasks.values())

    async def async_load(self):
        """Load all tasks."""
        package = f"{__package__}.tasks"
        task_files = Path(__file__).parent.joinpath("tasks")
        task_modules = (
            module.stem
            for module in task_files.glob("*.py")
            if module.name not in ("base.py", "__init__.py", "manager.py")
        )

        async def _load_module(module: str):
            task_module = import_module(f"{package}.{module}")
            if task := await task_module.async_setup():
                self.__tasks[task.slug] = task

        await asyncio.gather(*[_load_module(task) for task in task_modules])
        self.log.info("Loaded %s tasks", len(self.tasks))

    def get(self, slug: str) -> HacsTaskBase | None:
        """Return a task."""
        return self.__tasks.get(slug)

    async def async_execute_runtume_tasks(self) -> None:
        """Execute the the execute methods of each runtime task if the stage matches."""
        await asyncio.gather(
            *[
                task.execute()
                for task in self.tasks
                if task.type == HacsTaskType.RUNTIME
                and self.system.stage in task.stages
                or not task.stages
            ]
        )