import os
import sys
import pickle
import shutil
import argparse

import numpy as np
import pandas as pd
from PIL import Image
from skimage.io import imread
from skimage.transform import resize
from sklearn import svm
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix)
from sklearn.model_selection import GridSearchCV, train_test_split


# Based on : https://github.com/ShanmukhVegi/Image-Classification/blob/main/Shanmukh_Classification.ipynb
CATEGORIES = ["noughts", "crosses", "dashes","sun", "donut"]
DATADIR = "./training"
TRAINING_IMG_SIZE = [113,47]

def main():
    args = parse_args()
    if not args.fname is None:
        predict(args.fname)
        sys.exit()
    else:
        if args.sample:
            create_training_data()
        if args.train:
            train()        

def parse_args():
    parser = argparse.ArgumentParser(
                    description = 'This program manages the SVM classifier for training table symbols to feature availability conversion',
                    epilog = 'Please train or use the classifier')
    parser.add_argument('-f', '--filename', dest="fname", default=None)           # Sample image to classify after training
    parser.add_argument('-t', '--train',dest="train",default=True)      # Run classifier script in training mode to refine SVM
    parser.add_argument('-s', '--sample',dest="sample",default=False)    # Run classifier script in sample generation mode to seed SVM
    return parser.parse_args()

def train():
    flat_data_arr = []
    target_arr = []
    # please use datadir='/content' if the files are upload on to google collab
    # else mount the drive and give path of the parent-folder containing all category images folders.
    
    for i in CATEGORIES:
        print(f"loading... category : {i}")
        path = os.path.join(DATADIR, i)
        for img in os.listdir(path):
            img_array = imread(os.path.join(path, img))
            img_resized = resize(img_array, (150, 150, 3))
            flat_data_arr.append(img_resized.flatten())
            target_arr.append(CATEGORIES.index(i))
        print(f"loaded category:{i} successfully")
    flat_data = np.array(flat_data_arr)
    target = np.array(target_arr)
    df = pd.DataFrame(flat_data)
    df["Target"] = target
    print(df)

    x = df.iloc[:, :-1]
    y = df.iloc[:, -1]
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.20, random_state=77, stratify=y
    )
    print("Splitted Successfully")

    param_grid = {
        "C": [0.1, 1, 10, 100],
        "gamma": [0.0001, 0.001, 0.1, 1],
        "kernel": ["rbf", "poly"],
    }
    svc = svm.SVC(probability=True)
    print(
        "The training of the model is started, please wait for while as it may take few minutes to complete"
    )
    model = GridSearchCV(svc, param_grid)
    model.fit(x_train, y_train)
    print("The Model is trained well with the given images")
    print(model.best_params_)

    y_pred = model.predict(x_test)
    print("The predicted Data is :")
    print(y_pred)

    print("The actual data is:")
    print(np.array(y_test))

    pickle.dump(model, open("img_model.p", "wb"))
    print("Pickle is dumped successfully")

def create_training_data():
    """Read templates and dump randomly on white background
    to create training data
    """
    templates = {
        "crosses" : "data/template_x.jpg",
        "noughts" : "data/template_o.jpg",
        "donut"   : "data/template_d.jpg",
        "dashes"  : "data/template_-.jpg",
        "sun"     : "data/template_s.jpg"
    }
    for k,v in templates:
        out_path = os.path.join("training",k)
        background = Image.new(size=TRAINING_IMG_SIZE)
        Image.open(v)
        

def predict(url,encrich=False):
    img=imread(url)
    img_resize=resize(img,(150,150,3))
    l=[img_resize.flatten()]
    model=pickle.load(open('img_model.p','rb'))
    probability=model.predict_proba(l)
    for ind,val in enumerate(CATEGORIES):
        result = CATEGORIES[model.predict(l)[0]]
        proba = probability[0][ind]
        if encrich and  proba > 0.7:
            try:
                print(f"Enriching class {val} for {proba} ")
                shutil.move(url,os.path.join(DATADIR,result))
            except:
                pass
    return result

if __name__ == "__main__":
    main()