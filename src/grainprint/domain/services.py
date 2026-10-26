from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from grainprint.core.database import get_session
from grainprint.core.repository import Repository
from grainprint.core.schemas import SearchResult, EntityDetail
from grainprint.domain.entities import (EntityType, CropCreate, CropUpdate,
                                        SubspeciesCreate, SubspeciesUpdate,
                                        VarietyCreate, VarietyUpdate,
                                        MarkerCreate, MarkerUpdate,
                                        MarkerAssociationCreate,
                                        DeleteConfirmation,MarkerAssociationUpdate)


class EntityService:
    """统一的实体业务服务"""

    @staticmethod
    def create(entity_type: EntityType, data: BaseModel) -> int:
        with get_session() as session:
            repo = Repository(session)
            return repo.create(entity_type.value,
                               **data.model_dump(exclude_none=True))

    @staticmethod
    def update(entity_type: EntityType, entity_id: int,
               data: BaseModel) -> bool:
        with get_session() as session:
            repo = Repository(session)
            return repo.update(entity_type.value, entity_id,
                               data.model_dump(exclude_none=True))

    @staticmethod
    def delete(entity_type: EntityType, entity_id: int) -> bool:
        with get_session() as session:
            repo = Repository(session)
            return repo.delete(entity_type.value, entity_id)

    @staticmethod
    def get_delete_confirmation(entity_type: EntityType,
                                entity_id: int) -> DeleteConfirmation:
        with get_session() as session:
            repo = Repository(session)
            detail = repo.get_detail(entity_type.value, entity_id)

            impact = {}
            if entity_type == EntityType.CROP:
                impact['subspecies'] = len(
                    [c for c in detail.children if c.type == 'subspecies'])
                impact['varieties'] = sum(
                    len(repo.get_children('variety', c.id))
                    for c in detail.children)
                impact['associations'] = len(detail.markers)
            elif entity_type == EntityType.SUBSPECIES:
                impact['varieties'] = len(detail.children)
                impact['associations'] = len(detail.markers)
            elif entity_type == EntityType.VARIETY:
                impact['associations'] = len(detail.markers)
            elif entity_type == EntityType.MARKER:
                impact['associations'] = len(detail.children)

            return DeleteConfirmation(entity_type=entity_type,
                                      entity_id=entity_id,
                                      entity_name=detail.name,
                                      impact=impact)

    @staticmethod
    def search(keyword: str,
               entity_type: Optional[EntityType] = None) -> List[SearchResult]:
        with get_session() as session:
            repo = Repository(session)
            return repo.search(
                keyword,
                entity_type=entity_type.value if entity_type else None)

    @staticmethod
    def get_detail(entity_type: EntityType, entity_id: int) -> EntityDetail:
        with get_session() as session:
            repo = Repository(session)
            return repo.get_detail(entity_type.value, entity_id)

    @staticmethod
    def get_children(entity_type: EntityType,
                     parent_id: Optional[int] = None) -> List[Any]:
        with get_session() as session:
            repo = Repository(session)
            return repo.get_children(entity_type.value, parent_id)

    @staticmethod
    def get_marker_summaries() -> List[Dict[str, Any]]:
        with get_session() as session:
            return Repository(session).get_marker_summaries()

    @staticmethod
    def get_hierarchy() -> List[Dict[str, Any]]:
        with get_session() as session:
            return Repository(session).get_hierarchy()

    @staticmethod
    def get_association_editor_data() -> Dict[str, Any]:
        with get_session() as session:
            return Repository(session).get_association_editor_data()

    @staticmethod
    def get_entity_location(entity_type: EntityType, entity_id: int) -> tuple[int | None, int | None]:
        with get_session() as session:
            return Repository(session).get_entity_location(entity_type.value, entity_id)

    @staticmethod
    def reorder(entity_type: EntityType, ordered_ids: List[int],
                parent_id: Optional[int] = None) -> bool:
        with get_session() as session:
            repo = Repository(session)
            return repo.reorder(entity_type.value, ordered_ids, parent_id)

    @staticmethod
    def get_stats() -> Dict[str, Any]:
        with get_session() as session:
            repo = Repository(session)
            return repo.get_stats()


class MarkerService:
    """标志物相关业务服务"""

    @staticmethod
    def create_association(data: MarkerAssociationCreate) -> int:
        with get_session() as session:
            repo = Repository(session)
            return repo.create_marker_association(
                marker_id=data.marker_id, entity_type=data.entity_type.value,
                entity_id=data.entity_id, **data.model_dump(
                    exclude={'marker_id', 'entity_type', 'entity_id'}, exclude_none=True))

    @staticmethod
    def create_associations(marker_id: int, targets: list[tuple[EntityType, int]],
                            info: dict) -> list[int]:
        with get_session() as session:
            return Repository(session).create_marker_associations(
                marker_id, [(kind.value, entity_id) for kind, entity_id in targets], **info)

    @staticmethod
    def replace_association(association_id: int, data: MarkerAssociationCreate) -> int:
        with get_session() as session:
            return Repository(session).replace_marker_association(
                association_id, data.marker_id, data.entity_type.value, data.entity_id,
                **data.model_dump(exclude={'marker_id', 'entity_type', 'entity_id'}, exclude_none=True))

    @staticmethod
    def update_association(association_id: int, data: MarkerAssociationUpdate) -> bool:
        with get_session() as session:
            repo = Repository(session)
            return repo.update('association', association_id, data.model_dump(exclude_none=True))

    @staticmethod
    def get_associations_by_entity(entity_type: EntityType,
                                   entity_id: int) -> List[Any]:
        with get_session() as session:
            repo = Repository(session)
            return repo.get_marker_associations_by_entity(
                entity_type.value, entity_id)

