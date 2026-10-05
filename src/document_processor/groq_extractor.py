import json
import re

from .schemas import Invoice
from .llm_manager import LLMManager


llm_manager = LLMManager()


def build_invoice_prompt(text: str) -> str:
    return f"""
You are an invoice information extraction system.

Extract structured invoice information from the COMPLETE OCR text below.

IMPORTANT RULES:

1. Extract ONLY information explicitly present in the document.
2. Do NOT invent or guess information.
3. If a field is missing or unreadable, return null.
4. Preserve numbers accurately.
5. Extract EVERY line item from ALL pages.
6. Reconstruct multi-page tables correctly.
7. Return ONLY valid JSON.
8. Do NOT use markdown.
9. Do NOT use ```json.
10. Do NOT calculate values that are not explicitly present.
11. Do NOT calculate due_date from payment terms.
12. If due_date is not explicitly printed, return null.
13. Convert dates to YYYY-MM-DD format.
14. Remove commas from Indian number formatting when creating JSON numbers.
15. Values such as N/A, NA, MISSING, UNKNOWN, -, and NOT PROVIDED should become null.

LINE ITEM FIELDS:

For every line item extract:

- description
- hsn_sac
- quantity
- unit
- unit_price
- amount

FINANCIAL FIELDS:

Extract these fields when explicitly present:

- subtotal
- discount
- freight
- cgst
- sgst
- igst
- tax
- round_off
- total

FINANCIAL FIELD RULES:

IMPORTANT:
Search the COMPLETE OCR text, including the last page, for financial summary values.

Look specifically for:

- Sub Total
- Subtotal
- Sub Total Amount
- Less: Trade Discount
- Discount
- Add: Freight
- Freight & Packing
- Packing & Freight
- CGST
- SGST
- IGST
- Tax Amount
- Round Off
- Grand Total
- Revised G.T.
- Revised G.T
- Total

Indian number formatting:

"4,83,247.50" means 483247.50

"11,885.81" means 11885.81

"9,664.95" means 9664.95

Remove commas used as thousands separators.

SUBTOTAL:

If the OCR contains:

Sub Total 4,83,247.50

extract:

"subtotal": 483247.50

Do NOT return null when an explicitly labeled subtotal exists.

Do NOT confuse:

- Sub Total
- Carried Forward
- Brought Forward
- Discount
- Taxable Value
- Freight
- Grand Total

DISCOUNT:

If the document contains:

Less: Trade Discount @ 2% (-) 9,664.95

extract:

"discount": 9664.95

FREIGHT:

If the document explicitly contains a freight or freight & packing amount,
extract that amount into:

"freight"

CGST / SGST / IGST:

If CGST is explicitly present, extract it into "cgst".

If SGST is explicitly present, extract it into "sgst".

If IGST is explicitly present, extract it into "igst".

If both CGST and SGST are present and there is no separate total tax amount,
tax should equal:

cgst + sgst

TAX:

Do not invent tax.

If CGST and SGST are explicitly present, their sum may be used as tax.

ROUND OFF:

If the document explicitly contains Round Off, extract its numeric value.

TOTAL:

Prefer the final explicitly printed total, such as:

Grand Total
Revised G.T.

For example:

Revised G.T. = Rs. 495,278/-

must produce:

"total": 495278.00

Do not use a carried-forward amount as the final total.

EXPECTED JSON STRUCTURE:

{{
    "vendor_name": null,
    "invoice_number": null,
    "invoice_date": null,
    "due_date": null,

    "line_items": [
        {{
            "description": null,
            "hsn_sac": null,
            "quantity": null,
            "unit": null,
            "unit_price": null,
            "amount": null
        }}
    ],

    "subtotal": null,
    "discount": null,
    "freight": null,

    "cgst": null,
    "sgst": null,
    "igst": null,

    "tax": null,
    "round_off": null,
    "total": null
}}

Before returning JSON:

1. Search ALL pages.
2. Check the financial summary again.
3. Make sure explicitly printed financial values are not returned as null.
4. Make sure all line items are included.
5. Make sure the response is syntactically valid JSON.

INVOICE OCR TEXT:
----------------
{text}
----------------
"""


