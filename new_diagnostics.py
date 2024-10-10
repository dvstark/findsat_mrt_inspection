
import matplotlib.pyplot as plt
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from astropy.table import Table
import numpy as np
from astropy.nddata import bitmask, block_reduce
import acstools.utils_findsat_mrt as u
from pathlib import Path

image_rebin=4

def make_trail_diagnostic(image_arr,
                          final_mask_arr,
                          trail_mask_arr,
                          row,
                          profile,
                          profile_hdr,
                          big_rebin=8,
                          scale=[-1,3],
                          cmap='Greys', root='',
                          output_file = None, 
                          min_mask_width=10,
                          overwrite=False):

    if output_file is not None:
        if Path(output_file).exists() & (overwrite == False):
            print('Output file {} already exists.'.format(output_file))
            print('Set overwrite = True to replace it.')
            plt.close('all')
            return

    # set up figure grid
    fig = plt.figure(figsize=(15,12), layout='constrained')
    fig.suptitle('Trail Diagnostic\n'+root)
    [[p1, p2],[p3, p4]] = fig.subfigures(2,2)

    p1a1, p1a2 = p1.subplots(2,1)
    p2a1 = p2.subplots(1,1)
    p3a1, p3a2 = p3.subplots(2,1)
    p4a1, p4a2 = p4.subplots(2,1)

    # set up images
    __, image_med, image_stddev = sigma_clipped_stats(image_arr)
    for ax, wfc in zip([p1a1, p1a2], image_arr):
        ax.imshow(wfc, cmap=cmap, origin='lower', aspect='auto',
                    vmin=image_med - scale[0]*image_stddev,
                    vmax=image_med + scale[1]*image_stddev)
    p1a1.set_title('Image')
   

    # do this for the bottom left too
    for ax, wfc, trail_mask in zip([p3a1, p3a2], image_arr, trail_mask_arr):
        ax.imshow(wfc, cmap=cmap, origin='lower', aspect='auto',
                    vmin=image_med - scale[0]*image_stddev,
                    vmax=image_med + scale[1]*image_stddev)

        ax.imshow(np.ma.masked_where(trail_mask == 0, trail_mask)*255, alpha=0.5, origin='lower', aspect='auto', cmap='Set1')
    p3a1.set_title('Image with trail mask')

    # make the big masked image
    for ax, image, final_mask in zip([p4a1, p4a2], image_arr, final_mask_arr):
        masked_image = np.ma.masked_where(final_mask, image)
        rebinned_masked_image = block_reduce(masked_image, big_rebin, func=np.nanmedian)
        __, image_med, image_stddev = sigma_clipped_stats(rebinned_masked_image)

        ax.imshow(rebinned_masked_image, origin='lower', aspect='auto',
                  vmin=image_med - image_stddev, vmax = image_med + 5*image_stddev)
    p4a1.set_title('Rebinned final masked image')

    # show the 1d profile
    log_med = np.log10(profile+100)
    p2a1.plot(log_med)
    p2a1.axvline(profile_hdr['center'],color='red',alpha=0.5)
    p2a1.set_title('trail id={}'.format(row['id']))

    final_width = np.maximum(min_mask_width, profile_hdr['width'])

    p2a1.axvline(profile_hdr['center'] + final_width / 2, color='magenta', alpha=0.75)
    p2a1.axvline(profile_hdr['center'] - final_width / 2, color='magenta',alpha=0.75)

    xmin = np.maximum(profile_hdr['center'] - 3*final_width, 0)
    xmax = np.minimum(profile_hdr['center'] + 3*final_width, len(profile))

    p2a1.set_xlim(xmin, xmax)

    # add a little status string
    if row['status'] <= 1:
        status_string = 'status = rejected ({})'.format(row['status'])
    else:
        status_string = 'status = accepted ({})'.format(row['status'])

    p2a1.text(0.99,0.99,status_string,transform=p2a1.transAxes, ha='right', va='top')
    p2a1.text(0.99,0.94, 'width = {:.1f}'.format(profile_hdr['width']), transform=p2a1.transAxes, ha='right', va='top')

    #for ax in [p1a1, p1a2, p3a1, p3a2, p4a1, p4a2]:
    #    ax.axis('off')


    #plt.tight_layout()
    if output_file is not None:
        plt.savefig(output_file, dpi=150)

    plt.close()


