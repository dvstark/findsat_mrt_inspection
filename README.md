<h1> Instructions for running satellite mask inspection tools </h1>

<b>Disclaimer: All codes in this repo and under construction. Some (all?) are poorly documented, probably not very efficient, and definitely not very pretty or following best practices. Right now, they only work if files are organized in the same way that the supercal directories are.</b>

<h2> List of files: </h2>

  * inspect_sat_masks.py -- main tool in inspect satellite trails created by acstools.findsat_mrt
  * new_diagnostics.py -- codes to create updated trail and image diagnostic plots showing identified trails and their masks
  * update_diagnostics.py -- code to update image and trail diagnostic files to the newest format. Should be run prior to inspecting satellite trails masks
  * config.yaml -- configuration file for inspect_sat_masks.py

<h2> Setup </h2>

<h3> Environment </h3>

First you'll need to setup up the environment. We mostly use the standard ```stenv``` environment, but with a modified unreleased version of ```acstools```.

First, download the stenv environment and follow the instructions <a href="https://stenv.readthedocs.io/en/latest/index.html">here</a>. You may want to name the environment something aside from "stenv", for example, let's assume you call it "stenv_findsat_mrt".

Once the environment is set up, activate it
```bash
conda activate stenv_findsat_mrt
```
We are going to replace the standard version of ```acstools```, so let's first uninstall the version packaged with ```stenv```.
```bash
pip uninstall acstools
```

Next, run the following code to download a very specific branch of my personal acstools repo (this assumes you have git configured). 
```bash
git clone -b supercal_fix git@github.com:dvstark/acstools.git
```
And then install that repo
```bash
pip install [path to wherever you put the repo you just cloned]
```


<h3>Satellite mask inspection tools</h3>

The code is not packaged up as a nice repo yet, so for now, just download everything into a directory and run the codes from there. Specifically:
```bash
git clone git@github.com:dvstark/findsat_mrt_inspection.git
```
The codes to be run take directories as input, so it's ok that they are in their own space.

<h2>Running the codes</h2>

<h3> Updating diagnostic plots </h3>

The version of ```findsat_mrt``` in ```acstools```, even my updated version, does not create the most recent style of diagnostic plots. The code, ```update_diagnostics.py``` generates new diagnostic plots in the most recent style from existing output from ```findsat_mrt```. This needs to be run before running ```inspect_sat_masks.py```. To run it, just open python and type:
```python
from update_diagnostics import update_diagnostics
update_diagnostics(path_to_satellite_files)
```
where ```path_to_satellite_trail_files``` is the path where all the findsat_mrt output is saved.

<h3> Inspecting the satellite masks </h3>
The main code to inspect satellite trail masks is called ```inspect_sat_masks.py```. It only works if the file naming convention and directory structure is kept a certain way, so do not move things around.
To run this code, 

  * Go to the directory where it is located
  * open ipython
  * type:
    ```python
    from inspect_sat_masks import inspect_sat_masks 
  * type:
    ```python
    inspect_sat_masks(path_to_satellite_trail_files)
    ```
    where ```path_to_satellite_trail_files``` is the path where all the findsat_mrt output is saved.
    
This program finds all files in a directory and displays diagnostic plots for individual trails, followed by diagnostic plots for the whole image (showing all identified trails at once). By default, only the "robust" trails are shown, although this can be modified.

Options will change depending on whether you're looking at an individual trail or the final overview of the image. 

When looking at individual trails, these are the options:
* [w] Change trail width
* [r] Remove trail. Sets a trail as rejected and removes it from the mask
* [a] Add trail. Sets a trail as "good" and adds it to the mask
* [u] Undo changes. Undoes whtever you just did
* [ds9] Load image in ds9. Allows you to load the full multi-extension fits file for the exposure being considered.
* [i] Jump to another image. Displays a list of images in the directory under consideration. You then choose a number correpsonding to the file you want to jump to. The inspection continues from that point. 
* [t] Toggle only show "good" trails. By default, only the robustly identified trails are shown. These are trails that pass several different checks (intial detection, SNR, persistence across image). However, this option lets you display all "candidate" trails, which includes those that were detected in the MRT but failed subsequent checks. This might be useful in cases where a trail is present in the image but not masked (maybe it was detected but failed some later check). Some images have A LOT of trail candidates. You've been warned...If you select this option, it will go back to the start of the list of trails for the image under consideration. 
* [Q] Quit

  
When looking at the overall image, these are the options:

* [ENTER] Save and go to next image
* [n] Add a completely new trail. This option loads a ds9 window of the WFC extension of interest. Then it asks for coordinates to define the beginning and end of a trail. Don't worry if these coordinates don't touch the edge of the chip; the mask gets extrapolated. After this, a trail diagnostic image for the new trail is shown where the width can be further adjusted. Or the trail can be rejected.
* [r] Re-examine trails. This option allows you to go through each individual trail found for this image. If there are no trails, nothing happens. 
* [ds9] Load image in ds9.  See above for description.
* [i] Jump to another image. See above for description.
* [t] Toggle only show "good" trails. See above for description.
* [Q] Quit




