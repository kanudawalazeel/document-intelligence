import json
import sys
import time
from pathlib import Path
from datetime import date

from dotenv import load_dotenv
from groq import Groq

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.document_processor.document_processor import process_document
from src.document_processor.schemas import Invoice


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

client = Groq()

DOCUMENTS_DIR = Path("evaluation/documents")
GROUND_TRUTH_DIR = Path("evaluation/ground_truth")
REPORTS_DIR = Path("evaluation/reports")

REPORTS_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "openai/gpt-oss-20b"


# ============================================================
# PROMPT A - BASIC PROMPT
# ============================================================

BASIC_PROMPT = """
Extract invoice information from the document text below.

Return ONLY valid JSON.

Extract these fields:

- vendor_name
- invoice_number
- invoice_date
- due_date
- line_items
- subtotal
- tax
- total

For each line item extract:

- description
- quantity
- unit_price

If a field is not available, return null.

Document text:
----------------
{text}
----------------
"""


# ============================================================
# PROMPT B - IMPROVED PROMPT
# ============================================================

IMPROVED_PROMPT = """
You are an invoice information extraction system.

Extract invoice information from the text below.

Rules:

1. Extract only information explicitly present in the document.
2. Do not invent, guess, or infer information.
3. If a field is missing, unreadable, or ambiguous, return null.
4. Preserve numbers accurately.
5. Extract every line item.
6. Return ONLY valid JSON.
7. The JSON must contain these fields:
   - vendor_name
   - invoice_number
   - invoice_date
   - due_date
   - line_items
   - subtotal
   - tax
   - total
8. Convert dates to YYYY-MM-DD format.
9. Treat placeholder values such as:
   - MISSING
   - N/A
   - NA
   - UNKNOWN
   - -
   - NOT PROVIDED

   as missing values and return null.

For each line item, return:

- description
- quantity
- unit_price

Do not add fields that are not requested.

INVOICE TEXT:
----------------
{text}
----------------
"""


# ============================================================
# NORMALIZATION FUNCTIONS
# ============================================================

def normalize_date(value):
    if value is None:
        return None

    if isinstance(value, date):
        return value.isoformat()

    return str(value)


def normalize_value(value):
    if isinstance(value, dict):
        return {
            key: normalize_value(val)
            for key, val in value.items()
        }

    if isinstance(value, list):
        return [
            normalize_value(item)
            for item in value
        ]

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, float):
        return round(value, 2)

    return value


def normalize_invoice(data):
    return normalize_value(data)


# ============================================================
# LOAD GROUND TRUTH
# ============================================================

def load_ground_truth(filename):
    ground_truth_path = GROUND_TRUTH_DIR / filename.replace(
        ".pdf",
        ".json"
    )

    with open(ground_truth_path, "r", encoding="utf-8") as file:
        return json.load(file)


# ============================================================
# FIELD COMPARISON
# ============================================================

def compare_fields(predicted, actual):
    fields = [
        "vendor_name",
        "invoice_number",
        "invoice_date",
        "due_date",
        "line_items",
        "subtotal",
        "tax",
        "total"
    ]

    correct = 0
    total = len(fields)

    field_results = {}

    for field in fields:

        predicted_value = normalize_value(
            predicted.get(field)
        )

        actual_value = normalize_value(
            actual.get(field)
        )

        is_correct = predicted_value == actual_value

        if is_correct:
            correct += 1

        field_results[field] = {
            "correct": is_correct,
            "predicted": predicted_value,
            "actual": actual_value
        }

    accuracy = correct / total

    return accuracy, field_results


# ============================================================
# RUN ONE PROMPT
# ============================================================