def call_llm(prompt: str) -> str:
    return llm_manager.generate(prompt)


def _parse_number(value: str) -> float:
    """
    Convert invoice numbers such as:

    4,83,247.50
    11,885.81
    9,664.95

    into:

    483247.50
    11885.81
    9664.95
    """

    value = value.strip()

    # Remove common currency symbols.
    value = re.sub(r"[₹$€£]", "", value)

    # Remove currency text.
    value = value.replace("Rs.", "")
    value = value.replace("Rs", "")
    value = value.replace("INR", "")

    # Remove thousands separators.
    value = value.replace(",", "")

    # Keep only numeric characters, decimal point and minus sign.
    value = re.sub(
        r"[^0-9.\-]",
        "",
        value
    )

    if not value:
        raise ValueError(
            "Unable to parse numeric value."
        )

    return float(value)


def _extract_last_number_from_line(
    line: str
):
    """
    Extract the LAST numeric value from an invoice line.

    Example:

        CGST @ 2.5% 11,885.81

    contains:

        2.5
        11,885.81

    We want:

        11,885.81

    because the percentage is not the tax amount.
    """

    matches = re.findall(
        r"-?\d[\d,]*(?:\.\d{1,2})?",
        line
    )

    if not matches:
        return None

    value = matches[-1]

    try:
        return _parse_number(value)

    except ValueError:
        return None


def _extract_financial_value(
    text: str,
    patterns: list[str]
):
    """
    Search OCR text line-by-line for a financial label.

    Once a matching line is found, extract the LAST
    numeric value from that line.

    This is important because invoice lines often contain
    percentages before the actual monetary amount.
    """

    lines = text.splitlines()

    for line in lines:

        line_clean = line.strip()

        if not line_clean:
            continue

        for pattern in patterns:

            if re.search(
                pattern,
                line_clean,
                flags=re.IGNORECASE
            ):

                value = _extract_last_number_from_line(
                    line_clean
                )

                if value is not None:
                    return value

    return None


def extract_financial_values(
    text: str
) -> dict:
    """
    Deterministically extract explicitly labeled financial
    values from OCR text.

    The LLM handles the semantic invoice extraction.

    This function provides a reliable second layer for
    clearly labeled financial values.
    """

    financial = {}

    # =========================================================
    # SUBTOTAL
    # =========================================================

    subtotal = _extract_financial_value(
        text,
        [
            r"\bsub\s*total\b",
            r"\bsubtotal\b",
            r"\bsub\s*total\s*amount\b",
        ]
    )

    if subtotal is not None:
        financial["subtotal"] = subtotal

    # =========================================================
    # DISCOUNT
    # =========================================================

    discount = _extract_financial_value(
        text,
        [
            r"trade\s+discount",
            r"\bdiscount\b",
        ]
    )

    if discount is not None:
        financial["discount"] = discount

    # =========================================================
    # FREIGHT
    # =========================================================

    freight = _extract_financial_value(
        text,
        [
            r"freight\s*(?:&|and)\s*packing",
            r"packing\s*(?:&|and)\s*freight",
            r"\bfreight\b",
        ]
    )

    if freight is not None:
        financial["freight"] = freight

    # =========================================================
    # CGST
    # =========================================================

    cgst = _extract_financial_value(
        text,
        [
            r"\bCGST\b",
        ]
    )

    if cgst is not None:
        financial["cgst"] = cgst

    # =========================================================
    # SGST
    # =========================================================

    sgst = _extract_financial_value(
        text,
        [
            r"\bSGST\b",
        ]
    )

    if sgst is not None:
        financial["sgst"] = sgst

    # =========================================================
    # IGST
    # =========================================================

    igst = _extract_financial_value(
        text,
        [
            r"\bIGST\b",
        ]
    )

    if igst is not None:
        financial["igst"] = igst

    # =========================================================
    # ROUND OFF
    # =========================================================

    round_off = _extract_financial_value(
        text,
        [
            r"round\s*off",
        ]
    )

    if round_off is not None:
        financial["round_off"] = round_off

    # =========================================================
    # FINAL TOTAL
    # =========================================================

    # IMPORTANT:
    # Only use strong final-total labels.
    #
    # Do NOT simply search for "total", because an invoice
    # can contain many unrelated totals.

    total = _extract_financial_value(
        text,
        [
            r"revised\s*G\.?T\.?",
            r"grand\s*total",
        ]
    )

    if total is not None:
        financial["total"] = total

    # =========================================================
    # TAX
    # =========================================================

    # First look for an explicitly printed total tax amount.

    tax = _extract_financial_value(
        text,
        [
            r"tax\s*amount",
            r"total\s*tax",
        ]
    )

    if tax is not None:

        financial["tax"] = tax

    # If there is no explicit total tax amount,
    # calculate it only when BOTH CGST and SGST were
    # explicitly extracted.

    elif (
        cgst is not None
        and sgst is not None
    ):

        financial["tax"] = round(
            cgst + sgst,
            2
        )

    return financial


