from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.database import get_session
from app.security import require_form_csrf
from app.services import media, playlists

router = APIRouter(prefix="/admin", dependencies=[Depends(require_form_csrf)])
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[2] / "templates")
notices = {
    "created": "Playlist criada com sucesso.", "updated": "Playlist atualizada com sucesso.",
    "toggled": "Estado da playlist atualizado.", "added": "Item adicionado com sucesso.",
    "removed": "Item removido da playlist.", "moved": "Ordem atualizada.",
    "assigned": "Playlist associada com sucesso.", "unassigned": "Playlist desvinculada.",
}


def render_error(request, error):
    return templates.TemplateResponse(request=request, name="admin/playlists/error.html",
                                      context={"error": str(error)}, status_code=error.status_code)


def redirect(request, route, result, **parameters):
    return RedirectResponse(request.url_for(route, **parameters).include_query_params(result=result), status_code=303)


async def form_values(request, names):
    form = await request.form()
    values = {}
    for name in names:
        entries = form.getlist(name)
        if len(entries) > 1 or (entries and not isinstance(entries[0], str)):
            raise playlists.PlaylistError("Envie um único valor de texto por campo.")
        values[name] = entries[0] if entries else (None if name == "duration_seconds" else "")
    return values


def render_form(request, values, playlist_id=None, error=None):
    return templates.TemplateResponse(request=request, name="admin/playlists/form.html",
                                      context={"values": values, "playlist_id": playlist_id, "error": error},
                                      status_code=error.status_code if error else 200)


def render_detail(request, playlist_id, session, error=None, values=None):
    if error and error.status_code == 404:
        return render_error(request, error)
    try:
        playlist = playlists.find_playlist(playlist_id, session)
    except playlists.PlaylistError as exc:
        return render_error(request, exc)
    return templates.TemplateResponse(request=request, name="admin/playlists/detail.html", context={
        "playlist": playlist, "items": playlists.list_items(playlist.id, session),
        "assets": media.list_media(session), "screens": playlists.assigned_screens(playlist.id, session),
        "values": values or {"media_id": "", "duration_seconds": "15"}, "error": error,
        "notice": notices.get(request.query_params.get("result")),
    }, status_code=error.status_code if error else 200)


def render_assignment(request, screen_id, session, error=None, values=None):
    if error and error.status_code == 404:
        return render_error(request, error)
    try:
        screen = playlists.find_screen(screen_id, session)
    except playlists.PlaylistError as exc:
        return render_error(request, exc)
    current = playlists.screen_playlists(session).get(screen.id)
    return templates.TemplateResponse(request=request, name="admin/playlists/assignment.html", context={
        "screen": screen, "current": current, "options": playlists.available_playlists(session),
        "values": values if values is not None else {"playlist_id": str(current.id) if current else ""},
        "error": error, "notice": notices.get(request.query_params.get("result")),
    }, status_code=error.status_code if error else 200)


@router.get("/playlists", response_class=HTMLResponse, name="admin_playlists")
def list_playlists(request: Request, session: Session = Depends(get_session)):
    return templates.TemplateResponse(request=request, name="admin/playlists/list.html",
                                      context={"catalog": playlists.list_playlists(session)})


@router.get("/playlists/new", response_class=HTMLResponse, name="admin_new_playlist")
def new_playlist(request: Request):
    return render_form(request, {"name": "", "description": ""})


@router.post("/playlists", response_class=HTMLResponse, name="admin_create_playlist")
async def create_playlist(request: Request, session: Session = Depends(get_session)):
    values = {"name": "", "description": ""}
    try:
        values = await form_values(request, ("name", "description"))
        playlist_id = await run_in_threadpool(playlists.create_playlist, values["name"], values["description"], session)
    except playlists.PlaylistError as exc:
        return render_form(request, values, error=exc)
    return redirect(request, "admin_playlist_detail", "created", playlist_id=playlist_id)


@router.get("/playlists/{playlist_id}", response_class=HTMLResponse, name="admin_playlist_detail")
def detail(request: Request, playlist_id: str, session: Session = Depends(get_session)):
    return render_detail(request, playlist_id, session)


@router.get("/playlists/{playlist_id}/edit", response_class=HTMLResponse, name="admin_edit_playlist")
def edit_playlist(request: Request, playlist_id: str, session: Session = Depends(get_session)):
    try:
        playlist = playlists.find_playlist(playlist_id, session)
    except playlists.PlaylistError as exc:
        return render_error(request, exc)
    return render_form(request, {"name": playlist.name, "description": playlist.description or ""}, playlist.id)


