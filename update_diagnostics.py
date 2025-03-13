# script to update the diagnostic plots for a set of images

import os
import glob
from pathlib import Path
import logging
import datetime
import numpy as np
import matplotlib.pyplot as plt
from new_diagnostics import make_trail_diagnostic, make_image_diagnostic
from astropy.table import Table
from astropy.io import fits
from astropy.nddata import block_reduce
import acstools.utils_findsat_mrt as u

def check_files_exist(files):

    exists = []

    for file in files:
        exists.append(Path(file).exists())
    exists = np.array(exists)
    return exists    

def load_resources(image_dir, sat_dir, root, logger=None):
    # image 
    image_path = image_dir + '/' + root + '.fits'

    # catalogs
    catalog_path_4 = sat_dir + '/' + root + '_ext4_mrt_catalog.fits'
    catalog_path_1 = sat_dir + '/' + root + '_ext4_mrt_catalog.fits'

    # segmentation file
    segmentation_path_4 = sat_dir + '/' + root + '_ext4_mrt_segment.fits'
    segmentation_path_1 = sat_dir + '/' + root + '_ext1_mrt_segment.fits'

    # check for missing files
    file_list = [catalog_path_4, catalog_path_1, image_path,
                    segmentation_path_4, segmentation_path_1]
    exist = check_files_exist(file_list)

    # if any are missing, log them, then skip over this iteration
    if np.any(exist == False):
        print('Some files missing; see log file for details')

        for e, f in zip(exist, file_list):
            if ~e:
                logger.warning('Missing file: ' + f)

        return None           

    # otherwise, load everything
    resources = {'catalog':{}, 
                 'image':{}, 
                 'segmentation':{}
    }
    # catalogs
    resources['catalog'][1] = Table.read(catalog_path_1)
    resources['catalog'][4] = Table.read(catalog_path_4)

    # image (rebin it)
    hdu = fits.open(image_path)
    wfc1 = block_reduce(hdu[4].data, 4, func=np.nansum)
    wfc2 = block_reduce(hdu[1].data, 4, func=np.nansum)
    hdu.close()
    resources['image'][4] = wfc1
    resources['image'][1] = wfc2

    # segmentation file
    resources['segmentation'][4] = fits.getdata(segmentation_path_4)
    resources['segmentation'][1] = fits.getdata(segmentation_path_1)

    return resources


def update_diagnostics(sat_dir, image_rebin=4, remake_trail_diagnostics = True, 
                       remake_image_diagnostics = True, overwrite=False, 
                       image_list=None):


    # get the list of files:
    cwd = sat_dir  #'/Users/dstark/supercal/09575/satellites'
    image_dir = cwd + '/../'

    # if no image_list specified, use everything in the image directory
    if image_list is None:
        image_list = glob.glob(image_dir + '*flc.fits')

    print('updating diagnostics for the following:')
    print(image_list)

    # set up log
    logfile = cwd + '/update_diagnostics_log.txt'
    print('Log file is {}'.format(logfile))

    logger = logging.getLogger(__name__)
    FileOutputHandler = logging.FileHandler(logfile)

    logger.addHandler(FileOutputHandler)
    logger.setLevel('DEBUG')

    # note the start time
    now = datetime.datetime.now()
    logger.info('Started update_diagnostics at ' + now.strftime("%m/%d/%Y, %H:%M:%S") + '\n')

    ###########################################
    ## Next, find and load all needed files ###
    ###########################################

    # extract the roots
    roots = np.array([image.split('/')[-1].split('.fits')[0] for image in image_list])

    # cycle
    for root in roots:
        
        print('On file = {}'.format(root))

        # load the images/catalogs
        resources = load_resources(image_dir, sat_dir, root, logger=logger)

        # skip to next case if we're missing anything
        if resources is None:
            continue


        # The mask_arr, image_arr, segmentation_arr, and catalog_arr can be created here

        #total mask
        mask_arr = [resources['segmentation'][4] > 0, resources['segmentation'][1] > 0]

        # segmentation
        segmentation_arr = [resources['segmentation'][4], resources['segmentation'][1]]

        # image
        image_arr = [resources['image'][4], resources['image'][1]]

        # catalog
        catalog_arr = [resources['catalog'][4], resources['catalog'][1]]


        # begin remaking individual trail diagnostic plots
        if remake_trail_diagnostics:
            
            print('Remaking trail diagnostic plots')

            for ext in [1, 4]:

                print('On extension = {}'.format(ext)) 

                catalog = resources['catalog'][ext]

                # check if there are any entries in the catalog. Skip if none.
                if len(catalog) == 0:
                    print('no trail diagnostics to update')
                    continue

                # otherwise, iterate through entries
                for row in catalog:

                    print('Updating trail diagnostic plots for {}, ext {}, trail id {}'.format(root, ext, row['id']))

                    # set up output file. Check if it exists, and skip if overwrite not allowed
                    output_file = cwd + '/' + root + '_ext{}_mrt/{}_full_ext{}_mrt_{}_diagnostic.png'.format(ext, root, ext, row['id'])
                    if Path(output_file).exists() & (overwrite == False):
                        print('Output file {} already exists.'.format(output_file))
                        print('Set overwrite=True to replace it')
                        continue

                    # Create the individual trail mask
                    image = resources['image'][ext]
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

                    # ...and corresponding arra
                    trail_mask_arr = [trail_mask_wfc1, trail_mask_wfc2]

                    # load the 1d trail profile and its header
                    profile_file = sat_dir + '/' + root + '_ext{}_mrt/'.format(ext) + root + '_ext{}_mrt_1dprof_{}.fits'.format(ext, row['id'])

                    # if profile is missing, skip over this step
                    if not Path(profile_file).exists():
                        logging.warning('Missing 1D profile file: ' + profile_file)
                        continue

                    profile = fits.getdata(profile_file)
                    profile_hdr = fits.getheader(profile_file)

                    make_trail_diagnostic(image_arr, mask_arr, trail_mask_arr,
                                          row,profile, profile_hdr, root=root,
                                          output_file = output_file,
                                          overwrite=overwrite)


        if remake_image_diagnostics:

            # see if the diagnostic already exists
            output_file = sat_dir + '/' + root + '_full_mrt_diagnostic.png'

            if Path(output_file).exists() & (overwrite == False):
                print('Output file {} already exists.'.format(output_file))
                print('Set overwrite=True to replace it')

            else:

                make_image_diagnostic(image_arr,
                                    mask_arr,
                                    segmentation_arr,
                                    catalog_arr,
                                    root,
                                    sat_dir,
                                    scale=[-1,3],
                                    cmap='Greys',
                                    output_file = output_file, 
                                    min_mask_width=40/image_rebin, 
                                    overwrite=overwrite)
