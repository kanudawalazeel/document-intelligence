from document_processor.groq_extractor import extract_invoice


sample_text = """
ABC Technologies
Invoice Number: INV-1024

Invoice Date: 25/09/2026
Due Date: 25/10/2026

Item: Laptop
Quantity: 2
Unit Price: 75000

Subtotal: 150000
Tax: 27000
Total: 177000
"""


invoice = extract_invoice(sample_text)


print("========== GROQ EXTRACTION ==========")

print("\nVendor:")
print(invoice.vendor_name)

print("\nInvoice Number:")
print(invoice.invoice_number)

print("\nInvoice Date:")
print(invoice.invoice_date)

print("\nDue Date:")
print(invoice.due_date)

print("\nLine Items:")
for item in invoice.line_items:
    print(f"  Description: {item.description}")
    print(f"  Quantity: {item.quantity}")
    print(f"  Unit Price: {item.unit_price}")

print("\nSubtotal:")
print(invoice.subtotal)

print("\nTax:")
print(invoice.tax)

print("\nTotal:")
print(invoice.total)


print("\n========== FINAL JSON ==========")
print(invoice.model_dump_json(indent=4))