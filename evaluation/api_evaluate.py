import json
import time
import sys
from pathlib import Path

import requests


# ============================================================
# PROJECT PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(
    0,
    str(PROJECT_ROOT)
)

DOCUMENTS_DIR = (
    PROJECT_ROOT
    / "evaluation"
    / "documents"
)

GROUND_TRUTH_DIR = (
    PROJECT_ROOT
    / "evaluation"
    / "ground_truth"
)


# ============================================================
# FASTAPI URL
# ============================================================

API_URL = (
    "http://127.0.0.1:8000"
    "/extract-invoice"
)


# ============================================================
# DOCUMENTS TO TEST
# ============================================================

TEST_DOCUMENTS = sorted(
    path.name
    for path in DOCUMENTS_DIR.glob("*.pdf")
)


# ============================================================
# FIELDS
# ============================================================

FIELDS = [
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "due_date",
    "line_items",
    "subtotal",
    "tax",
    "total",
]


# ============================================================
# NORMALIZE VALUES
# ============================================================

def normalize_value(value):

    # Normalize strings
    if isinstance(value, str):

        return value.strip()

    # Normalize lists recursively
    if isinstance(value, list):

        return [
            normalize_value(item)
            for item in value
        ]

    # Normalize dictionaries recursively
    if isinstance(value, dict):

        return {
            key: normalize_value(val)
            for key, val in value.items()
        }

    return value


# ============================================================
# COMPARE FIELDS
# ============================================================

def compare_field(
    predicted,
    actual
):

    predicted = normalize_value(
        predicted
    )

    actual = normalize_value(
        actual
    )

    return predicted == actual


# ============================================================
# LOAD GROUND TRUTH
# ============================================================

def load_ground_truth(
    document_name
):

    ground_truth_path = (
        GROUND_TRUTH_DIR
        / f"{Path(document_name).stem}.json"
    )

    with open(
        ground_truth_path,
        "r",
        encoding="utf-8"
    ) as file:

        return json.load(file)


# ============================================================
# EVALUATE ONE DOCUMENT
# ============================================================

