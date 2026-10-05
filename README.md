# AI-Powered Document Intelligence & Structured Data Extraction

An AI-powered document processing system that extracts structured invoice information from digital and scanned PDF documents, validates the extracted data, handles errors and retries, and exposes the complete pipeline through a FastAPI API.

The project demonstrates a production-oriented document AI workflow:

**Document → Text Extraction/OCR → LLM Extraction → Structured JSON → Pydantic Validation → Business Validation → API Response → Evaluation**

---

## 1. Project Overview

The objective of this project is to automate information extraction from unstructured documents such as invoices.

The system can:

* Accept PDF documents.
* Extract text from digital PDFs.
* Automatically detect scanned/image-based PDFs.
* Apply OCR when a PDF does not contain extractable text.
* Use an LLM to extract predefined invoice fields.
* Generate structured JSON output.
* Validate the output using Pydantic.
* Apply business-rule validation.
* Handle missing and ambiguous information.
* Retry temporary extraction failures.
* Expose the extraction pipeline through FastAPI.
* Evaluate the system using a 40-document dataset.
* Compare two different prompting strategies.

---

# 2. System Workflow

                PDF Invoice
                    |
                    v
          +---------------------+
          | Document Processing |
          +---------------------+
                    |
             +------+------+
             |             |
        Digital PDF    Scanned PDF
             |             |
        PDF Text       OCR using
        Extraction     Tesseract
             |             |
             +------+------+
                    |
                    v
             Extracted Text
                    |
                    v
          +---------------------+
          |     Groq LLM        |
          | Structured          |
          | Extraction          |
          +---------------------+
                    |
                    v
             Structured JSON
                    |
                    v
          +---------------------+
          | Pydantic Validation |
          +---------------------+
                    |
                    v
          +---------------------+
          | Business Validation |
          +---------------------+
                    |
                    v
             Final Result
                    |
                    v
               FastAPI

---

# 3. Main Features

## Document Processing

The system supports:

* Digital PDF text extraction.
* Scanned PDF detection.
* OCR-based text extraction.
* Automatic selection between normal PDF extraction and OCR.

For digital PDFs, PyMuPDF is used.

For scanned PDFs, pages are converted into images and processed using Tesseract OCR.

---

## LLM-Based Extraction

The project uses Groq with the:

```text
openai/gpt-oss-20b
```

model.

The LLM extracts predefined invoice fields and returns structured JSON.

The extraction prompt instructs the model to:

* Extract only information present in the document.
* Avoid guessing.
* Return `null` for missing information.
* Extract all line items.
* Normalize dates.
* Preserve numerical values.
* Treat placeholders such as `MISSING`, `N/A`, `NA`, `UNKNOWN`, `-`, and `NOT PROVIDED` as missing values.

---

# 4. Extracted Invoice Fields

The system extracts:

### Invoice-level fields

* Vendor name
* Invoice number
* Invoice date
* Due date
* Subtotal
* Tax
* Total

### Line-item fields

* Description
* Quantity
* Unit price

Example:

```json
{
  "vendor_name": "ABC Pvt Ltd",
  "invoice_number": "INV-2026-001",
  "invoice_date": "2026-09-15",
  "due_date": "2026-10-15",
  "line_items": [
    {
      "description": "Laptop",
      "quantity": 2,
      "unit_price": 50000
    }
  ],
  "subtotal": 100000,
  "tax": 18000,
  "total": 118000
}
```

---

# 5. Pydantic Schema Validation

Pydantic is used to ensure that the LLM output follows the expected data structure.

The main schema contains:

```text
Invoice
 ├── vendor_name
 ├── invoice_number
 ├── invoice_date
 ├── due_date
 ├── line_items
 │    ├── description
 │    ├── quantity
 │    └── unit_price
 ├── subtotal
 ├── tax
 └── total
```

Pydantic validates:

* Data types.
* Date formats.
* List structures.
* Nested line-item structures.
* Required structural fields.

---

# 6. Business Validation

Schema validation alone does not guarantee that the invoice information makes business sense.

Therefore, additional business rules are applied.

Examples:

* Vendor name must exist.
* Invoice number must exist.
* Invoice date must exist.
* At least one line item must exist.
* Line-item description must exist.
* Quantity must be greater than zero.
* Unit price cannot be negative.
* Invoice date cannot be after due date.
* Subtotal must exist.
* Tax must exist.
* Total must exist.
* `subtotal + tax` must match the invoice total within a small tolerance.

Example:

```text
Subtotal = 1000
Tax      = 180
Total    = 1180

1000 + 180 = 1180
```

The invoice passes this business validation rule.

---

