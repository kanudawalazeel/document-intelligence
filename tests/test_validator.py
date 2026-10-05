from document_processor.schemas import Invoice
from document_processor.validators import validate_invoice


# Valid invoice
valid_invoice_data = {
    "vendor_name": "ABC Technologies",
    "invoice_number": "INV-1024",
    "invoice_date": "2026-09-25",
    "due_date": "2026-10-25",
    "line_items": [
        {
            "description": "Laptop",
            "quantity": 2,
            "unit_price": 75000
        }
    ],
    "subtotal": 150000,
    "tax": 27000,
    "total": 177000
}


invoice = Invoice(**valid_invoice_data)

errors = validate_invoice(invoice)


print("========== BUSINESS VALIDATION ==========")

if not errors:
    print("Invoice is valid.")
else:
    print("Invoice has errors:")
    for error in errors:
        print(f"- {error}")