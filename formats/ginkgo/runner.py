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
from common import namespace_sample_id, namespace_measurement_id, create_media_component, create_mapped_name, create_value_unit
from synbiohub_adapter.query_synbiohub import *
from synbiohub_adapter.SynBioHubUtil import *
from sbol import *
from .mappings import SampleContentsFilter

def convert_ginkgo(schema_file, input_file, verbose=True, output=True, output_file=None, config={}):

    # for SBH Librarian Mapping
    sbh_query = SynBioHubQuery(SD2Constants.SD2_SERVER)

    schema = json.load(open(schema_file))
    ginkgo_doc = json.load(open(input_file))

    output_doc = {}

    lab = SampleConstants.LAB_GINKGO

    # TODO cannot map yet
    output_doc[SampleConstants.EXPERIMENT_ID] = "UNKNOWN"
    output_doc[SampleConstants.CHALLENGE_PROBLEM] = SampleConstants.CP_UNKNOWN
    output_doc[SampleConstants.EXPERIMENT_REFERENCE] = SampleConstants.CP_REF_UNKNOWN

    output_doc[SampleConstants.LAB] = lab
    output_doc[SampleConstants.SAMPLES] = []
    samples_w_data = 0

    for ginkgo_sample in ginkgo_doc:
        sample_doc = {}
        #sample_doc[SampleConstants.SAMPLE_ID] = str(ginkgo_sample["sample_id"])
        sample_doc[SampleConstants.SAMPLE_ID] = namespace_sample_id(str(ginkgo_sample["sample_id"]), lab)

        contents = []
        for reagent in ginkgo_sample["content"]["reagent"]:

            reagent_id = reagent["id"]
            if int(reagent_id) not in SampleContentsFilter.GINKGO_LAB_IDS:
                reagent_name = reagent["name"]
                concentration_prop = "concentration"
                if concentration_prop in reagent:
                    contents.append(create_media_component(reagent_name, reagent_id, lab, sbh_query, reagent[concentration_prop]))
                else:
                    contents.append(create_media_component(reagent_name, reagent_id, lab, sbh_query))

        sample_doc[SampleConstants.CONTENTS] = contents

        for strain in ginkgo_sample["content"]["strain"]:
            sample_doc[SampleConstants.STRAIN] = create_mapped_name(strain["name"], strain["id"], lab, sbh_query)
            # TODO multiple strains?
            continue

        props = ginkgo_sample["properties"]

        control_for_prop = "control_for_samples"
        sbh_uri_prop = "SD2_SBH_URI"
        if control_for_prop in ginkgo_sample:
            control_for_val = ginkgo_sample[control_for_prop]

            #int -> str conversion
            if isinstance(control_for_val, list):
                if type(control_for_val[0]) == int:
                    control_for_val = [str(n) for n in control_for_val]

            if sbh_uri_prop in props:
                sbh_uri_val = props[sbh_uri_prop]
                if "fluorescein_control" in sbh_uri_val:
                    sample_doc[SampleConstants.STANDARD_TYPE] = SampleConstants.STANDARD_FLUORESCEIN
                    sample_doc[SampleConstants.STANDARD_FOR] = control_for_val
                else:
                    print("Unknown control for sample: {}".format(sample_doc[SampleConstants.SAMPLE_ID]))
            else:
                print("Unknown control for sample: {}".format(sample_doc[SampleConstants.SAMPLE_ID]))

        # do some cleaning
        temp_prop = "SD2_incubation_temperature"

        if temp_prop in props:
            temperature = props[temp_prop]
            if "centigrade" in temperature:
                temperature = temperature.replace("centigrade", "celsius")
            sample_doc[SampleConstants.TEMPERATURE] = create_value_unit(temperature)

        replicate_prop = "SD2_replicate"
        if replicate_prop in props:
            replicate_val = props[replicate_prop]
            if isinstance(replicate_val, six.string_types):
                replicate_val = int(replicate_val)
            sample_doc[SampleConstants.REPLICATE] = replicate_val

        for measurement_key in ginkgo_sample["measurements"].keys():
            measurement_doc = {}

            time_prop = "SD2_timepoint"
            if time_prop in props:
                time_val = props[time_prop]
                if time_val == "pre-pre-induction":
                    print("Warning: time val is not discrete, replacing fixed value!".format(time_val))
                    time_val = "-3:hour"
                elif time_val == "pre-induction":
                    print("Warning: time val is not discrete, replacing fixed value!".format(time_val))
                    time_val = "0:hour"

                # more cleanup
                if time_val.endswith("hours"):
                    time_val = time_val.replace("hours", "hour")
                measurement_doc[SampleConstants.TIMEPOINT] = create_value_unit(time_val)

            measurement_doc[SampleConstants.FILES] = []

            measurement_props = ginkgo_sample["measurements"][measurement_key]

            assay_type = measurement_props["assay_type"]
            if assay_type == "NGS (RNA)":
                measurement_type = SampleConstants.MT_RNA_SEQ
            elif assay_type == "FACS":
                measurement_type = SampleConstants.MT_FLOW
            elif assay_type == "Plate Reader Assay":
                measurement_type = SampleConstants.MT_PLATE_READER
            elif assay_type == "Global Proteomics":
                measurement_type = SampleConstants.MT_PROTEOMICS
            else:
                raise ValueError("Could not parse MT: {}".format(assay_type))


            measurement_doc[SampleConstants.MEASUREMENT_TYPE] = measurement_type
            measurement_doc[SampleConstants.MEASUREMENT_NAME] = measurement_props["measurement_name"]

            # use measurement_name to do some inference if we have no challenge problem, yet
            # (could be superceded later)
            if output_doc[SampleConstants.CHALLENGE_PROBLEM] == SampleConstants.CP_UNKNOWN:
                if measurement_doc[SampleConstants.MEASUREMENT_NAME].startswith("NC E. coli NAND") or measurement_doc[SampleConstants.MEASUREMENT_NAME].startswith("NC"):
                    print("Setting Novel Chassis Challenge Problem by Inference")
                    output_doc[SampleConstants.CHALLENGE_PROBLEM] = SampleConstants.CP_NOVEL_CHASSIS

            # use challenge_problem and lab to infer the experiment_reference
            # FIXME update this later
            if output_doc[SampleConstants.CHALLENGE_PROBLEM] == SampleConstants.CP_NOVEL_CHASSIS:
                output_doc[SampleConstants.EXPERIMENT_REFERENCE] = SampleConstants.EXPT_DEFAULT_REFERENCE_GINKGO

            # convey optional measurement id if provided by lab to help with troubleshooting
            measurement_doc[SampleConstants.MEASUREMENT_ID] = namespace_measurement_id(measurement_key, output_doc[SampleConstants.LAB])
            tmt_prop = "TMT_channel"
            if tmt_prop in measurement_props:
                tmt_val = measurement_props[tmt_prop]
                if SampleConstants.SAMPLE_TMT_CHANNEL not in sample_doc:
                    sample_doc[SampleConstants.SAMPLE_TMT_CHANNEL] = tmt_val
                else:
                    if sample_doc[SampleConstants.SAMPLE_TMT_CHANNEL] != tmt_val:
                        raise ValueError("Multiple TMT channels for sample?: {}".format(sample_doc[SampleConstants.SAMPLE_ID]))

            for key in measurement_props["dataset_files"].keys():
                if key == "processed":
                    for processed in measurement_props["dataset_files"]["processed"]:
                        for sub_processed in processed:
                            file_type = SampleConstants.infer_file_type(sub_processed)
                            measurement_doc[SampleConstants.FILES].append(
                                { SampleConstants.M_NAME : sub_processed, \
                                SampleConstants.M_TYPE : file_type, \
                                SampleConstants.M_STATE : SampleConstants.M_STATE_PROCESSED,
                                SampleConstants.FILE_LEVEL: SampleConstants.F_LEVEL_0})
                elif key == "raw":
                    for raw in measurement_props["dataset_files"]["raw"]:
                        for sub_raw in raw:
                            file_type = SampleConstants.infer_file_type(sub_raw)
                            measurement_doc[SampleConstants.FILES].append(
                                { SampleConstants.M_NAME : sub_raw, \
                                SampleConstants.M_TYPE : file_type,
                                SampleConstants.M_STATE : SampleConstants.M_STATE_RAW,
                                SampleConstants.FILE_LEVEL: SampleConstants.F_LEVEL_0})
                else:
                    raise ValueError("Unknown measurement type: {}".format(key))

            if len(measurement_doc[SampleConstants.FILES]) == 0:
                print("Warning, measurement contains no files, skipping {}".format(measurement_key))
            else:
                if SampleConstants.MEASUREMENTS not in sample_doc:
                    sample_doc[SampleConstants.MEASUREMENTS] = []
                sample_doc[SampleConstants.MEASUREMENTS].append(measurement_doc)
                samples_w_data = samples_w_data + 1
                print('sample {} / measurement {} contains {} files'.format(sample_doc[SampleConstants.SAMPLE_ID], measurement_key, len(measurement_doc[SampleConstants.FILES])))

        output_doc[SampleConstants.SAMPLES].append(sample_doc)

    print('Samples in file: {}'.format(len(ginkgo_doc)))
    print('Samples with data: {}'.format(samples_w_data))

    try:
        validate(output_doc, schema)
        #if verbose:
        #print(json.dumps(output_doc, indent=4))
        if output is True or output_file is not None:
            if output_file is None:
                path = os.path.join(
                    "output/ginkgo", os.path.basename(input_file))
            else:
                path = output_file
            with open(path, 'w') as outfile:
                json.dump(output_doc, outfile, indent=4)
        return True
    except ValidationError as err:
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
                convert_ginkgo(sys.argv[1], file_path)
            else:
                print("Skipping {}".format(file_path))
    else:
        convert_ginkgo(sys.argv[1], sys.argv[2])
