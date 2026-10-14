from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import MediaSettings, get_media_settings
from app.database import get_session
from app.models import MediaAsset
from app.services.media import stored_path

router = APIRouter(prefix="/media")


@router.get("/{media_id}/file", name="media_file")
def media_file(media_id: int, session: Session = Depends(get_session),
               settings: MediaSettings = Depends(get_media_settings)):
    asset = session.get(MediaAsset, media_id)
    path = stored_path(asset, settings) if asset is not None else None
    if path is None:
        raise HTTPException(status_code=404, detail="Mídia não encontrada")
    return FileResponse(path, media_type=asset.mime_type, filename=asset.stored_filename,
                        content_disposition_type="inline",
                        headers={"X-Content-Type-Options": "nosniff",
                                 "Content-Security-Policy": "default-src 'none'; sandbox"})
