#!/usr/bin/python
import json
import sys
import os
import six

from jsonschema import validate
from jsonschema import ValidationError
# Hack hack
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from common import SampleConstants
from common import namespace_sample_id, namespace_measurement_id, create_media_component, create_mapped_name, create_value_unit, map_experiment_reference, namespace_experiment_id
from synbiohub_adapter.query_synbiohub import *
from synbiohub_adapter.SynBioHubUtil import *
from sbol import *
from datacatalog.agavehelpers import AgaveHelper

"""
Schema closely aligns with V1 target schema
Walk and expand to dictionary/attribute blocks
as necessary
"""


def convert_transcriptic(schema_file, input_file, verbose=True, output=True, output_file=None, config={}, enforce_validation=True, reactor=None):

    if reactor is not None:
        helper = AgaveHelper(reactor.client)
        print("Helper loaded")
    else:
        print("Helper not loaded")

    DEFAULT_BEAD_MODEL = "SpheroTech URCP-38-2K"
    DEFAULT_BEAD_BATCH = "AJ02"
    DEFAULT_CYTOMETER_CHANNELS = ["BL1-A", "FSC-A", "SSC-A", "RL1-A"]
    DEFAULT_CYTOMETER_CONFIGURATION = "/sd2e-community/sample/transcriptic/instruments/flow/attune/1AAS220201014/12142017/cytometer_configuration.json"

    # for SBH Librarian Mapping
    sbh_query = SynBioHubQuery(SD2Constants.SD2_SERVER)

    schema = json.load(open(schema_file))
    transcriptic_doc = json.load(open(input_file))

    output_doc = {}

    lab = SampleConstants.LAB_TX

    output_doc[SampleConstants.EXPERIMENT_ID] = namespace_experiment_id(transcriptic_doc[SampleConstants.EXPERIMENT_ID], lab)

    cp = transcriptic_doc[SampleConstants.CHALLENGE_PROBLEM]
    #TX's name for YG...
    if cp == "YG":
        cp = SampleConstants.CP_YEAST_GATES
    elif cp == "NC":
        cp = SampleConstants.CP_NOVEL_CHASSIS
    else:
        raise ValueError("Unknown TX CP: {}".format(cp))

    output_doc[SampleConstants.CHALLENGE_PROBLEM] = cp

    output_doc[SampleConstants.EXPERIMENT_REFERENCE_URL] = transcriptic_doc[SampleConstants.EXPERIMENT_REFERENCE]

    map_experiment_reference(config, output_doc)

    output_doc[SampleConstants.LAB] = lab
    output_doc[SampleConstants.SAMPLES] = []
    samples_w_data = 0

    for transcriptic_sample in transcriptic_doc[SampleConstants.SAMPLES]:
        sample_doc = {}

        # e.g. aq1bsuhh8sb9px/ct1bsmggegqg89
        # first part is a unique sample id
        # second part encodes the measurement operation
        # e.g. grouping for OD or FCS
        tx_sample_measure_id = transcriptic_sample["tx_sample_id"].split("/")
        sample_id = tx_sample_measure_id[0]
        measurement_id = tx_sample_measure_id[1]

        sample_doc[SampleConstants.SAMPLE_ID] = namespace_sample_id(sample_id, lab)

        # media
        contents = []
        if SampleConstants.CONTENTS in transcriptic_sample:
            for reagent in transcriptic_sample[SampleConstants.CONTENTS]:
                if reagent is None or len(reagent) == 0:
                    print("Warning, reagent value is null or empty string {}".format(sample_doc[SampleConstants.SAMPLE_ID]))
                else:
                    if len(transcriptic_sample[SampleConstants.CONTENTS]) == 1 and SampleConstants.CONCENTRATION in transcriptic_sample:
                        contents.append(create_media_component(reagent, reagent, lab, sbh_query, transcriptic_sample[SampleConstants.CONCENTRATION]))
                    else:
                        contents.append(create_media_component(reagent, reagent, lab, sbh_query))

        if SampleConstants.MEDIA in transcriptic_sample and SampleConstants.MEDIA_RS_ID in transcriptic_sample:
            media = transcriptic_sample[SampleConstants.MEDIA]
            media_id = transcriptic_sample[SampleConstants.MEDIA_RS_ID]
            contents.append(create_media_component(media, media_id, lab, sbh_query))

        if len(contents) > 0:
            sample_doc[SampleConstants.CONTENTS] = contents

        # strain
        if SampleConstants.STRAIN in transcriptic_sample:
            strain = transcriptic_sample[SampleConstants.STRAIN]
            sample_doc[SampleConstants.STRAIN] = create_mapped_name(strain, strain, lab, sbh_query, strain=True)

        # temperature
        sample_doc[SampleConstants.TEMPERATURE] = create_value_unit(transcriptic_sample[SampleConstants.TEMPERATURE])

        # od
        if SampleConstants.INOCULATION_DENSITY in transcriptic_sample:
            sample_doc[SampleConstants.INOCULATION_DENSITY] = create_value_unit(transcriptic_sample[SampleConstants.INOCULATION_DENSITY])

        # replicate
        replicate_val = transcriptic_sample[SampleConstants.REPLICATE]
        if replicate_val is None:
            print("Warning, replicate value is null, sample {}".format(sample_doc[SampleConstants.SAMPLE_ID]))
        else:
            if isinstance(replicate_val, six.string_types):
                replicate_val = int(replicate_val)
            sample_doc[SampleConstants.REPLICATE] = replicate_val

        # time
        time_val = transcriptic_sample[SampleConstants.TIMEPOINT]

        # enum fix
        if time_val.endswith("hours"):
            time_val = time_val.replace("hours", "hour")

        # controls and standards
        # map standard for, type,
        if SampleConstants.STANDARD_TYPE in transcriptic_sample:
            sample_doc[SampleConstants.STANDARD_TYPE] = transcriptic_sample[SampleConstants.STANDARD_TYPE]
        if SampleConstants.STANDARD_FOR in transcriptic_sample:
            sample_doc[SampleConstants.STANDARD_FOR] = transcriptic_sample[SampleConstants.STANDARD_FOR]

        # map control for, type
        if SampleConstants.CONTROL_TYPE in transcriptic_sample:
            sample_doc[SampleConstants.CONTROL_TYPE] = transcriptic_sample[SampleConstants.CONTROL_TYPE]
        if SampleConstants.CONTROL_FOR in transcriptic_sample:
            sample_doc[SampleConstants.CONTROL_FOR] = transcriptic_sample[SampleConstants.CONTROL_FOR]

        # fill in attributes if we have a bead standard
        if SampleConstants.STANDARD_TYPE in sample_doc and \
            sample_doc[SampleConstants.STANDARD_TYPE] == SampleConstants.STANDARD_BEAD_FLUORESCENCE and \
                SampleConstants.STANDARD_ATTRIBUTES not in sample_doc:
                    sample_doc[SampleConstants.STANDARD_ATTRIBUTES] = {}
                    sample_doc[SampleConstants.STANDARD_ATTRIBUTES][SampleConstants.BEAD_MODEL] = DEFAULT_BEAD_MODEL
                    sample_doc[SampleConstants.STANDARD_ATTRIBUTES][SampleConstants.BEAD_BATCH] = DEFAULT_BEAD_BATCH

        # if control types are not available, infer based on sample ids
        # this is brittle, but the best we can do right now with the output provided
        # "wt-control-1" = precursor to "WT-Dead-Control" or "WT-Live-Control"
        # "NOR 00 Control" = "HIGH_FITC"
        # "WT-Dead-Control" = "CELL_DEATH_POS_CONTROL" - positive for the sytox stain
        # "WT-Live-Control" = "CELL_DEATH_NEG_CONTROL" - negative for the sytox stain
        original_sample_id = tx_sample_measure_id = transcriptic_sample[SampleConstants.SAMPLE_ID]
        if SampleConstants.CONTROL_TYPE not in transcriptic_sample:
            if original_sample_id == "wt-control-1":
                sample_doc[SampleConstants.CONTROL_TYPE] = SampleConstants.CONTROL_EMPTY_VECTOR
            elif original_sample_id == "NOR 00 Control":
                sample_doc[SampleConstants.CONTROL_TYPE] = SampleConstants.CONTROL_HIGH_FITC
            elif original_sample_id == "WT-Dead-Control":
                sample_doc[SampleConstants.CONTROL_TYPE] = SampleConstants.CONTROL_CELL_DEATH_POS_CONTROL
            elif original_sample_id == "WT-Live-Control":
                sample_doc[SampleConstants.CONTROL_TYPE] = SampleConstants.CONTROL_CELL_DEATH_NEG_CONTROL

        # determinstically derive measurement ids from sample_id + counter (local to sample)
        measurement_counter = 1

        for file in transcriptic_sample[SampleConstants.FILES]:
            measurement_doc = {}

            measurement_doc[SampleConstants.TIMEPOINT] = create_value_unit(time_val)

            measurement_doc[SampleConstants.FILES] = []

            measurement_type = file[SampleConstants.M_TYPE]

            # enum fix
            if measurement_type == "RNASeq":
                measurement_type = SampleConstants.MT_RNA_SEQ

            measurement_doc[SampleConstants.MEASUREMENT_TYPE] = measurement_type

            # apply defaults, if nothing mapped
            if measurement_type == SampleConstants.MT_FLOW:
                if SampleConstants.M_CHANNELS not in measurement_doc:
                    measurement_doc[SampleConstants.M_CHANNELS] = DEFAULT_CYTOMETER_CHANNELS
                if SampleConstants.M_INSTRUMENT_CONFIGURATION not in measurement_doc:
                    measurement_doc[SampleConstants.M_INSTRUMENT_CONFIGURATION] = DEFAULT_CYTOMETER_CONFIGURATION

            # TX can repeat measurement ids
            # across multiple measurement types, append
            # the type so we have a distinct id per actual grouped measurement
            typed_measurement_id = '.'.join([measurement_id, measurement_type])

            # generate a measurement id unique to this sample
            measurement_doc[SampleConstants.MEASUREMENT_ID] = namespace_measurement_id(".".join([sample_doc[SampleConstants.SAMPLE_ID], str(measurement_counter)]), output_doc[SampleConstants.LAB])

            # record a measurement grouping id to find other linked samples and files
            measurement_doc[SampleConstants.MEASUREMENT_GROUP_ID] = namespace_measurement_id(typed_measurement_id, output_doc[SampleConstants.LAB])

            measurement_counter = measurement_counter + 1

            file_name = file[SampleConstants.M_NAME]
            file_type = SampleConstants.infer_file_type(file_name)
            file_name_final = file_name
            if file_name.startswith('s3'):
                file_name_final = file_name.split('/')[-1]
            measurement_doc[SampleConstants.FILES].append(
                {SampleConstants.M_NAME: file_name_final,
                                SampleConstants.M_TYPE : file_type, \
                                SampleConstants.M_STATE : SampleConstants.M_STATE_RAW,
                                SampleConstants.FILE_LEVEL: SampleConstants.F_LEVEL_0})

            if len(measurement_doc[SampleConstants.FILES]) == 0:
                print("Warning, measurement contains no files, skipping {}".format(file_name))
            else:
                if SampleConstants.MEASUREMENTS not in sample_doc:
                    sample_doc[SampleConstants.MEASUREMENTS] = []
                sample_doc[SampleConstants.MEASUREMENTS].append(measurement_doc)
                samples_w_data = samples_w_data + 1
                print('sample {} / measurement {} contains {} files'.format(sample_doc[SampleConstants.SAMPLE_ID], file_name, len(measurement_doc[SampleConstants.FILES])))

        output_doc[SampleConstants.SAMPLES].append(sample_doc)

    print('Samples in file: {}'.format(len(transcriptic_doc)))
    print('Samples with data: {}'.format(samples_w_data))

    try:
        validate(output_doc, schema)
        #if verbose:
        #print(json.dumps(output_doc, indent=4))
        if output is True or output_file is not None:
            if output_file is None:
                path = os.path.join(
                    "output/transcriptic", os.path.basename(input_file))
            else:
                path = output_file
            with open(path, 'w') as outfile:
                json.dump(output_doc, outfile, indent=4)
        return True
    except ValidationError as err:
        if enforce_validation:
            raise ValidationError("Schema Validation Error", err)
        else:
            if verbose:
                print("Schema Validation Error: {0}\n".format(err))
            return False

if __name__ == "__main__":
    path = sys.argv[2]
    if os.path.isdir(path):
        for f in os.listdir(path):
            file_path = os.path.join(path, f)
            print(file_path)
            if file_path.endswith(".js") or file_path.endswith(".json"):
                convert_transcriptic(sys.argv[1], file_path)
            else:
                print("Skipping {}".format(file_path))
    else:
        convert_transcriptic(sys.argv[1], sys.argv[2])