# 7. Error Handling and Retry Mechanism

The project includes handling for:

* Empty documents.
* Unsupported file types.
* Large files.
* Documents with no extractable text.
* OCR processing issues.
* Empty LLM responses.
* Invalid JSON.
* Schema validation failures.
* Missing fields.
* Business validation failures.
* Unexpected server errors.

The Groq extraction function supports retries.

The retry mechanism uses increasing wait times:

```text
Attempt 1
   |
   v
Failure
   |
   v
Wait
   |
   v
Attempt 2
   |
   v
Failure
   |
   v
Wait
   |
   v
Attempt 3
```

This helps handle temporary extraction/API failures.

---

# 8. FastAPI

The complete pipeline is exposed through FastAPI.

Run the server using:

```powershell
uvicorn src.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

---

# 9. API Endpoint

## POST `/extract-invoice`

Upload an invoice PDF.

The API:

1. Receives the PDF.
2. Validates the uploaded file.
3. Saves it temporarily.
4. Extracts text or performs OCR.
5. Sends the text to the LLM.
6. Validates the structured output.
7. Performs business validation.
8. Returns the final JSON response.
9. Removes the temporary uploaded file.

---

# 10. Example API Response

Successful response:

```json
{
  "success": true,
  "errors": [],
  "invoice": {
    "vendor_name": "ABC Pvt Ltd",
    "invoice_number": "INV-2026-001",
    "invoice_date": "2026-09-15",
    "due_date": "2026-10-15",
    "line_items": [
      {
        "description": "Laptop",
        "quantity": 2,
        "unit_price": 50000
      }
    ],
    "subtotal": 100000,
    "tax": 18000,
    "total": 118000
  }
}
```

If business validation fails:

```json
{
  "success": false,
  "errors": [
    "Invoice date cannot be after due date."
  ],
  "invoice": {
    "..."
  }
}
```

---

# 11. API Error Handling

The API handles different classes of errors.

| Situation                   | HTTP Status |
| --------------------------- | ----------: |
| Invalid file type           |         400 |
| Empty file                  |         400 |
| File larger than 10 MB      |         413 |
| Document processing failure |         422 |
| LLM/extraction failure      |         502 |
| Unexpected server error     |         500 |

The maximum supported uploaded file size is:
10 MB

---

# 12. Project Structure

document-intelligence/
│
├── .venv/
│
├── data/
│   ├── input/
│   └── output/
│
├── evaluation/
│   ├── documents/
│   │   ├── invoice_01.pdf
│   │   ├── invoice_02.pdf
│   │   └── ...
│   │
│   ├── ground_truth/
│   │   ├── invoice_01.json
│   │   ├── invoice_02.json
│   │   └── ...
│   │
│   ├── reports/
│   │
│   ├── evaluate.py
│   ├── api_evaluate.py
│   └── prompt_comparison.py
│
├── src/
│   ├── main.py
│   │
│   ├── test_pdf_extraction.py
│   ├── test_scanned_pdf.py
│   ├── test_pdf_to_image.py
│   ├── test_image_ocr.py
│   ├── test_document_processor.py
│   ├── test_schema.py
│   ├── test_groq_extraction.py
│   ├── test_validator.py
│   └── test_invoice_pipeline.py
│
│   └── document_processor/
│       ├── __init__.py
│       ├── pdf_extractor.py
│       ├── ocr.py
│       ├── document_processor.py
│       ├── schemas.py
│       ├── groq_extractor.py
│       ├── validators.py
│       └── invoice_pipeline.py
│
├── .env
├── .gitignore
├── requirements.txt
└── README.md

---

# 13. Important Files

### `src/document_processor/pdf_extractor.py`

Responsible for extracting text from digital PDFs.

### `src/document_processor/ocr.py`

Responsible for OCR processing of scanned PDFs.

### `src/document_processor/document_processor.py`

Automatically decides whether to use normal PDF extraction or OCR.

### `src/document_processor/schemas.py`

Contains Pydantic models for structured invoice data.

### `src/document_processor/groq_extractor.py`

Handles LLM-based invoice extraction and retry logic.

### `src/document_processor/validators.py`

Contains business validation rules.

### `src/document_processor/invoice_pipeline.py`

Connects the complete document processing pipeline.

### `src/main.py`

FastAPI application.

### `evaluation/evaluate.py`

Performs internal evaluation against the ground-truth dataset.

### `evaluation/api_evaluate.py`

Evaluates the complete FastAPI pipeline.

### `evaluation/prompt_comparison.py`

Compares the basic and improved prompting strategies.

---

# 14. Evaluation Dataset

A dataset of **40 synthetic invoice documents** was created for evaluation.

The dataset contains:

```text
40 total documents
│
├── 20 digital PDFs
└── 20 scanned PDFs
```

Each document has a corresponding ground-truth JSON file.

```text
evaluation/
├── documents/
│   ├── invoice_01.pdf
│   ├── ...
│   └── invoice_40.pdf
│
└── ground_truth/
    ├── invoice_01.json
    ├── ...
    └── invoice_40.json
