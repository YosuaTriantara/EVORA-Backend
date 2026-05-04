from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.user import User


def search_users(
    db: Session,
    query: str,
    limit: int = 10,
    exclude_roles: Optional[List[str]] = None
):
    """
    Search users by email or full_name.
    
    **Auth:** Required
    **Permission:** ORGANIZER (limited search only)
    
    **Parameters:**
    - `query`: Search query (email or full_name)
    - `limit`: Max results (default: 10, max: 20)
    - `exclude_roles`: List of roles to exclude (default: excludes SUPER_ADMIN)
    
    **Returns:**
    - Limited fields: id, email, full_name only
    - Only users with role USER (not SUPER_ADMIN)
    """
    # Validate limit
    if limit > 20:
        limit = 20
    if limit < 1:
        limit = 10

    # Default exclude SUPER_ADMIN
    if exclude_roles is None:
        exclude_roles = ["SUPER_ADMIN"]

    # Build query
    search_filter = or_(
        User.email.ilike(f"%{query}%"),
        User.full_name.ilike(f"%{query}%")
    )

    # Exclude certain roles
    role_filter = User.role.notin_(exclude_roles) if exclude_roles else True

    users = (
        db.query(User)
        .filter(search_filter)
        .filter(role_filter)
        .limit(limit)
        .all()
    )

    # Format response with limited fields
    result = []
    for user in users:
        result.append({
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
        })

    return {
        "total": len(result),
        "data": result,
    }
