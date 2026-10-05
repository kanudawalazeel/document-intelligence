from document_processor.schemas import Invoice


invoice_data = {
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


invoice = Invoice(**invoice_data)

print("========== VALIDATED INVOICE ==========")
print(invoice)

print("\n========== JSON ==========")
print(invoice.model_dump_json(indent=4))