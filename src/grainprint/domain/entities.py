from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from enum import StrEnum


class EntityType(StrEnum):
    CROP = "crop"
    SUBSPECIES = "subspecies"
    VARIETY = "variety"
    MARKER = "marker"
    ASSOCIATION = "association"


class BaseEntity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    name: str = Field(..., min_length=1, max_length=100, description="名称")
    name_en: Optional[str] = Field(None, max_length=200, description="英文名")


class CropCreate(BaseEntity):
    description: Optional[str] = Field(None, description="描述")


class CropUpdate(BaseModel):
    name: Optional[str] = Field(None,
                                min_length=1,
                                max_length=100,
                                description="名称")
    name_en: Optional[str] = Field(None, max_length=200, description="英文名")
    description: Optional[str] = Field(None, description="描述")


class SubspeciesCreate(BaseEntity):
    crop_id: int = Field(..., description="所属粮食ID")
    description: Optional[str] = Field(None, description="描述")


class SubspeciesUpdate(BaseModel):
    name: Optional[str] = Field(None,
                                min_length=1,
                                max_length=100,
                                description="名称")
    name_en: Optional[str] = Field(None, max_length=200, description="英文名")
    description: Optional[str] = Field(None, description="描述")


class VarietyCreate(BaseEntity):
    subspecies_id: int = Field(..., description="所属品类ID")


class VarietyUpdate(BaseModel):
    name: Optional[str] = Field(None,
                                min_length=1,
                                max_length=100,
                                description="名称")
    name_en: Optional[str] = Field(None, max_length=200, description="英文名")


class MarkerCreate(BaseEntity):
    structure_formula: Optional[str] = Field(None, max_length=200, description="结构式")

class MarkerUpdate(BaseModel):
    name: Optional[str] = Field(None,
                                min_length=1,
                                max_length=100,
                                description="名称")
    name_en: Optional[str] = Field(None, max_length=200, description="英文名")
    structure_formula: Optional[str] = Field(None,
                                             max_length=200,
                                             description="结构式")


class MarkerAssociationCreate(BaseModel):
    marker_id: int = Field(..., description="标志物ID")
    entity_type: EntityType = Field(..., description="关联实体类型")
    entity_id: int = Field(..., description="关联实体ID")
    source: Optional[str] = Field(None, max_length=200, description="来源")
    screening_method: Optional[str] = Field(None,
                                            max_length=200,
                                            description="筛选方法")
    metabolic_pathway: Optional[str] = Field(None, description="代谢途径")
    literature_source: Optional[str] = Field(None, description="文献来源")
    notes: Optional[str] = Field(None, description="备注")

class MarkerAssociationUpdate(BaseModel):
    source: Optional[str] = Field(None, max_length=200, description="来源")
    screening_method: Optional[str] = Field(None, max_length=200, description="筛选方法")
    metabolic_pathway: Optional[str] = Field(None, description="代谢途径")
    literature_source: Optional[str] = Field(None, description="文献来源")
    notes: Optional[str] = Field(None, description="备注")

class DeleteConfirmation(BaseModel):
    entity_type: EntityType
    entity_id: int
    entity_name: str
    impact: dict[str, int] = Field(default_factory=dict)

    @property
    def warning_message(self) -> str:
        type_names = {
            EntityType.CROP: "粮食",
            EntityType.SUBSPECIES: "品类",
            EntityType.VARIETY: "品种",
            EntityType.MARKER: "标志物",
            EntityType.ASSOCIATION: "标志物关联"
        }

        msg = f"确定要删除这个{type_names.get(self.entity_type, '实体')}吗？"

        if self.impact:
            msg += "\n\n将同时删除："
            if subspecies := self.impact.get('subspecies'):
                msg += f"\n• {subspecies} 个品类"
            if varieties := self.impact.get('varieties'):
                msg += f"\n• {varieties} 个品种"
            if associations := self.impact.get('associations'):
                msg += f"\n• {associations} 个标志物关联"

        msg += "\n\n删除后将无法恢复！"
        return msg
