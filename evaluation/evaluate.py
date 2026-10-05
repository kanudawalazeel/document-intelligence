import json
import sys
import time
import csv
from pathlib import Path
from datetime import date

# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(0, str(SRC_DIR))

from document_processor.document_processor import process_document
from document_processor.groq_extractor import extract_invoice
from document_processor.validators import validate_invoice


DOCUMENTS_DIR = PROJECT_ROOT / "evaluation" / "documents"
GROUND_TRUTH_DIR = PROJECT_ROOT / "evaluation" / "ground_truth"
REPORTS_DIR = PROJECT_ROOT / "evaluation" / "reports"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# FIELDS TO EVALUATE
# ============================================================

FIELDS = [
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "due_date",
    "subtotal",
    "tax",
    "total",
    "line_items"
]


# ============================================================
# LOAD GROUND TRUTH
# ============================================================

def load_ground_truth(file_path):

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


# ============================================================
# DETERMINE DOCUMENT TYPE
# ============================================================

def get_document_type(document_name):

    try:

        number = int(
            Path(document_name).stem.split("_")[1]
        )

        if number <= 20:
            return "digital"

        return "scanned"

    except Exception:

        return "unknown"


# ============================================================
# NORMALIZE VALUES BEFORE COMPARISON
# ============================================================

def normalize_value(value):

    """
    Convert values into a comparable format.

    Important:
    Ground truth dates are strings such as:

        "2026-09-01"

    Pydantic converts them into:

        date(2026, 9, 1)

    This function converts both into the same format.
    """

    # Date object
    if isinstance(value, date):

        return value.isoformat()

    # List
    if isinstance(value, list):

        normalized_list = []

        for item in value:

            if isinstance(item, dict):

                normalized_item = {}

                for key, val in item.items():

                    normalized_item[key] = normalize_value(val)

                normalized_list.append(
                    normalized_item
                )

            else:

                normalized_list.append(
                    normalize_value(item)
                )

        return normalized_list

    # Dictionary
    if isinstance(value, dict):

        return {
            key: normalize_value(val)
            for key, val in value.items()
        }

    return value


# ============================================================
# COMPARE INDIVIDUAL FIELD
# ============================================================

def compare_field(predicted, actual):

    predicted = normalize_value(predicted)
    actual = normalize_value(actual)

    return predicted == actual


# ============================================================
# FIND EXPECTED MISSING FIELDS
# ============================================================

def get_missing_fields(data):

    missing = []

    for field in FIELDS:

        value = data.get(field)

        if value is None or value == []:

            missing.append(field)

    return missing


# ============================================================
# EVALUATE ONE INVOICE
# ============================================================

