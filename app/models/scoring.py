import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, Float, Boolean, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db.session import Base

class ScoreSheet(Base):
    __tablename__ = "score_sheets"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"))
    judge_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    inputter_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    total_score = Column(Float, default=0)
    is_locked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ScoreItem(Base):
    __tablename__ = "score_items"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sheet_id = Column(UUID(as_uuid=True), ForeignKey("score_sheets.id", ondelete="CASCADE"))
    assessment_item_id = Column(UUID(as_uuid=True), ForeignKey("assessment_items.id"))
    value = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

