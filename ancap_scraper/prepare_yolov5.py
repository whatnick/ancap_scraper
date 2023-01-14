import sys
import os
import shutil
from sklearn.model_selection import train_test_split

data_path = sys.argv[1]

images_dir = os.path.join(data_path,"images")
labels_dir = os.path.join(data_path,"labels")

# Read images and annotations
images = [os.path.join(images_dir, x) for x in os.listdir(images_dir) if x[-3:] == "jpg"]
annotations = [os.path.join(labels_dir, x) for x in os.listdir(labels_dir) if ((x[-3:] == "txt") and (not "labels.txt" in x))]

# Filter images with valid annotations
if len(images) > len(annotations):
    print("Not all images are annotated")
    images = [x[:-4].replace("labels","images")+".jpg" for x in annotations]

images.sort()
annotations.sort()

print(f"Found {len(images)} labelled images")

# Split the dataset into train-valid-test splits 
train_images, val_images, train_annotations, val_annotations = train_test_split(images, annotations, test_size = 0.2, random_state = 1)
val_images, test_images, val_annotations, test_annotations = train_test_split(val_images, val_annotations, test_size = 0.5, random_state = 1)

#Utility function to copy images 
def copy_files_to_folder(list_of_files, destination_folder):
    for f in list_of_files:
        try:
            shutil.copy(f, destination_folder)
        except:
            print(f)
            assert False

# Run to create staging area for dataset
# mkdir images/train images/val images/test labels/train labels/val labels/test
# Clean out previous cuts
# rm images/*/*.jpg labels/*/*.txt

# Move the splits into their folders
copy_files_to_folder(train_images, os.path.join(images_dir,'train'))
copy_files_to_folder(val_images, os.path.join(images_dir,'val'))
copy_files_to_folder(test_images, os.path.join(images_dir,'test'))
copy_files_to_folder(train_annotations, os.path.join(labels_dir,'train'))
copy_files_to_folder(val_annotations, os.path.join(labels_dir,'val'))
copy_files_to_folder(test_annotations, os.path.join(labels_dir,'test'))