# script to update the diagnostic plots for a set of images

import os
import glob

import numpy as np
import matplotlib.pyplot as plt
plt.ion()
from new_diagnostics import make_trail_diagnostic, make_image_diagnostic
from astropy.table import Table
from astropy.io import fits
from astropy.nddata import block_reduce
import acstools.utils_findsat_mrt as u

def update_diagnostics(sat_dir, image_rebin=4, remake_trail_diagnostics = True, 
                       remake_image_diagnostics = True):

    #image_rebin = 4  # make sure this matches the original file

    # get the list of files:
    cwd = sat_dir  #'/Users/dstark/supercal/09575/satellites'
    image_dir = cwd + '/../'
    image_list = glob.glob(image_dir + '*flc.fits')

    # extract the roots
    roots = np.array([image.split('/')[-1].split('.fits')[0] for image in image_list])

    if remake_trail_diagnostics:

        for root in roots:
            print('file = {}'.format(root))
            for ext in [1, 4]:
                print('extension = {}'.format(ext))

                # load catalog first to see if it's empty
                catalog_path = cwd + '/' + root + '_ext{}_mrt_catalog.fits'.format(ext)
                catalog = Table.read(catalog_path)

                if len(catalog) == 0:
                    print('no trail diagnostics to update')
                else:
                    for row in catalog:
                        print('Updating trail diagnostic plots for {}, ext {}, trail id {}'.format(root, ext, row['id']))

                        # load image file and arrange
                        image_file = image_dir + '/' + root + '.fits'
                        hdu = fits.open(image_file)
                        wfc1 = block_reduce(hdu[4].data, 4, func=np.nansum)
                        wfc2 = block_reduce(hdu[1].data, 4, func=np.nansum)

                        hdu.close()
                        image_arr = [wfc1, wfc2]

                        # load segmentation file, each extension
                        segmentation_file_4 = cwd + '/{}_ext{}_mrt_segment.fits'.format(root, ext)
                        segmentation_file_1 = cwd + '/{}_ext{}_mrt_segment.fits'.format(root, ext)
                        segment_wfc1 = fits.getdata(segmentation_file_4)
                        segment_wfc2 = fits.getdata(segmentation_file_1)

                        # masks
                        if ext == 4:
                            image = wfc1
                        else:
                            image = wfc2
                        trail_seg, trail_mask = u.create_mask(image, [row['id']],
                                                            [row['endpoints']], 
                                                            [row['width']], 
                                                            min_mask_width=40/image_rebin)

                        if ext == 4:
                            trail_mask_wfc1 = trail_mask
                            trail_mask_wfc2 = np.zeros_like(trail_mask_wfc1)
                        elif ext == 1:
                            trail_mask_wfc2 = trail_mask
                            trail_mask_wfc1 = np.zeros_like(trail_mask_wfc2)

                        trail_mask_arr = [trail_mask_wfc1, trail_mask_wfc2]

                        #get total mask with good trails only
                        mask_arr = [segment_wfc1 > 0, segment_wfc2 > 0]

                        # load the 1d trail profile and its header
                        profile = fits.getdata(cwd + '/' + root + '_ext{}_mrt/'.format(ext) + root + '_ext{}_mrt_1dprof_{}.fits'.format(ext, row['id']))
                        profile_hdr = fits.getheader(cwd + '/' + root + '_ext{}_mrt/'.format(ext) + root + '_ext{}_mrt_1dprof_{}.fits'.format(ext, row['id']))

                        
                        output_file = cwd + '/' + root + '_ext{}_mrt/{}_full_ext{}_mrt_{}_diagnostic.png'.format(ext, root, ext, row['id'])

                        panels = make_trail_diagnostic(image_arr,mask_arr,trail_mask_arr,row,profile,profile_hdr, root=root, output_file = output_file)


    if remake_image_diagnostics:

        for root in roots:

            # load the catalogs for each chip and combined
            catalog_4 = Table.read(sat_dir + '/{}_ext4_mrt_catalog.fits'.format(root))
            catalog_1 = Table.read(sat_dir + '/{}_ext1_mrt_catalog.fits'.format(root))
            catalog_arr = [catalog_4, catalog_1]

            # get image array
            image_file = image_dir + '/' + root + '.fits'
            hdu = fits.open(image_file)
            wfc1 = block_reduce(hdu[4].data, 4, func=np.nansum)
            wfc2 = block_reduce(hdu[1].data, 4, func=np.nansum)
            image_arr = [wfc1, wfc2]

            # get the current final masks
            segmentation_file_4 = sat_dir + '/{}_ext{}_mrt_segment.fits'.format(root, 4)
            segmentation_file_1 = sat_dir + '/{}_ext{}_mrt_segment.fits'.format(root, 1)
            segment_wfc1 = fits.getdata(segmentation_file_4)
            segment_wfc2 = fits.getdata(segmentation_file_1)

            segment_arr = [segment_wfc1, segment_wfc2]
            final_mask_arr = [segment_wfc1 > 0, segment_wfc2 > 0]

            sat_dir = cwd

            output_file = cwd + '/' + '{}_full_mrt_diagnostic.png'.format(root)

            make_image_diagnostic(image_arr,
                                final_mask_arr,
                                segment_arr,
                                catalog_arr,
                                root,
                                sat_dir,
                                scale=[-1,3],
                                cmap='Greys',
                                output_file = output_file, 
                                min_mask_width=10)