def evaluate_invoice(pdf_path, ground_truth_path):

    start_time = time.time()

    document_name = pdf_path.name

    document_type = get_document_type(
        document_name
    )

    ground_truth = load_ground_truth(
        ground_truth_path
    )

    result = {

        "document": document_name,

        "document_type": document_type,

        "success": False,

        "invalid_json": False,

        "schema_valid": False,

        "business_validation_failed": False,

        "expected_missing_fields": 0,

        "correctly_missing_fields": 0,

        "unexpected_missing_fields": 0,

        "field_accuracy": 0,

        "exact_match": False,

        "processing_time": 0,

        "error": "",

        "field_results": {},

        "business_validation_errors": []
    }

    try:

        # ====================================================
        # STEP 1: DOCUMENT PROCESSING
        # ====================================================

        text = process_document(
            str(pdf_path)
        )

        if not text.strip():

            raise ValueError(
                "No text could be extracted from document."
            )

        # ====================================================
        # STEP 2: LLM EXTRACTION
        # ====================================================

        invoice = extract_invoice(text)

        # ====================================================
        # STEP 3: SCHEMA VALIDATION
        # ====================================================

        result["schema_valid"] = True

        predicted = invoice.model_dump()

        # ====================================================
        # STEP 4: FIELD LEVEL COMPARISON
        # ====================================================

        correct_fields = 0

        expected_missing = 0

        correctly_missing = 0

        unexpected_missing = 0

        for field in FIELDS:

            actual_value = ground_truth.get(field)

            predicted_value = predicted.get(field)

            actual_missing = (
                actual_value is None
                or actual_value == []
            )

            predicted_missing = (
                predicted_value is None
                or predicted_value == []
            )

            is_correct = compare_field(
                predicted_value,
                actual_value
            )

            if is_correct:

                correct_fields += 1

            # --------------------------------------------
            # Missing field evaluation
            # --------------------------------------------

            if actual_missing:

                expected_missing += 1

                if predicted_missing:

                    correctly_missing += 1

            else:

                if predicted_missing:

                    unexpected_missing += 1

            # --------------------------------------------
            # Save field result
            # --------------------------------------------

            result["field_results"][field] = {

                "correct": is_correct,

                "expected_missing": actual_missing,

                "predicted_missing": predicted_missing,

                "expected": normalize_value(
                    actual_value
                ),

                "predicted": normalize_value(
                    predicted_value
                )
            }

        # ====================================================
        # FIELD ACCURACY
        # ====================================================

        result["field_accuracy"] = round(

            (
                correct_fields
                / len(FIELDS)
            ) * 100,

            2
        )

        result["expected_missing_fields"] = (
            expected_missing
        )

        result["correctly_missing_fields"] = (
            correctly_missing
        )

        result["unexpected_missing_fields"] = (
            unexpected_missing
        )

        result["exact_match"] = (

            correct_fields
            == len(FIELDS)
        )

        # ====================================================
        # STEP 5: BUSINESS VALIDATION
        # ====================================================

        validation_errors = validate_invoice(
            invoice
        )

        result[
            "business_validation_errors"
        ] = validation_errors

        if validation_errors:

            result[
                "business_validation_failed"
            ] = True

        # ====================================================
        # SUCCESS
        # ====================================================

        result["success"] = True

    except json.JSONDecodeError as error:

        result["invalid_json"] = True

        result["error"] = str(error)

    except Exception as error:

        result["error"] = str(error)

    finally:

        result["processing_time"] = round(

            time.time() - start_time,

            2
        )

    return result


# ============================================================
# SAVE CSV REPORT
# ============================================================

def save_csv_report(results):

    csv_path = (
        REPORTS_DIR
        / "evaluation_report.csv"
    )

    columns = [

        "document",

        "document_type",

        "success",

        "invalid_json",

        "schema_valid",

        "business_validation_failed",

        "expected_missing_fields",

        "correctly_missing_fields",

        "unexpected_missing_fields",

        "field_accuracy",

        "exact_match",

        "processing_time",

        "vendor_name",

        "invoice_number",

        "invoice_date",

        "due_date",

        "subtotal",

        "tax",

        "total",

        "line_items"
    ]

    with open(
        csv_path,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=columns
        )

        writer.writeheader()

        for result in results:

            row = {
                key: result.get(
                    key,
                    ""
                )

                for key in columns
            }

            for field in FIELDS:

                row[field] = (

                    result[
                        "field_results"
                    ]

                    .get(
                        field,
                        {}
                    )

                    .get(
                        "correct",
                        False
                    )
                )

            writer.writerow(row)

    return csv_path


# ============================================================
# CALCULATE OVERALL SUMMARY
# ============================================================