@router.post("/playlists/{playlist_id}/edit", response_class=HTMLResponse, name="admin_update_playlist")
async def update_playlist(request: Request, playlist_id: str, session: Session = Depends(get_session)):
    values = {"name": "", "description": ""}
    try:
        values = await form_values(request, ("name", "description"))
        await run_in_threadpool(playlists.update_playlist, playlist_id, values["name"], values["description"], session)
    except playlists.PlaylistError as exc:
        if exc.status_code == 404:
            return render_error(request, exc)
        return render_form(request, values, playlist_id, exc)
    return redirect(request, "admin_playlist_detail", "updated", playlist_id=playlist_id)


@router.post("/playlists/{playlist_id}/toggle", response_class=HTMLResponse, name="admin_toggle_playlist")
def toggle_playlist(request: Request, playlist_id: str, session: Session = Depends(get_session)):
    try:
        playlists.toggle_playlist(playlist_id, session)
    except playlists.PlaylistError as exc:
        return render_detail(request, playlist_id, session, exc)
    return redirect(request, "admin_playlist_detail", "toggled", playlist_id=playlist_id)


@router.post("/playlists/{playlist_id}/items", response_class=HTMLResponse, name="admin_add_playlist_item")
async def add_item(request: Request, playlist_id: str, session: Session = Depends(get_session)):
    values = {"media_id": "", "duration_seconds": ""}
    try:
        values = await form_values(request, ("media_id", "duration_seconds"))
        await run_in_threadpool(playlists.add_item, playlist_id, values["media_id"], values["duration_seconds"], session)
    except playlists.PlaylistError as exc:
        return await run_in_threadpool(render_detail, request, playlist_id, session, exc, values)
    return redirect(request, "admin_playlist_detail", "added", playlist_id=playlist_id)


def change_item(request, playlist_id, item_id, session, action):
    try:
        if action == "remove":
            playlists.remove_item(playlist_id, item_id, session)
        else:
            playlists.move_item(playlist_id, item_id, -1 if action == "up" else 1, session)
    except playlists.PlaylistError as exc:
        return render_detail(request, playlist_id, session, exc)
    return redirect(request, "admin_playlist_detail", "removed" if action == "remove" else "moved", playlist_id=playlist_id)


@router.post("/playlists/{playlist_id}/items/{item_id}/remove", response_class=HTMLResponse, name="admin_remove_playlist_item")
def remove_item(request: Request, playlist_id: str, item_id: str, session: Session = Depends(get_session)):
    return change_item(request, playlist_id, item_id, session, "remove")


@router.post("/playlists/{playlist_id}/items/{item_id}/move-up", response_class=HTMLResponse, name="admin_move_playlist_item_up")
def move_up(request: Request, playlist_id: str, item_id: str, session: Session = Depends(get_session)):
    return change_item(request, playlist_id, item_id, session, "up")


@router.post("/playlists/{playlist_id}/items/{item_id}/move-down", response_class=HTMLResponse, name="admin_move_playlist_item_down")
def move_down(request: Request, playlist_id: str, item_id: str, session: Session = Depends(get_session)):
    return change_item(request, playlist_id, item_id, session, "down")


@router.get("/screens/{screen_id}/playlist", response_class=HTMLResponse, name="admin_screen_playlist")
def screen_playlist(request: Request, screen_id: str, session: Session = Depends(get_session)):
    return render_assignment(request, screen_id, session)


@router.post("/screens/{screen_id}/playlist", response_class=HTMLResponse, name="admin_assign_playlist")
async def assign_playlist(request: Request, screen_id: str, session: Session = Depends(get_session)):
    values = {"playlist_id": ""}
    try:
        values = await form_values(request, ("playlist_id",))
        await run_in_threadpool(playlists.assign_playlist, screen_id, values["playlist_id"], session)
    except playlists.PlaylistError as exc:
        return await run_in_threadpool(render_assignment, request, screen_id, session, exc, values)
    return redirect(request, "admin_screen_playlist", "assigned", screen_id=screen_id)


@router.post("/screens/{screen_id}/playlist/unassign", response_class=HTMLResponse, name="admin_unassign_playlist")
def unassign_playlist(request: Request, screen_id: str, session: Session = Depends(get_session)):
    try:
        playlists.unassign_playlist(screen_id, session)
    except playlists.PlaylistError as exc:
        return render_assignment(request, screen_id, session, exc)
    return redirect(request, "admin_screen_playlist", "unassigned", screen_id=screen_id)
