from pydantic import BaseModel, ConfigDict


class SearchResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    path: list[str]
    association_info: str | None = None


class MarkerInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    formula: str | None
    source: str | None
    level: str
    screening_method: str | None = None
    metabolic_pathway: str | None = None
    literature_source: str | None = None
    notes: str | None = None


class EntityDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    name_en: str | None
    type: str
    path: list[str]
    markers: list[MarkerInfo]
    children: list[SearchResult]
