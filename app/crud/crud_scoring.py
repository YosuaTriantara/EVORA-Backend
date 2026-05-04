from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.scoring import ScoreSheet, ScoreItem
from app.models.event import AssessmentItem
from app.schemas.scoring import ScoringSubmit
import uuid

def process_score(db: Session, *, payload: ScoringSubmit):
    # 1. Cek apakah Score Sheet sudah ada dan apakah sudah dikunci
    db_sheet = db.query(ScoreSheet).filter(
        ScoreSheet.team_id == payload.team_id,
        ScoreSheet.judge_id == payload.judge_id
    ).first()

    if db_sheet and db_sheet.is_locked:
        raise HTTPException(status_code=403, detail="Penilaian sudah dikunci dan tidak bisa diubah.")

    # 2. Jika belum ada, buat sheet baru
    if not db_sheet:
        db_sheet = ScoreSheet(
            id=uuid.uuid4(),
            team_id=payload.team_id,
            judge_id=payload.judge_id,
            total_score=0
        )
        db.add(db_sheet)
        db.flush() # Ambil ID sheet untuk relasi score_items

    total_calculated = 0

    # 3. Validasi setiap item nilai
    for item_entry in payload.items:
        # Ambil definisi item dari database untuk cek allowed_values
        assessment_def = db.query(AssessmentItem).filter(
            AssessmentItem.id == item_entry.item_id
        ).first()

        if not assessment_def:
            raise HTTPException(status_code=404, detail=f"Kriteria {item_entry.item_id} tidak ditemukan.")

        # LOGIKA 2.4: Validasi Nilai Diskrit
        # Karena allowed_values disimpan sebagai JSONB (List), kita cek keanggotaannya
        if item_entry.val not in assessment_def.allowed_values:
            raise HTTPException(
                status_code=400, 
                detail=f"Nilai {item_entry.val} tidak sah untuk {assessment_def.label}. Pilihan: {assessment_def.allowed_values}"
            )

        # 4. Simpan atau Update detail nilai per item (ScoreItem)
        db_item = db.query(ScoreItem).filter(
            ScoreItem.sheet_id == db_sheet.id,
            ScoreItem.assessment_item_id == item_entry.item_id
        ).first()

        if db_item:
            db_item.value = item_entry.val
        else:
            new_score_item = ScoreItem(
                id=uuid.uuid4(),
                sheet_id=db_sheet.id,
                assessment_item_id=item_entry.item_id,
                value=item_entry.val
            )
            db.add(new_score_item)
        
        total_calculated += item_entry.val

    # 5. Update total_score di ScoreSheet
    db_sheet.total_score = total_calculated
    db.commit()
    db.refresh(db_sheet)

    return {"status": "success", "total_score": total_calculated, "sheet_id": db_sheet.id}