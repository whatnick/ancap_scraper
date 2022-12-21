"""Parse PDF and save image of the safety data table
main library : https://pypi.org/project/pypdfium2/
"""
import sys
import os

import pypdfium2 as pdfium


def get_table(doc,id=None):
    if(id is None):
        # Get metadata from file name
        fname = os.path.basename(doc)
        id = fname.split("_")[-1].replace(".pdf","")
    pdf = pdfium.PdfDocument(doc)
    version = pdf.get_version()  # get the PDF standard version
    n_pages = len(pdf)  # get the number of pages in the document
    print(version, n_pages)
    page_indices = [i for i in range(n_pages)]  # all pages
    renderer = pdf.render_to(
        pdfium.BitmapConv.pil_image,
        page_indices=page_indices,
        scale=300 / 72,  # 300dpi resolution
    )
    images = []
    for i, image in zip(page_indices, renderer):
        out_img = f"out_{i}_{id}.jpg"
        images.append(out_img)
        image.save(out_img)
    return images


if __name__ == "__main__":
    get_table(sys.argv[1])