def calculate_summary(results):

    total_documents = len(results)

    successful = sum(

        r["success"]

        for r in results
    )

    invalid_json = sum(

        r["invalid_json"]

        for r in results
    )

    schema_valid = sum(

        r["schema_valid"]

        for r in results
    )

    business_failures = sum(

        r["business_validation_failed"]

        for r in results
    )

    exact_matches = sum(

        r["exact_match"]

        for r in results
    )

    unexpected_missing = sum(

        r["unexpected_missing_fields"]

        for r in results
    )

    expected_missing = sum(

        r["expected_missing_fields"]

        for r in results
    )

    correctly_missing = sum(

        r["correctly_missing_fields"]

        for r in results
    )

    # ========================================================
    # AVERAGE FIELD ACCURACY
    # ========================================================

    average_accuracy = (

        sum(
            r["field_accuracy"]
            for r in results
        )

        / total_documents

        if total_documents

        else 0
    )

    # ========================================================
    # PRESENT FIELD ACCURACY
    # ========================================================

    total_present_fields = 0

    correct_present_fields = 0

    for result in results:

        if not result["success"]:
            continue

        for field in FIELDS:

            field_result = (

                result[
                    "field_results"
                ]

                .get(field)
            )

            if not field_result:
                continue

            # Only evaluate fields that
            # actually exist in ground truth.

            if not field_result[
                "expected_missing"
            ]:

                total_present_fields += 1

                if field_result["correct"]:

                    correct_present_fields += 1

    # ========================================================
    # PROCESSING TIME
    # ========================================================

    average_time = (

        sum(
            r["processing_time"]
            for r in results
        )

        / total_documents

        if total_documents

        else 0
    )

    # ========================================================
    # RETURN SUMMARY
    # ========================================================

    return {

        "total_documents":
            total_documents,

        "successful_documents":
            successful,

        "success_rate":
            round(
                successful
                / total_documents
                * 100,
                2
            )
            if total_documents
            else 0,

        "invalid_json_count":
            invalid_json,

        "invalid_json_rate":
            round(
                invalid_json
                / total_documents
                * 100,
                2
            )
            if total_documents
            else 0,

        "schema_valid_count":
            schema_valid,

        "schema_valid_rate":
            round(
                schema_valid
                / total_documents
                * 100,
                2
            )
            if total_documents
            else 0,

        "business_validation_failures":
            business_failures,

        "business_validation_failure_rate":
            round(
                business_failures
                / total_documents
                * 100,
                2
            )
            if total_documents
            else 0,

        "average_field_accuracy":
            round(
                average_accuracy,
                2
            ),

        "total_present_fields":
            total_present_fields,

        "correct_present_fields":
            correct_present_fields,

        "present_field_accuracy":
            round(
                correct_present_fields
                / total_present_fields
                * 100,
                2
            )
            if total_present_fields
            else 0,

        "exact_match_count":
            exact_matches,

        "exact_match_rate":
            round(
                exact_matches
                / total_documents
                * 100,
                2
            )
            if total_documents
            else 0,

        "expected_missing_fields":
            expected_missing,

        "correctly_missing_fields":
            correctly_missing,

        "missing_field_detection_rate":
            round(
                correctly_missing
                / expected_missing
                * 100,
                2
            )
            if expected_missing
            else 100,

        "unexpected_missing_fields":
            unexpected_missing,

        "average_processing_time":
            round(
                average_time,
                2
            )
    }


# ============================================================
# DIGITAL / SCANNED SUMMARY
# ============================================================

def calculate_group_summary(
    results,
    document_type
):

    group = [

        r

        for r in results

        if r["document_type"]
        == document_type
    ]

    if not group:

        return None

    total = len(group)

    return {

        "documents":
            total,

        "average_field_accuracy":
            round(

                sum(
                    r["field_accuracy"]
                    for r in group
                )
                / total,

                2
            ),

        "exact_match_rate":
            round(

                sum(
                    r["exact_match"]
                    for r in group
                )
                / total
                * 100,

                2
            ),

        "present_field_accuracy":
            calculate_present_field_accuracy(
                group
            ),

        "business_validation_failure_rate":
            round(

                sum(
                    r[
                        "business_validation_failed"
                    ]
                    for r in group
                )
                / total
                * 100,

                2
            ),

        "average_processing_time":
            round(

                sum(
                    r["processing_time"]
                    for r in group
                )
                / total,

                2
            ),

        "unexpected_missing_fields":
            sum(

                r[
                    "unexpected_missing_fields"
                ]

                for r in group
            )
    }


# ============================================================
# PRESENT FIELD ACCURACY FOR A GROUP
# ============================================================

def calculate_present_field_accuracy(
    results
):

    total = 0

    correct = 0

    for result in results:

        if not result["success"]:
            continue

        for field in FIELDS:

            field_result = (

                result[
                    "field_results"
                ]

                .get(field)
            )

            if not field_result:
                continue

            if not field_result[
                "expected_missing"
            ]:

                total += 1

                if field_result["correct"]:

                    correct += 1

    if total == 0:

        return 0

    return round(
        correct
        / total
        * 100,
        2
    )


# ============================================================
# FIELD PERFORMANCE
# ============================================================

