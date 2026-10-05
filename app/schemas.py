from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, title="Документ")

    id: int = Field(title="Идентификатор", examples=[10])
    rubrics: list[str] = Field(title="Рубрики", examples=[["VK-1603736028819866"]])
    text: str = Field(title="Текст", examples=["Кот соседа каждое утро сидит у нас на балконе."])
    created_date: datetime = Field(title="Дата создания", examples=["2020-02-18T08:05:17"])


class ErrorOut(BaseModel):
    model_config = ConfigDict(title="Ошибка")

    detail: str = Field(title="Описание ошибки", examples=["Документ не найден"])


class HealthOut(BaseModel):
    model_config = ConfigDict(title="Состояние сервиса")

    status: str = Field(title="Статус", examples=["ok"])
