# Machine learning training dataset for table detection
Annotations captured using [makesense](https://makesense.ai)

## Yolov5
- Clone YoloV5 repository
- Prepare datasets from images and annotations stored here using `prepare_yolov5.py`
- Place `ancap_table_data.yaml` in data folder in the YoloV5 repository to prime training
- Run training `python train.py --img 640 --cfg yolov5s.yaml --hyp hyp.scratch-high.yaml --batch 32 --epochs 100 --data ancap_table_data.yaml --weights yolov5s.pt --workers 24 --name ancap_table_det`