def calculate_field_summary(results):

    field_summary = {}

    for field in FIELDS:

        correct = 0

        total = 0

        expected_missing = 0

        correctly_missing = 0

        present_total = 0

        present_correct = 0

        for result in results:

            if not result["success"]:
                continue

            field_result = (

                result[
                    "field_results"
                ]

                .get(field)
            )

            if not field_result:
                continue

            total += 1

            if field_result["correct"]:

                correct += 1

            # --------------------------------------------
            # Missing field
            # --------------------------------------------

            if field_result[
                "expected_missing"
            ]:

                expected_missing += 1

                if field_result[
                    "predicted_missing"
                ]:

                    correctly_missing += 1

            # --------------------------------------------
            # Present field
            # --------------------------------------------

            else:

                present_total += 1

                if field_result[
                    "correct"
                ]:

                    present_correct += 1

        field_summary[field] = {

            "accuracy":
                round(
                    correct
                    / total
                    * 100,
                    2
                )
                if total
                else 0,

            "correct":
                correct,

            "total":
                total,

            "present_field_accuracy":
                round(
                    present_correct
                    / present_total
                    * 100,
                    2
                )
                if present_total
                else 0,

            "present_correct":
                present_correct,

            "present_total":
                present_total,

            "expected_missing":
                expected_missing,

            "correctly_missing":
                correctly_missing,

            "missing_detection_rate":
                round(
                    correctly_missing
                    / expected_missing
                    * 100,
                    2
                )
                if expected_missing
                else 100
        }

    return field_summary


# ============================================================
# MAIN
# ============================================================