def make_image_diagnostic(image_arr,
                          final_mask_arr,
                          segment_arr,
                          catalog_arr,
                          root,
                          satdir,
                          big_rebin=8,
                          scale=[-1,3],
                          cmap='Greys',
                          output_file = None, 
                          min_mask_width=10,
                          overwrite=False):
    
    if output_file is not None:
        if Path(output_file).exists() & (overwrite == False):
            print('Output file {} already exists.'.format(output_file))
            print('Set overwrite = True to replace it.')
            plt.close('all')
            return

    # set up figure grid
    fig = plt.figure(figsize=(15,12), layout='constrained')
    fig.suptitle('Final Image Diagnostic\n' + root)

    [[p1, p2],[p3, p4]] = fig.subfigures(2,2)

    p1a1, p1a2 = p1.subplots(2,1)
    p2a1, p2a2 = p2.subplots(2,1)
    p3a1, p3a2 = p3.subplots(2,1)
    p4a1, p4a2 = p4.subplots(2,1)

    # set up images
    __, image_med, image_stddev = sigma_clipped_stats(image_arr)
    for ax, wfc in zip([p1a1, p1a2], image_arr):
        ax.imshow(wfc, cmap=cmap, origin='lower', aspect='auto',
                    vmin=image_med - scale[0]*image_stddev,
                    vmax=image_med + scale[1]*image_stddev)
    p1a1.set_title('Image')

    for ax, segment, wfc in zip([p2a1, p2a2],segment_arr, image_arr):

        ax.imshow(wfc, cmap=cmap, origin='lower', aspect='auto',
            vmin=image_med - scale[0]*image_stddev,
            vmax=image_med + scale[1]*image_stddev,
            alpha=0.5)
       # get unique values in segment
        unique_vals = np.unique(segment)
        data = np.zeros_like(segment)
        counter = 1
        for uv in unique_vals[1:]:
            data[segment == uv] = counter
            counter += 1

        data_min = np.min(data).astype(int)
        data_max = np.max(data).astype(int)

        data_masked = np.ma.masked_where(data == 0, data)

        # update the colormap to match the segmentation IDs
        seg_cmap = plt.get_cmap('tab20', data_max - data_min + 1)
        mat = ax.imshow(data_masked, cmap=seg_cmap, vmin=data_min - 0.5,
                        vmax=data_max + 0.5, origin='lower', aspect='auto',
                        alpha=0.75)

        # tell the colorbar to tick at integers
        ticks = np.arange(len(unique_vals) + 1)
        cax = plt.colorbar(mat, ticks=ticks)
        cax.ax.set_yticklabels(np.concatenate([unique_vals,
                                               [unique_vals[-1] + 1]]))
        cax.ax.set_ylabel('trail ID')
        #x.set_title('Segmentation Mask')

    p2a1.set_title('Image with segmented mask')

    # # do this for the bottom left too
    # for ax, wfc, mask in zip([p3a1, p3a2], image_arr, final_mask_arr):
    #     ax.imshow(wfc, cmap=cmap, origin='lower', aspect='auto',
    #                 vmin=image_med - scale[0]*image_stddev,
    #                 vmax=image_med + scale[1]*image_stddev)

    #     ax.imshow(np.ma.masked_where(mask == 0, mask)*255, alpha=0.5, origin='lower', aspect='auto', cmap='Set1')
    # p3a1.set_title('Image with all trails masked')

    # make the big masked image
    for ax, image, final_mask in zip([p4a1, p4a2], image_arr, final_mask_arr):
        masked_image = np.ma.masked_where(final_mask, image)
        rebinned_masked_image = block_reduce(masked_image, big_rebin, func=np.nanmedian)
        __, image_med, image_stddev = sigma_clipped_stats(rebinned_masked_image)

        ax.imshow(rebinned_masked_image, origin='lower', aspect='auto',
                  vmin=image_med - image_stddev, vmax = image_med + 5*image_stddev)
    p4a1.set_title('Rebinned final masked image')

    # load all available profiles and plot; including their widths
    for ax, catalog, ext in zip([p3a1, p3a2], catalog_arr, [4,1]):
        print(len(catalog))
        if len(catalog) > 0:

            xlow = 0
            xhigh = 0
            for row in catalog:
                if row['status'] == 2:
                    # load the 1d profile and header, then plot
                    prof_dir = Path.joinpath(Path(satdir), '{}_ext{}_mrt/'.format(root, ext))

                    #profile_file = '{}{}_ext{}_mrt_1dprof_{}.fits'.format(prof_dir, root, ext, row['id'])
                    profile_file = Path.joinpath(prof_dir,
                                                 '{}_ext{}_mrt_1dprof_{}.fits'.format(root, ext, row['id']))
                    
                    if ~profile_file.exists():
                        print('Profile file missing. Skipping')
                        continue

                    prof = fits.getdata(profile_file)
                    prof_hdr = fits.getheader(profile_file)

                    # show the 1d profile
                    xarr = np.arange(len(prof)) - prof_hdr['center']
                    log_med = np.log10(prof+100)
                    if ext == 4:
                        chip = 'wfc1'
                    else:
                        chip = 'wfc2'
                    label = '{} - {}'.format(row['id'], chip)
                    ax.plot(xarr, log_med, label=label)
                    final_width = np.maximum(min_mask_width, prof_hdr['width'])
                    # indicate the iwdth

                    ax.axvline(-final_width/2, ls='--')
                    ax.axvline(final_width/2, ls='--')


                    if -3*final_width < xlow:
                        xlow = -3*final_width
                    if 3*final_width > xhigh:
                        xhigh = 3*final_width

                    ax.set_xlim(xlow, xhigh)
                    ax.legend()

    p3a1.set_title('1D trail profiles')

    #print(root)
    #plt.show()

    #plt.tight_layout()
    if output_file is not None:
            plt.savefig(output_file, dpi=150)

    plt.close()

