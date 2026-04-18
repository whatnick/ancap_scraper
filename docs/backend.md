# Backend

The backend consists of the core data extraction pipeline (`ancap_scraper/` package) and the FastAPI query service (`services/query_api.py`). All modules in `ancap_scraper/` can be run standalone from the CLI or orchestrated as batch jobs in Argo Workflows.

## Web Scraper — `get_model.py`

Scrapes all published safety rating PDFs from the ANCAP website.

### API Flow

```
ancap.com.au/api/config
  → list of { slug, models[] } for every manufacturer
    → ancap.com.au/api/search?manufacturer_slug=X&model_slug=Y
      → list of { id, ratingYear } for each variant
        → ancap.com.au/safety-ratings/{make}/{model}/{id}
          → BeautifulSoup extracts PDF download link from button class
            → download PDF → safety_data/{make}_{model}_{year}_{id}.pdf
```

### Caching

PDF downloads are skipped if the file already exists on disk. Call with `use_cache=True` to skip the API entirely and glob existing files.

```python
from ancap_scraper.get_model import get_all_reports, glob_all_reports

# Download all (or skip existing)
all_reports = get_all_reports()

# Just list cached PDFs for a specific year
reports_2022 = glob_all_reports("2022")
```

### Authentication

Uses static browser cookies and headers defined in `headers.py`. These mimic a Chrome 108 session. If ANCAP changes their anti-bot measures, update `COOKIES` and `HEADERS`.

## PDF Renderer — `get_table_image.py`

