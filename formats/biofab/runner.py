#!/usr/bin/python
import json
import sys
import os
from jsonschema import validate
from jsonschema import ValidationError
import six
from jq import jq
# Hack hack
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from common import SampleConstants
from common import namespace_sample_id, namespace_file_id, namespace_measurement_id, namespace_experiment_id, create_media_component, create_value_unit, create_mapped_name, map_experiment_reference
from synbiohub_adapter.query_synbiohub import *
from synbiohub_adapter.SynBioHubUtil import *
from sbol import *
from datacatalog.agavehelpers import AgaveHelper

# common across methods
attributes_attr = "attributes"
replicate_attr = "replicate"
sample_attr = "sample"
sample_id_attr = "sample_id"
sample_name_attr = "sample_name"
op_id = "operation_id"
job_id = "job_id"
type_attr = "type"
type_of_media_attr = "type_of_media"
part_of_attr = "part_of"
source_attr = "sources"
item_id_attr = "item_id"
media_attr = "media"
inducer_attr = "inducer"
experimental_antibiotic_attr = "experimental_antibiotic"
concentration_attr = "concentration"
volume_attr = "volume"
od600_attr = "od600"
control_attr = "control"
negative_control = False

def add_timepoint(measurement_doc, input_item_id, biofab_doc):
    try:
        time_val = jq(".operations[] | select(.inputs[].item_id ==\"" + input_item_id + "\").inputs[] | select (.name == \"Timepoint (hr)\").value").transform(biofab_doc)
        measurement_doc[SampleConstants.TIMEPOINT] = create_value_unit(time_val + ":hour")
    except StopIteration:
        print("Warning: could not find matching time value for {}".format(input_item_id))

def add_od(item, sample_doc):
    if item is not None and attributes_attr in item and od600_attr in item[attributes_attr]:
        od = item[attributes_attr][od600_attr]
        sample_doc[SampleConstants.INOCULATION_DENSITY] = create_value_unit(od + ":" + od600_attr)

def add_control(item, sample_doc):
    global negative_control
    if item is not None and attributes_attr in item and control_attr in item[attributes_attr]:
        control_val = item[attributes_attr][control_attr]
        if control_val == "negative_sytox":
            # have we marked a negative control yet? we can re-use the negative_sytox, which is an unadulterated WT
            if not negative_control:
                sample_doc[SampleConstants.CONTROL_TYPE] = SampleConstants.CONTROL_EMPTY_VECTOR
                negative_control = True
            else:
                sample_doc[SampleConstants.CONTROL_TYPE] = SampleConstants.CONTROL_CELL_DEATH_NEG_CONTROL
        elif control_val == "positive_sytox":
            sample_doc[SampleConstants.CONTROL_TYPE] = SampleConstants.CONTROL_CELL_DEATH_POS_CONTROL
        elif control_val == "positive_gfp":
            sample_doc[SampleConstants.CONTROL_TYPE] = SampleConstants.CONTROL_HIGH_FITC

def add_replicate(item, sample_doc):
    if attributes_attr in item and replicate_attr in item[attributes_attr]:
        replicate_val = item[attributes_attr][replicate_attr]
        if isinstance(replicate_val, six.string_types):
            replicate_val = int(replicate_val)
        sample_doc[SampleConstants.REPLICATE] = replicate_val

def add_strain(item, sample_doc, lab, sbh_query):
    if sample_attr in item:
        if sample_id_attr not in item[sample_attr]:
            print("Warning, sample is missing a strain entry: {}".format(item))
        else:
            sample_id = item[sample_attr][sample_id_attr]
            strain = item[sample_attr][sample_name_attr]
            sample_doc[SampleConstants.STRAIN] = create_mapped_name(strain, sample_id, lab, sbh_query, strain=True)

# operation id aggregates across files for a single measurement, e.g.
"""
"operation_id": "92240",
"operation_type": {
"operation_type_id": "415",
"category": "Flow Cytometry",
"name": "Flow Cytometry 96 well"
},
"""
# generate a measurement id unique to this sample
# Biofab does not have additional measurements per file, can fix to 1
def add_measurement_id(measurement_doc, sample_doc, output_doc):
    measurement_doc[SampleConstants.MEASUREMENT_ID] = namespace_measurement_id(
            ".".join([sample_doc[SampleConstants.SAMPLE_ID], "1"]), output_doc[SampleConstants.LAB])

def add_measurement_group_id(measurement_doc, file, output_doc):
    # record a measurement grouping id to find other linked samples and files
    file_gen = file["generated_by"]
    mg_val = None
    if op_id in file_gen:
        mg_val = file_gen[op_id]
    elif job_id in file_gen:
        mg_val = file_gen[job_id]
    else:
        raise ValueError("Cannot find measurement group id: {}".format(file))

    measurement_doc[SampleConstants.MEASUREMENT_GROUP_ID] = namespace_measurement_id(mg_val, output_doc[SampleConstants.LAB])


