from pydantic import BaseModel, Field


class TaskIn(BaseModel):
    title: str
    description: str | None = None
    assignee: str | None = None
    priority: str | None = None
    status: str | None = None
    start_date: str | None = None
    due_date: str | None = None
    repeat: str | None = None
    tag: str | None = None
    issue_type: str | None = None
    project_id: int | None = None
    note_json: str | None = None


class TaskPatch(TaskIn):
    title: str | None = None


class MoveTask(BaseModel):
    project_id: int


class ProjectIn(BaseModel):
    name: str
    proj_key: str | None = None
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    status: str | None = None
    budget: float | None = None
    notes: str | None = None


class ProjectPatch(ProjectIn):
    name: str | None = None


class InvoiceIn(BaseModel):
    party: str
    kind: str | None = None
    status: str | None = None
    invoice_no: str | None = None
    description: str | None = None
    amount: float | None = None
    invoice_date: str | None = None
    due_date: str | None = None
    attachment: str | None = None
    currency: str | None = None
    tax_no: str | None = None
    file_name: str | None = None
    source: str | None = None
    source_key: str | None = None


class InvoicePatch(InvoiceIn):
    party: str | None = None


class PaymentIn(BaseModel):
    amount: float = Field(gt=0)


class ReminderIn(BaseModel):
    title: str
    remind_date: str
    description: str | None = None
    remind_time: str | None = None
    repeat: str | None = None
    status: str | None = None


class ReminderPatch(BaseModel):
    title: str | None = None
    remind_date: str | None = None
    description: str | None = None
    remind_time: str | None = None
    repeat: str | None = None
    status: str | None = None


class ContactIn(BaseModel):
    name: str
    contact_person: str | None = None
    phone: str | None = None
    email: str | None = None
    tax_no: str | None = None
    address: str | None = None
    notes: str | None = None
    record_kind: str | None = None
    scope: str | None = None
    extension: str | None = None


class ContactPatch(ContactIn):
    name: str | None = None


class TransactionIn(BaseModel):
    kind: str
    category: str
    amount: float
    trans_date: str
    description: str | None = None
    party: str | None = None
    payment_method: str | None = None
    docs_json: str | None = None


class TransactionPatch(BaseModel):
    kind: str | None = None
    category: str | None = None
    amount: float | None = None
    trans_date: str | None = None
    description: str | None = None
    party: str | None = None
    payment_method: str | None = None
    docs_json: str | None = None


class OfferIn(BaseModel):
    project_id: int
    vendor: str
    title: str | None = None
    amount: float | None = None
    offer_date: str | None = None
    file_path: str | None = None
    url: str | None = None
    pros: str | None = None
    cons: str | None = None
    notes: str | None = None
    source_text: str | None = None


class OfferPatch(OfferIn):
    project_id: int | None = None
    vendor: str | None = None


class ReportIn(BaseModel):
    title: str
    invoice_id: int | None = None
    invoice_no: str | None = None
    amount: float | None = None
    reason: str | None = None
    saved_path: str | None = None


class ReportPatch(ReportIn):
    title: str | None = None


class TalepIn(BaseModel):
    title: str
    description: str | None = None
    work_code: str | None = None
    request_code: str | None = None
    source_name: str | None = None
    target_name: str | None = None
    target_code: str | None = None
    author_name: str | None = None
    author_email: str | None = None
    author_id: int | None = None
    assignee_id: int | None = None
    assignee_name: str | None = None
    priority: str | None = None
    due_date: str | None = None
    status: str | None = None
    scope: str | None = None
    file_name: str | None = None
    notes_json: str | None = None
    files_json: str | None = None
    number: str | None = None


class TalepPatch(TalepIn):
    title: str | None = None


class TakeIn(BaseModel):
    actor_id: int
    actor_name: str


class AssignIn(BaseModel):
    assignee_id: int
    assignee_name: str
    actor_name: str = ""


class StatusIn(BaseModel):
    status: str
    note: str = ""
    actor_name: str = ""


class CategoryIn(BaseModel):
    kind: str
    name: str


class SettingIn(BaseModel):
    value: str = ""


def dumped(body: BaseModel) -> dict:
    return {key: value for key, value in body.model_dump(exclude_unset=True).items() if value is not None}
