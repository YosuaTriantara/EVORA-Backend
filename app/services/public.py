from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.event import Event, Team
from app.models.transaction import VoteCategory, VoteCandidate
from datetime import datetime

class PublicService:
    @staticmethod
    def get_event_landing_page(db: Session, slug: str):
        # 1. Ambil Data Event Utama
        event = db.query(Event).filter(Event.slug == slug, Event.is_active == True).first()
        if not event:
            return None

        # 2. Logic: Status Kuota Pendaftaran
        categories_data = []
        for cat in event.categories:
            occupied = db.query(func.count(Team.id)).filter(
                Team.category_id == cat.id,
                Team.status.in_(["REGISTERED", "PENDING_PAYMENT", "PENDING_VERIFICATION"])
            ).scalar()
            
            categories_data.append({
                "id": cat.id,
                "name": cat.name,
                "fee": cat.registration_fee,
                "max_quota": cat.max_quota,
                "available_slots": max(0, cat.max_quota - occupied),
                "is_full": occupied >= cat.max_quota
            })

        # 3. Logic: Status & Data Voting
        now = datetime.now()
        voting_config = event.content_data.get("voting_settings", {})
        start_date = datetime.fromisoformat(voting_config.get("start_date")) if voting_config.get("start_date") else None
        end_date = datetime.fromisoformat(voting_config.get("end_date")) if voting_config.get("end_date") else None
        # Tentukan Fase Voting
        voting_status = "DISABLED"
        if event.content_data.get("is_voting_enabled"):
            if not start_date or now < start_date:
                voting_status = "PREPARATION"
            elif now >= start_date and now <= end_date:
                voting_status = "LIVE"
            elif now > end_date:
                voting_status = "CLOSED"

        # 4. Ambil Kategori Voting & Kandidat
        vote_categories = db.query(VoteCategory).filter(VoteCategory.event_id == event.id).all()
        voting_modules = []
        for v_cat in vote_categories:
            candidates = db.query(VoteCandidate).filter(VoteCandidate.vote_category_id == v_cat.id).all()
            voting_modules.append({
                "category_name": v_cat.name,
                "candidates": [
                    {
                        "team_name": c.team.name,
                        "candidate_name": c.candidate_name,
                        "image_url": c.image_url,
                        "current_votes": c.total_votes if voting_config.get("show_realtime") else None
                    } for c in candidates
                ]
            })

        return {
            "event": event,
            "registration": {
                "is_open": event.content_data.get("is_registration_open", True),
                "categories": categories_data
            },
            "voting": {
                "status": voting_status,
                "start_at": start_date,
                "data": voting_modules
            }
        }
        
        # app/services/public_service.py

    @staticmethod
    def get_all_events_preview(db: Session):
        """
        Hanya mengambil data untuk kartu katalog. 
        Sangat ringan karena tidak menarik data Team atau Candidate.
        """
        events = db.query(Event).filter(Event.is_active == True).all()
        
        result = []
        for event in events:
            result.append({
                "id": event.id,
                "title": event.title,
                "slug": event.slug,
                "organizer": event.organizer,
                "profil_url": event.profil_url,
                "event_date_start": event.event_date_start,
                "event_date_end": event.event_date_end,
                "banner_url": event.profil_url,
                "is_registration_open": event.is_active,
                "is_voting_live": event.is_voting_enabled,
                "location" : event.location
            })
        return result