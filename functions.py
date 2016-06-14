import asciidata
import subprocess
import pyfits
import galsim
import numpy as np
import matplotlib.pyplot as plt
from astropy.table import Table, Column

def make_line(point1, point2):
    """Return slope and intercept of line joining point 1 and point2"""
    x1 = point1[0]
    y1 = point1[1]
    x2 = point2[0]
    y2 = point2[1]
    slope = (y2-y1)/(x2-x1)
    intercept = -1*slope*x1+y1
    return (slope, intercept)

def is_below_boundary(x, y, x_div, y_div, slope, intercept, x_max):
    """Return True if point lies within x_div y_div or if it lies 
    under line with given slope and intercept"""
    output = True
    if x < x_div and y > y_div:
        output = False
    if x > x_div and y > slope*x + intercept:
        output = False
    if x > x_max:
        output = False
    return output

def is_below_boundary_table(x, y, x_div, y_div, slope, intercept, x_max):
    """Return True if point lies within x_div y_div or if it lies 
    under line with given slope and intercept"""
    cond1 = (x < x_div) & (y > y_div)
    cond2 = (x > x_div) & (y > slope*x + intercept)
    cond3 = x > x_max
    q, = np.where(cond1 ^ cond2 ^ cond3)
    return q

def lies_within(x_min, x_max, y_min, y_max,
	           A,B,C,D):
    """Return True if point lines within box with end points A,B,C,D"""
    (left_m, left_b) = make_line(A,B)
    (top_m, top_b) = make_line(B,C)
    (right_m, right_b) = make_line(C,D)
    (bottom_m, bottom_b) = make_line(D,A)
    cond1 = y_max < left_m*x_min+left_b
    cond2 = y_max < top_m*x_min+top_b
    cond3 = y_max < right_m*x_max+right_b
    cond4 = y_min > bottom_m*x_min+bottom_b
    if (cond1 and cond2 and cond3 and cond4):
    	return True
    else:
    	return False

def lies_within_table(x_min, x_max, y_min, y_max,
               A,B,C,D):
    """Return True if point lines within box with end points A,B,C,D"""
    (left_m, left_b) = make_line(A,B)
    (top_m, top_b) = make_line(B,C)
    (right_m, right_b) = make_line(C,D)
    (bottom_m, bottom_b) = make_line(D,A)
    cond1 = y_max < left_m*x_min+left_b
    cond2 = y_max < top_m*x_min+top_b
    cond3 = y_max < right_m*x_max+right_b
    cond4 = y_min > bottom_m*x_min+bottom_b
    return cond1 & cond2 & cond3 & cond4

def renumber(catalog):
    "Renumber detected objects while saving old number as well. Use asciidata"
    for i in range(catalog.nrows):
        catalog['OLD_NUMBER'][i] = catalog['NUMBER'][i]
        catalog['NUMBER'][i] = i
    catalog['OLD_NUMBER'].set_colcomment("Original detection number by sextractor")
    return catalog

def renumber_table(catalog):
    "Renumber detected objects while saving old number as well. Use astropy table"
    old = np.zeros(len(catalog))
    for i in range(len(catalog)):
        old [i] = catalog['NUMBER'][i]
        catalog['NUMBER'][i] = i
    col = Column(old, name='OLD_NUMBER', 
                 description="Original detection number by sextractor", dtype=int)
    catalog.add_column(col)
    return catalog

def mask_it(catalog):
    """Make mask =1 if inside diffraction spike or boundary"""   
    for i in range(catalog.nrows):
        catalog['IN_MASK'][i] = 1
        if (catalog['IN_BOUNDARY'][i] == 1) and \
           (catalog['IN_DIFF_MASK'][i] == 0):
           catalog['IN_MASK'][i] = 0
    return catalog

def mask_it_table(catalog):
    """Make mask =1 if inside diffraction spike or boundary"""  
    val = np.ones(len(catalog))
    val[np.where((catalog['IN_BOUNDARY'] == 1) & (catalog['IN_DIFF_MASK'] == 0))] = 0
    col = Column(val, name='IN_MASK', 
                 description="Inside a masked region", dtype=int)
    catalog.add_column(col)
    return catalog

def select_good_stars(catalog, nstars=25):
    """Return indices of nstars with the highest SNR in catalog."""
    dtype = [('snr', float), ('index',int)]
    values = np.array([(-np.inf,-1)], dtype=dtype)
    for i in range(catalog.nrows):
        if (catalog['IS_STAR'][i] == 1) and (catalog['IN_MASK'][i] == 0):
            values = np.append(values, np.array([(catalog['SNR'][i],
                                                catalog['NUMBER'][i])],dtype=dtype))
    best_stars = np.sort(values, order='snr')[-nstars:]['index']
    #print 'Best Stars [SNR, ID]', np.sort(values, order='snr')[-nstars:]
    return best_stars