```

The dataset includes documents with missing information to test the system's ability to detect missing fields.

---

# 15. Evaluation Metrics

The project evaluates:

* Field-level accuracy.
* Present-field accuracy.
* Exact-match accuracy.
* Success rate.
* Invalid JSON rate.
* Schema validation failure rate.
* Business validation failure rate.
* Missing-field detection rate.
* Average processing time.
* Digital vs scanned PDF performance.
* Prompt strategy performance.

---

# 16. Internal Pipeline Evaluation

The complete internal pipeline was evaluated on 40 documents.

### Overall Results

| Metric                           |   Result |
| -------------------------------- | -------: |
| Documents evaluated              |       40 |
| Success rate                     |  100.00% |
| Invalid JSON rate                |    0.00% |
| Schema validation rate           |  100.00% |
| Average field accuracy           |   99.38% |
| Present-field accuracy           |   99.32% |
| Exact match rate                 |   95.00% |
| Missing-field detection rate     |  100.00% |
| Unexpected missing fields        |        0 |
| Business validation failure rate |   55.00% |
| Average processing time          | 4.12 sec |

The business validation failure rate includes invoices intentionally containing missing or invalid business information in the synthetic evaluation dataset. Therefore, this metric does not directly represent an LLM extraction failure rate.

---

# 17. Digital vs Scanned PDF Evaluation

| Metric                    | Digital PDFs | Scanned PDFs |
| ------------------------- | -----------: | -----------: |
| Documents                 |           20 |           20 |
| Field accuracy            |       98.75% |      100.00% |
| Present-field accuracy    |       98.68% |      100.00% |
| Exact match               |       90.00% |      100.00% |
| Average processing time   |     3.15 sec |     5.10 sec |
| Unexpected missing fields |            0 |            0 |

The scanned documents required additional OCR processing, resulting in a higher average processing time.

---

# 18. FastAPI Evaluation

The complete FastAPI endpoint was evaluated using all 40 documents.

| Metric                      |   Result |
| --------------------------- | -------: |
| Documents tested            |       40 |
| Successful API requests     |    40/40 |
| API success rate            |  100.00% |
| Average field accuracy      |   99.69% |
| Exact match rate            |   97.50% |
| Average API processing time | 3.15 sec |

This evaluation measures the complete API workflow rather than only the internal extraction function.

---

# 19. Prompt Strategy Comparison

Two prompting strategies were evaluated using:

* The same Groq model.
* The same 40-document dataset.
* The same ground-truth data.
* The same evaluation metrics.

The only major difference was the extraction prompt.

## Basic Prompt

The basic prompt provides general instructions to extract the invoice fields and return JSON.

## Improved Prompt

The improved prompt adds more explicit instructions for:

* Missing values.
* `null` handling.
* No guessing.
* Date normalization.
* Placeholder detection.
* Line-item extraction.
* Expected JSON fields.
* Accurate numerical extraction.

---

# 20. Prompt Comparison Results

| Metric                  | Basic Prompt | Improved Prompt |
| ----------------------- | -----------: | --------------: |
| Success rate            |       95.00% |     **100.00%** |
| Field accuracy          |       94.38% |      **99.69%** |
| Exact match rate        |       90.00% |      **97.50%** |
| Invalid JSON rate       |        0.00% |           0.00% |
| Schema failure rate     |        2.50% |       **0.00%** |
| Average processing time | **4.24 sec** |        6.18 sec |

### Observations

The improved prompt produced:

* A 5.00 percentage-point increase in success rate.
* A 5.31 percentage-point increase in field accuracy.
* A 7.50 percentage-point increase in exact-match rate.
* A reduction in schema failure rate from 2.50% to 0%.
* No change in invalid JSON rate.

However, the improved prompt increased average processing time from 4.24 seconds to 6.18 seconds.

This demonstrates a trade-off between extraction accuracy/reliability and processing time.

---

# 21. Field-Level Performance

The final internal evaluation showed:

| Field          | Accuracy |
| -------------- | -------: |
| Vendor name    |     100% |
| Invoice number |      95% |
| Invoice date   |     100% |
| Due date       |     100% |
| Subtotal       |     100% |
| Tax            |     100% |
| Total          |     100% |
| Line items     |     100% |

Missing-field detection was:

```text
24 / 24 = 100%
```

The system correctly detected all expected missing fields in the evaluation dataset.

---

# 22. Installation

Clone/download the project and navigate to the project directory:

```powershell
cd C:\Users\user\Desktop\document-intelligence
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

