""" This is a utility module for loading dicom data and headers. It borrows heavily from pydicom.
    It will likely take a lot of DICOM knowledge to navigate..
"""

import dicom
import nibabel as nib
import numpy as np
import os
import glob
import re

from collections import defaultdict

from qtim_tools.qtim_utilities.file_util import human_sort, grab_files_recursive, sanitize_filename, replace_suffix
from qtim_tools.qtim_utilities.nifti_util import save_numpy_2_nifti, check_image_2d

def get_dicom_dictionary(input_filepath=[], dictionary_regex="*", return_type='name'):

    """ Returns a dictionary of dicom tags using pydicom. TODO: let users return tag
        dictionary.
    """

    if os.path.isdir(input_filepath):
        dictionary_file = glob.glob(os.path.join(input_filepath, '*'))[0]
    else:
        dictionary_file = input_filepath

    img_dicom = dicom.read_file(dictionary_file)

    output_dictionary = {}

    for key in img_dicom.dir():
        try:
            if key != 'PixelData':
                output_dictionary[key] = img_dicom.data_element(key).value
        except:
            pass

    return output_dictionary

def dcm_2_numpy(input_folder, return_header=False, verbose=True):

    """ Uses pydicom to stack an alphabetical list of DICOM files. TODO: Make it
        take slice_order into account.
    """

    if verbose:
        print 'Searching for dicom files...'

    found_files = grab_files_recursive(input_folder)

    if verbose:
        print 'Found', len(found_files), 'in directory. \n'
        print 'Checking DICOM compatability...'

    dicom_files = []
    for file in found_files:
        try:
            temp_dicom = dicom.read_file(file)
            dicom_files += [[file, temp_dicom.data_element('SeriesInstanceUID').value]]
        except:
            continue

    if verbose:
        print 'Found', len(dicom_files), 'DICOM files in directory. \n'
        print 'Counting volumes..'

    dicom_headers = [] 
    unique_dicoms = defaultdict(list)
    for dicom_file in dicom_files:
        UID = dicom_file[1]
        unique_dicoms[UID] += [dicom_file[0]]

    if verbose:
        print 'Found', len(unique_dicoms.keys()), 'unique volumes \n'
        print 'Saving out files from these volumes.'

    output_dict = {}

    for UID in unique_dicoms.keys():
        
        current_dicoms = [dicom.read_file(dcm) for dcm in unique_dicoms[UID]]
        volume_label = current_dicoms[0].data_element('SeriesDescription').value

        try:
            output_numpy = np.zeros((current_dicoms[0].pixel_array.shape + (len(current_dicoms),)), dtype=float)
            output_dict[volume_label] = output_numpy

            dicom_instances = [x.data_element('InstanceNumber').value for x in current_dicoms]
            current_dicoms = [x for _,x in sorted(zip(dicom_instances,current_dicoms))]

            for i in xrange(output_numpy.shape[-1]):
                output_numpy[..., i] = current_dicoms[i].pixel_array
        except:
            output_dict[volume_label] = None
            print 'Could not read DICOM at SeriesDescription...', volume_label

    return output_dict
    
