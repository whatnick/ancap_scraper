"""PyTorch and transformers based table detection
"""
import sys

from transformers import DetrImageProcessor, DetrForObjectDetection
from transformers import AutoFeatureExtractor, AutoModelForObjectDetection

import torch
from PIL import Image

def main():
        url = sys.argv[1]
        image = Image.open(url)

        extract_taha(image)
        extract_ms(image)

def extract_taha(image : Image):
        processor = DetrImageProcessor.from_pretrained("table-detect/taha")
        model = DetrForObjectDetection.from_pretrained("table-detect/taha")

        inputs = processor(images=image, return_tensors="pt")
        outputs = model(**inputs)

        # convert outputs (bounding boxes and class logits) to COCO API
        # let's only keep detections with score > 0.9
        target_sizes = torch.tensor([image.size[::-1]])
        results = processor.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=0.9)[0]
        print(results)

        for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
                box = [round(i, 2) for i in box.tolist()]
                print(
                        f"Detected {model.config.id2label[label.item()]} with confidence "
                        f"{round(score.item(), 3)} at location {box}"
                )

def extract_ms(image : Image):
        extractor = AutoFeatureExtractor.from_pretrained("table-detect/microsoft")
        model = AutoModelForObjectDetection.from_pretrained("table-detect/microsoft")

        inputs = extractor(images=image, return_tensors="pt")
        outputs = model(**inputs)

        # convert outputs (bounding boxes and class logits) to COCO API
        # let's only keep detections with score > 0.9
        target_sizes = torch.tensor([image.size[::-1]])
        results = extractor.post_process_object_detection(outputs, target_sizes=target_sizes, threshold=0.9)[0]
        print(results)

        for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
                box = [round(i, 2) for i in box.tolist()]
                print(
                        f"Detected {model.config.id2label[label.item()]} with confidence "
                        f"{round(score.item(), 3)} at location {box}"
                )

if __name__ == "__main__":
        main()
