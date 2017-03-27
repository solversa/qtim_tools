import dicom
import nibabel as nib
import os
import glob

def return_dicom_dictionary(filepath=[], folder=[], attributes_regex="*.dcm"):

    """ This is currently broken, and overly-specific. Consider removing.
    """

    image_numpy = nib.load('C:/Users/azb22/Documents/Scripting/Breast_MRI_Challenge/ISPY_data/AllFiles/ISPY1_1098_19860919/ISPY1_1098_19860919_BreastTissue.nii.gz')
    transform_matrix = image_numpy.affine

    if folder != []:
        img_dicom_list = []
        for root, dirnames, filenames in os.walk(folder):
            for filename in fnmatch.filter(filenames, attributes_regex):
                img_dicom_list.append(os.path.join(root, filename))

        if img_dicom_list == []:
            print "No DICOM attributes returned. Folder is empty."
        else:

            attribute_list = np.zeros((1, 10), dtype=object)
            temp_list = np.zeros((1, 10), dtype=object)
            attribute_list[0,:] = ['filename','PatientName','date','center1', 'center2', 'center3', 'lx','ly','lz','type']
            RadiusMatrix = np.zeros((3,3), dtype=float)

            for filepath_idx, filepath in enumerate(img_dicom_list):
                img_dicom = dicom.read_file(filepath)
                try:
                    # print img_dicom[0x117,0x1020][0][0x117,0x1043].value
                    RadiusMatrix[0,:] = img_dicom[0x117,0x1020][0][0x117,0x1043].value[0:3]
                    RadiusMatrix[1,:] = img_dicom[0x117,0x1020][0][0x117,0x1044].value[0:3]
                    RadiusMatrix[2,:] = img_dicom[0x117,0x1020][0][0x117,0x1045].value[0:3]
                    # print filepath
                    temp_list[0, 3] = img_dicom[0x117,0x1020][0][0x117,0x1042].value[0]
                    temp_list[0, 4] = img_dicom[0x117,0x1020][0][0x117,0x1042].value[1]
                    temp_list[0, 5] = img_dicom[0x117,0x1020][0][0x117,0x1042].value[2]
                    temp_list[0, 6] = np.max(abs(RadiusMatrix[:,0]))
                    temp_list[0, 7] = np.max(abs(RadiusMatrix[:,1]))
                    temp_list[0, 8] = np.max(abs(RadiusMatrix[:,2]))
                    # print filepath
                    temp_list[0, 9] = img_dicom[0x117,0x1020][0][0x117,0x1046].value
                    temp_list[0, 2] = img_dicom.StudyDate
                    temp_list[0, 1] = img_dicom.PatientID
                    temp_list[0, 0] = filepath
                    if [img_dicom.StudyDate, img_dicom.PatientID] not in attribute_list[:,1:3]:
                        attribute_list = np.vstack((attribute_list, temp_list))
                        # print temp_list
                    # print ''
                except:
                    continue
                if attribute_list[0, 7] == 'nan':
                    # continue
                    for i in xrange(attribute_list.shape[1]):
                        print attribute_list[0, i]
                    for i in xrange(2,6):
                        col_vec = attribute_list[0, i][0:3]
                        # col_vec[0]  = -col_vec[0]
                        # col_vec[1] = -col_vec[1]
                        # print np.round(nib.affines.apply_affine(transform_matrix, col_vec))
                    # print col_vec.shape
                    # for i in xrange(1,5):
                        # transformed = nib.affines.apply_affine(np.linalg.inv(transform_matrix), np.reshape(attribute_list[0, i][0:3], (1,3)))
                        # print transformed
                        # image = image_numpy.get_data()

                # fig = plt.figure()
                # imgplot = plt.imshow(image[:,:,int(transformed[0][2])], interpolation='none', aspect='auto')
                # plt.show()
                
                # print transform_matrix
                # print attribute_list[0, 1]
            with open('C:/Users/azb22/Documents/GitHub/QTIM_Pipelines/QTIM_Feature_Extraction_Pipeline/Test_Data/VOI_INFO_ISPY1.csv', 'wb') as writefile:
                csvfile = csv.writer(writefile, delimiter=',')
                for row in attribute_list:
                    csvfile.writerow(row)

        # print attribute_list

    elif filepath != []:
        img_dicom = dicom.read_file(filepath) 
        print img_dicom

    else:
        print "No DICOM attributes returned. Please provide a file or folder path."
        return

def dcm_2_numpy(filepath):

    # Maybe for the future...

    return