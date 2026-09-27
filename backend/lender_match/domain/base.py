from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
