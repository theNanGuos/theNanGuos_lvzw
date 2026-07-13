from music21 import converter

from lib.score import export_score
from models.state import ScoreSpec


def test_exports_musicxml_and_midi(tmp_path):
    spec = ScoreSpec.model_validate(
        {
            "title": "远征主题",
            "tempo_bpm": 96,
            "time_signature": "4/4",
            "key_signature": "C",
            "parts": [
                {
                    "name": "Piano",
                    "instrument": "Piano",
                    "notes": [
                        {"pitch": "C4", "duration": 1},
                        {"pitch": "E4", "duration": 1},
                        {"pitch": "G4", "duration": 2},
                        {"pitch": None, "duration": 1},
                    ],
                }
            ],
        }
    )

    artifacts = export_score(spec, tmp_path)

    musicxml = tmp_path / "score.musicxml"
    midi = tmp_path / "score.mid"
    assert artifacts == {"musicxml": str(musicxml), "midi": str(midi)}
    assert musicxml.is_file() and musicxml.stat().st_size > 0
    assert midi.is_file() and midi.stat().st_size > 0
    parsed = converter.parse(musicxml)
    assert len(parsed.parts) == 1
    assert [item.nameWithOctave for item in parsed.parts[0].recurse().notes] == [
        "C4",
        "E4",
        "G4",
    ]