def dcm_2_nifti(input_folder, output_folder, verbose=True, naming_tags=['SeriesDescription'], folder_tags=['PatientID', 'StudyDate'], folder_mode='combine', prefix='', suffix='', write_header=False, header_suffix='_header', harden_orientation=True):

    """ Uses pydicom to stack an alphabetical list of DICOM files. TODO: Make it
        take slice_order into account.
    """

    if verbose:
        print 'Searching for dicom files...'

    found_files = grab_files_recursive(input_folder)

    if verbose:
        print 'Found', len(found_files), 'in directory. \n'
        print 'Checking DICOM compatability...'

    dicom_files = []
    for file in found_files:
        try:
            temp_dicom = dicom.read_file(file)
            dicom_files += [[file, temp_dicom.data_element('SeriesInstanceUID').value]]
        except:
            continue

    if verbose:
        print 'Found', len(dicom_files), 'DICOM files in directory. \n'
        print 'Counting volumes..'

    dicom_headers = [] 
    unique_dicoms = defaultdict(list)
    for dicom_file in dicom_files:
        UID = dicom_file[1]
        unique_dicoms[UID] += [dicom_file[0]]

    if verbose:
        print 'Found', len(unique_dicoms.keys()), 'unique volumes \n'
        print 'Saving out files from these volumes.'

    output_dict = {}
    output_filenames = []
    for UID in unique_dicoms.keys():
    
        try:
            # Grab DICOMs for a certain Instance
            current_dicoms = [dicom.read_file(dcm) for dcm in unique_dicoms[UID]]

            # Sort DICOMs by Instance.
            dicom_instances = [x.data_element('InstanceNumber').value for x in current_dicoms]
            current_dicoms = [x for _,x in sorted(zip(dicom_instances,current_dicoms))]
            first_dicom, last_dicom = current_dicoms[0], current_dicoms[-1]

            # Create a filename for the DICOM
            volume_label = '_'.join([first_dicom.data_element(tag).value for tag in naming_tags]).replace(" ", "")
            volume_label = prefix + sanitize_filename(volume_label) + suffix + '.nii.gz'

            if verbose:
                print 'Saving...', volume_label

        except:
            print 'Could not read DICOM volume SeriesDescription. Skipping UID...', str(UID)
            continue

        try:
            # Extract patient position information for affine creation.
            output_affine = np.eye(4)
            image_position_patient = np.array(first_dicom.data_element('ImagePositionPatient').value).astype(float)
            image_orientation_patient = np.array(first_dicom.data_element('ImageOrientationPatient').value).astype(float)
            last_image_position_patient = np.array(last_dicom.data_element('ImagePositionPatient').value).astype(float)
            pixel_spacing_patient = np.array(first_dicom.data_element('PixelSpacing').value).astype(float)

            # Create DICOM Space affine (don't fully understand, TODO)
            output_affine[0:3, 0] = pixel_spacing_patient[0] * image_orientation_patient[0:3]
            output_affine[0:3, 1] = pixel_spacing_patient[1] * image_orientation_patient[3:6]
            output_affine[0:3, 2] = (image_position_patient - last_image_position_patient) / (1 - len(current_dicoms))
            output_affine[0:3, 3] = image_position_patient

            # Transformations from DICOM to Nifti Space (don't fully understand, TOO)
            cr_flip = np.eye(4)
            cr_flip[0:2,0:2] = [[0,1],[1,0]]
            neg_flip = np.eye(4)
            neg_flip[0:2,0:2] = [[-1,0],[0,-1]]
            output_affine = np.matmul(neg_flip, np.matmul(output_affine, cr_flip))

            # Create numpy array data...
            output_numpy = np.zeros((current_dicoms[0].pixel_array.shape + (len(current_dicoms),)), dtype=float)
            for i in xrange(output_numpy.shape[-1]):
                output_numpy[..., i] = current_dicoms[i].pixel_array

            # If preferred, harden to identity matrix space (LPS, maybe?)
            # Also unsure of the dynamic here, but they work.
            if harden_orientation is not None:

                cx, cy, cz = np.argmax(np.abs(output_affine[0:3,0:3]), axis=0)

                output_numpy = np.transpose(output_numpy, (cx,cy,cz))

                harden_matrix = np.eye(4)
                for dim, i in enumerate([cx,cy,cz]):
                    harden_matrix[i,i] = 0
                    harden_matrix[dim, i] = 1
                output_affine = np.matmul(output_affine, harden_matrix)

                flip_matrix = np.eye(4)
                for i in xrange(3):
                    if output_affine[i,i] < 0:
                        flip_matrix[i,i] = -1
                        output_numpy = np.flip(output_numpy, i)

                output_affine = np.matmul(output_affine, flip_matrix)

            # Create output folder according to tags.
            specific_folder = output_folder
            for tag in folder_tags:
                if specific_folder == output_folder or folder_mode == 'recursive':
                    specific_folder = os.path.join(specific_folder, sanitize_filename(first_dicom.data_element(tag).value))
                elif folder_mode == 'combine':
                    specific_folder = specific_folder + '_' + sanitize_filename(first_dicom.data_element(tag).value)
            if not os.path.exists(specific_folder):
                os.makedirs(specific_folder)

            # Save out file.
            output_filename = os.path.join(specific_folder, volume_label)
            if os.path.exists(output_filename) and output_filename in output_filenames:
                output_filename = replace_suffix(output_filename, '', '_copy')
            save_numpy_2_nifti(output_numpy, output_affine, output_filename)
            output_filenames += [output_filename]

        except:
            print 'Could not read DICOM at SeriesDescription...', volume_label

    return output_filenames

if __name__ == '__main__':
    pass