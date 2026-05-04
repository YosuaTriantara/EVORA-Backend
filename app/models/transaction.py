import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, Float, Boolean, DateTime, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.sql import func
from app.db.session import Base


class UserVoteBalance(Base):
    """User vote balance per event"""
    __tablename__ = "user_vote_balances"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), primary_key=True)
    point_balance = Column(Integer, nullable=False, default=0)
    total_purchased = Column(Integer, nullable=False, default=0)
    total_spent = Column(Integer, nullable=False, default=0)
    last_purchase_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class VotePackage(Base):
    __tablename__ = "vote_packages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    price_idr = Column(Integer, nullable=False)  # Changed to Integer for consistency
    points_amount = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    transaction_type = Column(String)
    amount = Column(Numeric(12,2), nullable=False)
    status = Column(String, server_default="PENDING")
    payment_provider = Column(String)
    external_ref_id = Column(String)
    meta_data = Column("metadata", JSONB)
    paid_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # New columns for verification tracking
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_ip = Column(INET(), nullable=True)
    admin_note = Column(Text(), nullable=True)


class VoteTransaction(Base):
    """Transactions for purchasing vote points"""
    __tablename__ = "vote_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    package_id = Column(UUID(as_uuid=True), ForeignKey("vote_packages.id", ondelete="SET NULL"), nullable=True)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    points_amount = Column(Integer, nullable=False)
    amount_idr = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="PENDING")
    payment_provider = Column(String(50), nullable=True)
    external_ref_id = Column(String(255), nullable=True)
    payment_token = Column(String(255), nullable=True)
    redirect_url = Column(String(500), nullable=True)
    idempotency_key = Column(UUID(as_uuid=True), nullable=True, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text(), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Vote(Base):
    """Individual votes with idempotency support"""
    __tablename__ = "votes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("vote_candidates.id", ondelete="CASCADE"), nullable=False)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    points = Column(Integer, nullable=False)
    idempotency_key = Column(UUID(as_uuid=True), nullable=False, unique=True)
    ip_address = Column(INET(), nullable=True)
    user_agent = Column(Text(), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class VoteLog(Base):
    __tablename__ = "vote_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    points_spent = Column(Integer, nullable=False)
    ip_address = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class VoteCategory(Base):
    __tablename__ = "vote_categories"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"))
    name = Column(String) # misal: "Danpas Terbaik", "Kostum Terfavorit"
    description = Column(String)
    target_event_category_id = Column(UUID(as_uuid=True), ForeignKey("event_categories.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class VoteCandidate(Base):
    """Menghubungkan Tim ke Kategori Voting tertentu dengan Aset Visual khusus"""
    __tablename__ = "vote_candidates"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vote_category_id = Column(UUID(as_uuid=True), ForeignKey("vote_categories.id"))
    team_id = Column(UUID(as_uuid=True), ForeignKey("teams.id"))
    image_url = Column(String, nullable=True) 
    candidate_name = Column(String, nullable=True) 
    total_votes = Column(Integer, default=0, nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    last_vote_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
