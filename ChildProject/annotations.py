import datetime
import os
import pandas as pd
import pympi
import shutil

from .projects import ChildProject
from .tables import IndexTable, IndexColumn

class AnnotationManager:
    INDEX_COLUMNS = [
        IndexColumn(name = 'set', description = 'annotation set (e.g. VTC, annotator1, etc.)', required = True),
        IndexColumn(name = 'recording_filename', description = 'recording filename as in the recordings index', required = True),
        IndexColumn(name = 'time_seek', description = 'reference time in seconds, e.g: 3600, or 3600.500.', regex = r"[0-9]{1,}(\.[0-9]{3})?", required = True),
        IndexColumn(name = 'range_onset', description = 'covered range start time in seconds, measured since time_seek', regex = r"[0-9]{1,}(\.[0-9]{3})?", required = True),
        IndexColumn(name = 'range_offset', description = 'covered range end time in seconds, measured since time_seek', regex = r"[0-9]{1,}(\.[0-9]{3})?", required = True),
        IndexColumn(name = 'raw_filename', description = 'input filename location', filename = True, required = True),
        IndexColumn(name = 'annotation_filename', description = 'output formatted annotation location', filename = True, required = False),
        IndexColumn(name = 'imported_at', description = 'importationd date', datetime = "%Y-%m-%d %H:%M:%S", required = False),
        IndexColumn(name = 'format', description = 'input annotation format', regex = r"(TextGrid|eaf|rttm)", required = True)
    ]

    SEGMENTS_COLUMNS = [
        IndexColumn(name = 'annotation_file', description = 'raw annotation path relative to /raw_annotations/', required = True),
        IndexColumn(name = 'segment_onset', description = 'segment start time in seconds', regex = r"[0-9]{1,}(\.[0-9]{3})?", required = True),
        IndexColumn(name = 'segment_offset', description = 'segment end time in seconds', regex = r"[0-9]{1,}(\.[0-9]{3})?", required = True),
        IndexColumn(name = 'speaker_id', description = '', required = True),
        IndexColumn(name = 'speaker_type', description = '', required = True),
        IndexColumn(name = 'ling_type', description = '1 if the vocalization contains at least a vowel (ie canonical or non-canonical)', required = True),
        IndexColumn(name = 'vcm_type', description = '', required = True),
        IndexColumn(name = 'lex_type', description = '', required = True),
        IndexColumn(name = 'mwu_type', description = '', required = True),
        IndexColumn(name = 'addresseee', description = '', required = True),
        IndexColumn(name = 'transcription', description = '', required = True)
    ]

    SPEAKER_ID_TO_TYPE = {
        'C1': 'OCH',
        'C2': 'OCH',
        'CHI': 'CHI',
        'CHI*': 'CHI',
        'EE1': 'ELE',
        'FA0': 'FEM',
        'FA1': 'FEM',
        'FA2': 'FEM',
        'FA3': 'FEM',
        'FA4': 'FEM',
        'FA5': 'FEM',
        'FA6': 'FEM',
        'FA7': 'FEM',
        'FA8': 'FEM',
        'FAE': 'ELE',
        'FC1': 'OCH',
        'FC2': 'OCH',
        'FC3': 'OCH',
        'MA0': 'MAL',
        'MA1': 'MAL',
        'MA2': 'MAL',
        'MA3': 'MAL',
        'MA4': 'MAL',
        'MA5': 'MAL',
        'MAE': 'ELE',
        'MC1': 'OCH',
        'MC2': 'OCH',
        'MC3': 'OCH',
        'MC4': 'OCH',
        'MC5': 'OCH',
        'MI1': 'OCH',
        'MOT*': 'FEM',
        'OC0': 'OCH',
        'UC1': 'OCH',
        'UC2': 'OCH',
        'UC3': 'OCH',
        'UC4': 'OCH',
        'UC5': 'OCH',
        'UC6': 'OCH'
    }


    def __init__(self, project):
        self.project = project
        self.annotations = None
        self.errors = []

        if not isinstance(project, ChildProject):
            raise ValueError('project should derive from ChildProject')

        project.read()

        index_path = os.path.join(self.project.path, 'annotations/annotations.csv')
        if not os.path.exists(index_path):
            open(index_path, 'w+').write(','.join([c.name for c in self.INDEX_COLUMNS]))

        errors, warnings = self.read()

    def read(self):
        table = IndexTable('input', path = os.path.join(self.project.path, 'annotations/annotations.csv'), columns = self.INDEX_COLUMNS)
        self.annotations = table.read()
        errors, warnings = table.validate()
        return errors, warnings

    def validate(self):
        errors, warnings = [], []

        for annotation in self.annotations.to_dict(orient = 'records'):
            segments = IndexTable(
                'segments',
                path = os.path.join(self.project.path, 'annotations', annotation['annotation_filename']),
                columns = AnnotationManager.SEGMENTS_COLUMNS
            )

            segments.read()
            res = segments.validate()
            errors += res[0]
            warnings += res[1]

        return errors, warnings
        

    def load_textgrid(self, filename):
        path = os.path.join(self.project.path, 'raw_annotations', filename)
        textgrid = pympi.Praat.TextGrid(path)

        segments = []
        for tier in textgrid.tiers:
            for interval in tier.intervals:
                tier_name = tier.name.strip()

                if tier_name == 'Autre':
                    continue

                if interval[2] == "":
                    continue

                segment = {
                    'annotation_file': filename,
                    'segment_onset': "{:.3f}".format(interval[0]),
                    'segment_offset': "{:.3f}".format(interval[1]),
                    'speaker_id': tier_name,
                    'ling_type': interval[2] if interval[2] else "",
                    'speaker_type': self.SPEAKER_ID_TO_TYPE[tier_name] if tier_name in self.SPEAKER_ID_TO_TYPE else 'NA',
                    'vcm_type': 'NA',
                    'lex_type': 'NA',
                    'mwu_type': 'NA',
                    'addresseee': 'NA',
                    'transcription': 'NA'
                }

                segments.append(segment)

        return pd.DataFrame(segments)

    def load_eaf(self, filename):
        path = os.path.join(self.project.path, 'raw_annotations', filename)
        eaf = pympi.Elan.Eaf(path)


        return None

    def load_vtc_rttm(self, filename):
        path = os.path.join(self.project.path, 'raw_annotations', filename)
        rttm = pd.read_csv(
            path,
            sep = " ",
            names = ['type', 'file', 'chnl', 'tbeg', 'tdur', 'ortho', 'stype', 'name', 'conf', 'unk']
        )

        df = rttm
        df['annotation_file'] = filename
        df['segment_onset'] = df['tbeg'].map(lambda f: "{:.3f}".format(f))
        df['segment_offset'] = (df['tbeg']+df['tdur']).map(lambda f: "{:.3f}".format(f))
        df['speaker_id'] = 'NA'
        df['ling_type'] = 'NA'
        df['speaker_type'] = df['name']
        df['vcm_type'] = 'NA'
        df['lex_type'] = 'NA'
        df['mwu_type'] = 'NA'
        df['addresseee'] = 'NA'
        df['transcription'] = 'NA'  

        df.drop(['type', 'file', 'chnl', 'tbeg', 'tdur', 'ortho', 'stype', 'name', 'conf', 'unk'], axis = 1, inplace = True)

        return df

    def import_annotation(self, raw_filename, output_filename, annotation_format):
        if annotation_format == 'TextGrid':
            df = self.load_textgrid(raw_filename)
        elif annotation_format == 'eaf':
            df = self.load_eaf(raw_filename)
        elif annotation_format == 'vtc_rttm':
            df = self.load_vtc_rttm(raw_filename)
        else:
            df = None
            self.errors.append("file format '{}' unknown for '{}'".format(annotation_format, raw_filename))

        if df is not None:
            os.makedirs(os.path.dirname(os.path.join(self.project.path, 'annotations', output_filename)), exist_ok = True)
            df.to_csv(os.path.join(self.project.path, 'annotations', output_filename))

    def import_annotations(self, input):
        imported = []
        for row in input.to_dict(orient = 'records'):
            source_recording = os.path.splitext(row['recording_filename'])[0]
            annotation_filename = "{}/{}_{}.csv".format(row['set'], source_recording, row['time_seek'])

            self.import_annotation(row['raw_filename'], annotation_filename, row['format'])

            row.update({
                'annotation_filename': annotation_filename,
                'imported_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

            imported.append(row)

        self.read()
        self.annotations = pd.concat([self.annotations, pd.DataFrame(imported)])
        self.annotations.to_csv(os.path.join(self.project.path, 'annotations/annotations.csv'), index = False)
