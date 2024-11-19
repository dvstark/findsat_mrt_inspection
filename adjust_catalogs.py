from pathlib import Path
import pdb
from astropy.table import Table
import numpy as np
import datetime
import glob

#(0,3),(87,94),(176,180)

def adjust_catalog(catalog, bad_theta_ranges = [(0,3),(87,94),(176,180)], logfile='catalog_adjustments.txt'):

    # set up the log
    catalog = Path(catalog)
    dir = catalog.parent
    logfile = Path.joinpath(dir, logfile)
    log = open(logfile,'a')

    now = datetime.datetime.now()

    # note the starting time and the file being adjusted
    #log.write('\n Started at '+now.strftime("%m/%d/%Y, %H:%M:%S")+ '\n')  
    #log.write(str(catalog) + '\n') 

    # load the catalog
    tbl = Table.read(catalog)

    # see if it has any length
    if len(tbl) == 0:
        return
    
    # if has length, check the conditions
    conditions = [np.logical_and(tbl['theta'] > b[0], tbl['theta'] < b[1]) for b in bad_theta_ranges]


    # adust status to 1 for cases that need adjusting
    sel=np.any(conditions, axis=0) & (tbl['status'] == 2)
    tbl['status'][sel] = 1

    subtbl = tbl[sel]
    sep = '    '
    if len(subtbl) > 0:
        log.write(str(catalog) + '\n') 
        for row in subtbl:
            log.write(datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S") + sep + str(row['id']) + sep + 'status' + sep + '2' + sep + '1\n')

    tbl.write(catalog, overwrite=True)
    log.close()


catalogs = glob.glob('/ifs/cs/astro/koekemoer/SUPERCAL/data-fields/GOODSS/satmask_acs_wfc_flcfiles/09500/satellites/*mrt_catalog.fits')
for catalog in catalogs:
    adjust_catalog(catalog)