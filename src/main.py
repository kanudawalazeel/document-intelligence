from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException
)

import shutil
import os
import uuid
import logging

from src.document_processor.invoice_pipeline import (
    process_invoice
)

from src.document_processor.logging_config import (
    setup_logging
)


setup_logging()

logger = logging.getLogger(
    "document_intelligence"
)


app = FastAPI(
    title="AI-Powered Document Intelligence API",
    description=(
        "Invoice extraction and validation API"
    ),
    version="1.0.0"
)


UPLOAD_DIR = "data/input"

MAX_FILE_SIZE = (
    10 * 1024 * 1024
)


os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


@app.get("/")
def home():

    return {
        "message": (
            "Document Intelligence API is running"
        )
    }


@app.post("/extract-invoice")
async def extract_invoice(
    file: UploadFile = File(...)
):

    # ---------------------------------------------
    # REQUEST ID
    # ---------------------------------------------

    request_id = str(
        uuid.uuid4()
    )

    logger.info(
        f"request_id={request_id} "
        f"event=request_received "
        f"filename={file.filename}"
    )

    # ---------------------------------------------
    # FILE VALIDATION
    # ---------------------------------------------

    if not file.filename:

        logger.warning(
            f"request_id={request_id} "
            f"event=invalid_file "
            f"reason=no_filename"
        )

        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "request_id": request_id,
                "stage": "document_validation",
                "status": "INVALID_FILE",
                "message": (
                    "No file was provided."
                ),
                "retryable": False
            }
        )

    if not file.filename.lower().endswith(
        ".pdf"
    ):

        logger.warning(
            f"request_id={request_id} "
            f"event=invalid_file "
            f"reason=unsupported_format"
        )

        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "request_id": request_id,
                "stage": "document_validation",
                "status": "UNSUPPORTED_FILE_TYPE",
                "message": (
                    "Only PDF files are supported."
                ),
                "retryable": False
            }
        )

    # ---------------------------------------------
    # SAVE FILE
    # ---------------------------------------------

    file_path = os.path.join(
        UPLOAD_DIR,
        file.filename
    )

    try:

        with open(
            file_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

        file_size = os.path.getsize(
            file_path
        )

        logger.info(
            f"request_id={request_id} "
            f"event=file_saved "
            f"size={file_size}"
        )

        # -----------------------------------------
        # EMPTY FILE
        # -----------------------------------------

        if file_size == 0:

            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "request_id": request_id,
                    "stage": "document_validation",
                    "status": "EMPTY_FILE",
                    "message": (
                        "Uploaded file is empty."
                    ),
                    "retryable": False
                }
            )

        # -----------------------------------------
        # FILE SIZE
        # -----------------------------------------

        if file_size > MAX_FILE_SIZE:

            raise HTTPException(
                status_code=413,
                detail={
                    "success": False,
                    "request_id": request_id,
                    "stage": "document_validation",
                    "status": "FILE_TOO_LARGE",
                    "message": (
                        "Maximum file size is 10 MB."
                    ),
                    "retryable": False
                }
            )

        # -----------------------------------------
        # PROCESS DOCUMENT
        # -----------------------------------------

        logger.info(
            f"request_id={request_id} "
            f"event=processing_started"
        )

        result = process_invoice(
            file_path
        )

        # -----------------------------------------
        # SUCCESS
        # -----------------------------------------

        if result.get("success"):

            logger.info(
                f"request_id={request_id} "
                f"event=processing_completed"
            )

            return {
                "success": True,
                "request_id": request_id,
                "status": "COMPLETED",
                "data": result
            }

        # -----------------------------------------
        # BUSINESS VALIDATION FAILURE
        # -----------------------------------------

        logger.warning(
            f"request_id={request_id} "
            f"event=business_validation_failed"
        )

        return {
            "success": False,
            "request_id": request_id,
            "status": "BUSINESS_VALIDATION_FAILED",
            "stage": "business_validation",
            "message": (
                "Invoice extraction completed, "
                "but business validation failed."
            ),
            "retryable": False,
            "errors": result.get(
                "errors",
                []
            ),
            "invoice": result.get(
                "invoice"
            )
        }

    except HTTPException:

        raise

    except ValueError as error:

        logger.error(
            f"request_id={request_id} "
            f"event=document_processing_error "
            f"error={error}"
        )

        raise HTTPException(
            status_code=422,
            detail={
                "success": False,
                "request_id": request_id,
                "stage": "document_processing",
                "status": "DOCUMENT_PROCESSING_FAILED",
                "message": str(error),
                "retryable": False
            }
        )

    except RuntimeError as error:

        error_text = str(error)

        logger.error(
            f"request_id={request_id} "
            f"event=runtime_error "
            f"error={error_text}"
        )

        # -----------------------------------------
        # DETERMINE STAGE
        # -----------------------------------------

        if "OCR_FAILED" in error_text:

            stage = "ocr"
            status = "OCR_FAILED"
            retryable = False
            http_status = 422

        elif (
            "LLM_FAILED" in error_text
            or "PRIMARY_LLM" in error_text
            or "FALLBACK_LLM" in error_text
        ):

            stage = "llm"
            status = "LLM_FAILED"
            retryable = True
            http_status = 502

        elif "SCHEMA" in error_text:

            stage = "schema_validation"
            status = "SCHEMA_VALIDATION_FAILED"
            retryable = False
            http_status = 422

        elif "INVALID_JSON" in error_text:

            stage = "json_validation"
            status = "INVALID_JSON"
            retryable = False
            http_status = 422

        else:

            stage = "processing"
            status = "PROCESSING_FAILED"
            retryable = False
            http_status = 500

        raise HTTPException(
            status_code=http_status,
            detail={
                "success": False,
                "request_id": request_id,
                "stage": stage,
                "status": status,
                "message": error_text,
                "retryable": retryable
            }
        )

    except Exception as error:

        logger.exception(
            f"request_id={request_id} "
            f"event=unexpected_error"
        )

        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "request_id": request_id,
                "stage": "unknown",
                "status": "INTERNAL_SERVER_ERROR",
                "message": (
                    "An unexpected error occurred "
                    "while processing the document."
                ),
                "retryable": False
            }
        )

    finally:

        if os.path.exists(
            file_path
        ):

            os.remove(
                file_path
            )

            logger.info(
                f"request_id={request_id} "
                f"event=temporary_file_deleted"
            )