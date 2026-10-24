from grainprint.core.database import get_session, reset_db, _backup_on_startup
from grainprint.config import DB_PATH
from pathlib import Path
import duckdb
from grainprint.core.repository import Repository


def _setup_base(repo):
    crop_id = repo.create("crop", name="稻谷", name_en="Rice")
    sub_id = repo.create(
        "subspecies", crop_id=crop_id, name="粳稻", name_en="Japonica"
    )
    var_id = repo.create(
        "variety", subspecies_id=sub_id, name="宁粳84", name_en="Ningjing 84"
    )
    marker_id = repo.create(
        "marker", name="己醛", name_en="Hexanal", structure_formula="CH₃(CH₂)₄CHO"
    )
    return crop_id, sub_id, var_id, marker_id


def test_edit_association_then_add_marker_keeps_existing_data():
    reset_db()
    with get_session() as s:
        repo = Repository(s)
        crop_id, sub_id, var_id, marker_id = _setup_base(repo)
        assoc_id = repo.create_marker_association(
            marker_id,
            "variety",
            var_id,
            source="旧来源",
            screening_method="旧方法",
        )

        repo.update("association", assoc_id, {"source": "新来源"})

        marker2 = repo.create(
            "marker", name="葡萄糖酸内酯", name_en="Gluconolactone",
            structure_formula="HOCH2(CHOH)3-CH(O)-CO(δ-lactone)",
        )
        repo.create_marker_association(marker2, "variety", var_id, source="新标志物")

        assert repo.get_children("crop")[0].name == "稻谷"
        assert len(repo.get_children("subspecies", crop_id)) == 1
        assert len(repo.get_children("variety", sub_id)) == 1
        assert len(repo.get_children("marker")) == 2
        assert len(repo.get_marker_associations_by_entity("variety", var_id)) == 2
        updated = repo.session.get(
            repo.entity_classes["association"], assoc_id
        )
        assert updated.source == "新来源"


def test_add_variety_after_association_edits_keeps_data():
    reset_db()
    with get_session() as s:
        repo = Repository(s)
        crop_id, sub_id, var_id, marker_id = _setup_base(repo)
        assoc_id = repo.create_marker_association(
            marker_id, "subspecies", sub_id
        )

        repo.update("association", assoc_id, {"source": "编辑后"})
        repo.create("variety", subspecies_id=sub_id, name="龙粳26", name_en="Longjing 26")

        assert len(repo.get_children("variety", sub_id)) == 2
        assert len(repo.get_children("crop")) == 1
        assert len(repo.get_children("marker")) == 1
        assert len(repo.get_marker_associations_by_entity("subspecies", sub_id)) == 1


def test_delete_one_crop_keeps_other_records_and_continues_editing():
    reset_db()
    with get_session() as s:
        repo = Repository(s)
        r_crop, r_sub, r_var, r_marker = _setup_base(repo)
        w_crop = repo.create("crop", name="小麦", name_en="Wheat")
        w_sub = repo.create(
            "subspecies", crop_id=w_crop, name="白小麦", name_en="White Wheat"
        )
        w_var = repo.create(
            "variety", subspecies_id=w_sub, name="济麦22", name_en="Jimai 22"
        )

        repo.delete("crop", r_crop)

        assert repo.get_children("crop")[0].name == "小麦"
        assert len(repo.get_children("subspecies", w_crop)) == 1
        assert len(repo.get_children("variety", w_sub)) == 1
        assert len(repo.get_children("marker")) == 1

        repo.create("variety", subspecies_id=w_sub, name="济麦23", name_en="Jimai 23")
        repo.update("crop", w_crop, {"description": "修改后仍可继续编辑"})
        assert len(repo.get_children("variety", w_sub)) == 2
        assert repo.get_children("crop")[0].description == "修改后仍可继续编辑"


def test_association_update_then_delete_then_create_different_marker():
    reset_db()
    with get_session() as s:
        repo = Repository(s)
        crop_id, sub_id, var_id, marker_id = _setup_base(repo)
        marker2 = repo.create("marker", name="旧标志物", name_en="Old")
        assoc_id = repo.create_marker_association(marker2, "variety", var_id)

        repo.update("association", assoc_id, {"notes": "备注1"})
        repo.delete("association", assoc_id)
        repo.create_marker_association(marker2, "variety", var_id, notes="重新建立")

        assert len(repo.get_marker_associations_by_entity("variety", var_id)) == 1
        assert len(repo.get_children("marker")) == 2
        assert len(repo.get_children("variety", sub_id)) == 1


def test_reset_db_should_backup_instead_of_silently_deleting_data():
    reset_db()
    with get_session() as s:
        repo = Repository(s)
        _setup_base(repo)

    original_size = DB_PATH.stat().st_size
    reset_db()

    assert DB_PATH.exists()
    backups = sorted(Path(DB_PATH.parent).glob("grainprint.duckdb.bak*"))
    assert backups, "reset_db 必须保留旧数据备份，不能直接清空"
    assert DB_PATH.stat().st_size > 0


def test_startup_backup_keeps_recoverable_copy():
    from grainprint.config import DATA_DIR
    latest = DATA_DIR / "backup" / "grainprint_latest.duckdb"
    if latest.exists():
        latest.unlink()
    reset_db()
    with get_session() as s:
        repo = Repository(s)
        _setup_base(repo)

    backup = _backup_on_startup()
    assert backup is not None and backup.exists()
    assert backup.stat().st_size > 0
    con = duckdb.connect(str(backup), read_only=True)
    try:
        assert con.execute("select count(*) from crops").fetchone()[0] >= 1
    finally:
        con.close()