def main():

    pdf_files = sorted(

        DOCUMENTS_DIR.glob(
            "*.pdf"
        )
    )

    if not pdf_files:

        print(
            "No PDF files found."
        )

        return

    results = []

    print("\n")

    print("=" * 70)

    print(
        "INVOICE DOCUMENT INTELLIGENCE EVALUATION"
    )

    print("=" * 70)

    print(
        f"\nFound {len(pdf_files)} documents."
    )

    # ========================================================
    # PROCESS DOCUMENTS
    # ========================================================

    for index, pdf_path in enumerate(
        pdf_files,
        start=1
    ):

        print(
            f"\n[{index}/{len(pdf_files)}] "
            f"Processing {pdf_path.name}"
        )

        ground_truth_path = (

            GROUND_TRUTH_DIR

            / f"{pdf_path.stem}.json"
        )

        if not ground_truth_path.exists():

            print(
                "Ground truth not found. "
                "Skipping."
            )

            continue

        result = evaluate_invoice(

            pdf_path,

            ground_truth_path
        )

        results.append(result)

        print(
            f"Type: "
            f"{result['document_type']}"
        )

        print(
            f"Accuracy: "
            f"{result['field_accuracy']}%"
        )

        print(
            f"Exact match: "
            f"{result['exact_match']}"
        )

        print(
            f"Processing time: "
            f"{result['processing_time']} sec"
        )

        if result[
            "unexpected_missing_fields"
        ]:

            print(
                "Unexpected missing fields: "
                f"{result['unexpected_missing_fields']}"
            )

        if result[
            "business_validation_failed"
        ]:

            print(
                "Business validation: FAILED"
            )

    # ========================================================
    # CALCULATE SUMMARIES
    # ========================================================

    summary = calculate_summary(
        results
    )

    digital_summary = (
        calculate_group_summary(
            results,
            "digital"
        )
    )

    scanned_summary = (
        calculate_group_summary(
            results,
            "scanned"
        )
    )

    field_summary = (
        calculate_field_summary(
            results
        )
    )

    # ========================================================
    # COMPLETE JSON REPORT
    # ========================================================

    report = {

        "overall":
            summary,

        "digital":
            digital_summary,

        "scanned":
            scanned_summary,

        "field_performance":
            field_summary,

        "documents":
            results
    }

    json_path = (

        REPORTS_DIR
        / "evaluation_report.json"
    )

    with open(
        json_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            indent=4,
            default=str
        )

    # ========================================================
    # CSV REPORT
    # ========================================================

    csv_path = save_csv_report(
        results
    )

    # ========================================================
    # OVERALL SUMMARY
    # ========================================================

    print("\n")

    print("=" * 70)

    print(
        "OVERALL EVALUATION SUMMARY"
    )

    print("=" * 70)

    print(
        f"\nDocuments evaluated: "
        f"{summary['total_documents']}"
    )

    print(
        f"Success rate: "
        f"{summary['success_rate']}%"
    )

    print(
        f"Invalid JSON rate: "
        f"{summary['invalid_json_rate']}%"
    )

    print(
        f"Schema validation rate: "
        f"{summary['schema_valid_rate']}%"
    )

    print(
        f"Average field accuracy: "
        f"{summary['average_field_accuracy']}%"
    )

    print(
        f"Present-field accuracy: "
        f"{summary['present_field_accuracy']}%"
    )

    print(
        f"Exact match rate: "
        f"{summary['exact_match_rate']}%"
    )

    print(
        f"Expected missing fields: "
        f"{summary['expected_missing_fields']}"
    )

    print(
        f"Correctly detected missing fields: "
        f"{summary['correctly_missing_fields']}"
    )

    print(
        f"Missing-field detection rate: "
        f"{summary['missing_field_detection_rate']}%"
    )

    print(
        f"Unexpected missing fields: "
        f"{summary['unexpected_missing_fields']}"
    )

    print(
        f"Business validation failure rate: "
        f"{summary['business_validation_failure_rate']}%"
    )

    print(
        f"Average processing time: "
        f"{summary['average_processing_time']} sec"
    )

    # ========================================================
    # DIGITAL VS SCANNED
    # ========================================================

    print("\n")

    print("=" * 70)

    print(
        "DIGITAL VS SCANNED"
    )

    print("=" * 70)

    if digital_summary:

        print("\nDIGITAL PDFs")

        print(
            f"Documents: "
            f"{digital_summary['documents']}"
        )

        print(
            f"Average field accuracy: "
            f"{digital_summary['average_field_accuracy']}%"
        )

        print(
            f"Present-field accuracy: "
            f"{digital_summary['present_field_accuracy']}%"
        )

        print(
            f"Exact match rate: "
            f"{digital_summary['exact_match_rate']}%"
        )

        print(
            f"Average processing time: "
            f"{digital_summary['average_processing_time']} sec"
        )

        print(
            f"Unexpected missing fields: "
            f"{digital_summary['unexpected_missing_fields']}"
        )

    if scanned_summary:

        print("\nSCANNED PDFs")

        print(
            f"Documents: "
            f"{scanned_summary['documents']}"
        )

        print(
            f"Average field accuracy: "
            f"{scanned_summary['average_field_accuracy']}%"
        )

        print(
            f"Present-field accuracy: "
            f"{scanned_summary['present_field_accuracy']}%"
        )

        print(
            f"Exact match rate: "
            f"{scanned_summary['exact_match_rate']}%"
        )

        print(
            f"Average processing time: "
            f"{scanned_summary['average_processing_time']} sec"
        )

        print(
            f"Unexpected missing fields: "
            f"{scanned_summary['unexpected_missing_fields']}"
        )

    # ========================================================
    # FIELD PERFORMANCE
    # ========================================================

    print("\n")

    print("=" * 70)

    print(
        "FIELD PERFORMANCE"
    )

    print("=" * 70)

    for field, data in field_summary.items():

        print(
            f"\n{field}:"
        )

        print(
            f"  Overall accuracy: "
            f"{data['accuracy']}%"
        )

        print(
            f"  Correct: "
            f"{data['correct']}/"
            f"{data['total']}"
        )

        print(
            f"  Present-field accuracy: "
            f"{data['present_field_accuracy']}%"
        )

        print(
            f"  Present fields correct: "
            f"{data['present_correct']}/"
            f"{data['present_total']}"
        )

        if data[
            "expected_missing"
        ]:

            print(
                f"  Expected missing: "
                f"{data['expected_missing']}"
            )

            print(
                f"  Missing detected correctly: "
                f"{data['correctly_missing']}"
            )

            print(
                f"  Missing detection rate: "
                f"{data['missing_detection_rate']}%"
            )

    # ========================================================
    # REPORT LOCATIONS
    # ========================================================

    print("\n")

    print("=" * 70)

    print(
        "REPORTS GENERATED"
    )

    print("=" * 70)

    print(
        f"\nCSV: "
        f"{csv_path}"
    )

    print(
        f"JSON: "
        f"{json_path}"
    )


# ============================================================
# RUN PROGRAM
# ============================================================

if __name__ == "__main__":

    main()
    