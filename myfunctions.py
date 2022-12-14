from PIL import Image
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.io
import plotly.express as px
from scipy import ndimage as ndi
import tensorflow
import imageio
from skimage.segmentation import flood, flood_fill
from scipy import signal
import tensorflow_probability as tfp
import tensorflow as tf
from tqdm import tqdm


def event_separation(data):
    #this function takes in the data from the excel file and splits them into a nested list: each list within the nested list corresponds to the excel lines of a single division 
    #it differentiates the lines based on conditions on both frame number and x,y-distance that could potentially be changed if they don't work
    length_of_file=len(data)-1
    all_event_lines=[]
    single_divison_events=[]
    for excelindex in range(0,length_of_file):
        framedataline1= data.iloc[excelindex,1] 
        framedataline2= data.iloc[excelindex+1,1] 
        framediff= abs(framedataline2-framedataline1)

        ydistancedataline1= data.iloc[excelindex,2]
        ydistancedataline2= data.iloc[excelindex+1,2]
        ydistancediff= abs(ydistancedataline2-ydistancedataline1)

        xdistancedataline1= data.iloc[excelindex,2]
        xdistancedataline2= data.iloc[excelindex+1,2]
        xdistancediff= abs(xdistancedataline2-xdistancedataline1)

        if framediff < 10 and ydistancediff <  10 and xdistancediff < 10 :
            single_divison_events.append(excelindex)
            if excelindex == length_of_file-1:
                single_divison_events.append(excelindex+1)
                all_event_lines.append(single_divison_events)
        else:
            single_divison_events.append(excelindex)
            all_event_lines.append(single_divison_events)
            single_divison_events=[]
    return all_event_lines


def image_crop_save(l,list_of_divisions, data, img, outputname):   
    division_list=[]
    for index_list in range(0, l):
        l1=len(list_of_divisions[index_list])
        division_list=[]

        for index_list1 in range(0,l1):
            division_list.append(list_of_divisions[index_list][index_list1])
            minlist=division_list[0]
            maxlist=division_list[index_list1]

        data_croped= data.iloc[minlist:maxlist,1:4]
        frame1=int(data_croped['axis-0'].min())
        frame2=int(data_croped['axis-0'].max())
        ymean = data_croped['axis-1'].mean()
        xmean = data_croped['axis-2'].mean()
        ycrop1=ymean+128
        ycrop2=ymean-128
        xcrop1=xmean+128
        xcrop2=xmean-128

        if ycrop1 > 2048:                           #safety conditions in case pics are at the edges
            ycrop1=2048
            ycrop2=1792
        if xcrop1 > 2048:
            xcrop1=2048
            xcrop2=1792
        
        dataar=np.zeros((frame2-frame1, 256, 256))

        for frame_index, frame_number in enumerate(range (frame1, frame2)):
            img.seek(frame_number) #starts from 0 I think?
            box = (xcrop2, ycrop2, xcrop1, ycrop1) #choose dimensions of box
            imcrop= img.crop(box)
        
            dataar[frame_index, :, :] = np.array(imcrop)
        currname_crop = f'{outputname}_{index_list}.tiff'
        imageio.mimwrite(currname_crop, (dataar).astype(np.uint16))   



def image_crop_save_gauss(l,list_of_divisions, data, img, outputname):   
    division_list=[]
    for index_list in range(0, l):
        l1=len(list_of_divisions[index_list])
        division_list=[]

        for index_list1 in range(0,l1):
            division_list.append(list_of_divisions[index_list][index_list1])
            minlist=division_list[0]
            maxlist=division_list[index_list1]

        data_croped= data.iloc[minlist:maxlist,1:4]
        frame1=int(data_croped['axis-0'].min())
        frame2=int(data_croped['axis-0'].max())
        ymean = data_croped['axis-1'].mean()
        xmean = data_croped['axis-2'].mean()
        ycrop1=ymean+128
        ycrop2=ymean-128
        xcrop1=xmean+128
        xcrop2=xmean-128

        if ycrop1 > 2048:                           #safety conditions in case pics are at the edges
            ycrop1=2048
            ycrop2=1792
        if xcrop1 > 2048:
            xcrop1=2048
            xcrop2=1792

        dataar_gauss=np.zeros((frame2-frame1, 256, 256))

        for frame_index, frame_number in enumerate(range (frame1, frame2)):
            img.seek(frame_number) #starts from 0 I think?
            box = (xcrop2, ycrop2, xcrop1, ycrop1) #choose dimensions of box
            imcrop= img.crop(box)
        
            dataar_gauss[frame_index, :, :] = np.array(imcrop)
        currname_crop_gauss = f'{outputname}_{index_list}gauss.tiff'

        imageio.mimwrite(currname_crop_gauss, (dataar_gauss).astype(np.uint8))

