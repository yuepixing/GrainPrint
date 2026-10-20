"""检查关联数据是否有悬空引用"""
from grainprint.core.database import get_session
from grainprint.core.models import MarkerAssociation, Marker, Crop, Subspecies, Variety


def main():
    with get_session() as session:
        associations = session.query(MarkerAssociation).all()
        print(f"总关联数：{len(associations)}")

        broken = []
        for a in associations:
            marker = session.query(Marker).filter_by(id=a.marker_id).first()
            if not marker:
                broken.append(f"  关联 #{a.id}: 标志物 {a.marker_id} 不存在")
                continue

            entity = None
            if a.crop_id:
                entity = session.query(Crop).filter_by(id=a.crop_id).first()
                entity_label = f"crop({a.crop_id})"
            elif a.subspecies_id:
                entity = session.query(Subspecies).filter_by(id=a.subspecies_id).first()
                entity_label = f"subspecies({a.subspecies_id})"
            elif a.variety_id:
                entity = session.query(Variety).filter_by(id=a.variety_id).first()
                entity_label = f"variety({a.variety_id})"
            else:
                broken.append(f"  关联 #{a.id}: 没有实体引用（三个 id 都空）")
                continue

            if not entity:
                broken.append(
                    f"  关联 #{a.id}: 标志物 '{marker.name}' -> {entity_label} 实体不存在"
                )

        if broken:
            print(f"\n❌ 发现 {len(broken)} 条悬空关联：")
            for b in broken:
                print(b)
        else:
            print("\n✅ 所有关联都是有效的")


if __name__ == "__main__":
    main()