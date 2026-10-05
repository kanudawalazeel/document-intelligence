from .schemas import Invoice


def validate_invoice(invoice: Invoice) -> list[str]:
    errors = []

    # Invoice number is optional because some invoices
    # explicitly contain N/A or do not provide it.
    # Missing invoice number should not fail the invoice.

    # Invoice date is optional because some invoices
    # may not provide it.
    # If present, it is validated by the Pydantic schema.

    # Line items are optional because some invoices
    # legitimately contain no line-item information.
    if invoice.line_items:
        for index, item in enumerate(invoice.line_items, start=1):

            if item.quantity is not None and item.quantity <= 0:
                errors.append(
                    f"Line item {index}: quantity must be greater than 0."
            )

        if item.unit_price is not None and item.unit_price < 0:
            errors.append(
                f"Line item {index}: unit price cannot be negative."
            )

    # Validate date relationship only when both dates exist.
    if invoice.invoice_date and invoice.due_date:
        if invoice.invoice_date > invoice.due_date:
            errors.append(
                "Invoice date cannot be after due date."
            )

    # Subtotal and total are optional because some invoices
    # may explicitly contain N/A or may not provide them.

    # Validate arithmetic consistency only when all
    # required values are actually available.
    if (
        invoice.subtotal is not None
        and invoice.tax is not None
        and invoice.total is not None
    ):
        calculated_total = invoice.subtotal + invoice.tax

        if abs(calculated_total - invoice.total) > 0.01:
            errors.append(
                f"Subtotal + tax ({calculated_total}) does not match "
                f"total ({invoice.total})."
            )

    return errors