def get_gaussian(mu, sigma, size):
    mu = ((mu[1]+0.5-0.5*size[1])/(size[1]*0.5), (mu[0]+0.5-0.5*size[0])/(size[0]*0.5))
    sigma = (sigma[0]/size[0], sigma[1]/size[1])
    mvn = tfp.distributions.MultivariateNormalDiag(loc=mu, scale_diag=sigma)
    x,y = tf.cast(tf.linspace(-1,1,size[0]),tf.float32), tf.cast(tf.linspace(-1,1,size[1]), tf.float32)
    # meshgrid as a list of [x,y] coordinates
    coords = tf.reshape(tf.stack(tf.meshgrid(x,y),axis=-1),(-1,2)).numpy()
    gauss = mvn.prob(coords)
    return tf.reshape(gauss, size)


def image_crop_negative(l,list_of_divisions, data, img, outputname):
    division_list=[]
    for index_list in range(0, l):
        l1=len(list_of_divisions[index_list])
        division_list=[]

        for index_list1 in range(0,l1):
            division_list.append(list_of_divisions[index_list][index_list1])
            minlist=division_list[0]
            maxlist=division_list[index_list1]

        data_croped_after_event= data.iloc[minlist:maxlist,1:4]
        
        frame_number_max=int(data_croped_after_event['axis-0'].max())
        if frame_number_max<90:
            frame1_after=frame_number_max
            frame2_after=frame_number_max+10
            ymean_after = data_croped_after_event['axis-1'].mean()
            xmean_after = data_croped_after_event['axis-2'].mean()
            y_moved_lower=ymean_after+64
            y_moved_upper=ymean_after+320
            x_moved_lower=xmean_after+64
            x_moved_upper=xmean_after+320
            if y_moved_upper>2048 and x_moved_upper>2048:
                y_moved_lower=ymean_after-320
                y_moved_upper=ymean_after-64
                x_moved_lower=xmean_after-320
                x_moved_upper=xmean_after-64
            elif y_moved_upper<2048 and x_moved_upper>2048:
                y_moved_lower=ymean_after+64
                y_moved_upper=ymean_after+320
                x_moved_lower=xmean_after-320
                x_moved_upper=xmean_after-64
            elif y_moved_upper>2048 and x_moved_upper<2048:
                y_moved_lower=ymean_after-320
                y_moved_upper=ymean_after-64
                x_moved_lower=xmean_after+64
                x_moved_upper=xmean_after+320



            dataar_a=np.zeros((frame2_after-frame1_after, 256, 256))

            for frame_index_a, frame_number_a in enumerate(range (frame1_after, frame2_after)):
                img.seek(frame_number_a) #starts from 0 I think?
                box_a = (x_moved_lower, y_moved_lower, x_moved_upper, y_moved_upper) #choose dimensions of box
                imcrop= img.crop(box_a)
                
                dataar_a[frame_index_a, :, :] = np.array(imcrop)
        
            currname_crop_a = f'{outputname}_{index_list}_neg.tiff' 
            imageio.mimwrite(currname_crop_a, (dataar_a).astype(np.uint16))


## AUGMENTATION OF DATA (I need to go through this again) ##

def augImg(input_img, output_img, transform, **kwargs):
    input_mask = (input_img>0).astype(np.uint8)
    transformed = transform(image=input_img, image0=output_img)
    
    aug_input_img, aug_output_img= transformed['image'], transformed['image0']
    
    # aug_fission_coords = preprocessing.fissionCoords(aug_labels, aug_output_img)
    # aug_output_img, aug_fission_props = preprocessing.prepareProc(aug_output_img, coords=aug_fission_coords, **kwargs)
    return aug_input_img.astype(np.uint8), aug_output_img
    

def augStack(input_data, output_data, transform, **kwargs):
    aug_input_data = np.zeros(input_data.shape, dtype=np.uint8)
    aug_output_data = np.zeros(output_data.shape, dtype=np.float32)
    
    for i in tqdm(range(input_data.shape[0]), total=input_data.shape[0]):
        aug_input_data[i], aug_output_data[i]= augImg(input_data[i], output_data[i], transform, **kwargs)
    return aug_input_data, aug_output_data