def add_measurement_type(file, measurement_doc):
    if type_attr in file:
        assay_type = file[type_attr]
        if assay_type == "FCS":
            measurement_type = SampleConstants.MT_FLOW
        elif assay_type == "CSV":
            measurement_type = SampleConstants.MT_PLATE_READER
        else:
            raise ValueError("Could not parse MT: {}".format(assay_type))
    else:
        # Workaround for biofab; uploaded txts are PR
        # Otherwise the abve version of this fails
        # Files that did not have a type
        fn = file['filename']
        if fn.endswith(".txt"):
            measurement_type = SampleConstants.MT_PLATE_READER
        else:
            raise ValueError("Could not parse MT: {}".format(file['filename']))

    measurement_doc[SampleConstants.MEASUREMENT_TYPE] = measurement_type

def add_measurement_doc(measurement_doc, sample_doc, output_doc):
    if len(measurement_doc[SampleConstants.FILES]) == 0:
        print("Warning, measurement contains no files, skipping {}".format(measurement_key))
    else:
        if SampleConstants.MEASUREMENTS not in sample_doc:
            sample_doc[SampleConstants.MEASUREMENTS] = []
        sample_doc[SampleConstants.MEASUREMENTS].append(measurement_doc)

        output_doc[SampleConstants.SAMPLES].append(sample_doc)

def add_file_name(config, file, measurement_doc, original_experiment_id, lab):
    if config.get('extend', False):
        file_name = extend_biofab_filename(
            file['filename'], original_experiment_id, file['generated_by'])
    else:
        file_name = file["filename"]

    file_id = file.get('file_id', None)
    if file_id is not None:
        file_id = namespace_file_id(file_id, lab)
    file_type = SampleConstants.infer_file_type(file_name)
    measurement_doc[SampleConstants.FILES].append(
                        { SampleConstants.M_NAME : file_name, \
                        SampleConstants.M_TYPE : file_type, \
                        SampleConstants.M_STATE : SampleConstants.M_STATE_RAW,
                        SampleConstants.FILE_LEVEL: SampleConstants.F_LEVEL_0,
                        SampleConstants.FILE_ID: file_id})

def extend_biofab_filename(file_name, plan_id, generated_by):
    # Add context to the filename while we have enough information to
    # generate it
    gen_id = None
    if 'operation_id' in generated_by:
        gen_id = 'op_' + generated_by['operation_id']
    elif 'job_id' in generated_by:
        gen_id = 'job_' + generated_by['job_id']
    else:
        gen_id = 'unknown'
    return '/'.join([str(plan_id), gen_id, file_name])