Converts every page of a PDF to a 300 DPI JPEG image using [pypdfium2](https://pypi.org/project/pypdfium2/).

```python
from ancap_scraper.get_table_image import get_table

images = get_table("safety_data/toyota_corolla_2022_abc123.pdf")
# Returns: ["out_0_abc123.jpg", "out_1_abc123.jpg", ...]
```

The vehicle ID is extracted from the PDF filename (`{make}_{model}_{year}_{id}.pdf`). The last image typically contains the safety features table.

## Table Extraction — `get_table_content.py`

Extracts the structured safety features table from a rendered page image. This is the most complex module.

### Pipeline

```
Page image
  → Crop to features column (hard-coded bounding box)
    → Tesseract OCR → feature names (text)
  → Crop to AU availability column
    → Slice into individual symbol cells (one per feature)
      → SVM classifier → nought/cross/dash/sun/donut
        → Map to: STANDARD / NOT AVAILABLE / OPTIONAL / PREMIUM STANDARD / SUBJECT TO CHANGE
  → Repeat for NZ availability column
  → Combine into DataFrame → save to Excel
```

### Layout Versions

The bounding boxes differ by report year:

| Year Range | Layout | Details |
|---|---|---|
| 2020+ | Single table | One features column + AU/NZ columns |
| 2018-2019 | Double table | Two side-by-side tables on the same page |

Hard-coded crop coordinates are defined as constants at the top of the module. The experimental `detect_table.py` module is intended to replace these with ML-based detection.

### Key Functions

| Function | Purpose |
|---|---|
| `get_safety_table_all(image, year)` | Entry point — dispatches to 2018 or 2020+ layout handler |
| `get_safety_table_2018(image, id)` | Handles double-table layout, concatenates both DataFrames |
| `get_safety_table_2020(image, id)` | Handles single-table layout |
| `get_safety_features(image, tool, id, ...)` | Core extractor — OCR + classification for one table region |
| `get_feature_available(image, zone, country, id, ...)` | Crops and classifies each symbol cell in a column |

## SVM Classifier — `classify_result.py`

A [scikit-learn SVM](https://scikit-learn.org/stable/modules/svm.html) that classifies 150x150 resized images of table symbols into 5 categories.

### Categories

| Class | Symbol | Meaning |
|---|---|---|
| `noughts` | ○ | STANDARD |
| `crosses` | ✕ | NOT AVAILABLE |
| `dashes` | — | SUBJECT TO CHANGE |
| `sun` | ☀ | PREMIUM STANDARD |
| `donut` | ◎ | OPTIONAL |

### Training

```bash
# Train from images in training/{noughts,crosses,dashes,sun,donut}/
PYTHONPATH=. python ancap_scraper/classify_result.py --train

# Writes img_model.p (pickled GridSearchCV model)
```

Training uses `GridSearchCV` over RBF and poly kernels with C and gamma hyperparameter grids. Images are resized to 150x150x3 and flattened.

### Prediction

```python
from ancap_scraper.classify_result import predict

result = predict("test_AU_5_abc123.jpg")  # Returns: "noughts", "crosses", etc.
```

The `predict()` function also supports `enrich=True` to auto-move high-confidence predictions into training folders for dataset growth.

### Model File

`img_model.p` at the repo root is the pickled `GridSearchCV` object. It must be present for prediction to work.

## Table Detection (Experimental) — `detect_table.py`

Uses HuggingFace Transformer models to detect table bounding boxes in page images, intended to replace hard-coded crop coordinates.

### Models

| Config | Model | Backbone | Source |
|---|---|---|---|
| `table-detect/taha/` | `DetrForObjectDetection` | ResNet-50 | [TahaDouaji/detr-doc-table-detection](https://huggingface.co/TahaDouaji/detr-doc-table-detection) |
| `table-detect/microsoft/` | `TableTransformerForObjectDetection` | ResNet-18 | [microsoft/table-transformer-detection](https://huggingface.co/microsoft/table-transformer-detection) |

These models are configured locally but require downloading weights from HuggingFace on first use.

## YOLOv5 Dataset Prep — `prepare_yolov5.py`

Utility to split annotated images from `page_samples/` into train/val/test folders (80/10/10) for fine-tuning a custom YOLOv5 table detection model. Configuration is in `page_samples/ancap_table_data.yaml` (1 class: "table").

## Batch Orchestrator — `parse_all_reports.py`

Ties the pipeline together for bulk processing:

```python
for year in [2018, 2019, 2020, 2021, 2022]:
    for report in glob_all_reports(str(year)):
        images = get_table(report)        # render PDF
        table_image = images[-1]          # last page has the table
        xls = get_safety_table_all(table_image, year)  # extract
        shutil.move(xls, excel_folder)    # save Excel
```

## Query API — `services/query_api.py`

FastAPI service that implements RAG (Retrieval-Augmented Generation) over the indexed PDF data.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Health check — returns vector store status |
| `POST` | `/query` | Ask a question — returns answer + source documents |
| `POST` | `/reset` | Clear conversation memory |

### RAG Chain

```
User question
  → Bedrock Titan Embed v2 (embed query)
  → ChromaDB similarity search (top-k=4 chunks)
  → Bedrock Claude 3.5 Sonnet (generate answer with retrieved context)
  → Return answer + source PDF pages
```

### Configuration (Environment Variables)

| Variable | Default | Purpose |
|---|---|---|
| `CHROMA_HOST` | (empty = local dir) | ChromaDB server hostname |
| `CHROMA_PORT` | `8000` | ChromaDB server port |
| `CHROMA_DIR` | `/data/chromadb` | Local ChromaDB directory (if no host) |
| `BEDROCK_REGION` | `us-east-1` | AWS region for Bedrock |
| `EMBED_MODEL` | `amazon.titan-embed-text-v2:0` | Embedding model ID |
| `LLM_MODEL` | `anthropic.claude-3-5-sonnet-20241022-v2:0` | LLM model ID |
| `LLM_TEMPERATURE` | `0.3` | Generation temperature |
| `RETRIEVER_K` | `4` | Number of chunks to retrieve |

## Dependencies

All Python dependencies are in `ancap_scraper/requirements.txt`. Key libraries:

| Library | Purpose |
|---|---|
| `requests` + `beautifulsoup4` | Web scraping |
| `pypdfium2` | PDF rendering |
| `pyocr` | Tesseract OCR wrapper |
| `scikit-learn` + `scikit-image` | SVM classifier |
| `pillow` + `opencv-python` | Image manipulation |
| `pandas` + `openpyxl` | DataFrame handling + Excel I/O |
| `transformers` + `timm` | Table detection models |
| `langchain` + `chromadb` | RAG pipeline |
| `langchain-aws` + `boto3` | Bedrock integration (query API + embedder) |
| `fastapi` + `uvicorn` | Query API server |
