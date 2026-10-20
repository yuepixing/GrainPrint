#!/usr/bin/env python3
from grainprint.core.database import get_session, reset_db
from grainprint.core.repository import Repository


def test_crud_operations():
    print("🧪 测试 Repository 增删改功能...")

    reset_db()
    print("✅ 数据库已重置")

    with get_session() as session:
        repo = Repository(session)

        print("\n📝 测试创建功能:")
        crop_id = repo.create('crop',
                              name="测试作物",
                              name_en="Test Crop",
                              description="这是测试用的作物")
        print(f"  ✅ 创建作物: ID={crop_id}")

        subspecies_id = repo.create('subspecies',
                                    crop_id=crop_id,
                                    name="测试亚种",
                                    name_en="Test Subspecies",
                                    description="测试亚种描述")
        print(f"  ✅ 创建亚种: ID={subspecies_id}")

        variety_id = repo.create('variety',
                                 subspecies_id=subspecies_id,
                                 name="测试品种",
                                 name_en="Test Variety")
        print(f"  ✅ 创建品种: ID={variety_id}")

        marker_id = repo.create('marker',
                                name="测试标志物",
                                name_en="Test Marker",
                                structure_formula="C₆H₁₂O₆")
        print(f"  ✅ 创建标志物: ID={marker_id}")

        assoc_id = repo.create_marker_association(marker_id=marker_id,
                                                  entity_type='subspecies',
                                                  entity_id=subspecies_id,
                                                  source="测试来源",
                                                  screening_method="测试方法",
                                                  metabolic_pathway="测试代谢途径")
        print(f"  ✅ 创建标志物关联: ID={assoc_id}")

        print("\n✏️ 测试更新功能:")
        success = repo.update('crop', crop_id, {'description': '更新后的描述'})
        print(f"  ✅ 更新作物描述: {success}")

        success = repo.update('marker', marker_id,
                              {'structure_formula': 'H₂O'})
        print(f"  ✅ 更新标志物结构式: {success}")

        print("\n🔍 测试查询功能:")
        crops = repo.get_children('crop')
        print(f"  作物总数: {len(crops)}")

        subspecies_list = repo.get_children('subspecies', parent_id=crop_id)
        print(f"  测试作物的亚种数: {len(subspecies_list)}")

        varieties = repo.get_children('variety', parent_id=subspecies_id)
        print(f"  测试亚种的品种数: {len(varieties)}")

        markers = repo.get_children('marker')
        print(f"  标志物总数: {len(markers)}")

        associations = repo.get_marker_associations_by_entity(
            'subspecies', subspecies_id)
        print(f"  测试亚种的标志物关联数: {len(associations)}")

        print("\n🔎 测试搜索功能:")
        results = repo.search("测试")
        print(f"  搜索'测试': 找到 {len(results)} 条结果")
        for r in results[:3]:
            print(f"    - {r.type}: {' > '.join(r.path)}")

        print("\n🔍 测试按类型搜索:")
        results = repo.search("测试", entity_type="marker")
        print(f"  搜索'测试'(仅标志物): 找到 {len(results)} 条结果")
        for r in results:
            print(f"    - {r.type}: {' > '.join(r.path)}")

        print("\n📊 测试统计功能:")
        stats = repo.get_stats()
        print(f"  总计: {stats['total']}")
        print(f"  标志物统计: {stats['markers']}")

        print("\n📋 测试详情查询:")
        detail = repo.get_detail('subspecies', subspecies_id)
        print(f"  {detail.name}:")
        print(f"    路径: {' > '.join(detail.path)}")
        print(f"    标志物数: {len(detail.markers)}")
        print(f"    子项数: {len(detail.children)}")

        print("\n🗑️ 测试删除功能:")
        success = repo.delete('association', assoc_id)
        print(f"  ✅ 删除标志物关联: {success}")

        success = repo.delete('variety', variety_id)
        print(f"  ✅ 删除品种: {success}")

        success = repo.delete('subspecies', subspecies_id)
        print(f"  ✅ 删除亚种: {success}")

        success = repo.delete('crop', crop_id)
        print(f"  ✅ 删除作物: {success}")

        success = repo.delete('marker', marker_id)
        print(f"  ✅ 删除标志物: {success}")

        print("\n✅ 验证删除结果:")
        crops = repo.get_children('crop')
        markers = repo.get_children('marker')
        print(f"  剩余作物数: {len(crops)}")
        print(f"  剩余标志物数: {len(markers)}")


