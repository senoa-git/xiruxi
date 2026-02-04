# app/models.py
from __future__ import annotations

from datetime import datetime, date
from typing import Optional
from sqlmodel import SQLModel, Field, Index


class User(SQLModel, table=True):
    # Cookieで保持する匿名ID（UUID文字列を想定）
    anon_id: str = Field(primary_key=True, index=True)
    nickname: str = Field(min_length=1, max_length=32)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)


class Bottle(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # 誰が投げたか（完全匿名にしたければ nullable にしてもOK）
    author_anon_id: Optional[str] = Field(default=None, index=True)

    # MVPは文字だけ
    content: str = Field(min_length=1, max_length=2000)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # モデレーション最小（通報で隠す）
    is_hidden: bool = Field(default=False)
    report_count: int = Field(default=0)


class Delivery(SQLModel, table=True):
    """
    1日1通の配達ログ
    - 同じ日に同じユーザーへ複数回配らない
    - その日に何が届いたかを確定させる
    """
    id: Optional[int] = Field(default=None, primary_key=True)

    user_anon_id: str = Field(index=True)
    bottle_id: int = Field(index=True)

    delivered_on: date = Field(index=True)  # JST基準で運用（サーバーでJST扱い）
    delivered_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        Index("ix_delivery_unique_user_day", "user_anon_id", "delivered_on", unique=True),
    )