def convert_biofab(schema_file, input_file, verbose=True, output=True, output_file=None, config={}, enforce_validation=True, reactor=None):

    if reactor is not None:
        helper = AgaveHelper(reactor.client)
        print("Helper loaded")
    else:
        print("Helper not loaded")

    print(input_file)
    # for SBH Librarian Mapping
    sbh_query = SynBioHubQuery(SD2Constants.SD2_SERVER)

    schema = json.load(open(schema_file))
    biofab_doc = json.load(open(input_file))

    output_doc = {}

    lab = SampleConstants.LAB_UWBF

    original_experiment_id = biofab_doc["plan_id"]
    output_doc[SampleConstants.EXPERIMENT_ID] = namespace_experiment_id(biofab_doc["plan_id"], lab)
    output_doc[SampleConstants.CHALLENGE_PROBLEM] = biofab_doc.get("attributes", {}).get("challenge_problem", "UNKNOWN")
    output_doc[SampleConstants.EXPERIMENT_REFERENCE] = biofab_doc.get(
        "attributes", {}).get("experiment_reference", "Unknown")

    map_experiment_reference(config, output_doc)

    output_doc[SampleConstants.LAB] = biofab_doc.get("attributes", {}).get("lab", lab)
    output_doc[SampleConstants.SAMPLES] = []

    missing_part_of_items = set()

    # process bottom up from file -> sample
    for biofab_sample in biofab_doc["files"]:
        sample_doc = {}
        if source_attr not in biofab_sample:
            print("Warning, file is missing a source, skipping {}".format(biofab_sample))
            continue
        file_source = biofab_sample[source_attr][0]
        # sample_doc[SampleConstants.SAMPLE_ID] = file_source
        sample_doc[SampleConstants.SAMPLE_ID] = namespace_sample_id(file_source, lab)

        item = jq(".items[] | select(.item_id==\"" + file_source + "\")").transform(biofab_doc)

        # plate this source is a part of?
        plate = None
        found_plate = False
        part_of = None
        if part_of_attr not in item:

            if attributes_attr in item and type_of_media_attr in item[attributes_attr]:
                # use ourself instead of doing part_of
                plate = item
                found_plate = True
                part_of = file_source
            else:
                # lookup provenance not resolving, handle this top down, below
                # (PlateReader in particular does this)
                missing_part_of_items.add(file_source)
                continue
        else:
            part_of = item[part_of_attr]
            plate = jq(".items[] | select(.item_id==\"" + part_of + "\")").transform(biofab_doc)

        reagents = []

        plate_source_lookup = None
        plate_source = None
        # one additional lookup
        if found_plate:
            plate_source = plate[source_attr][0]
            plate_source_lookup = plate
        else:
            plate_source = plate[source_attr][0]
            plate_source_lookup = jq(".items[] | select(.item_id==\"" + plate_source + "\")").transform(biofab_doc)

        if type_of_media_attr in plate_source_lookup[attributes_attr] and source_attr not in item:
            media_name = plate_source_lookup[attributes_attr][type_of_media_attr]
            # case for old files that do not have this.
            reagents.append(create_media_component(media_name, media_name, lab, sbh_query))
        else:
            if source_attr not in item:
                print("Warning, item is missing a source {}".format(item))
            else:
                # need to follow *another* source chain to find the media_id
                media_source_lookup = None
                media_source_ = item[source_attr][0]
                media_source_lookup = jq(".items[] | select(.item_id==\"" + media_source_ + "\")").transform(biofab_doc)

                if attributes_attr in media_source_lookup and media_attr in media_source_lookup[attributes_attr]:
                    if sample_id_attr in media_source_lookup[attributes_attr][media_attr]:
                        media_id = media_source_lookup[attributes_attr][media_attr][sample_id_attr]
                        reagents.append(create_media_component(media_id, media_id, lab, sbh_query))
                    else:
                        raise ValueError("No media id? {}".format(media_source_lookup))
                else:
                    # no media attribute, try to look up through the last source 
                    if source_attr in media_source_lookup:
                        last_source_ = media_source_lookup[source_attr][0]
                        last_source_lookup = jq(".items[] | select(.item_id==\"" + last_source_ + "\")").transform(biofab_doc)
                        if attributes_attr in last_source_lookup:
                            if inducer_attr in last_source_lookup[attributes_attr]:
                                combined_inducer = last_source_lookup[attributes_attr][inducer_attr]
                                if combined_inducer != "None":
                                    #"IPTG_0.25|arab_25.0"
                                    combined_inducer_split = combined_inducer.split("|")
                                    for inducer in combined_inducer_split:
                                        inducer_split = inducer.split("_")
                                        reagents.append(create_media_component(inducer_split[0], inducer_split[0], lab, sbh_query, inducer_split[1]))
                            if experimental_antibiotic_attr in last_source_lookup[attributes_attr]:
                                experimental_antibiotic = last_source_lookup[attributes_attr][experimental_antibiotic_attr]
                                reagents.append(create_media_component(experimental_antibiotic, experimental_antibiotic, lab, sbh_query))

                add_od(media_source_lookup, sample_doc)

                add_control(media_source_lookup, sample_doc)

        if "growth_temperature" in plate_source_lookup:
            temperature = plate_source_lookup["attributes"]["growth_temperature"]
            sample_doc[SampleConstants.TEMPERATURE] = create_value_unit(str(temperature) + ":celsius")
        else:
            try:
                temp_value = jq(".operations[].inputs[] | select (.name | contains (\"Growth Temperature\")).value").transform(biofab_doc)
            except StopIteration:
                print("Warning, could not find temperature for {}".format(original_experiment_id))
                temp_value = None
            if temp_value is not None:
                sample_doc[SampleConstants.TEMPERATURE] = create_value_unit(str(temp_value) + ":celsius")

        if len(reagents) > 0:
            sample_doc[SampleConstants.CONTENTS] = reagents

        # could use ID
        add_strain(item, sample_doc, lab, sbh_query)

        add_od(item, sample_doc)

        add_control(item, sample_doc)

        add_replicate(item, sample_doc)

        # skip controls for now
        # code from Ginkgo doc...
        """
        control_for_prop = "control_for_samples"
        sbh_uri_prop = "SD2_SBH_URI"
        if control_for_prop in biofab_sample:
            control_for_val = biofab_sample[control_for_prop]

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
        """
        measurement_doc = {}

        add_timepoint(measurement_doc, plate_source, biofab_doc)

        measurement_doc[SampleConstants.FILES] = []

        add_measurement_type(biofab_sample, measurement_doc)

        add_measurement_id(measurement_doc, sample_doc, output_doc)

        add_measurement_group_id(measurement_doc, biofab_sample, output_doc)

        # TODO
        #measurement_doc[SampleConstants.MEASUREMENT_NAME] = measurement_props["measurement_name"]

        add_file_name(config, biofab_sample, measurement_doc, original_experiment_id, lab)

        add_measurement_doc(measurement_doc, sample_doc, output_doc)

    # alternate temperate when we lack provenance
    temp_value = None
    if len(missing_part_of_items) > 0:
        try:
            temp_value = jq(".operations[].inputs[] | select (.name | contains (\"Growth Temperature\")).value").transform(biofab_doc)
        except StopIteration:
            print("Warning, could not find temperature for {}".format(original_experiment_id))
            temp_value = None

    # Instead of bottom up from files, process top down from items
    for missing_part_of in missing_part_of_items:

        items = jq(".items[] | select(.part_of==\"" + missing_part_of + "\")").transform(biofab_doc, multiple_output=True)

        if len(items) == 0:
            item = jq(".items[] | select(.item_id==\"" + missing_part_of + "\")").transform(biofab_doc)
            if item is not None:
                items.append(item)

        for item in items:

            sample_doc = {}
            item_id = item[item_id_attr]
            try:
                item_source = jq(".items[] | select(.sources[]? | contains (\"" + item_id + "\"))").transform(biofab_doc)
            except StopIteration:
                # no source, use the original item
                item_source = item

            if item_source is not None:

                reagents = []

                sample_doc[SampleConstants.SAMPLE_ID] = namespace_sample_id(item_source[item_id_attr], lab)

                if attributes_attr in item_source and (concentration_attr in item_source[attributes_attr] or volume_attr in item_source[attributes_attr]):
                    # reagent
                    media_id = item_source[sample_attr][sample_id_attr]
                    media_name = item_source[sample_attr][sample_name_attr]
                    reagent_obj = None
                    if concentration_attr in item_source[attributes_attr]:
                        reagent_obj = create_media_component(media_name, media_id, lab, sbh_query, item_source[attributes_attr][concentration_attr])
                    else:
                        reagent_obj = create_media_component(media_name, media_id, lab, sbh_query)

                    if volume_attr in item_source[attributes_attr]:
                        volume_value_unit = create_value_unit(item_source[attributes_attr][volume_attr])
                        reagent_obj["volume"] = volume_value_unit

                    reagents.append(reagent_obj)

                else:
                    # strain
                    add_strain(item_source, sample_doc, lab, sbh_query)

                add_od(item_source, sample_doc)

                add_control(item_source, sample_doc)

                add_replicate(item_source, sample_doc)

                if attributes_attr in item_source and media_attr in item_source[attributes_attr]:
                    if sample_id_attr in item_source[attributes_attr][media_attr]:
                        media_id = item_source[attributes_attr][media_attr][sample_id_attr]
                        reagents.append(create_media_component(media_id, media_id, lab, sbh_query))
                    else:
                        raise ValueError("No media id? {}".format(item_source))
                else:
                    print("Warning, could not find media for {}".format(item_source[item_id_attr]))

                if len(reagents) > 0:
                    sample_doc[SampleConstants.CONTENTS] = reagents

            if temp_value is not None:
                sample_doc[SampleConstants.TEMPERATURE] = create_value_unit(str(temp_value) + ":celsius")

            measurement_doc = {}

            if part_of_attr in item_source:
                add_timepoint(measurement_doc, item_source[part_of_attr], biofab_doc)

            measurement_doc[SampleConstants.FILES] = []

            files = jq(".files[] | select(.sources[]? | contains (\"" + missing_part_of + "\"))").transform(biofab_doc, multiple_output=True)

            for file in files:
                add_measurement_type(file, measurement_doc)

                add_measurement_id(measurement_doc, sample_doc, output_doc)

                add_measurement_group_id(measurement_doc, file, output_doc)

                add_file_name(config, file, measurement_doc, original_experiment_id, lab)

            add_measurement_doc(measurement_doc, sample_doc, output_doc)
    try:
        validate(output_doc, schema)
        #if verbose:
            #print(json.dumps(output_doc, indent=4))
        if output is True or output_file is not None:
            if output_file is None:
                path = os.path.join("output/biofab", os.path.basename(input_file))
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
        return False

if __name__ == "__main__":
    path = sys.argv[2]
    if os.path.isdir(path):
        for f in os.listdir(path):
            file_path = os.path.join(path, f)
            print(file_path)
            if file_path.endswith(".js") or file_path.endswith(".json"):
                convert_biofab(sys.argv[1], file_path)
            else:
                print("Skipping {}".format(file_path))
    else:
        convert_biofab(sys.argv[1], sys.argv[2])
