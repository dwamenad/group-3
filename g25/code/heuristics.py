import os

def create_key(template, outtype=('nii.gz',), annotation_classes=None):
        if template is None or not template:
                raise ValueError('Template must be a valid format string')
        return template, outtype, annotation_classes

def infotodict(seqinfo):
    t1w = create_key('sub-{subject}/anat/sub-{subject}_T1w')
    mag = create_key('sub-{subject}/fmap/sub-{subject}_acq-bold_magnitude')
    phase = create_key('sub-{subject}/fmap/sub-{subject}_acq-bold_phasediff')
    t2_flair = create_key('sub-{subject}/anat/sub-{subject}_FLAIR')
    trust_mag = create_key('sub-{subject}/func/sub-{subject}_task-trust_run-{item:d}_part-mag_bold')
    trust_phase = create_key('sub-{subject}/func/sub-{subject}_task-trust_run-{item:d}_part-phase_bold')
    trust_sbref = create_key('sub-{subject}/func/sub-{subject}_task-trust_run-{item:d}_sbref')
    SST_mag = create_key('sub-{subject}/func/sub-{subject}_task-SST_run-{item:d}_part-mag_bold')
    SST_phase = create_key('sub-{subject}/func/sub-{subject}_task-SST_run-{item:d}_part-phase_bold')
    SST_sbref = create_key('sub-{subject}/func/sub-{subject}_task-SST_run-{item:d}_sbref')
    adview_mag = create_key('sub-{subject}/func/sub-{subject}_task-adview_run-{item:d}_part-mag_bold')
    adview_phase = create_key('sub-{subject}/func/sub-{subject}_task-adview_run-{item:d}_part-phase_bold')
    adview_sbref = create_key('sub-{subject}/func/sub-{subject}_task-adview_run-{item:d}_sbref')
    dwi = create_key('sub-{subject}/dwi/sub-{subject}_dwi')
    dwi_pa = create_key('sub-{subject}/fmap/sub-{subject}_acq-dwi_dir-PA_epi')
    dwi_ap = create_key('sub-{subject}/fmap/sub-{subject}_acq-dwi_dir-AP_epi')

    info = {t1w: [],
            mag: [], phase: [],
            dwi: [], dwi_pa: [], dwi_ap: [],
            t2_flair: [],
            trust_mag: [], trust_phase: [], trust_sbref: [],
            SST_mag: [], SST_phase: [], SST_sbref: [],
            adview_mag: [], adview_phase: [], adview_sbref: []}

    list_of_ids = [s.series_id for s in seqinfo]

    for s in seqinfo:

        # anatomicals and standard fmaps
        if ('T1w-anat_mpg_07sag_iso' in s.protocol_name):
            info[t1w] = [s.series_id]

        if ('gre_field' in s.protocol_name) and ('P' not in s.image_type):
            idx = list_of_ids.index(s.series_id)
            if idx + 1 < len(seqinfo) and 'P' in seqinfo[idx + 1].image_type:
                info[mag].append(s.series_id)  # magnitude (scan 6)
        if ('gre_field' in s.protocol_name) and ('P' in s.image_type):
            info[phase] = [s.series_id]  # phasediff (scan 7)
        if ('t2_tse_dark-fluid_tra_p3' in s.protocol_name) and (s.dim3 == 47):
            info[t2_flair] = [s.series_id]

        # diffusion images and se fmaps
        if ('cmrr_fieldmapse_ap' in s.protocol_name) and (s.dim4 == 2):
            info[dwi_ap] = [s.series_id]
        if ('cmrr_fieldmapse_pa' in s.protocol_name) and (s.dim4 == 2):
            info[dwi_pa] = [s.series_id]
        if ('cmrr_mb3hydi_ipat2_64ch' in s.protocol_name) and (s.dim4 == 145):
            info[dwi] = [s.series_id]

        # functionals: mag, phase, and sbref
        if (s.dim4 == 1380) and ('Trust' in s.series_description) and ('_Pha' not in s.series_description):
            info[trust_mag].append(s.series_id)
            idx = list_of_ids.index(s.series_id)
            info[trust_sbref].append(list_of_ids[idx -2])
        if (s.dim4 == 1380) and ('Trust' in s.series_description) and ('TR1615_Pha' in s.series_description):
            info[trust_phase].append(s.series_id)

        if (s.dim4 == 1220) and ('SST' in s.series_description) and ('_Pha' not in s.series_description):
            info[SST_mag].append(s.series_id)
            idx = list_of_ids.index(s.series_id)
            info[SST_sbref].append(list_of_ids[idx -2])
        if (s.dim4 == 1220) and ('SST' in s.series_description) and ('TR1615_Pha' in s.series_description):
            info[SST_phase].append(s.series_id)

        if (s.dim4 == 1080) and ('PassiveAds' in s.series_description) and ('_Pha' not in s.series_description):
            info[adview_mag].append(s.series_id)
            idx = list_of_ids.index(s.series_id)
            info[adview_sbref].append(list_of_ids[idx -2])
        if (s.dim4 == 1080) and ('PassiveAds' in s.series_description) and ('TR1615_Pha' in s.series_description):
            info[adview_phase].append(s.series_id)

    return info

POPULATE_INTENDED_FOR_OPTS = {
                'matching_parameters': ['ModalityAcquisitionLabel'],
                'criterion': 'Closest'
}
