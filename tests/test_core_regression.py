from pathlib import Path
import duckdb
import pytest

from grainprint.core.database import get_session, reset_db, DB_PATH
from grainprint.core.repository import Repository
from grainprint.domain.entities import EntityType
from grainprint.domain.errors import UserOperationError
from grainprint.domain.services import MarkerService


def setup_data(repo):
    crop = repo.create('crop', name='稻谷')
    subspecies = repo.create('subspecies', crop_id=crop, name='粳稻')
    variety = repo.create('variety', subspecies_id=subspecies, name='龙粳31')
    marker = repo.create('marker', name='3-戊醇', notes='标志物', notes2='自行筛选')
    feature = repo.create('marker', name='己醛', notes='特征物质', notes2='文献报道：https://example.org')
    return crop, subspecies, variety, marker, feature


def test_material_classification_summary_and_stats():
    reset_db()
    with get_session() as session:
        repo = Repository(session)
        crop, sub, variety, marker, feature = setup_data(repo)
        repo.create_marker_association(marker, 'variety', variety)
        repo.create_marker_association(feature, 'variety', variety)
        summaries = {item['name']: item for item in repo.get_marker_summaries()}
        assert summaries['3-戊醇']['material_type'] == '标志物'
        assert summaries['己醛']['material_type'] == '特征物质'
        assert summaries['己醛']['material_source'] == '文献报道'
        stats = repo.get_stats()
        assert stats['total']['material_types'] == {'标志物': 1, '特征物质': 1, '未分类': 0}
        assert stats['markers']['material_sources']['自行筛选']['标志物'] == 1
        assert stats['markers']['material_sources']['文献报道']['特征物质'] == 1
        assert repo.get_marker_count_by_crop_and_type(crop, '标志物') == 1
        assert repo.get_marker_count_by_crop_and_type(crop, '特征物质') == 1


def test_replace_association_failure_preserves_old_association():
    reset_db()
    with get_session() as session:
        repo = Repository(session)
        _, _, variety, marker, feature = setup_data(repo)
        old_id = repo.create_marker_association(marker, 'variety', variety)
        repo.create_marker_association(feature, 'variety', variety)

    # Replacing marker with an already-associated feature must roll back and
    # leave the original association untouched.
    with pytest.raises(UserOperationError):
        MarkerService.replace_association(old_id, type('Request', (), {
            'marker_id': feature, 'entity_type': EntityType.VARIETY,
            'entity_id': variety,
            'model_dump': lambda self, **kwargs: {},
        })())

    with get_session() as session:
        repo = Repository(session)
        associated = {a.marker_id for a in repo.get_marker_associations_by_entity('variety', variety)}
        assert associated == {marker, feature}


def test_batch_association_is_all_or_nothing():
    reset_db()
    with get_session() as session:
        repo = Repository(session)
        crop, sub, variety, marker, feature = setup_data(repo)
        repo.create_marker_association(marker, 'variety', variety)

    with pytest.raises(UserOperationError):
        MarkerService.create_associations(marker, [(EntityType.CROP, crop), (EntityType.VARIETY, variety)], {})

    with get_session() as session:
        repo = Repository(session)
        assert repo.get_marker_associations_by_entity('crop', crop) == []
        assert len(repo.get_marker_associations_by_entity('variety', variety)) == 1


def test_marker_schema_contains_material_notes():
    with get_session() as session:
        columns = {row[1] for row in session.connection().exec_driver_sql("pragma table_info('markers')").fetchall()}
    assert {'notes', 'notes2'} <= columns


def test_legacy_association_notes_are_migrated_to_material():
    reset_db()
    with get_session() as session:
        repo = Repository(session)
        crop, _, _, marker, _ = setup_data(repo)
        # Simulate a v0.4.0 material that had no material-level metadata.
        repo.update('marker', marker, {'notes': None, 'notes2': None})
        repo.create_marker_association(marker, 'crop', crop, notes='标志物', notes2='自行筛选')
        session.connection().exec_driver_sql("""
            UPDATE markers AS m SET notes = (
                SELECT a.notes FROM marker_associations AS a
                WHERE a.marker_id = m.id AND a.notes IS NOT NULL AND a.notes <> ''
                ORDER BY a.id LIMIT 1
            ) WHERE m.notes IS NULL OR m.notes = ''
        """)
        session.connection().exec_driver_sql("""
            UPDATE markers AS m SET notes2 = (
                SELECT a.notes2 FROM marker_associations AS a
                WHERE a.marker_id = m.id AND a.notes2 IS NOT NULL AND a.notes2 <> ''
                ORDER BY a.id LIMIT 1
            ) WHERE m.notes2 IS NULL OR m.notes2 = ''
        """)
        material = session.get(repo.entity_classes['marker'], marker)
        assert material.notes == '标志物'
        assert material.notes2 == '自行筛选'
