from sqlalchemy import Index, Integer, LargeBinary, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base, _id, _stamp, _text


class TalepUser(Base):
    __tablename__ = "talep_users"
    __table_args__ = (
        Index(
            "idx_talep_users_username",
            "username",
            unique=True,
            postgresql_where=text("username IS NOT NULL AND username <> ''"),
            sqlite_where=text("username IS NOT NULL AND username != ''"),
        ),
    )

    id: Mapped[int] = _id()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    password: Mapped[str] = mapped_column(Text, nullable=False)
    totp_secret: Mapped[str] = mapped_column(Text, nullable=False)
    is_admin: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[str | None] = _stamp()
    username: Mapped[str | None] = _text()
    must_change: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    role: Mapped[str | None] = _text()


class TalepTeam(Base):
    __tablename__ = "talep_teams"

    id: Mapped[int] = _id()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[str | None] = _stamp()
    topic: Mapped[str | None] = _text()


class TalepMember(Base):
    __tablename__ = "talep_members"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(Integer, primary_key=True)


class TalepRequest(Base):
    __tablename__ = "talep_requests"

    id: Mapped[int] = _id()
    number: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    target_team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    author_id: Mapped[int] = mapped_column(Integer, nullable=False)
    work_code: Mapped[str | None] = _text()
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = _text()
    priority: Mapped[str | None] = _text()
    due_date: Mapped[str | None] = _text()
    status: Mapped[str] = mapped_column(Text, nullable=False)
    file_path: Mapped[str | None] = _text()
    notes_json: Mapped[str | None] = _text()
    vkv_task_id: Mapped[int | None] = mapped_column(Integer)
    vkv_key: Mapped[str | None] = _text()
    created_at: Mapped[str | None] = _stamp()


class TalepLoginLog(Base):
    __tablename__ = "talep_login_logs"

    id: Mapped[int] = _id()
    user_id: Mapped[int | None] = mapped_column(Integer)
    name: Mapped[str | None] = _text()
    email: Mapped[str | None] = _text()
    event: Mapped[str] = mapped_column(Text, nullable=False)
    device: Mapped[str | None] = _text()
    os_name: Mapped[str | None] = _text()
    ip: Mapped[str | None] = _text()
    created_at: Mapped[str | None] = _text()


class TalepRequestCode(Base):
    __tablename__ = "talep_request_codes"

    id: Mapped[int] = _id()
    code: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    work_code: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str | None] = _stamp()
    title: Mapped[str | None] = _text()
    scope: Mapped[str | None] = mapped_column(Text, server_default=text("'İç'"))
    all_teams: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))


class TalepReset(Base):
    __tablename__ = "talep_resets"

    id: Mapped[int] = _id()
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str | None] = _text()


class TalepFile(Base):
    __tablename__ = "talep_files"

    id: Mapped[int] = _id()
    request_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
