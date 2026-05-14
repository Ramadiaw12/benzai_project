#Stécy

from typing import Annotated, TypedDict, List, Optional, Any
from langchain_core.messages import BaseMessage
import operator

def merge_lists(left: List[Any], right: List[Any]) -> List[Any]:
    if not left: left = []
    if not right: right = []
    return list(set(left + right))

class PatientData(TypedDict, total=False):
    age: Optional[int]
    gender: Optional[str]
    medical_history: List[str]
    current_medications: List[str]

class MedicalState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    patient_id: str
    patient_info: PatientData 
    next_agent: str                                
    current_question_index: int
    is_diagnosis_complete: bool
    extracted_symptoms: Annotated[List[str], merge_lists] 
    requires_physician_review: bool
    physician_validation: Optional[bool]
    physician_notes: Optional[str]
    errors: Annotated[List[str], operator.add] 
    diagnostic_summary: Optional[str]
    interim_care: Optional[str]    
