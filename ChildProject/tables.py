import pandas as pd
import os
import re
import datetime
import numpy as np

def read_dataframe(filename):
    extension = os.path.splitext(filename)[1]

    pd_flags = {
        'keep_default_na': False,
        'na_values': ['-1.#IND', '1.#QNAN', '1.#IND', '-1.#QNAN',
                    '#N/A N/A', '#N/A', 'N/A', 'n/a', '', '#NA',
                    'NULL', 'null', 'NaN', '-NaN', 'nan',
                    '-nan', ''],
        'parse_dates': False,
        'index_col': False
    }

    if extension == '.csv':
        df = pd.read_csv(filename, **pd_flags)
    elif extension == '.xls' or extension == '.xlsx':
        df = pd.read_excel(filename, **pd_flags)
    else:
        raise Exception('table format not supported ({})'.format(extension))

    df.index = df.index+2
    return df

def is_boolean(x):
    return x == 'NA' or int(x) in [0,1]

class IndexColumn:
    def __init__(self, name = "", description = "", required = False,
                 regex = None, filename = False, datetime = None, function = None, choices = None,
                 unique = False, generated = False):
        self.name = name
        self.description = description
        self.required = required
        self.filename = filename
        self.regex = regex
        self.datetime = datetime
        self.function = function
        self.choices = choices
        self.unique = unique
        self.generated = generated

class IndexTable:
    def __init__(self, name, path = None, columns = []):
        self.name = name
        self.path = path
        self.columns = columns
        self.df = None
    
    def read(self, lookup_extensions = None):
        if lookup_extensions is None:
            self.df = read_dataframe(self.path)
            return self.df
        else:
            for extension in lookup_extensions:
                if os.path.exists(self.path + extension):
                    self.df = read_dataframe(self.path + extension)
                    return self.df

        raise Exception("could not find table '{}'".format(self.path))

    def validate(self):
        errors, warnings = [], []

        for rc in self.columns:
            if not rc.required:
                continue

            if rc.name not in self.df.columns:
                errors.append("{} table is missing column '{}'".format(self.name, rc.name))

            null = self.df[self.df[rc.name].isnull()].index.values.tolist()
            if len(null) > 0:
                errors.append(
                    """{} table has undefined values
                    for column '{}' in lines: {}""".format(self.name, rc.name, ','.join([str(n) for n in null])))

        unknown_columns = [
            c for c in self.df.columns
            if c not in [c.name for c in self.columns]
        ]

        if len(unknown_columns) > 0:
            warnings.append("unknown column{} '{}' in {}, exepected columns are: {}".format(
                's' if len(unknown_columns) > 1 else '',
                ','.join(unknown_columns),
                self.name,
                ','.join([c.name for c in self.columns])
            ))

        for line_number, row in self.df.iterrows():
            for column_name in self.df.columns:
                column_attr = next((c for c in self.columns if c.name == column_name), None)

                if column_attr is None:
                    continue

                if callable(column_attr.function):
                    try:
                        ok = column_attr.function(str(row[column_name])) == True
                    except:
                        ok = False

                    if not ok:
                        message = "'{}' does not pass callable test for column '{}' on line {}".format(row[column_name], column_name, line_number)
                        if column_attr.required and str(row[column_name]) != 'NA':
                                errors.append(message)
                        elif column_attr.required or str(row[column_name]) != 'NA':
                                warnings.append(message)

                if column_attr.choices and str(row[column_name]) not in column_attr.choices:
                    message = "'{}' is not a permitted value for column '{}' on line {}, should be any of [{}]".format(row[column_name], column_name, line_number, ",".join(column_attr.choices))
                    if column_attr.required and str(row[column_name]) != 'NA':
                            errors.append(message)
                    elif column_attr.required or str(row[column_name]) != 'NA':
                            warnings.append(message)


                if column_attr.datetime:
                    try:
                        dt = datetime.datetime.strptime(row[column_name], column_attr.datetime)
                    except:
                        message = "'{}' is not a proper date/time for column '{}' (expected {}) on line {}".format(row[column_name], column_name, column_attr.datetime, line_number)
                        if column_attr.required and str(row[column_name]) != 'NA':
                            errors.append(message)
                        elif column_attr.required or str(row[column_name]) != 'NA':
                            warnings.append(message)
                elif column_attr.regex:
                    if not re.fullmatch(column_attr.regex, str(row[column_name])):
                        message = "'{}' does not match the format required for '{}' on line {}, expected '{}'".format(row[column_name], column_name, line_number, column_attr.regex)
                        if column_attr.required and str(row[column_name]) != 'NA':
                            errors.append(message)
                        elif column_attr.required or str(row[column_name]) != 'NA':
                            warnings.append(message)

        for c in self.columns:
            if not c.unique:
                continue

            grouped = self.df[self.df[c.name] != 'NA']
            grouped['lineno'] = grouped.index
            grouped = grouped.groupby(c.name)['lineno']\
                .agg([
                    ('count', len),
                    ('lines', lambda lines: ",".join([str(line) for line in sorted(lines)])),
                    ('first', np.min)
                ])\
                .sort_values('first')

            duplicates = grouped[grouped['count'] > 1]
            for col, row in duplicates.iterrows():
                errors.append("{} '{}' appears {} times in lines [{}], should appear once".format(
                    c.name,
                    col,
                    row['count'],
                    row['lines']
                ))

        return errors, warnings