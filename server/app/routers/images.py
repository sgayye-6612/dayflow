"""Vision-board pictures and voice-note recordings (stored as data URLs)."""
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Image, User
from ..schemas import ImageIn

router = APIRouter(prefix="/api/images", tags=["Images"])

KEY = Path(..., min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")


@router.put("/{key}", status_code=status.HTTP_204_NO_CONTENT)
def put_image(body: ImageIn, key: str = KEY, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.src.startswith("data:"):
        raise HTTPException(422, "Send the file as a data URL.")
    row = db.get(Image, (user.id, key))
    if row:
        row.src = body.src
    else:
        db.add(Image(user_id=user.id, key=key, src=body.src))
    db.commit()


@router.get("/{key}")
def get_image(key: str = KEY, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Image, (user.id, key))
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found.")
    return {"src": row.src}


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(key: str = KEY, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(Image, (user.id, key))
    if row:
        db.delete(row)
        db.commit()
