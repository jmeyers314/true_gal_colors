import galsim
import os
import numpy as np
import functions as fn
import get_objects as go
import subprocess
import pyfits
from astropy.table import Table, Column

### rectangular postage stamps

def run(params):
    out_dir = params.out_path + params.seg_id+ '/'

    if os.path.isdir(out_dir + 'postage_stamps') is False:
            subprocess.call(["mkdir", out_dir + 'postage_stamps'])
    catalogs = []
    tt_files =[]
    #Open main catalog in all filters
    for filt in params.filters:
        cat_name = out_dir + '/' + filt + "_clean.cat"
        catalog = Table.read(cat_name, format="ascii.basic")
        col= Column(np.zeros(len(catalog)),name='IS_PSTAMP',dtype='int', description = 'created postage stamp' )
        catalog.add_column(col)
        catalogs.append(catalog)
        tt_file = params.tt_file_path + "/" + filt + "/{}_stars.txt".format(filt)
        tt_files.append(np.loadtxt(tt_file))
    # Get indices of galaxies higher than cut off SNR and not masked. 
    # ALso get their size in differnt filters  
    idx=[[],[],[],[]]    
    for i in range(len(catalogs[0])):
        x0 = catalogs[0]['X_IMAGE'][int(i)]
        y0 = catalogs[0]['Y_IMAGE'][int(i)]
        x_sizes = []
        y_sizes = []
        pos=[]
        for f,filter in enumerate(params.filters):
            cond1 = (catalogs[f]['IS_STAR'][i] == 0)
            cond2 = (catalogs[f]['IN_MASK'][i] == 0)
            cond3 = (catalogs[f]['SNR'][i] >= 4.5)
            cond4 = (catalogs[f]['MULTI_DET'][i] == 0)
            if  cond1 and cond2 and cond3 and cond4 :
                t = (catalogs[f]['THETA_IMAGE'][int(i)])*np.pi/180.
                e = catalogs[f]['ELLIPTICITY'][int(i)]
                A = 2.5*(catalogs[f]['A_IMAGE'][int(i)])*(catalogs[f]['KRON_RADIUS'][int(i)])
                x_size = A*(np.absolute(np.sin(t))+(1-e)*np.absolute(np.cos(t)))
                y_size = A*(np.absolute(np.cos(t))+(1-e)*np.absolute(np.sin(t)))
                x_sizes.append(x_size)
                y_sizes.append(y_size)            
            else:
                break
            tt_pos = fn.get_closest_tt(x0,y0,tt_files[f])
            if tt_pos:
                pos.append(tt_pos)
            else:
                break
            if f == len(params.filters)-1:
                idx[0].append(i)
                idx[1].append(x_sizes)
                idx[2].append(y_sizes)
                idx[3].append(pos)
    obj_ids = np.array(idx[0], dtype=int)
    np.savetxt(out_dir+'objects_with_p_stamps.txt', obj_ids, fmt="%i")
    #save catalogs 
    for f,filt in enumerate(params.filters):
        catalogs[f]['IS_PSTAMP'][obj_ids] == 1
        cat_name = out_dir + '/' + filt + "_full.cat"
        catalogs[f].write(cat_name, format="ascii.basic")
    #Get postage stamp image of the galaxy in all filters. 
    #Postage stamp size is set by the largest filter image  
    for num, i in enumerate(idx[0]):
        print "Saving postage stamp with object id:",i
        gal_images=[]
        psf_images=[]
        info={}
        x0 = catalogs[0]['X_IMAGE'][int(i)]
        y0 = catalogs[0]['Y_IMAGE'][int(i)]
        x_stamp_size = max(idx[1][num])
        y_stamp_size = max(idx[2][num])
        stamp_size =[int(y_stamp_size), int(x_stamp_size)]
        print "Stamp size of image:", stamp_size
        #import ipdb; ipdb.set_trace()
        gal_header = pyfits.Header()
        psf_header = pyfits.Header()
        temp = go.GalaxyCatalog(None)
        header_params = temp.output_params
        #import ipdb; ipdb.set_trace()
        for f, filter in enumerate(params.filters):
            tt_pos = idx[3][num][f]
            gal_file_name = out_dir + 'postage_stamps/' + filter + '_' + params.seg_id + '_' + str(i)+'_image.fits'
            psf_file_name = out_dir + 'postage_stamps/' + filter + '_' + params.seg_id + '_' + str(i)+'_psf.fits'
            seg_file_name = out_dir + 'postage_stamps/' + filter + '_' + params.seg_id + '_' + str(i)+'_seg.fits'

            a = np.loadtxt(out_dir+filter+'_focus_with_num_stars.txt')
            focus = a[-1][1]
            print "Focus is ", focus
            gal_name = params.data_files[filter]
            gal_image = fn.get_subImage_pyfits(x0,y0, stamp_size, gal_name, None, None, save_img=False)
            #gal_images.append(galsim.Image(gal_image))
            #gal_images.append(gal_image)
            
            psf_name = params.tt_file_path + filter+'/'+ params.tt_file_name[focus]
            psf_image = fn.get_subImage_pyfits(tt_pos[0],tt_pos[1], stamp_size, psf_name, None, None, save_img=False)
            #psf_images.append(galsim.Image(psf_image))
            #psf_images.append(psf_image)

            seg_name = out_dir + filter +'_comb_seg_map.fits'
            seg_image = fn.get_subImage_pyfits(x0,y0, stamp_size, seg_name, None, None, save_img=False)
            

            for header_param in header_params:
                gal_header[header_param] = catalogs[f][header_param][i]
            psf_header['X'] = tt_pos[0]
            psf_header['Y'] = tt_pos[1]
            psf_header['width'] = stamp_size[0]
            psf_header['height'] = stamp_size[1]
            pyfits.writeto(gal_file_name,gal_image,gal_header, clobber=True)
            pyfits.writeto(psf_file_name,psf_image,psf_header, clobber=True)
            pyfits.writeto(seg_file_name,seg_image, clobber=True)
