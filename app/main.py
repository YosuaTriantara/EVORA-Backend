from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router

tags_metadata = [
    {
        "name": "Auth",
        "description": "User registration, login, and profile retrieval.",
    },
    {
        "name": "Events",
        "description": "Public-facing event operations for organizers (create, read, customise).",
    },
    {
        "name": "Registration",
        "description": "Team registration, payment proof upload, member management, and organizer verification.",
    },
    {
        "name": "Scoring",
        "description": "Judge score submission with discrete-value validation.",
    },
    {
        "name": "Voting",
        "description": "Vote casting using point balance.",
    },
    {
        "name": "Public",
        "description": "Unauthenticated endpoints for landing pages and event catalogue.",
    },
    # ------------------------------------------------------------------
    # SuperAdmin groups
    # ------------------------------------------------------------------
    {
        "name": "SuperAdmin - Dashboard",
        "description": "Platform-wide aggregate statistics for the SuperAdmin control panel.",
    },
    {
        "name": "SuperAdmin - Users",
        "description": (
            "Full CRUD over platform user accounts. "
            "Allows creating accounts with explicit roles, updating profile/status, "
            "and soft-deleting users."
        ),
    },
    {
        "name": "SuperAdmin - Events",
        "description": (
            "Full lifecycle management of events including creation, update, "
            "soft-delete, and feature toggles (Payment Gateway, Voting, Active status)."
        ),
    },
    {
        "name": "SuperAdmin - Event Staff",
        "description": (
            "Assign and remove user roles (ORGANIZER, JUDGE, TABULATOR, OFFICIAL_TEAM) "
            "on specific events."
        ),
    },
    {
        "name": "SuperAdmin - Categories",
        "description": (
            "Manage competition categories per event: create, update quota/fee, "
            "and delete (blocked when active teams exist)."
        ),
    },
    {
        "name": "SuperAdmin - Assessment Schema",
        "description": (
            "Upload and retrieve the hierarchical assessment schema "
            "(Sections → Groups → Items) used by judges during scoring. "
            "Uploading replaces the existing schema for the target category."
        ),
    },
    {
        "name": "SuperAdmin - Teams",
        "description": (
            "Full admin control over teams: list, view details, override status, "
            "assign lot numbers, delete, and manage team members."
        ),
    },
    {
        "name": "SuperAdmin - Transactions",
        "description": (
            "View and verify payment transactions. "
            "Approving a transaction marks the team as REGISTERED; "
            "rejecting sets it to CANCELLED."
        ),
    },
    {
        "name": "SuperAdmin - Vote Packages",
        "description": "CRUD for purchasable voting-point packages (name, price, points amount).",
    },
    {
        "name": "SuperAdmin - Vote Categories",
        "description": (
            "Create and manage voting categories per event "
            "(e.g. 'Danpas Terbaik', 'Kostum Terfavorit'). "
            "Can be scoped to a specific competition category."
        ),
    },
    {
        "name": "SuperAdmin - Vote Candidates",
        "description": (
            "Register teams as voting candidates within a vote category, "
            "and manage their display name and image URL."
        ),
    },
    {
        "name": "SuperAdmin - Scoring",
        "description": (
            "Admin view of all score sheets per event/team, "
            "plus lock/unlock controls to finalise judge scores."
        ),
    },
    {
        "name": "SuperAdmin - Rankings",
        "description": (
            "Compute and retrieve final ranked standings per competition category. "
            "Only locked score sheets are included in the calculation."
        ),
    },
]

app = FastAPI(
    title="EVORA SaaS API",
    description=(
        "Backend for the **EVORA** Event Management & Tiered Scoring Platform.\n\n"
        "## Authentication\n"
        "All protected endpoints require a **Bearer JWT** token obtained from `POST /api/v1/auth/login`.\n\n"
        "## Role Hierarchy\n"
        "| Role | Scope |\n"
        "|------|-------|\n"
        "| `SUPER_ADMIN` | Full platform access including all `/superadmin/*` routes |\n"
        "| `USER` | Self-service: register teams, cast votes, view own data |\n"
        "| `ORGANIZER` | Manage a specific event's settings and verify registrations |\n"
        "| `JUDGE` | Submit scores for assigned teams |\n"
        "| `TABULATOR` | Input scores on behalf of a judge |\n"
        "| `OFFICIAL_TEAM` | Manage own team's members and upload payment proof |\n"
    ),
    version="1.0.0",
    openapi_tags=tags_metadata,
    contact={
        "name": "EVORA Engineering",
        "email": "dev@evora.id",
    },
    license_info={
        "name": "Proprietary",
    },
)

origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "Welcome to EVORA API",
        "docs": "/docs",
        "redoc": "/redoc",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}
