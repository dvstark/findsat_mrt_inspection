'''
This set of codes is used to inspect, and interactively update, satellite masks
generated by findsat_mrt in a given folder
'''

import os
import glob
import shutil
from pathlib import Path
import pdb
import warnings
import yaml


# 3rd party
import numpy as np
from astropy.table import Table, vstack
from astropy.stats import sigma_clipped_stats
from astropy.nddata import block_reduce

# import matplotlib and undo agg if needed
import matplotlib as mpl
default_backend = mpl.get_backend()
import matplotlib.pyplot as plt
plt.ion()
import matplotlib.image as mpimage
from acstools.findsat_mrt import WfcWrapper
from astropy.io import fits

from acstools import utils_findsat_mrt as u

from new_diagnostics import make_trail_diagnostic, make_image_diagnostic

# load configuration entries
with open("config.yaml") as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

# define ds9 executable (can change across computers)
ds9_command = config['ds9_exe']


def show_trail_diagnostic(trail_diagnostic, xsize=15, ysize=12):
    fig, ax = plt.subplots(figsize=(xsize, ysize))
    ax.imshow(trail_diagnostic)
    ax.axis('off')
    plt.tight_layout()
    
def show_image_diagnostic(image_diagnostic, xsize=15, ysize=12):
    fig, ax = plt.subplots(figsize=(xsize, ysize))
    ax.imshow(image_diagnostic)
    ax.axis('off')
    plt.tight_layout()