def merge_financial_values(
    invoice_data: dict,
    financial_values: dict
) -> dict:
    """
    Merge deterministic financial extraction into the
    LLM result.

    Explicitly labeled OCR values take priority over
    the LLM values.
    """

    for field, value in financial_values.items():

        invoice_data[field] = value

    return invoice_data


def extract_invoice(
    text: str,
    max_retries: int = 1
) -> Invoice:

    llm_manager.reset_metrics()

    prompt = build_invoice_prompt(text)

    print(
        "\n========== LLM EXTRACTION =========="
    )

    print(
        "Requesting structured invoice JSON..."
    )

    # =========================================================
    # LLM CALL
    # =========================================================

    try:

        result_text = call_llm(prompt)

        print(
            "\n========== RAW LLM RESPONSE =========="
        )

        print(result_text)

    except Exception as error:

        print(
            "\nLLM extraction failed:"
        )

        print(error)

        raise RuntimeError(
            f"LLM_FAILED: {error}"
        )

    # =========================================================
    # JSON PARSING
    # =========================================================

    try:

        result = json.loads(
            result_text
        )

    except json.JSONDecodeError as error:

        print(
            "\nInvalid JSON returned by LLM."
        )

        raise RuntimeError(
            "INVALID_JSON: "
            f"LLM returned invalid JSON. "
            f"Details: {error}"
        )

    # =========================================================
    # DETERMINISTIC FINANCIAL EXTRACTION
    # =========================================================

    print(
        "\n========== DETERMINISTIC "
        "FINANCIAL EXTRACTION =========="
    )

    financial_values = extract_financial_values(
        text
    )

    if financial_values:

        print(
            "Financial values found directly "
            "in OCR:"
        )

        for field, value in financial_values.items():

            print(
                f"  {field}: {value}"
            )

    else:

        print(
            "No explicitly labeled financial "
            "values were found."
        )

    # =========================================================
    # MERGE
    # =========================================================

    result = merge_financial_values(
        result,
        financial_values
    )

    print(
        "\n========== MERGED EXTRACTION =========="
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        )
    )

    # =========================================================
    # PYDANTIC SCHEMA VALIDATION
    # =========================================================

    try:

        invoice = Invoice.model_validate(
            result
        )

    except Exception as error:

        print(
            "\nSchema validation failed:"
        )

        print(error)

        raise RuntimeError(
            f"SCHEMA_VALIDATION_FAILED: {error}"
        )

    print(
        "\nSchema validation successful."
    )

    print(
        "Invoice extraction successful."
    )

    return invoice