def run_prompt(prompt_name, prompt_template):

    print("\n" + "=" * 70)
    print(f"RUNNING {prompt_name.upper()}")
    print("=" * 70)

    documents = sorted(
        DOCUMENTS_DIR.glob("*.pdf")
    )

    results = []

    total_field_accuracy = 0
    exact_matches = 0
    successful_extractions = 0
    invalid_json_count = 0
    schema_failure_count = 0
    total_processing_time = 0

    for index, document_path in enumerate(documents, start=1):

        print(
            f"\n[{index}/{len(documents)}] "
            f"Processing {document_path.name}"
        )

        start_time = time.perf_counter()

        result_record = {
            "document": document_path.name,
            "success": False,
            "field_accuracy": 0,
            "exact_match": False,
            "processing_time": 0,
            "error": None
        }

        try:

            # ------------------------------------------------
            # STEP 1: DOCUMENT PROCESSING
            # ------------------------------------------------

            text = process_document(
                str(document_path)
            )

            if not text.strip():
                raise ValueError(
                    "No text could be extracted."
                )

            # ------------------------------------------------
            # STEP 2: BUILD PROMPT
            # ------------------------------------------------

            prompt = prompt_template.format(
                text=text
            )

            # ------------------------------------------------
            # STEP 3: GROQ
            # ------------------------------------------------

            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You extract invoice information "
                            "accurately and return structured JSON."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={
                    "type": "json_object"
                }
            )

            result_text = response.choices[0].message.content

            if not result_text:
                raise RuntimeError(
                    "Empty response from Groq."
                )

            # ------------------------------------------------
            # STEP 4: JSON PARSING
            # ------------------------------------------------

            try:

                predicted_json = json.loads(
                    result_text
                )

            except json.JSONDecodeError as error:

                invalid_json_count += 1

                raise RuntimeError(
                    f"Invalid JSON: {error}"
                )

            # ------------------------------------------------
            # STEP 5: PYDANTIC VALIDATION
            # ------------------------------------------------

            try:

                invoice = Invoice.model_validate(
                    predicted_json
                )

            except Exception as error:

                schema_failure_count += 1

                raise RuntimeError(
                    f"Schema validation failed: {error}"
                )

            predicted = invoice.model_dump()

            # ------------------------------------------------
            # STEP 6: GROUND TRUTH
            # ------------------------------------------------

            actual = load_ground_truth(
                document_path.name
            )

            # ------------------------------------------------
            # STEP 7: FIELD COMPARISON
            # ------------------------------------------------

            field_accuracy, field_results = compare_fields(
                predicted,
                actual
            )

            exact_match = (
                field_accuracy == 1.0
            )

            total_field_accuracy += field_accuracy

            if exact_match:
                exact_matches += 1

            successful_extractions += 1

            result_record["success"] = True
            result_record["field_accuracy"] = field_accuracy
            result_record["exact_match"] = exact_match
            result_record["field_results"] = field_results

            print(
                f"Field accuracy: "
                f"{field_accuracy * 100:.2f}%"
            )

            print(
                f"Exact match: "
                f"{exact_match}"
            )

        except Exception as error:

            result_record["error"] = str(error)

            print(
                f"ERROR: {error}"
            )

        finally:

            processing_time = (
                time.perf_counter() - start_time
            )

            result_record["processing_time"] = (
                processing_time
            )

            total_processing_time += (
                processing_time
            )

            results.append(
                result_record
            )

    # ========================================================
    # SUMMARY
    # ========================================================

    document_count = len(documents)

    if document_count > 0:

        average_field_accuracy = (
            total_field_accuracy /
            document_count
        )

        exact_match_rate = (
            exact_matches /
            document_count
        )

        success_rate = (
            successful_extractions /
            document_count
        )

        average_processing_time = (
            total_processing_time /
            document_count
        )

    else:

        average_field_accuracy = 0
        exact_match_rate = 0
        success_rate = 0
        average_processing_time = 0

    summary = {
        "prompt": prompt_name,
        "model": MODEL_NAME,
        "documents_tested": document_count,
        "successful_extractions": successful_extractions,
        "success_rate": round(
            success_rate * 100,
            2
        ),
        "average_field_accuracy": round(
            average_field_accuracy * 100,
            2
        ),
        "exact_match_rate": round(
            exact_match_rate * 100,
            2
        ),
        "invalid_json_rate": round(
            (
                invalid_json_count /
                document_count *
                100
            ) if document_count else 0,
            2
        ),
        "schema_validation_failure_rate": round(
            (
                schema_failure_count /
                document_count *
                100
            ) if document_count else 0,
            2
        ),
        "average_processing_time_seconds": round(
            average_processing_time,
            2
        ),
        "results": results
    }

    print("\n" + "-" * 70)
    print(f"{prompt_name.upper()} SUMMARY")
    print("-" * 70)

    print(
        f"Documents tested: "
        f"{document_count}"
    )

    print(
        f"Success rate: "
        f"{summary['success_rate']:.2f}%"
    )

    print(
        f"Average field accuracy: "
        f"{summary['average_field_accuracy']:.2f}%"
    )

    print(
        f"Exact match rate: "
        f"{summary['exact_match_rate']:.2f}%"
    )

    print(
        f"Invalid JSON rate: "
        f"{summary['invalid_json_rate']:.2f}%"
    )

    print(
        f"Schema validation failure rate: "
        f"{summary['schema_validation_failure_rate']:.2f}%"
    )

    print(
        f"Average processing time: "
        f"{summary['average_processing_time_seconds']:.2f} sec"
    )

    return summary


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("=" * 70)
    print("PROMPT COMPARISON EVALUATION")
    print("=" * 70)

    print(
        "\nSame model, same documents, "
        "different prompts."
    )

    # --------------------------------------------------------
    # RUN PROMPT A
    # --------------------------------------------------------

    basic_results = run_prompt(
        "Prompt A - Basic",
        BASIC_PROMPT
    )

    # --------------------------------------------------------
    # RUN PROMPT B
    # --------------------------------------------------------

    improved_results = run_prompt(
        "Prompt B - Improved",
        IMPROVED_PROMPT
    )

    # ========================================================
    # COMPARISON
    # ========================================================

    comparison = {
        "model": MODEL_NAME,
        "prompt_a": basic_results,
        "prompt_b": improved_results
    }

    output_path = (
        REPORTS_DIR /
        "prompt_comparison_report.json"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            comparison,
            file,
            indent=4,
            default=str
        )

    print("\n")
    print("=" * 70)
    print("FINAL PROMPT COMPARISON")
    print("=" * 70)

    print(
        f"\n{'Metric':<35}"
        f"{'Basic Prompt':>15}"
        f"{'Improved Prompt':>20}"
    )

    print("-" * 70)

    print(
        f"{'Success rate':<35}"
        f"{basic_results['success_rate']:>14.2f}%"
        f"{improved_results['success_rate']:>19.2f}%"
    )

    print(
        f"{'Field accuracy':<35}"
        f"{basic_results['average_field_accuracy']:>14.2f}%"
        f"{improved_results['average_field_accuracy']:>19.2f}%"
    )

    print(
        f"{'Exact match rate':<35}"
        f"{basic_results['exact_match_rate']:>14.2f}%"
        f"{improved_results['exact_match_rate']:>19.2f}%"
    )

    print(
        f"{'Invalid JSON rate':<35}"
        f"{basic_results['invalid_json_rate']:>14.2f}%"
        f"{improved_results['invalid_json_rate']:>19.2f}%"
    )

    print(
        f"{'Schema failure rate':<35}"
        f"{basic_results['schema_validation_failure_rate']:>14.2f}%"
        f"{improved_results['schema_validation_failure_rate']:>19.2f}%"
    )

    print(
        f"{'Average processing time':<35}"
        f"{basic_results['average_processing_time_seconds']:>14.2f}s"
        f"{improved_results['average_processing_time_seconds']:>19.2f}s"
    )

    print("\n")
    print(
        f"Report saved to: {output_path}"
    )


if __name__ == "__main__":
    main()
