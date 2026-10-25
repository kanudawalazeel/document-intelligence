# AI-Powered Document Intelligence & Structured Data Extraction

An AI-powered document processing pipeline that extracts structured information from invoices and other business documents such as purchase orders, forms, resumes, and contracts.

The system supports digital and scanned PDFs, OCR-based text extraction, LLM-powered structured extraction, Pydantic schema validation, business-rule validation, error handling, retry mechanisms, and automatic LLM fallback.

---

## 🚀 Features

- 📄 PDF document processing
- 🔍 Automatic detection of digital vs scanned PDFs
- 🖨️ OCR for scanned documents using Tesseract
- 🤖 LLM-based structured information extraction
- 📦 Pydantic schema validation
- ✅ Business-rule validation
- 🔄 Retry mechanism for LLM failures
- 🔀 Automatic fallback from Groq to Gemini
- 🛠️ Invalid JSON handling and schema repair
- ⚠️ Meaningful error handling
- 🌐 FastAPI REST API
- 📊 Extraction performance evaluation
- 🧪 Automated tests for major pipeline components
- 🔐 Environment-based API key management
- 📈 Prompt comparison and evaluation support
- 🐳 Docker containerization
- ⚙️ Docker Compose support
- 🔄 Development reload using Docker bind mounts

---

## 🏗️ System Architecture

```text
                    ┌─────────────────────┐
                    │   PDF / Document    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Document Processor  │
                    └──────────┬──────────┘
                               │
                     ┌─────────┴─────────┐
                     │                   │
                 Digital PDF        Scanned PDF
                     │                   │
                     ▼                   ▼
              PDF Text             OCR Processing
              Extraction             (Tesseract)
                     │                   │
                     └─────────┬─────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    LLM Manager      │
                    │                     │
                    │  Primary: Groq      │
                    │  Fallback: Gemini   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Structured Invoice  │
                    │        JSON         │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Pydantic Validation │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Business Validation│
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   FastAPI Response  │
                    └─────────────────────┘
```

---

## 📁 Project Structure

```text
document-intelligence/
│
├── evaluation/
│   ├── api_evaluate.py
│   ├── evaluate.py
│   └── prompt_comparison.py
│
├── src/
│   ├── main.py
│   │
│   └── document_processor/
│       ├── __init__.py
│       ├── document_processor.py
│       ├── errors.py
│       ├── gemini_provider.py
│       ├── groq_extractor.py
│       ├── groq_provider.py
│       ├── invoice_pipeline.py
│       ├── llm_manager.py
│       ├── llm_provider.py
│       ├── logging_config.py
│       ├── ocr.py
│       ├── pdf_extractor.py
│       ├── schemas.py
│       └── validators.py
│
├── tests/
│   ├── test_business_validation.py
│   ├── test_gemini_provider.py
│   ├── test_groq_extraction.py
│   ├── test_image_ocr.py
│   ├── test_invalid_json.py
│   ├── test_invoice_pipeline.py
│   ├── test_llm_fallback.py
│   ├── test_llm_manager.py
│   ├── test_llm_provider.py
│   ├── test_ocr.py
│   ├── test_ocr_failure.py
│   ├── test_pdf_extraction.py
│   ├── test_pdf_to_image.py
│   ├── test_pipeline_fallback.py
│   ├── test_scanned_pdf.py
│   ├── test_schema.py
│   ├── test_schema_repair.py
│   └── test_validator.py
│
├── .dockerignore
├── .gitignore
├── compose.yaml
├── Dockerfile
├── README.md
└── requirements.txt
```

> Invoice datasets, ground-truth files, generated reports, API keys, virtual environments, and temporary files are intentionally excluded from the repository.

---

## 🔄 Processing Pipeline

The system processes a document through the following stages.

### 1. Document Upload

The FastAPI endpoint accepts PDF documents.

The API validates:

- File type
- File size
- Upload request
- Processing errors

---

### 2. PDF Text Extraction

