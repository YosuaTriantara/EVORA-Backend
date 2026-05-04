# Implementation Guide: "Get My Managed Events" Endpoint

## Overview
This document outlines the strategy for implementing the new `/api/v1/events/my-managed` endpoint requested by the frontend team, strictly utilizing existing schemas and models in the backend codebase to prevent unnecessary redundancy.

## 1. Requirement Analysis
*   **Endpoint:** `GET /api/v1/events/my-managed`
*   **Target:** Authenticated users (Requires Bearer token).
*   **Output:** Array of objects containing the user's `role`, `meta_data`, and a concise `event` preview object.
*   **Condition:** Fetches active events (`is_active=True`) where the logged-in user has an entry in the `event_users` table.

## 2. Utilizing Existing Codebase (Avoiding Redundancy)
Based on an analysis of the existing codebase, we will reuse the following existing structures:
*   **Model (`app/models/user.py`):** The `EventUser` model already exists and contains the exact fields we need (`role`, `meta_data`, `user_id`, `event_id`).
*   **Model (`app/models/event.py`):** The `Event` model already has the `is_active` boolean flag.
*   **Schema (`app/schemas/public.py`):** There is an existing `EventPreview` schema designed specifically as a "lightweight event card". We will reuse this schema for the `event` payload in our response instead of creating a new one. It naturally prevents exposing heavy fields like `content_data` and `theme_setting`.

## 3. Data Flow & Schema Definition
To bridge the existing `EventUser` database model with the requested JSON response, we only need to define the parent response schema.

**In `app/schemas/events.py` (or a dedicated response schema file):**
```python
from app.schemas.public import EventPreview

class ManagedEventResponse(BaseModel):
    role: str
    meta_data: Optional[Dict[str, Any]] = None
    event: EventPreview

    class Config:
        from_attributes = True
```
*By using `EventPreview`, we satisfy the frontend's request for a "format ringkas" without creating duplicate event schemas.*

## 4. Execution Plan (Step-by-Step)

### Phase 1: Service Layer Update (`app/services/events.py`)
Instead of putting raw queries in the route, we will add a clean service function. This function will use SQLAlchemy's eager loading to prevent the N+1 query problem when fetching the related `Event` for each `EventUser` assignment.

1.  **Add `get_user_managed_events`:**
    ```python
    from sqlalchemy.orm import Session, joinedload
    from app.models.user import EventUser
    from app.models.event import Event
    from uuid import UUID

    def get_user_managed_events(db: Session, user_id: UUID):
        return (
            db.query(EventUser)
            .join(Event, EventUser.event_id == Event.id)
            .options(joinedload(EventUser.event))
            .filter(
                EventUser.user_id == user_id,
                Event.is_active == True
            )
            .all()
        )
    ```

### Phase 2: Router Implementation (`app/api/v1/endpoints/events.py`)
1.  **Inject the Endpoint:** We will add the new route to the existing events router.
    ```python
    from app.schemas.events import ManagedEventResponse # Adjust import based on where it's placed
    from app.api import deps
    from app.models.user import User
    from app.services import events as event_service

    @router.get("/my-managed", response_model=List[ManagedEventResponse])
    def read_my_managed_events(
        db: Session = Depends(deps.get_db),
        current_user: User = Depends(deps.get_current_active_user)
    ):
        """
        Get all active events where the current logged-in user is assigned a specific role
        (e.g., ORGANIZER, JUDGE, TABULATOR).
        """
        managed_events = event_service.get_user_managed_events(db, user_id=current_user.id)
        return managed_events
    ```

### Phase 3: Security & Validation
*   **Authentication:** The dependency `Depends(deps.get_current_active_user)` ensures the route is completely protected.
*   **Authorization:** The `user_id=current_user.id` filter in the query ensures users can *never* query another user's assigned events.
*   **Data Validation:** Pydantic's `response_model` combined with `from_attributes = True` will automatically serialize the SQLAlchemy `EventUser` object into the precise JSON structure the frontend requested.

## Conclusion
This strategy ensures zero redundancy by capitalizing on existing schemas (`EventPreview`) and models (`EventUser`, `Event`), while delivering an optimized, secure, and easily testable endpoint.