def select_good_stars_table(catalog, nstars=25):
    """Return indices of nstars with the highest SNR in catalog."""
    new_catalog = catalog[np.where((catalog['IS_STAR'] == 1) & (catalog['IN_MASK'] == 0))]
    new_catalog.sort('SNR')
    best_stars = np.array(new_catalog['NUMBER'][-nstars:])
    return best_stars

def get_subImage(x0,y0, L, image,
                 out_dir, out_name, save_img=False):

    f = pyfits.open(image)
    image_data = f[0].data
    f.close()
    img = galsim.Image(image_data)
    xmin = int(x0 - L/2.)
    xmax = xmin + L
    ymin = int(y0 - L/2.)
    ymax = ymin + L
    b = galsim.BoundsI(xmin, xmax, ymin, ymax)
    sub = img.subImage(b)
    if save_img:
        try:
            sub.write(out_dir+out_name+".fits")
        except:
            subprocess.call(["mkdir", out_dir])
            sub.write(out_dir+out_name+".fits")
    return sub
def get_subImage_pyfits(x0,y0, L, image,
                 out_dir, out_name, save_img=False):

    f = pyfits.open(image)
    img = f[0].data
    f.close()
    xmin = int(x0 - L/2.)
    xmax = xmin + L
    ymin = int(y0 - L/2.)
    ymax = ymin + L
    sub_img = img[ymin:ymax, xmin:xmax]
    if save_img:
        try:
            sub_img.write(out_dir+out_name+".fits")
        except:
            subprocess.call(["mkdir", out_dir])
            sub_img.write(out_dir+out_name+".fits")
    return sub_img


##### Check #######
def rotate(x,y,x0,y0,theta):
    theta = np.radians(theta)
    x_rotated = []
    y_rotated = []
    for i in range(len(x)):
        x_rotated.append(np.cos(theta)*x[i]-np.sin(theta)*y[i]+(1-np.cos(theta))*x0+np.sin(theta)*y0)
        y_rotated.append(np.sin(theta)*x[i]+np.cos(theta)*y[i]-np.sin(theta)*x0+(1-np.cos(theta))*y0)
    return [x_rotated,y_rotated]

def rotate_table(x,y,x0,y0,theta):
    theta = np.radians(theta)
    x_rotated = np.cos(theta)*x - np.sin(theta)*y + (1-np.cos(theta))*x0 + np.sin(theta)*y0
    y_rotated = np.sin(theta)*x +np.cos(theta)*y - np.sin(theta)*x0 + (1-np.cos(theta))*y0
    return [x_rotated,y_rotated]

def get_closest_tt(x0,y0,tt_table,dist=200.):    
    x = tt_table.T[0]
    y = tt_table.T[1]
    d = ((x-x0)**2+(y-y0)**2)**0.5 
    best = np.argmin(d)
    if (abs(x0-x[best]) < dist and abs(y0-y[best]) < dist):
        return [x[best],y[best]]
    else:
        return False


def inpoly(px,py,x,y):
    crossings = 0
    x = np.array(x)
    y = np.array(y)
    x = np.append(x,x[0])
    y = np.append(y,y[0])
    #Change to px,py coordinate system
    x = x - px
    y = y - py
    if sum(y) - sum(abs(y)) == 0 or sum(y) + sum(abs(y)) == 0:
        return 0
    for i in range(len(x)-1):
        Ax = x[i]
        Ay = y[i]
        Bx = x[i+1]
        By = y[i+1]
        if Ay*By < 0:
            if Ax>0 and Bx>0:
                crossings += 1
            else:
                c = Ax-(Ay*(Bx-Ax))/(By-Ay)
                if c > 0:
                    crossings += 1
    return crossings % 2


def set_col_any(arr, buff, set_to):
    """Set the column value to set_to that are within buff of any non zero value in arr"""
    s = arr.shape
    for i in range(s[1]):
        temp = arr[:,i]
        q, = np.where(temp!=0)
        d = np.array([range(j-buff,j+buff+1) for j in q])
        d = d.reshape(1,d.size)[0]
        d = d[np.where((d>=0) &(d<s[0]))]
        if len(d) != 0: 
            temp[d]= set_to
        arr[:,i]=temp
    return arr

def seg_expand(seg, val=0, buff=20, set_to=-1):
    """Expand the seg map by buffering buff pixels around pixel val """
    arr = np.array(seg).copy()
    temp1 = set_col_any(arr, buff, set_to)
    temp2 = set_col_any(arr.T, buff, set_to).T
    new_seg = np.minimum(temp1, temp2)
    return arr


#################    