For digital PDFs, text is extracted directly using PyMuPDF.

If meaningful text is found:

```text
Digital PDF detected
        ↓
Direct text extraction
```

---

### 3. OCR Processing

If the PDF does not contain usable text, the system automatically switches to OCR.

```text
Scanned PDF
     ↓
PDF pages → Images
     ↓
Tesseract OCR
     ↓
Extracted text
```

OCR includes retry logic with alternate processing configurations to improve reliability for difficult scanned documents.

---

### 4. LLM Extraction

The extracted document text is passed to an LLM to identify predefined invoice fields.

The system uses:

**Primary provider:** Groq

**Fallback provider:** Gemini

The LLM manager includes retry and fallback handling so that temporary failures from the primary provider do not necessarily stop the complete pipeline.

---

### 5. Structured Output

The extracted information is converted into a structured Pydantic model.

Example:

```json
{
  "vendor_name": "ABC Textiles",
  "invoice_number": "INV-1001",
  "invoice_date": "2026-05-04",
  "due_date": null,
  "line_items": [
    {
      "description": "Cotton Fabric",
      "hsn_sac": "5208",
      "quantity": 100,
      "unit": "Meter",
      "unit_price": 85.5,
      "amount": 8550
    }
  ],
  "subtotal": 8550,
  "discount": 100,
  "freight": 200,
  "cgst": 778.5,
  "sgst": 778.5,
  "igst": null,
  "tax": 1557,
  "round_off": 0,
  "total": 10207
}
```

---

## 📋 Invoice Schema

The system currently extracts fields including:

### Invoice Information

- Vendor name
- Invoice number
- Invoice date
- Due date

### Line Items

- Description
- HSN/SAC
- Quantity
- Unit
- Unit price
- Amount

### Financial Information

- Subtotal
- Discount
- Freight
- CGST
- SGST
- IGST
- Total tax
- Round off
- Final total

---

## ✅ Validation

The project uses two levels of validation.

### Schema Validation

Pydantic verifies that the extracted response follows the expected structure and data types.

This helps detect:

- Invalid field types
- Missing required structures
- Incorrect JSON structure
- Invalid values

### Business Validation

Additional business rules verify logical consistency.

Examples:

```text
Quantity must be greater than 0
Unit price cannot be negative
Invoice date cannot be after due date
Subtotal + tax should match total
Line item description should be present
```

Validation errors are returned as meaningful messages rather than silently accepting incorrect data.

---

## 🔄 Error Handling & Fallback

The pipeline is designed to handle common real-world failures.

### OCR Failure

```text
OCR attempt
    ↓
Failure
    ↓
Retry with alternate configuration
    ↓
Failure
    ↓
Meaningful OCR error
```

### LLM Failure

```text
Groq
  ↓
Retry
  ↓
Failure
  ↓
Gemini fallback
  ↓
Structured extraction
```

### Invalid JSON

If the LLM returns malformed JSON, the pipeline attempts to repair and validate the response before returning a final result.

### Schema Failure

Invalid structured output is detected through Pydantic validation and handled through the schema-repair flow.

### Multiple Provider Failure

If both the primary and fallback LLM providers fail, the pipeline returns a controlled error response instead of crashing.

---

## 🌐 FastAPI

The project exposes the document-processing pipeline through FastAPI.

Start the API with:

```powershell
uvicorn src.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

FastAPI interactive documentation:

```text
http://127.0.0.1:8000/docs
```

The API accepts a PDF document and returns structured invoice information or a meaningful error response.

---

## 🐳 Docker

The project supports Docker for containerized execution.

### Build the Docker image

```powershell
docker build -t document-intelligence .
```

### Run the Docker container

```powershell
docker run --name document-intelligence-container -p 8000:8000 --env-file .env document-intelligence:latest
```

The API will then be available at:

```text
http://localhost:8000/docs
```

The Docker image installs Tesseract OCR inside the container so scanned-document processing works without requiring a local Tesseract installation.

---

## ⚙️ Docker Compose

The project also includes Docker Compose configuration.

Start the application:

```powershell
docker compose up -d
```

Check running services:

```powershell
docker compose ps
```

View application logs:

```powershell
docker compose logs
```

Stop the services:

```powershell
docker compose down
```

The Compose configuration uses a bind mount for the source code and Uvicorn reload mode during development.

```text
Local src/
    ↓
