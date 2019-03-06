print("BEGIN Predict_Image_Segmentation_Model")

import os, cv2, uuid, random
import pandas as pd

from PIL import Image
from os.path import join, exists
from os import remove, listdir, makedirs
from ast import literal_eval as make_tuple

import torch
import torch.nn as nn
import torch.nn.init as init
import torch.nn.functional as F
from torch.utils.data import Dataset 

from torch.utils import model_zoo
from torchvision import models

from argparse import ArgumentParser
from torch.optim import SGD, Adam
from torch.autograd import Variable
from torchvision.transforms import Compose
from torch.utils.data import DataLoader
from torchvision.transforms import ToTensor, ToPILImage, Normalize, Resize

if 'variables' in locals():
    NUM_CLASSES   = int(str(variables.get("NUM_CLASSES")))
    DATASET_PATH  = variables.get("DATASET_PATH")
    MODEL_PATH    = variables.get("MODEL_PATH")
    NET_MODEL     = variables.get("NET_MODEL")
    NET_TRANSFORM = variables.get("NET_TRANSFORM")
    NET_CRITERION = variables.get("NET_CRITERION") 
    IMG_SIZE      = variables.get("IMG_SIZE")
    SHUFFLE       = variables.get("SHUFFLE")
    BATCH_SIZE    = int(str(variables.get("BATCH_SIZE")))
    NUM_WORKERS   = int(str(variables.get("NUM_WORKERS")))

IMG_SIZE = tuple(IMG_SIZE)

assert DATASET_PATH is not None
assert MODEL_PATH is not None
assert NET_MODEL is not None
assert NET_TRANSFORM is not None

print(MODEL_PATH)
# Load NET model
exec(NET_MODEL)
model.eval()

# Load trained model
model = torch.load(MODEL_PATH,map_location={'cuda:0': 'cpu'})

# http://pytorch.org/docs/master/cuda.html#torch.cuda.is_available
# Returns a bool indicating if CUDA is currently available.
use_gpu = torch.cuda.is_available()
if use_gpu:
    model = model.cuda()

# Load CNN transform
# data_transforms
exec(NET_TRANSFORM)

# Get an unique ID
ID = str(uuid.uuid4())

# Create an empty dir
OUTPUT_FOLDER = join('output', ID)
os.makedirs(OUTPUT_FOLDER, exist_ok=True) 
print("OUTPUT_FOLDER: " + OUTPUT_FOLDER)

# VOC12 DATASET
EXTENSIONS = ['.jpg', '.png']

def load_image(file):
    return Image.open(file)

def is_image(filename):
    return any(filename.endswith(ext) for ext in EXTENSIONS)

def image_path(root, basename, extension):
    return os.path.join(root, f'{basename}{extension}')

def image_basename(filename):
    return os.path.basename(os.path.splitext(filename)[0])

class VOC12(Dataset):
    def __init__(self, root, input_transform=None, target_transform=None):
        self.images_root = os.path.join(root, 'images')
        self.labels_root = os.path.join(root, 'classes')

        self.filenames = [image_basename(f)
          for f in os.listdir(self.labels_root) if is_image(f)]
        self.filenames.sort()

        self.input_transform = input_transform
        self.target_transform = target_transform

    def __getitem__(self, index):
        filename = self.filenames[index]

        with open(image_path(self.images_root, filename, '.jpg'), 'rb') as f:
            image = load_image(f).convert('RGB')
            file_name_image = image_path(self.images_root, filename, '.jpg')
        with open(image_path(self.labels_root, filename, '.png'), 'rb') as f:
            label = load_image(f).convert('P')
            image_size = image.size

        if self.input_transform is not None:
            image = self.input_transform(image)
        if self.target_transform is not None:
            label = self.target_transform(label)

        return image, label, image_size, file_name_image

    def __len__(self):
        return len(self.filenames)

# Load dataset
DATASET_TEST_PATH = join(DATASET_PATH, 'test')
loader = DataLoader(VOC12(DATASET_TEST_PATH, input_transform, target_transform), 
                    num_workers=NUM_WORKERS, batch_size=BATCH_SIZE, shuffle=True)