if __name__ == '__main__':

    test_trail_diagnostic = True
    test_image_diagnostic = False

    # testing
    root = '09575_eg_acs_wfc_f775w_02_j8fnegrbq_flc'

    image_file = '/Users/dstark/supercal/09575/{}.fits'.format(root)

    # load image file
    hdu = fits.open(image_file)
    wfc1 = block_reduce(hdu[4].data, 4, func=np.nansum)
    wfc2 = block_reduce(hdu[1].data, 4, func=np.nansum)

    hdu.close()
    image_arr = [wfc1, wfc2]

    catalog_file = '/Users/dstark/supercal/09575/satellites/{}_ext4_mrt_catalog.fits'.format(root)
    catalog = Table.read(catalog_file)
    row = catalog[0]
    ext=4
    segmentation_file_4 = '/Users/dstark/supercal/09575/satellites/{}_ext4_mrt_segment.fits'.format(root)
    segmentation_file_1 = '/Users/dstark/supercal/09575/satellites/{}_ext1_mrt_segment.fits'.format(root)
    segment_wfc1 = fits.getdata(segmentation_file_4)
    segment_wfc2 = fits.getdata(segmentation_file_1)
    segment_arr = [segment_wfc1, segment_wfc2]

    # load the catalogs for each chip too
    catalog_4 = Table.read('/Users/dstark/supercal/09575/satellites/{}_ext4_mrt_catalog.fits'.format(root))
    catalog_1 = Table.read('/Users/dstark/supercal/09575/satellites/{}_ext1_mrt_catalog.fits'.format(root))
    catalog_arr = [catalog_4, catalog_1]


    # get trail mask

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

    #get total mask
    mask_arr = [segment_wfc1 > 0, segment_wfc2 > 0]

    # load the 1d trail profile and its header
    profile = fits.getdata('/Users/dstark/supercal/09575/satellites/{}_ext{}_mrt/{}_ext{}_mrt_1dprof_{}.fits'.format(root, ext, root, ext, row['id']))
    profile_hdr = fits.getheader('/Users/dstark/supercal/09575/satellites/{}_ext{}_mrt/{}_ext{}_mrt_1dprof_{}.fits'.format(root, ext, root, ext, row['id']))

    root = image_file.split('/')[-1].split('.fits')[0]
    sat_dir = '/Users/dstark/supercal/09575/satellites/'


    if test_trail_diagnostic:
        panels = make_trail_diagnostic(image_arr,mask_arr,trail_mask_arr,row,profile,profile_hdr, root=root)


    if test_image_diagnostic:
        panels = make_image_diagnostic(image_arr,
                                        mask_arr,
                                        segment_arr,
                                        catalog_arr,
                                        root,
                                        sat_dir,
                                        scale=[-1,3],
                                        cmap='Greys', 
                                        output_file = None)