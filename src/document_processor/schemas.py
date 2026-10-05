from datetime import date

from pydantic import BaseModel


class LineItem(BaseModel):
    description: str | None = None
    hsn_sac: str | None = None
    quantity: float | None = None
    unit: str | None = None
    unit_price: float | None = None
    amount: float | None = None


class Invoice(BaseModel):
    vendor_name: str | None = None
    invoice_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None

    line_items: list[LineItem]

    subtotal: float | None = None
    discount: float | None = None
    freight: float | None = None

    cgst: float | None = None
    sgst: float | None = None
    igst: float | None = None

    tax: float | None = None
    round_off: float | None = None
    total: float | None = None