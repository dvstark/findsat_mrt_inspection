from pathlib import Path
import pdb
import numpy as np
import datetime
import glob

from astropy.table import Table
from astropy.io import fits
from acstools import utils_findsat_mrt as u



def adjust_catalog(catalog, bad_theta_ranges = [(0,3),(87,94),(176,180)], logfile='catalog_adjustments.txt', remake_masks=True):

    '''Code to make adjustments to findsat_mrt catalog. Right now it just adjusts the status of trails overlapping certain angles, but more could be added later.

    By default, it remakes the masks and segmentation files for any
    image where an adjustment was made.
    
    Input:

    catalog = findsat_mrt catalog (should be .fits file)

    bad_theta_ranges = ranges of trail angles (specified by
    findsat_mrt theta coordinate where trails should be demoted if
    status=2.

    logfile = a text file containing a record of what was adjusted

    remake_masks = bool flag to remake masks. True by default.

    '''

    print('Checking catalog ' + catalog)

    # set up the log
    catalog = Path(catalog)
    dir = catalog.parent
    logfile = Path.joinpath(dir, logfile)
    log = open(logfile,'a')

    now = datetime.datetime.now()

    # note the starting time and the file being adjusted
    #log.write('\n ' + now.strftime("%m/%d/%Y, %H:%M:%S") + '\n')  
    #log.write(str(catalog) + '\n') 

    # load the catalog
    tbl = Table.read(catalog)

    # see if it has any length
    if len(tbl) == 0:
        print('No changes necessary')
        return
    
    # if has length, check the conditions
    conditions = [np.logical_and(tbl['theta'] > b[0], tbl['theta'] < b[1]) for b in bad_theta_ranges]


    # adust status to 1 for cases that need adjusting
    sel=np.any(conditions, axis=0) & (tbl['status'] == 2)
    tbl['status'][sel] = 1

    subtbl = tbl[sel]
    sep = '    '
    if len(subtbl) == 0:

        print('No changes necessary')

    else:

        print('Making adjustments to catalog')

        log.write(str(catalog) + sep + now.strftime("%m/%d/%Y, %H:%M:%S") + '\n') 
        for row in subtbl:
            log.write(str(row['id']) + sep + 'status' + sep + '2' + sep + '1\n')

        tbl.write(catalog, overwrite=True)

        # remake hte mask
        if remake_masks:

            # get the original mask shape
            mask_file = str(catalog).replace('catalog', 'mask')
            segment_file = str(catalog).replace('catalog', 'segment')
            mask_hdr = fits.getheader(mask_file, ext=1)
            mask_image = np.zeros((mask_hdr['NAXIS2'], mask_hdr['NAXIS1']))
            min_mask_width = int(40 * mask_hdr['NAXIS1']/4096)

            include = [s['status'] in [2] for s in tbl]
            if np.sum(include) > 0:
                trail_id = tbl['id'][include]
                endpoints = tbl['endpoints'][include]
                widths = tbl['width'][include]
                segment, mask = u.create_mask(mask_image, trail_id, endpoints, widths, min_mask_width=min_mask_width)
            else:
                mask = np.zeros(mask_image.shape, dtype=bool)
                segment = np.zeros(mask_image.shape, dtype=int)    

            # write the new masks
            with fits.open(segment_file, mode='update') as h:
                h[0].data = segment
                h.flush()
                h.close()

            with fits.open(mask_file, mode='update') as h:
                h[1].data = mask.astype(int)
                h.flush()
                h.close()

    log.close()


catalogs = glob.glob('/ifs/cs/astro/koekemoer/SUPERCAL/data-fields/GOODSS/satmask_acs_wfc_flcfiles/09500/satellites/*mrt_catalog.fits')
for catalog in catalogs:
    adjust_catalog(catalog)