class inspect_sat_masks(WfcWrapper):
    def __init__(self, sat_dir,
                 image_dir=None,
                 inspect_good_only=True):

        # other related programs use the non-interactive "agg" backend. 
        # Make sure htat is not set still
        mpl.use(default_backend)


        self.sat_dir = Path(sat_dir)

        self.inspect_good_only = inspect_good_only
        if self.inspect_good_only:
            self.min_allowed_status = 2
        else:
            self.min_allowed_status = -1


        # get the directory containing the output (current directory)
        #self.sat_dir = Path.cwd()

        # set the image directory to default if not specified
        if image_dir is None:
            self.image_dir = self.sat_dir.parents[0]

        #print(self.image_dir)
        #print(list(Path.glob(self.image_dir, "*.fits")))
        
        # get the unique image ids
        image_roots = []
        for file in list(Path.glob(self.image_dir, "*.fits")):
            image_roots.append(file.stem)
        
        # sort these so they are always in the same order. Then add to class
        image_roots = np.sort(image_roots)
        self.image_roots = np.array(image_roots)

        # set the current image and trail index to -1 to start
        self.image_index = -1
        self.trail_index = -1
        
        # set the image extenson to 4. We iterate 4 to 1 and back
        self.ext = 1

        # indicate that nothing has been updated yet
        self.updates_made = False


        print(f'\nNumber of files to inspect: {len(self.image_roots)}')
        for file in self.image_roots:
            print(file)

        # define the temporary file file names (put sat_dir in front of these!)
        self.profile_fits_backup = Path.joinpath(self.sat_dir, '_current_profile_backup.fits')
        self.profile_diagnostic_backup = Path.joinpath(self.sat_dir, '_current_profile_backup.png')
        self.updated_image_diagnostic = Path.joinpath(self.sat_dir, '_current_updated_image_diagnostic.png')


        self.execute()

        #self.cycle_through_files()

    def execute(self):
        self.quit = False

        self.menu_type = 'trail'

        print('\nLoading the first image')
        self.next_image()

        while not self.quit:
            if len(self.catalog) > 0:
                print(self.catalog)
            self.menu()

    def cycle_through_files(self):
        for image_root in self.image_roots:
            print('\nCurrent Image: {}'.format(image_root))

            for ext in [1, 4]:
                print('\nImage extension: {}'.format(ext))
                files_exist = self.check_files_exist(image_root, ext)
                if not files_exist:
                    print('Some files missing, skipping to next image/ext')
                    continue
                else:
                    print('All files found')


    def check_files_exist(self, image_root, ext):
        '''checks that all the satellite mask subfiles have been created'''
        
        # update this to loop over possible files needed?

        catalog_path = Path.joinpath(self.sat_dir, image_root + '_ext{}_mrt_catalog.fits'.format(ext))
        mask_path = Path.joinpath(self.sat_dir, image_root + '_ext{}_mrt_mask.fits'.format(ext))

        if catalog_path.exists():
            print('Trail catalog: FOUND')
        else:
            print('Trail catalog: NOT FOUND')
        
        if mask_path.exists():
            print('Trail Mask: FOUND')
        else:
            print('Trail Mask: NOT FOUND')

        return mask_path.exists() & (catalog_path.exists())
    
    def load_catalog(self):

        self.catalog_path = Path.joinpath(self.sat_dir, self.image_roots[self.image_index] + '_ext{}_mrt_catalog.fits'.format(self.ext))
        self.catalog = Table.read(self.catalog_path)

        # also update the source list 
        self.source_list = self.catalog

        #if len(self.catalog) == 0:
        #    print('\n No trails found in ext {}'.format(self.ext))

    def load_diagnostic(self):
        #self.image_diagnostic = Path.joinpath(self.sat_dir, self.current_image + '_full_mrt_diagnostic.png'.format(self.ext))

        image_diagnostic = mpimage.imread(self.updated_image_diagnostic)
        
        show_image_diagnostic(image_diagnostic)


    def load_trail_diagnostic(self):
        
        print('trail id: {}'.format(self.trail_id))
        #print(self.sat_dir)
        #print(self.image_roots[self.image_index] + '_ext{}_mrt'.format(self.ext))
        #print(self.image_roots[self.image_index] + '_ext{}_mrt_{}_diagnostic.png'.format(self.ext, self.trail_id))

        trail_diagnostic = mpimage.imread(str(self.trail_diagnostic_path))
        
        show_trail_diagnostic(trail_diagnostic)

        #scale=1.2
        #fig, ax = plt.subplots(figsize=(12*scale,10*scale))
        #ax.imshow(trail_diagnostic)
        #ax.axis('off')
        #plt.tight_layout()
        # try to fix this plotting issue with the routine here: https://stackoverflow.com/questions/30880358/matplotlib-figure-not-updating-on-data-change.
        # I don't want to window to keep opening and closing constsantly

    def load_revised_trail_diagnostic(self):
        revised_diagnostic = mpimage.imread(str('_current_updated_trail_diagnostic.png'))
        show_trail_diagnostic(revised_diagnostic)


    def set_trail_status(self, trail_id, new_status):

        sel = np.where(self.catalog['id'] == trail_id)[0]
        self.catalog['status'][sel] = new_status


    def remove_trail(self):
        print('\nRemoving the current trail')
        self.set_trail_status(self.trail_id, -1)  # I'm using -1 to indicate rejected by hand
        self.remake_masks()

    def add_trail(self):
        print('\nAdding this as a good trail')
        self.set_trail_status(self.trail_id, 2)
        self.remake_masks()

    def remake_masks(self):
        # regenerates the mask and segmentation image

        include = [s['status'] in [2] for s in self.catalog]
        trail_id = self.catalog['id'][include]
        endpoints = self.catalog['endpoints'][include]
        widths = self.catalog['width'][include]

        if np.sum(include) > 0:
            self.segment, self.mask = u.create_mask(self.image, trail_id, endpoints,
                                        widths, 
                                        min_mask_width=self.min_mask_width)
        else:
            self.mask = np.zeros(self.image.shape, dtype=bool)
            self.segment = np.zeros(self.image.shape, dtype=int)


    def add_new_trail(self):

        print('Which extension?\n'
              '4: WFC1\n'
              '1: WFC2')
        ext = int(input()) # add error checking here in case there's a bad input
        if ext not in [1, 4]:
            print('\nTsk Tsk. Input extension has to be 4 or 1')
            return
        
        # update the extension we're modifying
        self.ext = int(ext)

        # re-specify the paths and reload images as needed.
        # if ext=1, we don't need to reload anything (proper files alreayd in place)
        if self.ext == 4:
            self.specify_image_paths()
            self.load_images()
            self.load_catalog()

        self.load_in_ds9(ext=self.ext)

        # get starting point
        print('Provide the starting x and y coordinates in the unbinned image (separated by a space)')
        user_input = input()
        x0, y0 = np.array(user_input.split()).astype(float)/self.binsize
    
        # get ending point
        print('Provide the ending x and y coordinates separated by a space (separated by a space)')
        user_input = input()
        x1, y1 = np.array(user_input.split()).astype(float)/self.binsize
        
        print('Provide a trail width')
        user_input = input()
        width = float(user_input)

        endpoints = [[[x0,y0],[x1,y1]]]
        
        dtype = [(name, self.catalog.dtype[name]) for name in self.catalog.columns]
        new_row = Table(data=np.zeros(1, dtype=dtype))
        
        # update catalog entries
        new_row['endpoints'] = endpoints
        new_row['width'] = width
        new_row['status'] = 2

        # set the other names to -1 so it's clear they contain missing data
        for n in new_row.columns:
            if n not in ['endpoints', 'width','status','id']:
                new_row[n] = -1

        if len(self.catalog) == 0:
            new_row['id'] = 1
            self.catalog = new_row
        else:
            new_row['id'] = self.catalog['id'].max() + 1    
            self.catalog = vstack([self.catalog, new_row])

        self.trail_index = len(self.catalog)-1
        self.trail_id = self.catalog['id'][self.trail_index]

        # now that the trail ID is specified, redefine the trail paths
        self.specify_trail_paths()

        # need to extract the profile from the image
        import pdb
        rotated, [[rx1, ry1], [rx2, ry2]], theta = u.rotate_image_to_trail(self.image,
                                                                         endpoints[0])

        # update ry1/2 to include buffer region
        ry1_new = np.min([ry1, ry2]) - 100
        ry2_new = np.max([ry1, ry2]) + 100  # making sure ry1 lower than ry2
        streak_y_rot = (ry1 + ry2) / 2  # streak position, possible slight
        # difference in ry1/ry2 due to finite angle sampling

        # buffer region could extend off edge of chip. Truncate ry1/ry2 if so
        fixed_inds = u.good_indices([(ry1_new, ry2_new), (rx1, rx2)],
                                  rotated.shape)
        ry1_trim, ry2_trim = fixed_inds[0]
        rx1_trim, rx2_trim = fixed_inds[1]

        # find distance of streak from current bottom of the cutout
        dy_streak = streak_y_rot - ry1_trim

        # extract final cutout
        subregion = rotated[int(ry1_trim):int(ry2_trim),
                            int(rx1_trim):int(rx2_trim)]

        # make 1D profile of trail (looking down its axis) by taking a median
        # of all pixels in each row
        with warnings.catch_warnings():
            warnings.filterwarnings(action='ignore',
                                    message='All-NaN slice encountered')
            medarr = np.nanmedian(subregion, axis=1)
        
        # get number of pixels being considered at each point; remove those
        # that are too small such that median unreliable
        narr = np.sum(np.isfinite(subregion), axis=1)
        medarr[narr < 25] = np.nan
        self.prof = medarr
        
        # write out the profile file  # THIS SHOULD NOW BE HANDLED ABOVE
        #self.trail_profile_path = Path.joinpath(self.sat_dir, 
        #                                        self.image_roots[self.image_index] + '_ext{}_mrt'.format(self.ext), 
        #                                        self.image_roots[self.image_index] + '_ext{}_mrt_1dprof_{}.fits'.format(self.ext, self.trail_id))
        hdu = fits.PrimaryHDU(self.prof)
        hdu.header['center'] = dy_streak
        hdu.header['width'] = width
        hdu.header['avgflux'] = -999
        hdu.header['snr'] = -999
        hdu.header['ext'] = self.ext
        hdu.header['image'] = self.current_image
        self.prof_hdr = hdu.header
        hdu.writeto(self.trail_profile_path, overwrite=True)

        # regenerate masks
        self.remake_masks()


    # create the new diagnostic plot for the trail and show
        self.regenerate_diagnostics()

        self.updates_made = True
        self.menu_type = 'trail'


    def change_width(self):
        sel = np.where(self.catalog['id'] == self.trail_id)[0]
        print(sel)
        #print(f'current width (binned pix) = {self.catalog['width'][sel]}')
        print('\nWhat width would you like?')
        new_width = input()

        # make sure this is a number
        try:
            new_width = float(new_width)
            print('new width = {}'.format(new_width))

            # update catalog
            self.catalog['width'][sel] = new_width

            # update profile
            self.prof_hdr['width'] = new_width
            
        except:
            print('This width must be a number')

    def save(self):
        # need to save (a) trail diagnostic plot (b) 1d trail profile (c) catalog

        print('\nsaving changes')

        self.specify_image_paths()
        self.specify_trail_paths()

        # trail diagnostic plot
        if Path('./_current_updated_trail_diagnostic.png').is_file():
            shutil.copy('./_current_updated_trail_diagnostic.png', self.trail_diagnostic_path)

        # image diagnostic plot
        shutil.copy(self.updated_image_diagnostic, self.image_diagnostic_path)

        #1d profile data
        fits.writeto(self.trail_profile_path, self.prof, header=self.prof_hdr, overwrite=True)

        # catalog
        self.catalog.write(self.catalog_path, overwrite=True)

        # segmentation plot
        with fits.open(self.segmentation_path, mode='update') as h:
            h[0].data = self.segment
            h.flush()
            h.close()

        # mask
        with fits.open(self.mask_path, mode='update') as h:
            h[1].data = self.mask.astype(int)
            h.flush()
            h.close()


    def specify_image_paths(self):

        # reads image name, current extension, and current trail id (if any) and updates the paths

        # image path
        self.image_path = Path.joinpath(self.image_dir, self.current_image + '.fits')

        # segmentation path
        self.segmentation_path = Path.joinpath(self.sat_dir, self.current_image + '_ext{}_mrt_segment.fits'.format(self.ext))

        # mask path
        self.mask_path = Path.joinpath(self.sat_dir, self.current_image + '_ext{}_mrt_mask.fits'.format(self.ext))

        # catalog path
        self.catalog_path = Path.joinpath(self.sat_dir, self.image_roots[self.image_index] + '_ext{}_mrt_catalog.fits'.format(self.ext))

       # trail directory
        self.trail_dir = Path.joinpath(self.sat_dir,
                                        self.image_roots[self.image_index] + f'_ext{self.ext}_mrt')

        # image diagnostic
        self.image_diagnostic_path = Path.joinpath(self.sat_dir, self.current_image + '_full_mrt_diagnostic.png')

    def specify_trail_paths(self):

        # 1d profile path
        self.trail_profile_path = Path.joinpath(self.sat_dir, 
                                                self.image_roots[self.image_index] + '_ext{}_mrt'.format(self.ext), 
                                                self.image_roots[self.image_index] + '_ext{}_mrt_1dprof_{}.fits'.format(self.ext, self.trail_id))
        # trail diagnostic
        self.trail_diagnostic_path = Path.joinpath(self.sat_dir, 
                                                   self.image_roots[self.image_index] + '_ext{}_mrt'.format(self.ext), 
                                                   self.image_roots[self.image_index] + '_full_ext{}_mrt_{}_diagnostic.png'.format(self.ext, self.trail_id))
 

    def next_trail(self):
        
        if self.updates_made:
            self.save()
            self.updates_made = False

        print('\nMoving to the next trail')
        plt.close('all')

        self.trail_index += 1

        print('extension: ',self.ext)
        print('catalog length: ',len(self.catalog))

        if self.trail_index >= len(self.catalog):
            print('No more trails on this iamge/extension')
            if self.ext == 1:
                self.load_diagnostic()
                self.menu_type = 'image'
            else:
                self.next_image() 

        else:

            if self.catalog['status'][self.trail_index] < self.min_allowed_status:
                self.next_trail()  # I'm calling a function inside itself...this seems bad
            else:
                self.trail_id = self.catalog['id'][self.trail_index]

                self.specify_trail_paths()

                # self.trail_diagnostic_path = Path.joinpath(self.sat_dir, 
                #                                            self.image_roots[self.image_index] + '_ext{}_mrt'.format(self.ext), 
                #                                            self.image_roots[self.image_index] + '_full_ext{}_mrt_{}_diagnostic.png'.format(self.ext, self.trail_id))
                # self.trail_profile_path = Path.joinpath(self.sat_dir, 
                #                                         self.image_roots[self.image_index] + '_ext{}_mrt'.format(self.ext), 
                #                                         self.image_roots[self.image_index] + '_ext{}_mrt_1dprof_{}.fits'.format(self.ext, self.trail_id))
            
                self.load_trail_diagnostic()

                # backup the trail diagnostic file in case we start editing
                shutil.copy(self.trail_diagnostic_path, self.profile_diagnostic_backup)

                self.load_1d_prof()


                # backup the trail profile itself in case any header info is changed
                shutil.copy(self.trail_profile_path, self.profile_fits_backup)

    def reexamine_trails(self):

        # roll the image index back 1, then run next_image
        self.image_index = self.image_index - 1

        self.menu_type = 'trail'
        self.next_image()

    def load_1d_prof(self):
        # open the trail profile itself and header
        prof = fits.getdata(self.trail_profile_path)
        self.prof = np.copy(prof)
        self.prof_hdr = fits.getheader(self.trail_profile_path)

    def next_image(self):
        
        
        # reset the trail index
        self.trail_index = -1

        # set the menu back to "trail"
        self.menu_type = 'trail'

        # kill any open windows
        plt.close('all')

        # update the extension
        if self.ext == 1:
            self.ext = 4
        else:
            self.ext = 1

        # if we've gone back to ext 4, update the image index    
        if self.ext == 4:
            self.image_index += 1

        # exit if we've reached the end
        if self.image_index >= len(self.image_roots):
            print('No more images to load')
            self.exit()
        else:

            # proceed to load everything
            self.current_image = self.image_roots[self.image_index]

            # tell user what we're looking at
            print(f'Image : {self.current_image}')
            print(f'extension: {self.ext}')

            # specify all the input paths
            self.specify_image_paths()

            # copy the image diagnostic over to a temp file
            #self.image_diagnostic_path = Path.joinpath(self.sat_dir, self.current_image + '_full_mrt_diagnostic.png'.format(self.ext))
            shutil.copy(self.image_diagnostic_path, self.updated_image_diagnostic)

            # set the trails directory for ths image
            #self.trail_dir = self.image_roots[self.image_index] + f'_ext{self.ext}_mrt'

            # load the images (original, mask, segment)
            self.load_images()

            # otherwise load the trail catalog 
            self.load_catalog()

            if len(self.catalog) > 0:
            # ...and the first trail
                self.next_trail()
            else:
                if self.ext == 1:
                    self.load_diagnostic()
                    self.menu_type = 'image'
                else:
                    self.next_image()


    def load_images(self):
        
        # load the original image
        #self.image_path = Path.joinpath(self.image_dir, self.current_image + '.fits')
        self.image = fits.getdata(self.image_path, ext=self.ext)

        # load the previously created segmentation file
        #self.segmentation_path = Path.joinpath(self.sat_dir, self.current_image + '_ext{}_mrt_segment.fits'.format(self.ext))
        self.segment = fits.getdata(self.segmentation_path)

        # mask
        #self.mask_path = Path.joinpath(self.sat_dir, self.current_image + '_ext{}_mrt_mask.fits'.format(self.ext))
        self.mask = fits.getdata(self.mask_path, ext=1)

        # get the binning amount
        self.binsize = int(self.image.shape[0] / self.segment.shape[0])
        self.rebin()

        # use this bin size to set the min mask width
        self.min_mask_width = 40./self.binsize

    def exit(self):        
        print('\nSayonara!')
        plt.close('all')
        self.quit = True

    def regenerate_diagnostics(self):

        plt.close('all')

        # create custom mask here to overlay only this trail on image
        id = self.catalog['id'][self.trail_index]
        endpoints = self.catalog['endpoints'][self.trail_index]
        widths = self.catalog['width'][self.trail_index]


        # mask for just this trail
        subseg, submask = u.create_mask(self.image, [id], [endpoints],
                                        [widths], 
                                        min_mask_width=40/self.binsize)

        # # mask for all good trails
        # include = [s['status'] in [2] for s in self.catalog]
        # trail_id = self.catalog['id'][include]
        # endpoints = self.catalog['endpoints'][include]
        # widths = self.catalog['width'][include]

        # if np.sum(include) > 0:
        #     self.segment, self.mask = u.create_mask(self.image, trail_id, endpoints,
        #                                 widths, 
        #                                 min_mask_width=self.min_mask_width)
        # else:
        #     self.mask = np.zeros(self.image.shape, dtype=bool)
        #     self.segment = np.zeros(self.image.shape, dtype=int)

        # the new trail diagnostics show both chips. Need to load data accordingly

        # image
        hdu = fits.open(self.image_path)
        wfc1 = block_reduce(hdu[4].data, self.binsize, func=np.nansum)
        wfc2 = block_reduce(hdu[1].data, self.binsize, func=np.nansum)
        hdu.close()
        image_arr = [wfc1, wfc2]

        # trail mask
        if self.ext == 4:
            trail_mask_wfc1 = submask
            trail_mask_wfc2 = np.zeros_like(trail_mask_wfc1)
        elif self.ext == 1:
            trail_mask_wfc2 = submask
            trail_mask_wfc1 = np.zeros_like(trail_mask_wfc2)

        trail_mask_arr = [trail_mask_wfc1, trail_mask_wfc2]

        # full mask
        mask_4 = fits.getdata(Path.joinpath(self.sat_dir, self.current_image + '_ext{}_mrt_mask.fits'.format(4)))
        mask_1 = fits.getdata(Path.joinpath(self.sat_dir, self.current_image + '_ext{}_mrt_mask.fits'.format(1)))

        # replace the relevant mask with the one we just updated
        if self.ext == 4:
            full_mask_wfc1 = self.mask
            full_mask_wfc2 = mask_1
        elif self.ext == 1:
            full_mask_wfc1 = mask_4
            full_mask_wfc2 = self.mask
        full_mask_arr = [full_mask_wfc1, full_mask_wfc2]

        # segmentation masks
        segment_4 = fits.getdata(Path.joinpath(self.sat_dir, self.current_image + '_ext4_mrt_segment.fits'))
        segment_1 = fits.getdata(Path.joinpath(self.sat_dir, self.current_image + '_ext1_mrt_segment.fits'))   

        if self.ext == 4:
            segment_arr = [self.segment, segment_1]
        else:
            segment_arr = [segment_4, self.segment]

        #catalogs
        catalog_4 = Table.read(Path.joinpath(self.sat_dir, self.image_roots[self.image_index] + '_ext4_mrt_catalog.fits'))
        catalog_1 = Table.read(Path.joinpath(self.sat_dir, self.image_roots[self.image_index] + '_ext1_mrt_catalog.fits'))

        if self.ext == 4:
            catalog_arr = [self.catalog, catalog_1]
        else:
            catalog_arr = [catalog_4, self.catalog]

        make_trail_diagnostic(image_arr,full_mask_arr,trail_mask_arr,
                              self.catalog[self.trail_index],self.prof,
                              self.prof_hdr, root=self.current_image,
                              overwrite=True
                              output_file='_current_updated_trail_diagnostic.png')
        
        make_image_diagnostic(image_arr,
                            full_mask_arr,
                            segment_arr,
                            catalog_arr,
                            self.current_image,
                            self.sat_dir,
                            big_rebin=16,
                            scale=[-1,3],
                            cmap='Greys',
                            output_file = self.updated_image_diagnostic, 
                            min_mask_width=10,
                            overwrite=True)
        # make_trail_diagnostic(self.image, submask, self.mask, self.catalog[self.trail_index],
        #                       self.prof, self.prof_hdr, scale=[-1,3], cmap='Greys',
        #                       root=self.current_image, big_rebin=16, 
        #                       output_file='_current_updated_diagnostic.png')
        plt.close('all')
        self.load_revised_trail_diagnostic()

    def toggle_show_all_trails(self):
        if self.inspect_good_only == True:
            self.inspect_good_only = False
            self.min_allowed_status = -1
        else:
            self.inspect_good_only = True
            self.min_allowed_status = 2

        # restart inspection
        self.trail_index = -1
        self.ext = 1
        self.image_index = self.image_index - 1
        self.next_image()
        
    def undo_changes(self):

        if self.updates_made == False:
            print('\n Nothing to undo')
        else:

            print('\n Undoing all changes')
            plt.close('all')

            # move the backup of the diagnostic plot over
            if Path('_current_updated_trail_diagnostic.png').is_file():
                os.remove('_current_updated_trail_diagnostic.png')

            # replace the working image diagnostic plot
            shutil.copy(self.image_diagnostic_path, 
                        self.updated_image_diagnostic)

            # reload the catalog
            self.load_catalog()

            # reload the images
            self.load_images()

            if self.menu_type == 'trail':
                # show the original diagnostic
                self.load_trail_diagnostic()

                # reload the original 1d profile
                self.load_1d_prof()

            else:
                self.ext = 1  # reset to index present when we inspect image
                shutil.copy(self.image_diagnostic_path, self.updated_image_diagnostic)
                self.load_diagnostic()


            # reset updates_made flag
            self.updates_made = False


    def reset_exposure(self):
        ...
    def load_in_ds9(self, ext=None):

        # this now part of config file
        #ds9_command = '/Applications/SAOImageDS9.app/Contents/MacOS/ds9'


        if ext is None:
            os.system(ds9_command + ' -multiframe ' + str(self.image_path) + ' &')
        else:
            os.system(ds9_command + ' ' + str(self.image_path) + '[{}] &'.format(ext))


    def choose_image(self):
        print('\nPick the number corresponding to the image you want to look at')
        for i, image in enumerate(self.image_roots):
            print(i, image)
        new_index = input()

        #make sure it's a number
        try:
            new_index = int(new_index)
            # set the image index to 1 minus this, and ext to 4, so "next_image" iterates to what we want
            self.image_index = new_index - 1
            self.ext = 1
            print('new image = {}'.format(self.image_roots[new_index]))

            self.next_image()

        except:
            print('You must supply a number')

    def menu(self):

        trail_options = {'': {'desc':' [ENTER] Save and go to next trail', 'func':self.next_trail},
                   'w': {'desc': '[w] Change trail width', 'func': self.change_width},
                   'r': {'desc': '[r] Remove trail', 'func': self.remove_trail},
                   'a': {'desc': '[a] Add trail', 'func': self.add_trail},
                   'u': {'desc': '[u] Undo changes', 'func': self.undo_changes},
                   'ds9': {'desc': '[ds9] Load image in ds9', 'func': self.load_in_ds9},
                   'i': {'desc': '[i] Jump to another image (this does not save)', 'func': self.choose_image},
                   't': {'desc': '[t] Toggle only show "good" trails (currently {})'.format(self.inspect_good_only),'func': self.toggle_show_all_trails},
                   'Q': {'desc': '[Q] Quit', 'func': self.exit}
        }

        image_options = {'': {'desc':'[ENTER] Save and go to next image', 'func':self.next_image},
                   'n': {'desc': '[n] Add a completely new trail', 'func': self.add_new_trail},
                   'r': {'desc': '[r] Re-examine trails', 'func': self.reexamine_trails},
                   'ds9': {'desc': '[ds9] Load image in ds9', 'func': self.load_in_ds9},
                   'i': {'desc': '[i] Jump to another image (this does not save)', 'func': self.choose_image},
                   't': {'desc': '[t] Toggle only show "good" trails (currently {})'.format(self.inspect_good_only),'func': self.toggle_show_all_trails},
                   'Q': {'desc': '[Q] Quit', 'func': self.exit}
        }

        if self.menu_type == 'trail':
            options = trail_options
        elif self.menu_type == 'image':
            options = image_options

        refresh_options = ['w', 'r', 'a', 'n']
                   
        print('\n Choose an option:\n')
        for key in options:
            print(options[key]['desc'])

        proceed = False

        while not proceed:
            print("What'll it be?")
            user_input = input()

            print('\n user input was : ', user_input)


            if user_input not in list(options.keys()):
                print("That command does not do anything...yet...")
            else:
                proceed = True
                options[user_input]['func']()
                if (user_input in refresh_options) & (self.menu_type == 'trail'):
                    print(self.catalog)
                    self.regenerate_diagnostics()
                    self.updates_made=True


if __name__ == '__main__':
    # run on current directory if called as standalone function
    f=inspect_sat_masks('./')


    
