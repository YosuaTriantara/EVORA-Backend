import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, Date, Float, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class Event(Base):
    __tablename__ = "events"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    organizer = Column(String, nullable=False)
    profil_url = Column(String, nullable=True)
    location = Column(String, nullable=True)
    theme_setting = Column(JSONB, nullable=True, default={})
    content_data = Column(JSONB, nullable=True, default={})
    event_date_start = Column(Date, nullable=False)
    event_date_end = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    is_pg_enabled = Column(Boolean, default=False)
    is_voting_enabled = Column(Boolean, default=False)
    categories = relationship("EventCategory", back_populates="event", cascade="all, delete-orphan")

class EventCategory(Base):
    __tablename__ = "event_categories"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    max_quota = Column(Integer, nullable=False, default=0)
    registration_fee = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    event = relationship("Event", back_populates="categories")
    team = relationship("Team", back_populates="category")

class AssessmentSection(Base):
    __tablename__ = "assessment_sections"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey("event_categories.id", ondelete="CASCADE"))
    title = Column(String, nullable=False)
    weight_percentage = Column(Integer, nullable=False)
    sort_order = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class AssessmentGroup(Base):
    __tablename__ = "assessment_groups"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    section_id = Column(UUID(as_uuid=True), ForeignKey("assessment_sections.id", ondelete="CASCADE"))
    title = Column(String, nullable=False)
    sort_order = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class AssessmentItem(Base):
    __tablename__ = "assessment_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("assessment_groups.id", ondelete="CASCADE"))
    label = Column(String, nullable=False)
    display_number = Column(Integer)
    allowed_values = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Team(Base):
    __tablename__ = "teams"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"))
    category_id = Column(UUID(as_uuid=True), ForeignKey("event_categories.id", ondelete="CASCADE"))
    official_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    name = Column(String, nullable=False)
    institution = Column(String, nullable=True)
    lot_number = Column(Integer)
    status = Column(String, server_default="PENDING_PAYMENT")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    category = relationship("EventCategory", back_populates="team")
    members = relationship("TeamMember", back_populates="team")
    
class TeamMember(Base):
    __tablename__ = "team_members"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    identity_number = Column(String, nullable=True) 
    role = Column(String, nullable=False) 
    extra_data = Column(JSONB, nullable=True) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    team = relationship("Team", back_populates="members")