def test_edge_cases():
    print("\n\n🔧 测试边缘情况:")

    with get_session() as session:
        repo = Repository(session)

        success = repo.update('crop', 99999, {'name': '不存在'})
        print(f"  更新不存在的作物: {success}")

        success = repo.delete('marker', 99999)
        print(f"  删除不存在的标志物: {success}")

        success = repo.update('invalid_type', 1, {'name': '测试'})
        print(f"  更新无效类型: {success}")

        success = repo.delete('invalid_type', 1)
        print(f"  删除无效类型: {success}")


def test_complex_scenario():
    print("\n\n🎯 测试复杂场景:")

    with get_session() as session:
        repo = Repository(session)

        rice_id = repo.create('crop', name="水稻", name_en="Rice")
        japonica_id = repo.create('subspecies',
                                  crop_id=rice_id,
                                  name="粳稻",
                                  name_en="Japonica")
        indica_id = repo.create('subspecies',
                                crop_id=rice_id,
                                name="籼稻",
                                name_en="Indica")

        variety1_id = repo.create('variety',
                                  subspecies_id=japonica_id,
                                  name="越光",
                                  name_en="Koshihikari")
        variety2_id = repo.create('variety',
                                  subspecies_id=japonica_id,
                                  name="秋田小町",
                                  name_en="Akitakomachi")
        variety3_id = repo.create('variety',
                                  subspecies_id=indica_id,
                                  name="泰国香米",
                                  name_en="Thai Jasmine")

        marker1_id = repo.create('marker',
                                 name="香气物质A",
                                 name_en="Aroma A",
                                 structure_formula="C₈H₈O")
        marker2_id = repo.create('marker',
                                 name="香气物质B",
                                 name_en="Aroma B",
                                 structure_formula="C₇H₆O₂")

        repo.create_marker_association(marker1_id,
                                       'crop',
                                       rice_id,
                                       source="作物层级")
        repo.create_marker_association(marker2_id,
                                       'subspecies',
                                       japonica_id,
                                       source="亚种层级")
        repo.create_marker_association(marker1_id,
                                       'variety',
                                       variety3_id,
                                       source="品种层级")

        print("  测试标志物继承:")
        detail = repo.get_detail('variety', variety3_id)
        print(f"    {detail.name} 的标志物:")
        for marker in detail.markers:
            print(f"      - {marker.name}: {marker.level}")

        print("\n  测试按类型搜索:")
        results = repo.search("稻", entity_type="subspecies")
        print(f"    搜索'稻'(仅亚种): 找到 {len(results)} 条结果")
        for r in results:
            print(f"      - {r.name}")

        print("\n  测试完整统计:")
        stats = repo.get_stats()
        print(f"    数据总量: 作物={stats['total']['crops']}, "
              f"亚种={stats['total']['subspecies']}, "
              f"品种={stats['total']['varieties']}")
        print(f"    标志物关联分布: {stats['markers']['associations_by_level']}")

        print("\n  测试级联删除:")
        crops_before = len(repo.get_children('crop'))
        success = repo.delete('crop', rice_id)
        crops_after = len(repo.get_children('crop'))
        print(f"    删除水稻: {success}")
        print(f"    作物数量: {crops_before} → {crops_after}")

        markers = repo.get_children('marker')
        print(f"    标志物数量: {len(markers)}")


if __name__ == "__main__":
    test_crud_operations()
    test_edge_cases()
    test_complex_scenario()

    print("\n\n✨ 所有测试完成！")
