"""
Generic repository base that wraps common ORM operations.
Concrete repositories should inherit from BaseRepository[Model].
"""
from typing import Generic, Optional, TypeVar

from django.db.models import Model, QuerySet

M = TypeVar("M", bound=Model)


class BaseRepository(Generic[M]):
    model: type[M]

    def get_by_id(self, pk: int) -> Optional[M]:
        try:
            return self.model.objects.get(pk=pk)
        except self.model.DoesNotExist:
            return None

    def all(self) -> QuerySet[M]:
        return self.model.objects.all()

    def filter(self, **kwargs) -> QuerySet[M]:
        return self.model.objects.filter(**kwargs)

    def create(self, **kwargs) -> M:
        return self.model.objects.create(**kwargs)

    def update(self, instance: M, **kwargs) -> M:
        for attr, value in kwargs.items():
            setattr(instance, attr, value)
        instance.save(update_fields=list(kwargs.keys()))
        return instance

    def delete(self, instance: M) -> None:
        instance.delete()
