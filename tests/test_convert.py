from ChildProject.ChildProject import ChildProject, RecordingProfile
import os
import pandas

def test_import():
    project = ChildProject("examples/valid_raw_data")
    project.import_data("examples/convert")
    project = ChildProject("examples/convert")
    profile = project.convert_recordings(RecordingProfile(
        name = 'test'
    ))

    recordings = project.recordings
    converted_recordings = profile.recordings

    assert os.path.exists("examples/convert/converted_recordings/test"), "missing converted recordings folder"
    assert recordings.shape[0] == converted_recordings.shape[0], "conversion table is incomplete"
    assert all(converted_recordings['success'].tolist()), "not all recordings were successfully converted"
    assert all([
        os.path.exists(os.path.join("examples/convert/converted_recordings/test", f))
        for f in converted_recordings['converted_filename'].tolist()
    ]), "recording files are missing"


