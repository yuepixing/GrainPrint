#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from grainprint.core.database import reset_db, get_session
from grainprint.core.repository import Repository


def create_sample_data():
    with get_session() as session:
        repo = Repository(session)

        # 创建标志物
        marker_ids = {
            "己醛":
            repo.create('marker',
                        name="己醛",
                        name_en="Hexanal",
                        structure_formula="CH₃(CH₂)₄CHO"),
            "4-甲基-3-戊烯-2-酮":
            repo.create('marker',
                        name="4-甲基-3-戊烯-2-酮",
                        name_en="4-Methyl-3-penten-2-one",
                        structure_formula="CH₃-C(O)-CH=C(CH₃)-CH₃"),
            "3-戊醇":
            repo.create('marker',
                        name="3-戊醇",
                        name_en="3-Pentanol",
                        structure_formula="CH₃CH₂CH(OH)CH₂CH₃")
        }

        # ========== 稻谷 ==========
        rice_id = repo.create('crop', name="稻谷", name_en="Rice")

        # 粳稻
        japonica_id = repo.create('subspecies',
                                  crop_id=rice_id,
                                  name="粳稻",
                                  name_en="Japonica Rice")

        # 粳稻品种
        ningjing84_id = repo.create('variety',
                                    subspecies_id=japonica_id,
                                    name="宁粳84",
                                    name_en="Ningjing 84")
        zhejing100_id = repo.create('variety',
                                    subspecies_id=japonica_id,
                                    name="浙粳100",
                                    name_en="Zhejing 100")

        # 粳稻标志物关联
        repo.create_marker_association(marker_id=marker_ids["己醛"],
                                       entity_type='subspecies',
                                       entity_id=japonica_id,
                                       source="劣变",
                                       screening_method="GC-IMS",
                                       metabolic_pathway="不饱和脂肪酸氧化")

        # 籼稻
        indica_id = repo.create('subspecies',
                                crop_id=rice_id,
                                name="籼稻",
                                name_en="Indica Rice")

        # 籼稻标志物关联
        repo.create_marker_association(
            marker_id=marker_ids["4-甲基-3-戊烯-2-酮"],
            entity_type='subspecies',
            entity_id=indica_id,
            source="霉变",
            screening_method="HS-SPME-GC-MS、GC-IMS",
            literature_source="https://doi.org/10.1016/j.foodcont.2025.111294")

        repo.create_marker_association(
            marker_id=marker_ids["3-戊醇"],
            entity_type='subspecies',
            entity_id=indica_id,
            source="霉变",
            screening_method="HS-SPME-GC-MS、GC-IMS",
            literature_source="https://doi.org/10.1016/j.foodcont.2025.111294")

        # 杂交稻
        hybrid_id = repo.create('subspecies',
                                crop_id=rice_id,
                                name="杂交稻",
                                name_en="Hybrid Rice")

        # ========== 小麦 ==========
        wheat_id = repo.create('crop', name="小麦", name_en="Wheat")

        # 小麦亚种
        white_wheat_id = repo.create('subspecies',
                                     crop_id=wheat_id,
                                     name="白小麦",
                                     name_en="White Wheat")
        red_wheat_id = repo.create('subspecies',
                                   crop_id=wheat_id,
                                   name="红小麦",
                                   name_en="Red Wheat")
        mixed_wheat_id = repo.create('subspecies',
                                     crop_id=wheat_id,
                                     name="混合小麦",
                                     name_en="Mixed Wheat")

        # ========== 大豆 ==========
        soybean_id = repo.create('crop', name="大豆", name_en="Soybean")

        # 大豆亚种
        normal_soybean_id = repo.create('subspecies',
                                        crop_id=soybean_id,
                                        name="普通大豆",
                                        name_en="Normal Soybean")
        high_oil_soybean_id = repo.create('subspecies',
                                          crop_id=soybean_id,
                                          name="高油大豆",
                                          name_en="High Oil Soybean")

        # ========== 玉米 ==========
        corn_id = repo.create('crop', name="玉米", name_en="Corn")

        # 玉米亚种
        yellow_corn_id = repo.create('subspecies',
                                     crop_id=corn_id,
                                     name="黄玉米",
                                     name_en="Yellow Corn")
        white_corn_id = repo.create('subspecies',
                                    crop_id=corn_id,
                                    name="白玉米",
                                    name_en="White Corn")
        mixed_corn_id = repo.create('subspecies',
                                    crop_id=corn_id,
                                    name="混合玉米",
                                    name_en="Mixed Corn")

        print("✅ 示例数据创建成功")


def test_queries():
    with get_session() as session:
        repo = Repository(session)

        print("\n📋 测试搜索功能:")

        # 测试搜索作物
        results = repo.search("稻")
        print(f"搜索'稻': 找到 {len(results)} 条结果")
        for r in results[:5]:  # 只显示前5个
            print(f"  - {r.type}: {' > '.join(r.path)}")

        # 测试搜索品种
        results = repo.search("粳")
        print(f"\n搜索'粳': 找到 {len(results)} 条结果")
        for r in results:
            print(f"  - {r.type}: {' > '.join(r.path)}")

        # 测试搜索标志物
        results = repo.search("醛")
        print(f"\n搜索'醛': 找到 {len(results)} 条结果")
        for r in results:
            print(f"  - {r.type}: {' > '.join(r.path)}")

        print("\n📊 测试详情查询:")

        # 获取粳稻详情（测试标志物）
        results = repo.search("粳稻")
        subspecies_result = next(
            (r for r in results if r.type == 'subspecies' and r.name == "粳稻"),
            None)

        if subspecies_result:
            detail = repo.get_detail("subspecies", subspecies_result.id)
            print(f"\n{detail.name} 的信息:")
            print(f"  英文名: {detail.name_en}")
            print(f"  品种数: {len(detail.children)}")
            print(f"  标志物:")
            for marker in detail.markers:
                print(
                    f"    - {marker.name} ({marker.formula}) - {marker.level}")

        # 获取作物概览
        print("\n📈 数据库概览:")
        crops = repo.get_children('crop')
        for crop in crops:
            print(f"\n{crop.name} ({crop.name_en})")
            subspecies_list = repo.get_children('subspecies',
                                                parent_id=crop.id)
            for sub in subspecies_list:
                varieties = repo.get_children('variety', parent_id=sub.id)
                print(f"  └─ {sub.name} ({len(varieties)} 个品种)")


if __name__ == "__main__":
    print("🚀 初始化 GrainPrint 数据库...")

    # 重置数据库（清空并重建）
    reset_db()
    print("✅ 数据库表创建成功")

    # 创建示例数据
    create_sample_data()

    # 测试查询
    test_queries()

    print("\n✨ 初始化完成！")