# Begin of the functions to generate mask segmenattion

def random_color():
    levels = range(32,256,32)
    return tuple(random.choice(levels) for _ in range(3))

def genetate_color():
    color_list = []
    for color in range(NUM_CLASSES):
        color_list.append(random_color())
    return color_list
 
def label_images(get_color, root):
    for color in range(NUM_CLASSES):
        img =  cv2.imread(os.path.join(OUTPUT_FOLDER, os.path.basename(root)))
        img [np.where((img ==[color,color,color]).all(axis=2))] = get_color[color]
        cv2.imwrite(os.path.join(OUTPUT_FOLDER, os.path.basename(root)), img) 

def label_binary_images(get_color, root):
    for color in range(NUM_CLASSES):
        img =  cv2.imread(os.path.join(OUTPUT_FOLDER, os.path.basename(root)))
        img [np.where((img !=[[0,0,0]]).all(axis=2))] = [3,3,3]
        img [np.where((img ==[0,0,0]).all(axis=2))] =   [248,248,255]
        cv2.imwrite(os.path.join(OUTPUT_FOLDER, os.path.basename(root)), img) 

        
# End of the functions to generate mask segmenattion  

def predict_model(_model, loader, _use_gpu):
    image_name = []
    label_name = []
    get_color = genetate_color()

    for i, (images, labels, image_size, filename_test_img) in enumerate(loader):
        if use_gpu:
            images = images.cuda()
        inputs = Variable(images)
        width, height = image_size
        width = width.numpy()
        height = height.numpy()
        file_names = ''.join((filename_test_img))
        
        if NUM_CLASSES == 1:  
            #outputs = model(Variable(images).unsqueeze(0))
            outputs = model(inputs)
            preds = outputs
        else:  
            outputs = model(inputs)
            _, preds = torch.max(outputs.data, 1)
        
        to_img = ToPILImage()

        if NUM_CLASSES == 1:
            if use_gpu:
                out = preds.cpu().detach().numpy().squeeze(axis=0).astype(np.uint8).transpose((1, 2, 0))
            else:
                out = preds.detach().numpy().squeeze(axis=0).astype(np.uint8).transpose((1, 2, 0))

        if NUM_CLASSES != 1:
            if use_gpu:
                out = preds.cpu().numpy().astype(np.uint8).transpose((1, 2, 0))
            else:
                out = preds.numpy().astype(np.uint8).transpose((1, 2, 0))
        
        im = to_img(out)
        imres = im.resize((int(width), int(height)))
        imres.save(os.path.join(OUTPUT_FOLDER, os.path.basename(file_names)))

        if NUM_CLASSES == 1:
            label_binary_images(get_color, file_names)
        else:
            label_images(get_color, file_names)
            
        print('Segmenting: ', file_names)
        
        image_name.append(filename_test_img)
        image_adress = os.path.join(OUTPUT_FOLDER, os.path.basename(file_names))
        label_name.append(image_adress)
    return image_name, label_name

image_name, label_name = predict_model(model, loader, use_gpu)

df_name = pd.DataFrame(image_name)
df_image_name = pd.DataFrame(image_name)
df_label_name = pd.DataFrame(label_name)
df_name.columns = ['Image Paths']
df_image_name.columns = ['Images']
df_label_name.columns = ['Outputs']

df = pd.concat([df_name, df_image_name, df_label_name], axis=1)

if 'variables' in locals():
    variables.put("PREDICT_DATA_JSON", df.to_json(orient='split'))
    variables.put("BATCH_SIZE", BATCH_SIZE)
    variables.put("NUM_WORKERS", NUM_WORKERS)
    variables.put("SHUFFLE", True)
    variables.put("OUTPUT_FOLDER", OUTPUT_FOLDER)
    variables.put("NUM_CLASSES", NUM_CLASSES)

print("END Predict_Image_Segmentation_Model")