Docker bind mount
    ↓
/app/src
    ↓
Uvicorn --reload
```

This allows source-code changes to be reflected inside the running development container without rebuilding the image for every code change.

---

## 🔐 Environment Variables

API keys are stored in a local `.env` file.

Example:

```env
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
```

Never commit `.env` to GitHub.

The `.gitignore` file prevents environment files from being uploaded.

---

## ⚙️ Installation

### 1. Clone the repository

```powershell
git clone https://github.com/kanudawalazeel/document-intelligence.git
cd document-intelligence
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

### 3. Activate the environment

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```powershell
pip install -r requirements.txt
```

### 5. Configure API keys

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
```

### 6. Run the application

```powershell
uvicorn src.main:app --reload
```

---

## 🧪 Running Tests

Tests are located inside:

```text
tests/
```

Run all tests using:

```powershell
pytest
```

The test suite covers areas such as:

- PDF extraction
- OCR
- OCR failure handling
- Schema validation
- Schema repair
- Business validation
- Invalid JSON
- LLM providers
- LLM fallback
- Pipeline fallback
- Invoice processing

---

## 📊 Evaluation

The project includes evaluation scripts for measuring extraction performance.

```text
evaluation/
├── evaluate.py
├── api_evaluate.py
└── prompt_comparison.py
```

The evaluation framework can measure metrics such as:

- Field-level accuracy
- Exact match rate
- API success rate
- Pipeline success rate
- Processing time
- Prompt performance

### Evaluation Dataset

Invoice datasets and ground-truth files used for evaluation are intentionally **not included in this GitHub repository**.

This keeps the repository lightweight and prevents private or sample document data from being unnecessarily exposed.

---

## 📈 Evaluation Results

A previous 40-document evaluation produced the following results:

| Metric | Result |
|---|---:|
| Documents tested | 40 |
| API success rate | 100.00% |
| Pipeline success rate | 100.00% |
| Average field accuracy | 99.38% |
| Exact match rate | 95.00% |
| Average API processing time | 4.45 sec |

These results are dependent on the evaluation dataset, model/provider configuration, prompts, and runtime environment.

---

## 🧰 Technologies Used

| Technology | Purpose |
|---|---|
| Python | Core programming language |
| FastAPI | REST API |
| Pydantic | Structured schema and validation |
| PyMuPDF | PDF text extraction |
| Tesseract OCR | Scanned document OCR |
| Pillow | Image processing |
| Groq | Primary LLM provider |
| Gemini | Fallback LLM provider |
| pytest | Testing |
| Docker | Containerization |
| Docker Compose | Container orchestration |
| Git/GitHub | Version control |

---

## 🎯 Project Goals

The project focuses on building a reliable document-intelligence pipeline capable of handling real-world document-processing challenges.

Key goals include:

- Automating document information extraction
- Supporting both digital and scanned PDFs
- Producing reliable structured JSON
- Validating extracted information
- Handling malformed or incomplete LLM responses
- Providing LLM fallback mechanisms
- Exposing the pipeline through an API
- Measuring extraction quality and performance
- Improving robustness using real-world documents
- Supporting containerized deployment and development

---

## 🔮 Future Improvements

Potential future improvements include:

- Support for additional document types
- More advanced OCR preprocessing
- Improved table extraction
- Additional LLM providers
- Configurable fallback providers
- Asynchronous document processing
- Background job processing
- API authentication
- More extensive evaluation datasets
- Improved confidence scoring for extracted fields
- Production-ready monitoring and observability

---

## 👨‍💻 Author

**Zeel Kanudawala**
