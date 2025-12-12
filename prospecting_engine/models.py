from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Gatekeeper:
    name: str
    title: str
    email: Optional[str] = None
    phone: Optional[str] = None
    bio_url: Optional[str] = None
    is_thought_leader: bool = False
    wom_evidence: Optional[str] = None
    seniority_level: Optional[str] = None
    years_at_institution: Optional[str] = None

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Gatekeeper":
        return Gatekeeper(
            name=str(data.get("name", "")),
            title=str(data.get("title", "")),
            email=data.get("email"),
            phone=data.get("phone"),
            bio_url=data.get("bio_url"),
            is_thought_leader=bool(data.get("is_thought_leader", False)),
            wom_evidence=data.get("wom_evidence"),
            seniority_level=data.get("seniority_level"),
            years_at_institution=data.get("years_at_institution"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "title": self.title,
            "email": self.email,
            "phone": self.phone,
            "bio_url": self.bio_url,
            "is_thought_leader": self.is_thought_leader,
            "wom_evidence": self.wom_evidence,
            "seniority_level": self.seniority_level,
            "years_at_institution": self.years_at_institution,
        }


@dataclass
class Clinic:
    clinic_name: str
    key_practitioners: Optional[str] = None
    specialization: Optional[str] = None
    athletic_affiliations: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Clinic":
        return Clinic(
            clinic_name=str(data.get("clinic_name", data.get("name", "Unknown"))),
            key_practitioners=data.get("key_practitioners") or data.get("practitioners"),
            specialization=data.get("specialization"),
            athletic_affiliations=data.get("athletic_affiliations"),
            website=data.get("website") or data.get("url"),
            location=data.get("location"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clinic_name": self.clinic_name,
            "key_practitioners": self.key_practitioners,
            "specialization": self.specialization,
            "athletic_affiliations": self.athletic_affiliations,
            "website": self.website,
            "location": self.location,
        }


@dataclass
class Dossier:
    university: str
    athletics_domain: Optional[str] = None
    gatekeepers: List[Gatekeeper] = field(default_factory=list)
    local_ecosystem: List[Clinic] = field(default_factory=list)
    research_notes: Optional[str] = None

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Dossier":
        return Dossier(
            university=str(data.get("university", "")),
            athletics_domain=data.get("athletics_domain"),
            gatekeepers=[Gatekeeper.from_dict(x) for x in data.get("gatekeepers", [])],
            local_ecosystem=[Clinic.from_dict(x) for x in data.get("local_ecosystem", [])],
            research_notes=data.get("research_notes"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "university": self.university,
            "athletics_domain": self.athletics_domain,
            "gatekeepers": [g.to_dict() for g in self.gatekeepers],
            "local_ecosystem": [c.to_dict() for c in self.local_ecosystem],
            "research_notes": self.research_notes,
        }

{
  "cells": [],
  "metadata": {
    "language_info": {
      "name": "python"
    }
  },
  "nbformat": 4,
  "nbformat_minor": 2
}