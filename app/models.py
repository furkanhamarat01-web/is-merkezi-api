from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _id() -> Mapped[int]:
    return mapped_column(Integer, primary_key=True)


def _text() -> Mapped[str | None]:
    return mapped_column(Text)


def _stamp() -> Mapped[datetime | None]:
    return mapped_column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (Index("idx_tasks_owner", "owner_id"),)

    id: Mapped[int] = _id()
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = _text()
    assignee: Mapped[str | None] = _text()
    priority: Mapped[str | None] = _text()
    status: Mapped[str | None] = _text()
    start_date: Mapped[str | None] = _text()
    due_date: Mapped[str | None] = _text()
    repeat: Mapped[str | None] = _text()
    tag: Mapped[str | None] = _text()
    created_at: Mapped[str | None] = _stamp()
    owner_id: Mapped[int | None] = mapped_column(Integer)
    waiting_since: Mapped[str | None] = _text()
    sla_next: Mapped[str | None] = _text()
    note_json: Mapped[str | None] = _text()
    project_id: Mapped[int | None] = mapped_column(Integer)
    issue_no: Mapped[int | None] = mapped_column(Integer)
    issue_type: Mapped[str | None] = _text()


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        Index("idx_invoices_owner", "owner_id"),
        Index(
            "idx_invoices_source",
            "source_key",
            unique=True,
            postgresql_where=text("source_key IS NOT NULL AND source_key <> ''"),
            sqlite_where=text("source_key IS NOT NULL AND source_key != ''"),
        ),
    )

    id: Mapped[int] = _id()
    kind: Mapped[str | None] = _text()
    party: Mapped[str] = mapped_column(Text, nullable=False)
    invoice_no: Mapped[str | None] = _text()
    description: Mapped[str | None] = _text()
    amount: Mapped[float | None] = mapped_column(Float)
    invoice_date: Mapped[str | None] = _text()
    due_date: Mapped[str | None] = _text()
    status: Mapped[str | None] = _text()
    attachment: Mapped[str | None] = _text()
    created_at: Mapped[str | None] = _stamp()
    source: Mapped[str | None] = _text()
    source_key: Mapped[str | None] = _text()
    currency: Mapped[str | None] = _text()
    tax_no: Mapped[str | None] = _text()
    excel_status: Mapped[str | None] = _text()
    file_name: Mapped[str | None] = _text()
    report_reason: Mapped[str | None] = _text()
    report_files: Mapped[str | None] = _text()
    paid_amount: Mapped[float | None] = mapped_column(Float)
    events_json: Mapped[str | None] = _text()
    owner_id: Mapped[int | None] = mapped_column(Integer)


class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = (Index("idx_reminders_owner", "owner_id"),)

    id: Mapped[int] = _id()
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = _text()
    remind_date: Mapped[str | None] = _text()
    remind_time: Mapped[str | None] = _text()
    repeat: Mapped[str | None] = _text()
    status: Mapped[str | None] = _text()
    last_notified: Mapped[str | None] = _text()
    created_at: Mapped[str | None] = _stamp()
    owner_id: Mapped[int | None] = mapped_column(Integer)


class Contact(Base):
    __tablename__ = "contacts"
    __table_args__ = (Index("idx_contacts_owner", "owner_id"),)

    id: Mapped[int] = _id()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    contact_person: Mapped[str | None] = _text()
    phone: Mapped[str | None] = _text()
    email: Mapped[str | None] = _text()
    tax_no: Mapped[str | None] = _text()
    address: Mapped[str | None] = _text()
    notes: Mapped[str | None] = _text()
    created_at: Mapped[str | None] = _stamp()
    owner_id: Mapped[int | None] = mapped_column(Integer)
    record_kind: Mapped[str | None] = _text()
    scope: Mapped[str | None] = _text()
    extension: Mapped[str | None] = _text()


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (Index("idx_transactions_owner", "owner_id"),)

    id: Mapped[int] = _id()
    kind: Mapped[str | None] = _text()
    category: Mapped[str | None] = _text()
    description: Mapped[str | None] = _text()
    amount: Mapped[float | None] = mapped_column(Float)
    trans_date: Mapped[str | None] = _text()
    party: Mapped[str | None] = _text()
    payment_method: Mapped[str | None] = _text()
    created_at: Mapped[str | None] = _stamp()
    owner_id: Mapped[int | None] = mapped_column(Integer)
    docs_json: Mapped[str | None] = _text()


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (Index("idx_projects_owner", "owner_id"),)

    id: Mapped[int] = _id()
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = _text()
    start_date: Mapped[str | None] = _text()
    end_date: Mapped[str | None] = _text()
    status: Mapped[str | None] = _text()
    budget: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = _text()
    created_at: Mapped[str | None] = _stamp()
    owner_id: Mapped[int | None] = mapped_column(Integer)
    proj_key: Mapped[str | None] = _text()


class NotifyLog(Base):
    __tablename__ = "notify_log"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    last_on: Mapped[str | None] = _text()


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str | None] = _text()


class IgnoredSource(Base):
    __tablename__ = "ignored_sources"

    key: Mapped[str] = mapped_column(Text, primary_key=True)


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (Index("idx_reports_owner", "owner_id"),)

    id: Mapped[int] = _id()
    invoice_id: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str | None] = _text()
    invoice_no: Mapped[str | None] = _text()
    amount: Mapped[float | None] = mapped_column(Float)
    reason: Mapped[str | None] = _text()
    saved_path: Mapped[str | None] = _text()
    created_at: Mapped[str | None] = _stamp()
    owner_id: Mapped[int | None] = mapped_column(Integer)


class Offer(Base):
    __tablename__ = "offers"
    __table_args__ = (Index("idx_offers_owner", "owner_id"),)

    id: Mapped[int] = _id()
    project_id: Mapped[int] = mapped_column(Integer, nullable=False)
    vendor: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = _text()
    amount: Mapped[float | None] = mapped_column(Float)
    offer_date: Mapped[str | None] = _text()
    file_path: Mapped[str | None] = _text()
    pros: Mapped[str | None] = _text()
    cons: Mapped[str | None] = _text()
    notes: Mapped[str | None] = _text()
    source_text: Mapped[str | None] = _text()
    created_at: Mapped[str | None] = _stamp()
    owner_id: Mapped[int | None] = mapped_column(Integer)
    url: Mapped[str | None] = _text()


class Talep(Base):
    __tablename__ = "talepler"

    id: Mapped[int] = _id()
    number: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = _text()
    work_code: Mapped[str | None] = _text()
    source_name: Mapped[str | None] = _text()
    target_name: Mapped[str | None] = _text()
    author_name: Mapped[str | None] = _text()
    author_email: Mapped[str | None] = _text()
    priority: Mapped[str | None] = _text()
    due_date: Mapped[str | None] = _text()
    status: Mapped[str | None] = _text()
    file_name: Mapped[str | None] = _text()
    notes_json: Mapped[str | None] = _text()
    created_at: Mapped[str | None] = _stamp()
    files_json: Mapped[str | None] = _text()
    request_code: Mapped[str | None] = _text()
    scope: Mapped[str | None] = _text()
    author_id: Mapped[int | None] = mapped_column(Integer)
    assignee_id: Mapped[int | None] = mapped_column(Integer)
    assignee_name: Mapped[str | None] = _text()
