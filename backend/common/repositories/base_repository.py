from typing import Type, TypeVar, List, Optional, Any, Dict
from django.db import models, transaction
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet

T = TypeVar('T', bound=models.Model)

class BaseRepository:
    """
    Enterprise Base Repository providing abstract database access.
    No business logic is permitted here.
    """
    model: Type[T] = None

    @classmethod
    def get_queryset(cls) -> QuerySet:
        if cls.model is None:
            raise ValueError("Repository must define a model class")
        return cls.model.objects.all()

    @classmethod
    def get_by_id(cls, obj_id: Any, select_related: List[str] = None, prefetch_related: List[str] = None) -> Optional[T]:
        qs = cls.get_queryset()
        if select_related:
            qs = qs.select_related(*select_related)
        if prefetch_related:
            qs = qs.prefetch_related(*prefetch_related)
            
        try:
            return qs.get(id=obj_id)
        except cls.model.DoesNotExist:
            return None

    @classmethod
    def create(cls, **kwargs) -> T:
        return cls.model.objects.create(**kwargs)

    @classmethod
    def update(cls, instance: T, **kwargs) -> T:
        for attr, value in kwargs.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    @classmethod
    def delete(cls, instance: T) -> None:
        """
        Relies on the model's delete method. If the model is a SoftDeleteModel, 
        this will soft delete it.
        """
        instance.delete()

    @classmethod
    def exists(cls, **kwargs) -> bool:
        return cls.get_queryset().filter(**kwargs).exists()

    @classmethod
    @transaction.atomic
    def bulk_create(cls, objs: List[T], batch_size: int = 100) -> List[T]:
        return cls.model.objects.bulk_create(objs, batch_size=batch_size)

    @classmethod
    @transaction.atomic
    def bulk_update(cls, objs: List[T], fields: List[str], batch_size: int = 100) -> int:
        return cls.model.objects.bulk_update(objs, fields, batch_size=batch_size)

    @classmethod
    def paginate(cls, qs: QuerySet, page: int = 1, limit: int = 50) -> QuerySet:
        offset = (page - 1) * limit
        return qs[offset:offset + limit]
