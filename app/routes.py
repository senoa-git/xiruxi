# app/routes.py
from __future__ import annotations

import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request, Response, HTTPException, Form
from sqlmodel import select, func

from fastapi.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER, HTTP_204_NO_CONTENT

from .database import get_session
from .models import User, Bottle, Delivery

router = APIRouter()
JST = ZoneInfo("Asia/Tokyo")


def today_jst() -> date:
    return datetime.now(JST).date()


@router.post("/anon")
def create_anon(request: Request, nickname: str = Form(...)):
    existing = request.cookies.get("anon_id")
    if existing:
        with get_session() as session:
            user = session.get(User, existing)
            if user:
                # AJAXなら204、通常ならリダイレクト
                if "application/json" in (request.headers.get("accept") or ""):
                    return Response(status_code=HTTP_204_NO_CONTENT)
                return RedirectResponse(url="/?info=already_in_sea", status_code=HTTP_303_SEE_OTHER)

    nickname = nickname.strip()
    if not nickname:
        return RedirectResponse(url="/?error=nickname_required", status_code=HTTP_303_SEE_OTHER)
    if len(nickname) > 32:
        return RedirectResponse(url="/?error=nickname_too_long", status_code=HTTP_303_SEE_OTHER)

    anon_id = str(uuid.uuid4())

    with get_session() as session:
        user = User(anon_id=anon_id, nickname=nickname)
        session.add(user)
        session.commit()

    wants_ajax = "application/json" in (request.headers.get("accept") or "")

    response = Response(status_code=HTTP_204_NO_CONTENT) if wants_ajax \
        else RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)

    response.set_cookie(
        key="anon_id",
        value=anon_id,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 365,
    )
    return response


def require_anon_id(request: Request) -> str:
    anon_id = request.cookies.get("anon_id")
    if not anon_id:
        raise HTTPException(status_code=401, detail="no anon_id cookie")
    return anon_id


@router.get("/today")
def get_today_bottle(request: Request):
    anon_id = require_anon_id(request)
    today = today_jst()

    with get_session() as session:
        # user更新（存在確認も兼ねる）
        user = session.get(User, anon_id)
        if not user:
            # AJAXならJSON、通常ならリダイレクト
            if "application/json" in (request.headers.get("accept") or ""):
                resp = Response(status_code=401)
                resp.delete_cookie(key="anon_id")
                return resp
            resp = RedirectResponse(url="/?info=need_nick", status_code=HTTP_303_SEE_OTHER)
            resp.delete_cookie(key="anon_id")
            return resp
        user.last_seen_at = datetime.utcnow()
        session.add(user)
        session.commit()

        # すでに今日の配達があるなら、それを返す
        existing = session.exec(
            select(Delivery).where(
                Delivery.user_anon_id == anon_id,
                Delivery.delivered_on == today,
            )
        ).first()

        if existing:
            bottle = session.get(Bottle, existing.bottle_id)
            if not bottle or bottle.is_hidden:
                # 例外：届いたボトルが消されてたら再配布（MVPの簡易措置）
                session.delete(existing)
                session.commit()
            else:
                return {"date": str(today), "bottle": {"id": bottle.id, "content": bottle.content}}

        # 今日未配布なら割り当てる
        # 条件：
        # - hiddenじゃない
        # - 自分の投稿は除外（必要なら）
        # - すでに自分が受け取ったことあるボトルは除外（Deliveryから）
        received_ids = session.exec(
            select(Delivery.bottle_id).where(Delivery.user_anon_id == anon_id)
        ).all()
        received_ids_set = set(received_ids)

        q = select(Bottle.id).where(Bottle.is_hidden == False)

        # 既受信除外（件数増えると重いので、MVPではこれでOK）
        if received_ids_set:
            q = q.where(Bottle.id.not_in(received_ids_set))

        # ランダムに1本（SQLiteでも動くように random()）
        bottle_id = session.exec(
            q.order_by(func.random()).limit(1)
        ).first()

        if bottle_id is None:
            return {
                "date": str(today),
                "bottle": None,
                "message": "まだ海にボトルがない。君が最初の1本を流していい。"
            }

        delivery = Delivery(user_anon_id=anon_id, bottle_id=bottle_id, delivered_on=today)
        session.add(delivery)
        session.commit()

        bottle = session.get(Bottle, bottle_id)
        return {"date": str(today), "bottle": {"id": bottle.id, "content": bottle.content}}


@router.post("/bottles")
def post_bottle(request: Request, content: str = Form(...)):
    anon_id = require_anon_id(request)
    content = content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    if len(content) > 90:
        raise HTTPException(status_code=400, detail="content too long")

    today = today_jst()

    with get_session() as session:
        # 投稿レート制限（MVP）：1日3本まで
        count_today = session.exec(
            select(func.count(Bottle.id)).where(
                Bottle.author_anon_id == anon_id,
                func.date(Bottle.created_at) == str(today),  # SQLiteの簡易比較
            )
        ).one()

        if count_today >= 3:
            raise HTTPException(status_code=429, detail="daily limit reached (3)")

        bottle = Bottle(author_anon_id=anon_id, content=content)
        session.add(bottle)
        session.commit()
        session.refresh(bottle)

    return RedirectResponse(url="/", status_code=HTTP_303_SEE_OTHER)


@router.post("/report")
def report_bottle(bottle_id: int = Form(...)):
    with get_session() as session:
        bottle = session.get(Bottle, bottle_id)
        if not bottle:
            raise HTTPException(status_code=404, detail="bottle not found")
        bottle.report_count += 1
        # 閾値はMVPなので雑でOK（あとで調整）
        if bottle.report_count >= 3:
            bottle.is_hidden = True
        session.add(bottle)
        session.commit()
    return {"ok": True}
