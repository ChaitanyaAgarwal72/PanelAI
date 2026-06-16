from pydantic import BaseModel, Field
from typing import List, Literal

class Concern(BaseModel):
    concern: str = Field(description="Description of the ethical, privacy, or methodological concern.")
    citation: str = Field(description="Exact source reference from the retrieved guidelines (e.g., 'Belmont Report - Informed Consent').")

class Modification(BaseModel):
    modification: str = Field(description="What must change in the proposal.")
    reason: str = Field(description="Why the change is needed, citing the specific source rule.")

class SpecialistReviewOutput(BaseModel):
    risk_level: Literal["Low", "Medium", "High"] = Field(description="The assigned risk level based on the evaluation.")
    concerns: List[Concern] = Field(description="A list of identified concerns. Empty if no concerns are found.")
    required_modifications: List[Modification] = Field(description="A list of required modifications. Empty if none are needed.")
