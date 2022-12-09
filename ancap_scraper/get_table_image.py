"""Parse PDF and save image of the safety data table
main library : https://pypi.org/project/pypdfium2/
"""
import sys
import pypdfium2 as pdfium


def get_table(doc):
    pdf = pdfium.PdfDocument(doc)
    version = pdf.get_version()  # get the PDF standard version
    n_pages = len(pdf)  # get the number of pages in the document
    print(version, n_pages)
    page_indices = [i for i in range(n_pages)]  # all pages
    n_digits = 2
    renderer = pdf.render_to(
        pdfium.BitmapConv.pil_image,
        page_indices=page_indices,
        scale=300 / 72,  # 300dpi resolution
    )
    for i, image in zip(page_indices, renderer):
        image.save("out_%0*d.jpg" % (n_digits, i))


if __name__ == "__main__":
    get_table(sys.argv[1])
