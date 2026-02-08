import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.db import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    siren = Column(String, index=True, nullable=False)
    depth = Column(Integer, nullable=False, default=3)
    status = Column(String, nullable=False, default="queued")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    error = Column(Text, nullable=True)
    result_json = Column(JSON, nullable=True)

    artifacts = relationship("Artifact", back_populates="job")


class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    kind = Column(String, nullable=False)  # pdf | graph
    path = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    job = relationship("Job", back_populates="artifacts")


class Company(Base):
    __tablename__ = "companies"

    siren = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=True)
    last_seen = Column(DateTime, nullable=True)


class OwnershipLink(Base):
    __tablename__ = "ownership_links"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_siren = Column(String, nullable=False)
    child_siren = Column(String, nullable=False)
    pct = Column(String, nullable=True)
    source = Column(String, nullable=True)
    confidence = Column(Integer, nullable=True)
    as_of = Column(DateTime, nullable=True)
