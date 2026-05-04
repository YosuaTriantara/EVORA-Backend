# Import Base dari session
from app.db.session import Base

# Modul A: Core & Identity
from app.models.user import User, EventUser  # Pastikan EventUser ada di sini

# Modul B: Event Configuration & Hierarchical Scoring
from app.models.event import (
    Event, 
    EventCategory, 
    AssessmentSection, 
    AssessmentGroup, 
    AssessmentItem, 
    Team
)

# Modul C: Operational & Scoring Data
from app.models.scoring import ScoreSheet, ScoreItem

# Modul D: Finance & Voting
from app.models.transaction import VotePackage, Transaction, VoteLog

# Membantu Alembic menemukan metadata dengan eksplisit
metadata = Base.metadata