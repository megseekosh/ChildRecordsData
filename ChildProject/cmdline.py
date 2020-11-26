#!/usr/bin/env python3
from ChildProject.projects import ChildProject, RecordingProfile    
from ChildProject.annotations import AnnotationManager

import argparse
import os
import pandas as pd
import sys

def validate(args):
    project = ChildProject(args.source)
    errors, warnings = project.validate_input_data(args.ignore_files)

    for error in errors:
        print("error: {}".format(error), file = sys.stderr)

    for warning in warnings:
        print("warning: {}".format(warning))

    if len(errors) > 0:
        print("validation failed, {} error(s) occured".format(len(errors)), file = sys.stderr)
        sys.exit(1)


def import_annotations(args):
    project = ChildProject(args.source)
    errors, warnings = project.validate_input_data()

    if len(errors) > 0:
        print("validation failed, {} error(s) occured".format(len(errors)), file = sys.stderr)
        sys.exit(1)

    if args.annotations:
        annotations = pd.read_csv(args.annotations)
    else:
        annotations = pd.DataFrame([{col.name: getattr(args, col.name) for col in AnnotationManager.INDEX_COLUMNS if not col.generated}])

    am = AnnotationManager(project)
    am.import_annotations(annotations)

    errors, warnings = am.validate()

    if len(am.errors) > 0:
        print("importation completed with {} errors and {} warnings".format(len(am.errors)+len(errors), len(warnings)), file = sys.stderr)
        print("\n".join(am.errors), file = sys.stderr)
        print("\n".join(errors), file = sys.stderr)
        print("\n".join(warnings))

def import_data(args):
    import datalad.api
    import datalad.distribution.dataset

    if args.destination:
        destination = args.destination
    else:
        destination = os.path.splitext(os.path.basename(args.dataset))[0]

    datalad.api.install(source = args.dataset, path = destination)

    ds = datalad.distribution.dataset.require_dataset(
        destination,
        check_installed = True,
        purpose = 'configuration'
    )

    cmd = 'setup'
    if args.storage_hostname:
        cmd += ' "{}"'.format(args.storage_hostname)

    datalad.api.run_procedure(spec = cmd, dataset = ds)

def convert(args):
    profile = RecordingProfile(
        name = args.name,
        format = args.format,
        codec = args.codec,
        sampling = args.sampling,
        split = args.split
    )

    project = ChildProject(args.source)
    results = project.convert_recordings(profile, skip_existing = args.skip_existing, threads = args.threads)

    for error in project.errors:
        print("error: {}".format(error), file = sys.stderr)

    for warning in project.warnings:
        print("warning: {}".format(warning))

    if len(project.errors) > 0:
        print("conversion failed, {} error(s) occured".format(len(project.errors)), file = sys.stderr)
        print("cannot convert recordings", file = sys.stderr)
        sys.exit(1)

    print("recordings successfully converted to '{}'".format(os.path.join(project.path, 'converted_recordings', profile.name)))

def stats(args):
    project = ChildProject(args.source)

    errors, warnings = project.validate_input_data()

    if len(errors) > 0:
        print("validation failed, {} error(s) occured".format(len(errors)), file = sys.stderr)
        sys.exit(1)

    stats = project.get_stats()
    args.stats = args.stats.split(',') if args.stats else []

    for stat in stats:
        if not args.stats or stat in args.stats:
            print("{}: {}".format(stat, stats[stat]))

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    parser_v = subparsers.add_parser('validate', description = "validate the consistency of the dataset returning detailed errors and warnings")
    parser_v.add_argument("source", help = "project path")
    parser_v.add_argument('--ignore-files', dest='ignore_files', required = False, default = False, action='store_true')
    parser_v.set_defaults(func = validate)

    parser_ia = subparsers.add_parser('import-annotations', description = "convert and import a set of annotations")
    parser_ia.add_argument("source", help = "project path")
    parser_ia.add_argument("--annotations", help = "path to input annotations index (csv)", default = "")

    for col in AnnotationManager.INDEX_COLUMNS:
        if col.generated:
            continue

        parser_ia.add_argument("--{}".format(col.name), help = col.description, type = str, default = None)
    parser_ia.set_defaults(func = import_annotations)

    parser_c = subparsers.add_parser('convert', description = "convert recordings to a given format")
    default_profile = RecordingProfile("default")
    parser_c.add_argument("source", help = "project path")
    parser_c.add_argument("--name", help = "profile name", required = True)
    parser_c.add_argument("--format", help = "audio format (e.g. {})".format(default_profile.format), required = True)
    parser_c.add_argument("--codec", help = "audio codec (e.g. {})".format(default_profile.codec), required = True)
    parser_c.add_argument("--sampling", help = "sampling frequency (e.g. {})".format(default_profile.sampling), required = True)
    parser_c.add_argument("--split", help = "split duration (e.g. 15:00:00)", required = False, default = None)
    parser_c.add_argument('--skip-existing', dest='skip_existing', required = False, default = False, action='store_true')
    parser_c.add_argument('--threads', help = "amount of threads running conversions in parallel (0 = uses all available cores)", required = False, default = 0, type = int)
    parser_c.set_defaults(func = convert)

    parser_id = subparsers.add_parser('import-data')
    parser_id.add_argument("dataset", help = "dataset to install. Should be a valid repository name at https://github.com/LAAC-LSCP. (e.g.: solomon-data)")
    parser_id.add_argument("--destination", help = "destination path", required = False, default = "")
    parser_id.add_argument("--storage-hostname", dest = "storage_hostname", help = "ssh storage hostname (e.g. 'foberon')", required = False, default = "")
    parser_id.set_defaults(func = import_data)

    parser_s = subparsers.add_parser('stats')
    parser_s.add_argument("source", help = "source data path")
    parser_s.add_argument("--stats", help = "stats to retrieve (comma-separated)", required = False, default = "")
    parser_s.set_defaults(func = stats)

    args = parser.parse_args()
    args.func(args)