def evaluate_document(
    document_name
):

    pdf_path = (
        DOCUMENTS_DIR
        / document_name
    )

    ground_truth = (
        load_ground_truth(
            document_name
        )
    )

    print("\n" + "=" * 70)

    print(
        f"Testing: {document_name}"
    )

    print("=" * 70)

    start_time = time.perf_counter()

    try:

        # ====================================================
        # SEND REQUEST TO FASTAPI
        # ====================================================

        with open(
            pdf_path,
            "rb"
        ) as file:

            response = requests.post(

                API_URL,

                files={
                    "file": (
                        document_name,
                        file,
                        "application/pdf"
                    )
                },

                timeout=120
            )

        processing_time = (
            time.perf_counter()
            - start_time
        )

        print(
            f"HTTP status: "
            f"{response.status_code}"
        )

        print(
            f"API processing time: "
            f"{processing_time:.2f} sec"
        )


        # ====================================================
        # HTTP ERROR
        # ====================================================

        if response.status_code != 200:

            print(
                "API request failed."
            )

            print(
                response.text
            )

            return {

                "document":
                    document_name,

                "success":
                    False,

                "status_code":
                    response.status_code,

                "processing_time":
                    round(
                        processing_time,
                        2
                    ),

                "field_accuracy":
                    0,

                "exact_match":
                    False,

                "error":
                    response.text
            }


        # ====================================================
        # PARSE RESPONSE JSON
        # ====================================================

        try:

            api_result = (
                response.json()
            )

        except ValueError:

            print(
                "API returned invalid JSON."
            )

            return {

                "document":
                    document_name,

                "success":
                    False,

                "status_code":
                    response.status_code,

                "processing_time":
                    round(
                        processing_time,
                        2
                    ),

                "field_accuracy":
                    0,

                "exact_match":
                    False,

                "error":
                    "API returned invalid JSON."
            }


        # ====================================================
        # EXTRACT FASTAPI DATA
        # ====================================================
        #
        # Expected FastAPI structure:
        #
        # {
        #     "success": true,
        #     "request_id": "...",
        #     "status": "COMPLETED",
        #     "data": {
        #         "success": true,
        #         "errors": [],
        #         "invoice": {
        #             ...
        #         },
        #         "metrics": {
        #             ...
        #         }
        #     }
        # }
        #
        # ====================================================

        data = api_result.get(
            "data",
            {}
        )


        # ====================================================
        # CHECK DATA OBJECT
        # ====================================================

        if not isinstance(
            data,
            dict
        ):

            print(
                "Invalid API response: "
                "'data' is not an object."
            )

            return {

                "document":
                    document_name,

                "success":
                    False,

                "status_code":
                    response.status_code,

                "processing_time":
                    round(
                        processing_time,
                        2
                    ),

                "field_accuracy":
                    0,

                "exact_match":
                    False,

                "error":
                    "API response 'data' is invalid."
            }


        # ====================================================
        # CHECK PIPELINE SUCCESS
        # ====================================================

        pipeline_success = data.get(
            "success",
            False
        )

        if not pipeline_success:

            print(
                "Pipeline returned "
                "success=false"
            )

            print(
                "Errors:",
                data.get(
                    "errors",
                    []
                )
            )


        # ====================================================
        # EXTRACT INVOICE
        # ====================================================

        predicted_invoice = data.get(
            "invoice",
            {}
        )


        # ====================================================
        # SAFETY CHECK
        # ====================================================

        if not isinstance(
            predicted_invoice,
            dict
        ):

            predicted_invoice = {}


        # ====================================================
        # FIELD COMPARISON
        # ====================================================

        correct_fields = 0

        field_results = {}


        for field in FIELDS:

            predicted = (
                predicted_invoice.get(
                    field
                )
            )

            actual = (
                ground_truth.get(
                    field
                )
            )

            correct = compare_field(
                predicted,
                actual
            )

            if correct:

                correct_fields += 1


            field_results[field] = {

                "correct":
                    correct,

                "predicted":
                    normalize_value(
                        predicted
                    ),

                "actual":
                    normalize_value(
                        actual
                    )
            }


        # ====================================================
        # CALCULATE FIELD ACCURACY
        # ====================================================

        field_accuracy = (

            correct_fields
            / len(FIELDS)
            * 100
        )


        # ====================================================
        # EXACT MATCH
        # ====================================================

        exact_match = (

            correct_fields
            == len(FIELDS)
        )


        # ====================================================
        # PRINT RESULT
        # ====================================================

        print(
            f"Field accuracy: "
            f"{field_accuracy:.2f}%"
        )

        print(
            f"Exact match: "
            f"{exact_match}"
        )


        # ====================================================
        # FIELD DETAILS
        # ====================================================

        for field, result in (
            field_results.items()
        ):

            status = (

                "PASS"

                if result["correct"]

                else "FAIL"
            )

            print(
                f"  {field}: "
                f"{status}"
            )


        # ====================================================
        # PRINT PIPELINE ERRORS IF ANY
        # ====================================================

        business_validation_errors = (
            data.get(
                "errors",
                []
            )
        )


        if business_validation_errors:

            print(
                "\nBusiness validation "
                "errors:"
            )

            for error in (
                business_validation_errors
            ):

                print(
                    f"  - {error}"
                )


        # ====================================================
        # RETURN RESULT
        # ====================================================

        return {

            "document":
                document_name,

            "success":
                True,

            "status_code":
                response.status_code,

            "processing_time":
                round(
                    processing_time,
                    2
                ),

            "field_accuracy":
                round(
                    field_accuracy,
                    2
                ),

            "exact_match":
                exact_match,

            "pipeline_success":
                pipeline_success,

            "business_validation_errors":
                business_validation_errors,

            "field_results":
                field_results,

            "error":
                ""
        }


    # ========================================================
    # REQUEST TIMEOUT
    # ========================================================

    except requests.exceptions.Timeout:

        processing_time = (
            time.perf_counter()
            - start_time
        )

        print(
            "API request timed out."
        )

        return {

            "document":
                document_name,

            "success":
                False,

            "status_code":
                None,

            "processing_time":
                round(
                    processing_time,
                    2
                ),

            "field_accuracy":
                0,

            "exact_match":
                False,

            "error":
                "API request timed out."
        }


    # ========================================================
    # CONNECTION ERROR
    # ========================================================

    except requests.exceptions.ConnectionError as error:

        processing_time = (
            time.perf_counter()
            - start_time
        )

        print(
            "Could not connect to FastAPI."
        )

        print(
            f"Error: {error}"
        )

        return {

            "document":
                document_name,

            "success":
                False,

            "status_code":
                None,

            "processing_time":
                round(
                    processing_time,
                    2
                ),

            "field_accuracy":
                0,

            "exact_match":
                False,

            "error":
                f"FastAPI connection error: {error}"
        }


    # ========================================================
    # UNEXPECTED ERROR
    # ========================================================

    except Exception as error:

        processing_time = (
            time.perf_counter()
            - start_time
        )

        print(
            f"Unexpected error: "
            f"{error}"
        )

        return {

            "document":
                document_name,

            "success":
                False,

            "status_code":
                None,

            "processing_time":
                round(
                    processing_time,
                    2
                ),

            "field_accuracy":
                0,

            "exact_match":
                False,

            "error":
                str(error)
        }


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")

    print("=" * 70)

    print(
        "FASTAPI INVOICE EVALUATION"
    )

    print("=" * 70)

    print(
        f"\nAPI endpoint:"
        f"\n{API_URL}"
    )

    print(
        f"\nDocuments found: "
        f"{len(TEST_DOCUMENTS)}"
    )


    results = []


    # ========================================================
    # TEST EACH DOCUMENT
    # ========================================================

    for document in TEST_DOCUMENTS:

        pdf_path = (
            DOCUMENTS_DIR
            / document
        )

        if not pdf_path.exists():

            print(
                f"\nFile not found: "
                f"{pdf_path}"
            )

            continue


        result = evaluate_document(
            document
        )

        results.append(
            result
        )


    # ========================================================
    # CHECK RESULTS
    # ========================================================

    if not results:

        print(
            "\nNo documents were evaluated."
        )

        return


    # ========================================================
    # SUCCESSFUL API REQUESTS
    # ========================================================

    successful = [

        result

        for result in results

        if result["success"]
    ]


    total = len(
        results
    )


    successful_count = len(
        successful
    )


    # ========================================================
    # AVERAGE FIELD ACCURACY
    # ========================================================

    average_accuracy = (

        sum(
            result[
                "field_accuracy"
            ]

            for result in successful
        )
        / successful_count

        if successful_count

        else 0
    )


    # ========================================================
    # EXACT MATCH COUNT
    # ========================================================

    exact_matches = sum(

        result[
            "exact_match"
        ]

        for result in successful
    )


    # ========================================================
    # AVERAGE PROCESSING TIME
    # ========================================================

    average_time = (

        sum(
            result[
                "processing_time"
            ]

            for result in successful
        )
        / successful_count

        if successful_count

        else 0
    )


    # ========================================================
    # PIPELINE SUCCESS COUNT
    # ========================================================

    pipeline_successes = sum(

        1

        for result in successful

        if result.get(
            "pipeline_success",
            False
        )
    )


    # ========================================================
    # PIPELINE SUCCESS RATE
    # ========================================================

    pipeline_success_rate = (

        pipeline_successes
        / total
        * 100

        if total

        else 0
    )


    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("\n")

    print("=" * 70)

    print(
        "FASTAPI EVALUATION SUMMARY"
    )

    print("=" * 70)


    print(
        f"\nDocuments tested: "
        f"{total}"
    )


    print(
        f"Successful API requests: "
        f"{successful_count}/{total}"
    )


    print(
        f"API success rate: "
        f"{successful_count / total * 100:.2f}%"
    )


    print(
        f"Pipeline success rate: "
        f"{pipeline_success_rate:.2f}%"
    )


    print(
        f"Average field accuracy: "
        f"{average_accuracy:.2f}%"
    )


    print(
        f"Exact match rate: "
        f"{exact_matches / successful_count * 100:.2f}%"

        if successful_count

        else
        "Exact match rate: 0%"
    )


    print(
        f"Average API processing time: "
        f"{average_time:.2f} sec"
    )


    # ========================================================
    # SAVE RESULT
    # ========================================================

    report_path = (

        PROJECT_ROOT
        / "evaluation"
        / "reports"
        / "api_evaluation_report.json"
    )


    report_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )


    report = {

        "api_url":
            API_URL,

        "documents_tested":
            total,

        "successful_requests":
            successful_count,

        "api_success_rate":
            round(
                successful_count
                / total
                * 100,
                2
            ),

        "pipeline_successes":
            pipeline_successes,

        "pipeline_success_rate":
            round(
                pipeline_success_rate,
                2
            ),

        "average_field_accuracy":
            round(
                average_accuracy,
                2
            ),

        "exact_match_rate":
            round(
                exact_matches
                / successful_count
                * 100,
                2
            )

            if successful_count

            else 0,

        "average_processing_time":
            round(
                average_time,
                2
            ),

        "documents":
            results
    }


    with open(
        report_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            indent=4
        )


    print(
        f"\nReport saved to:"
    )


    print(
        report_path
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()