---

# 23. Environment Variables

Create a `.env` file in the project root:

```text
GROQ_API_KEY=your_groq_api_key
```

Do not commit the `.env` file to Git.

The `.gitignore` already contains:

```text
.env
```

---

# 24. Running the API

From the project root:

```powershell
uvicorn src.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

Use the `/extract-invoice` endpoint to upload a PDF.

---

# 25. Running Internal Evaluation

From the project root:

```powershell
python evaluation/evaluate.py
```

The evaluation report is generated in:

```text
evaluation/reports/
```

---

# 26. Running FastAPI Evaluation

Start the API first:

```powershell
uvicorn src.main:app --reload
```

Then, in another terminal:

```powershell
python evaluation/api_evaluate.py
```

The API evaluation report is stored in:

```text
evaluation/reports/api_evaluation_report.json
```

---

# 27. Running Prompt Comparison

From the project root:

```powershell
python evaluation/prompt_comparison.py
```

This compares:

```text
Basic Prompt
      vs
Improved Prompt
```

and generates:

```text
evaluation/reports/prompt_comparison_report.json
```

---

# 28. Technologies Used

* Python
* FastAPI
* Uvicorn
* PyMuPDF
* Tesseract OCR
* Pytesseract
* Pillow
* Pydantic
* Groq API
* OpenAI GPT-OSS-20B through Groq
* python-dotenv
* Requests

---

# 29. Limitations

The current implementation has several limitations:

1. The project currently focuses on invoice documents.
2. OCR accuracy depends on document quality.
3. Complex invoice layouts may require more advanced layout-aware processing.
4. LLM extraction can still produce occasional field-level errors.
5. Processing time increases when OCR is required.
6. The evaluation dataset contains synthetic invoices and is relatively small.
7. Only one LLM provider/model is used in the final production pipeline.
8. The current fallback mechanism primarily uses retries rather than a secondary LLM/provider.
9. Business validation rules are currently designed specifically for invoices.

---

# 30. Future Improvements

Possible future improvements include:

* Support for additional document types such as:

  * Purchase orders
  * Resumes
  * Contracts
  * Forms
* Layout-aware document understanding.
* Better table extraction.
* Multiple LLM/provider fallback.
* Confidence scoring.
* Human-in-the-loop verification.
* Database storage.
* Authentication and authorization.
* Background processing for large documents.
* Batch document processing.
* More extensive real-world evaluation datasets.
* Advanced OCR models.
* Monitoring and production logging.
* Cost and token-usage tracking.

---

# 31. Learning Outcomes

This project covers the complete workflow of a production-oriented Document AI system:

```text
Document AI
    ↓
PDF Text Extraction
    ↓
OCR
    ↓
LLM Structured Extraction
    ↓
Prompt Engineering
    ↓
JSON Output
    ↓
Pydantic Schema Validation
    ↓
Business Validation
    ↓
Error Handling
    ↓
Retry Mechanism
    ↓
FastAPI
    ↓
Evaluation
    ↓
Prompt Comparison
```

The project demonstrates how unstructured documents can be converted into reliable structured data using a combination of document processing, OCR, LLMs, schema validation, business rules, APIs, and quantitative evaluation.

---

# 32. Project Status

The major requirements of the assignment have been implemented:

* [x] PDF upload
* [x] Digital PDF text extraction
* [x] Scanned PDF OCR
* [x] Automatic document processing
* [x] LLM-based structured extraction
* [x] JSON output
* [x] Pydantic schema validation
* [x] Business-rule validation
* [x] Missing-field handling
* [x] Error handling
* [x] Retry mechanism
* [x] FastAPI integration
* [x] 40-document evaluation dataset
* [x] Field-level accuracy evaluation
* [x] Exact-match evaluation
* [x] API evaluation
* [x] Digital vs scanned evaluation
* [x] Prompt strategy comparison
* [x] Evaluation reports
* [x] README documentation

---

# 33. Summary

This project implements an end-to-end AI-powered invoice document intelligence pipeline.

It combines:

**PDF Processing + OCR + LLM Extraction + Structured JSON + Pydantic + Business Validation + Error Handling + Retry + FastAPI + Evaluation + Prompt Engineering**

The final evaluation demonstrates high extraction accuracy while also identifying the practical trade-off between improved prompt quality and processing time.