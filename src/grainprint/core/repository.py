from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from grainprint.core.models import Crop, Subspecies, Variety, Marker, MarkerAssociation
from grainprint.core.schemas import SearchResult, MarkerInfo, EntityDetail


class Repository:
    entity_classes = {
        'crop': Crop,
        'subspecies': Subspecies,
        'variety': Variety,
        'marker': Marker,
        'association': MarkerAssociation
    }

    def __init__(self, session: Session):
        self.session = session

    def search(self,
               keyword: str,
               entity_type: str = None) -> list[SearchResult]:
        results = []

        models = [(Crop, 'crop'), (Subspecies, 'subspecies'),
                  (Variety, 'variety'), (Marker, 'marker')]
        if entity_type:
            models = [(m, t) for m, t in models if t == entity_type]

        for model, type_name in models:
            query = self.session.query(model)

            if model == Subspecies:
                query = query.join(Crop)
            elif model == Variety:
                query = query.join(Subspecies).join(Crop)

            filters = [model.name.contains(keyword)]
            if hasattr(model, 'name_en'):
                filters.append(model.name_en.ilike(f"%{keyword}%"))
            if model == Marker:
                filters.append(Marker.structure_formula.contains(keyword))

            for entity in query.filter(or_(*filters)).all():
                results.append(
                    SearchResult(id=entity.id,
                                 name=entity.name,
                                 type=type_name,
                                 path=self._get_entity_path(entity,
                                                            type_name)))

        return results

    def get_detail(self, entity_type: str, entity_id: int) -> EntityDetail:
        entity = self.session.get(self.entity_classes[entity_type], entity_id)

        markers = []
        children = []

        match entity_type:
            case 'crop':
                markers = [
                    self._marker_info_full(a, "") for a in entity.markers
                ]
                for sub in entity.subspecies:
                    markers.extend([
                        self._marker_info_full(
                            a, f"品类：{sub.name}") for a in sub.markers
                    ])
                    for var in sub.varieties:
                        markers.extend([
                            self._marker_info_full(
                                a, f"品种：{var.name}") for a in var.markers
                        ])
                children = [
                    SearchResult(id=s.id,
                                 name=s.name,
                                 type='subspecies',
                                 path=[entity.name, s.name])
                    for s in entity.subspecies
                ]
            case 'subspecies':
                markers = ([
                    self._marker_info_full(a, f"继承：{entity.crop.name}")
                    for a in entity.crop.markers
                ] + [self._marker_info_full(a, "") for a in entity.markers])
                children = [
                    SearchResult(id=v.id,
                                 name=v.name,
                                 type='variety',
                                 path=[entity.crop.name, entity.name, v.name])
                    for v in entity.varieties
                ]
            case 'variety':
                markers = ([
                    self._marker_info_full(
                        a, f"继承：{entity.subspecies.crop.name}")
                    for a in entity.subspecies.crop.markers
                ] + [
                    self._marker_info_full(a, f"继承：{entity.subspecies.name}")
                    for a in entity.subspecies.markers
                ] + [self._marker_info_full(a, "") for a in entity.markers])
                children = []
            case 'marker':
                for assoc in entity.associations:
                    if e := (assoc.crop or assoc.subspecies or assoc.variety):
                        t = 'crop' if assoc.crop else (
                            'subspecies' if assoc.subspecies else 'variety')

                        association_info = []
                        if assoc.source:
                            association_info.append(f"来源: {assoc.source}")
                        if assoc.screening_method:
                            association_info.append(
                                f"筛选: {assoc.screening_method}")
                        if assoc.metabolic_pathway:
                            association_info.append(
                                f"途径: {assoc.metabolic_pathway}")
                        if assoc.literature_source:
                            association_info.append(
                                f"文献: {assoc.literature_source}")
                        if assoc.notes:
                            association_info.append(f"备注: {assoc.notes}")
                        if assoc.notes2:
                            association_info.append(f"备注2: {assoc.notes2}")

                        result = SearchResult(id=e.id,
                                              name=e.name,
                                              type=t,
                                              path=self._get_entity_path(e, t))
                        result.association_info = " • ".join(
                            association_info) if association_info else None
                        children.append(result)

        return EntityDetail(id=entity.id,
                            name=entity.name,
                            name_en=entity.name_en,
                            type=entity_type,
                            path=self._get_entity_path(entity, entity_type),
                            markers=markers,
                            children=children)

    def _marker_info(self, assoc: MarkerAssociation, level: str) -> MarkerInfo:
        return MarkerInfo(id=assoc.marker.id,
                          name=assoc.marker.name,
                          formula=assoc.marker.structure_formula,
                          source=assoc.source,
                          level=level)

    def _marker_info_full(self, assoc: MarkerAssociation,
                          level: str) -> MarkerInfo:
        info = MarkerInfo(id=assoc.marker.id,
                          name=assoc.marker.name,
                          formula=assoc.marker.structure_formula,
                          source=assoc.source,
                          level=level)
        info.screening_method = assoc.screening_method
        info.metabolic_pathway = assoc.metabolic_pathway
        info.literature_source = assoc.literature_source
        info.notes = assoc.notes
        info.notes2 = assoc.notes2
        return info

    def _get_entity_path(self, entity, entity_type: str) -> list[str]:
        match entity_type:
            case 'crop' | 'marker':
                return [entity.name]
            case 'subspecies':
                return [entity.crop.name, entity.name]
            case 'variety':
                return [
                    entity.subspecies.crop.name, entity.subspecies.name,
                    entity.name
                ]

    def create(self, entity_type: str, **data) -> int:
        if entity_class := self.entity_classes.get(entity_type):
            if entity_type in ('crop', 'subspecies') and 'sort_order' not in data:
                max_order = self.session.query(func.max(
                    entity_class.sort_order
                )).scalar() or 0
                data['sort_order'] = max_order + 1
            entity = entity_class(**data)
            self.session.add(entity)
            self.session.flush()
            return entity.id
        raise ValueError(f"Unknown entity type: {entity_type}")

    def reorder(self, entity_type: str, ordered_ids: list[int],
                parent_id: int | None = None) -> bool:
        """按拖动后的顺序保存粮食/品类排序。"""
        model = self.entity_classes.get(entity_type)
        if model is None or entity_type not in ('crop', 'subspecies'):
            return False

        query = self.session.query(model)
        if entity_type == 'subspecies' and parent_id:
            query = query.filter_by(crop_id=parent_id)
        entities = {e.id: e for e in query.all()}

        for index, entity_id in enumerate(ordered_ids):
            entity = entities.get(entity_id)
            if entity is not None:
                entity.sort_order = index + 1
        self.session.flush()
        return True

    def create_marker_association(self, marker_id: int, entity_type: str,
                                  entity_id: int, **kwargs) -> int:
        field_map = {
            'crop': 'crop_id',
            'subspecies': 'subspecies_id',
            'variety': 'variety_id'
        }
        if field := field_map.get(entity_type):
            kwargs.update({field: entity_id, 'marker_id': marker_id})
            association = MarkerAssociation(**kwargs)
            self.session.add(association)
            self.session.flush()
            return association.id
        raise ValueError(f"Unknown entity type: {entity_type}")

    def update(self, entity_type: str, entity_id: int, data: dict) -> bool:
        if entity_class := self.entity_classes.get(entity_type):
            if entity := self.session.get(entity_class, entity_id):
                for key, value in data.items():
                    if hasattr(entity, key):
                        setattr(entity, key, value)
                self.session.flush()
                return True
        return False

    def delete(self, entity_type: str, entity_id: int) -> bool:
        if entity_class := self.entity_classes.get(entity_type):
            if entity := self.session.get(entity_class, entity_id):
                match entity_type:
                    case 'crop':
                        subspecies_ids = []
                        variety_ids = []

                        for sub in entity.subspecies:
                            subspecies_ids.append(sub.id)
                            variety_ids.extend([v.id for v in sub.varieties])

                        if variety_ids:
                            self.session.query(MarkerAssociation).filter(
                                MarkerAssociation.variety_id.in_(variety_ids)
                            ).delete(synchronize_session=False)
                        self.session.commit()

                        if variety_ids:
                            self.session.query(Variety).filter(
                                Variety.id.in_(variety_ids)).delete(
                                    synchronize_session=False)
                        self.session.commit()

                        if subspecies_ids:
                            self.session.query(MarkerAssociation).filter(
                                MarkerAssociation.subspecies_id.in_(
                                    subspecies_ids)).delete(
                                        synchronize_session=False)
                        self.session.commit()

                        if subspecies_ids:
                            self.session.query(Subspecies).filter(
                                Subspecies.id.in_(subspecies_ids)).delete(
                                    synchronize_session=False)
                        self.session.commit()

                        self.session.query(MarkerAssociation).filter_by(
                            crop_id=entity_id).delete()
                        self.session.commit()

                        self.session.query(Crop).filter_by(
                            id=entity_id).delete()
                        self.session.commit()

                    case 'subspecies':
                        variety_ids = [v.id for v in entity.varieties]

                        if variety_ids:
                            self.session.query(MarkerAssociation).filter(
                                MarkerAssociation.variety_id.in_(variety_ids)
                            ).delete(synchronize_session=False)
                        self.session.commit()

                        if variety_ids:
                            self.session.query(Variety).filter(
                                Variety.id.in_(variety_ids)).delete(
                                    synchronize_session=False)
                        self.session.commit()

                        self.session.query(MarkerAssociation).filter_by(
                            subspecies_id=entity_id).delete()
                        self.session.commit()

                        self.session.query(Subspecies).filter_by(
                            id=entity_id).delete()
                        self.session.commit()

                    case 'variety':
                        self.session.query(MarkerAssociation).filter_by(
                            variety_id=entity_id).delete()
                        self.session.commit()

                        self.session.query(Variety).filter_by(
                            id=entity_id).delete()
                        self.session.commit()

                    case 'marker':
                        self.session.query(MarkerAssociation).filter_by(
                            marker_id=entity_id).delete()
                        self.session.commit()

                        self.session.query(Marker).filter_by(
                            id=entity_id).delete()
                        self.session.commit()

                    case 'association':
                        self.session.delete(entity)
                        self.session.commit()

                return True
        return False

    def get_children(self, entity_type: str, parent_id: int = None) -> list:
        match entity_type:
            case 'crop':
                return self.session.query(Crop).order_by(
                    Crop.sort_order, Crop.id).all()
            case 'subspecies':
                query = self.session.query(Subspecies)
                if parent_id:
                    query = query.filter_by(crop_id=parent_id)
                return query.order_by(
                    Subspecies.sort_order, Subspecies.id).all()
            case 'variety':
                query = self.session.query(Variety)
                if parent_id:
                    query = query.filter_by(subspecies_id=parent_id)
                return query.order_by(Variety.name, Variety.id).all()
            case 'marker':
                return self.session.query(Marker).order_by(Marker.name, Marker.id).all()
            case _:
                return []

    def get_marker_associations_by_entity(
            self, entity_type: str, entity_id: int) -> list[MarkerAssociation]:
        field_map = {
            'crop': 'crop_id',
            'subspecies': 'subspecies_id',
            'variety': 'variety_id'
        }
        if field := field_map.get(entity_type):
            return self.session.query(MarkerAssociation).filter_by(
                **{
                    field: entity_id
                }).all()
        return []

    def get_marker_count_by_crop(self, crop_id: int) -> int:
        sub_ids = [s.id for s in self.session.query(Subspecies.id)
                   .filter_by(crop_id=crop_id).all()]
        var_ids = []
        if sub_ids:
            var_ids = [v.id for v in self.session.query(Variety.id)
                       .filter(Variety.subspecies_id.in_(sub_ids)).all()]

        crop_count = self.session.query(MarkerAssociation).filter_by(
            crop_id=crop_id).count()
        sub_count = (self.session.query(MarkerAssociation).filter(
            MarkerAssociation.subspecies_id.in_(sub_ids)).count()
            if sub_ids else 0)
        var_count = (self.session.query(MarkerAssociation).filter(
            MarkerAssociation.variety_id.in_(var_ids)).count()
            if var_ids else 0)
        return crop_count + sub_count + var_count

    def get_stats(self) -> dict:
        total_associations = self.session.query(MarkerAssociation).count()
        markers_with_association = self.session.query(
            MarkerAssociation.marker_id).distinct().count()

        return {
            'total': {
                'crops': self.session.query(Crop).count(),
                'subspecies': self.session.query(Subspecies).count(),
                'varieties': self.session.query(Variety).count(),
                'markers': self.session.query(Marker).count(),
                'associations': total_associations
            },
            'markers': {
                'total_associations':
                total_associations,
                'markers_without_association':
                self.session.query(Marker).count() - markers_with_association,
                'associations_by_level': {
                    'crop':
                    self.session.query(MarkerAssociation).filter(
                        MarkerAssociation.crop_id.isnot(None)).count(),
                    'subspecies':
                    self.session.query(MarkerAssociation).filter(
                        MarkerAssociation.subspecies_id.isnot(None)).count(),
                    'variety':
                    self.session.query(MarkerAssociation).filter(
                        MarkerAssociation.variety_id.isnot(None)).count()
                }
            }
        }
