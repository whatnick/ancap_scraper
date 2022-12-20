# ANCAP Scraper

Designed to download all car safety tests data from ANCAP website for analysis

## Usage
- Install dependencies in a Python 3.8+ environment - *pip install -r ancap_scraper/requirements.txt*
- PDF to Images implemented using [PyPDFium2](https://readthedocs.org/projects/pypdfium2/).
- OCR implemented using [PyOCR](https://gitlab.gnome.org/World/OpenPaperwork/pyocr/-/tree/master).
- SVM Machine Learning from table symbols to variables implemented using [Scikit Learn](https://scikit-learn.org/stable/modules/svm.html).
- Install Tesseract OCR Tooling
- Run *python ancap_scraper\get_model.py* to scrape ANCAP for Data
- Run *python ancap_scraper\get_table_image.py* to render PDF to images for parsing
- Run *python ancap_scraper\get_table_content.py* to take a given page to save to Excel for features and status in AU/NZ.
- Run *python ancap_scraper\classify_result.py* to retrain SVM classifier.

## Roadmap
- Set up [template matching](https://github.com/whatnick/ancap_scraper/issues/1) to fine align area of image from which to extract table
- Use [table detection](https://github.com/asagar60/TableNet-pytorch) image analysis methods to [auto-detect location of tables](https://github.com/whatnick/ancap_scraper/issues/2) in images
  - Table Detection Code samples from Hugging Face : [Microsoft](https://huggingface.co/microsoft/table-transformer-detection), [TahaDouaji](https://huggingface.co/TahaDouaji/detr-doc-table-detection)
- [Retrain SVM](https://github.com/whatnick/ancap_scraper/issues/3) using randomly placed templates.
- Retrain Table detection and column detection using ANCAP specific dataset.
- Stitch all of the steps of the code together to run on schedule and save all results in S3 (PDF's from ANCAP) + DynamoDB (Safety Features).
- Add manual canonical safety features to error-correct OCR if that happens.
- Try Random forest and Neural Network based symbology classifiers.
- Add a web service to lookup vehicle models by particular set of safety features.
- Link to vehicle images.
- Extract test result photos for impact tests on bonnet etc.