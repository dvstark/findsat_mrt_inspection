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

plt.ion()


def check_files_exist(files):

    exists = []

    for file in files:
        exists.append(Path(file).exists())
    exists = np.array(exists)
    return exists    

def update_diagnostics(sat_dir, image_rebin=4, remake_trail_diagnostics = True, 
                       remake_image_diagnostics = True):



    #image_rebin = 4  # make sure this matches the original file

    # get the list of files:
    cwd = sat_dir  #'/Users/dstark/supercal/09575/satellites'
    image_dir = cwd + '/../'
    image_list = glob.glob(image_dir + '*flc.fits')

    # set up log
    logfile = cwd + '/update_diagnostics_log.txt'
    print('Log file is {}'.format(logfile))

    logger = logging.getLogger(__name__)
    FileOutputHandler = logging.FileHandler(logfile)

    logger.addHandler(FileOutputHandler)
    logger.setLevel('DEBUG')

    #if not Path(logfile).exists():
    #    os.system('touch' + logfile)

    #logging.basicConfig(filename=logfile, 
    #                    format="%(name)s → %(levelname)s: %(message)s",
    #                    filemode='w')
    now = datetime.datetime.now()
    logger.info('Started update_diagnostics at ' + now.strftime("%m/%d/%Y, %H:%M:%S") + '\n')

    # extract the roots
    roots = np.array([image.split('/')[-1].split('.fits')[0] for image in image_list])

    if remake_trail_diagnostics:

        for root in roots:
            print('file = {}'.format(root))
            for ext in [1, 4]:
                print('extension = {}'.format(ext))

                # define files we'll be loading
                catalog_path = cwd + '/' + root + '_ext{}_mrt_catalog.fits'.format(ext)
                image_path = image_dir + '/' + root + '.fits'
                segmentation_path_4 = cwd + '/{}_ext{}_mrt_segment.fits'.format(root, ext)
                segmentation_path_1 = cwd + '/{}_ext{}_mrt_segment.fits'.format(root, ext)

                # check that all of them exist
                file_list = [catalog_path, image_path, segmentation_path_4,
                             segmentation_path_1]
                exist = check_files_exist(file_list)

                # if any are missing, log them, then skip over this iteration
                if np.any(exist == False):
                    print('Some files missing; see log file for details')

                    for e, f in zip(exist, file_list):
                        if ~e:
                            logger.warning('Missing file: ' + f)

                    continue   

                # load catalog first to see if it's empty
                catalog = Table.read(catalog_path)

                if len(catalog) == 0:
                    print('no trail diagnostics to update')
                else:
                    for row in catalog:
                        print('Updating trail diagnostic plots for {}, ext {}, trail id {}'.format(root, ext, row['id']))

                        # load image file and arrange. Have to rebin to match 
                        # findsat_mrt output
                        hdu = fits.open(image_path)
                        wfc1 = block_reduce(hdu[4].data, 4, func=np.nansum)
                        wfc2 = block_reduce(hdu[1].data, 4, func=np.nansum)
                        hdu.close()

                        image_arr = [wfc1, wfc2]

                        # load segmentation file, each extension
                        segment_wfc1 = fits.getdata(segmentation_path_4)
                        segment_wfc2 = fits.getdata(segmentation_path_1)

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
                        profile_file = cwd + '/' + root + '_ext{}_mrt/'.format(ext) + root + '_ext{}_mrt_1dprof_{}.fits'.format(ext, row['id'])

                        # if profile is missing, skip over this step
                        if not Path(profile_file).exists():
                            logging.warning('Missing file: ' + f)
                            continue

                        profile = fits.getdata(profile_file)
                        profile_hdr = fits.getheader(profile_file)

                        output_file = cwd + '/' + root + '_ext{}_mrt/{}_full_ext{}_mrt_{}_diagnostic.png'.format(ext, root, ext, row['id'])

                        make_trail_diagnostic(image_arr,mask_arr,trail_mask_arr,row,profile,profile_hdr, root=root, output_file = output_file)


    if remake_image_diagnostics:

        for root in roots:

            print('file = {}'.format(root))

            # define the files to be loaded:
            catalog_path_4 = sat_dir + '/{}_ext4_mrt_catalog.fits'.format(root)
            catalog_path_1 = sat_dir + '/{}_ext1_mrt_catalog.fits'.format(root)
            image_path = image_dir + '/' + root + '.fits'
            segmentation_path_4 = sat_dir + '/{}_ext{}_mrt_segment.fits'.format(root, 4)
            segmentation_path_1 = sat_dir + '/{}_ext{}_mrt_segment.fits'.format(root, 1)

            # check that all of them exist
            file_list = [catalog_path, image_path, segmentation_path_4,
                            segmentation_path_1]
            exist = check_files_exist(file_list)

            # if any are missing, log them, then skip over this iteration
            if np.any(exist == False):
                print('Some files missing; see log file for details')
                for e, f in zip(exist, file_list):
                    if ~e:
                        logging.warning('Missing file: ' + f)

                continue               

            # load the catalogs for each chip and combined
            catalog_4 = Table.read(catalog_path_4)
            catalog_1 = Table.read(catalog_path_1)
            catalog_arr = [catalog_4, catalog_1]

            # get image array
            hdu = fits.open(image_path)
            wfc1 = block_reduce(hdu[4].data, 4, func=np.nansum)
            wfc2 = block_reduce(hdu[1].data, 4, func=np.nansum)
            image_arr = [wfc1, wfc2]

            # get the current final masks
            segment_wfc1 = fits.getdata(segmentation_path_4)
            segment_wfc2 = fits.getdata(segmentation_path_1)

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