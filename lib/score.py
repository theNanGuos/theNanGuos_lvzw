from pathlib import Path

from music21 import instrument, key, metadata, meter, note, stream, tempo

from models.state import ScoreSpec, State


def build_score(spec: ScoreSpec) -> stream.Score:
    score = stream.Score(id="theNanGuos")
    score.metadata = metadata.Metadata(title=spec.title)

    for index, part_spec in enumerate(spec.parts):
        part = stream.Part(id=f"part-{index + 1}")
        part.partName = part_spec.name
        try:
            part.insert(0, instrument.fromString(part_spec.instrument))
        except instrument.InstrumentException:
            fallback = instrument.Instrument()
            fallback.instrumentName = part_spec.instrument
            part.insert(0, fallback)
        part.insert(0, tempo.MetronomeMark(number=spec.tempo_bpm))
        part.insert(0, meter.TimeSignature(spec.time_signature))
        part.insert(0, key.Key(spec.key_signature))

        for event in part_spec.notes:
            element = note.Note(event.pitch) if event.pitch else note.Rest()
            element.duration.quarterLength = event.duration
            if isinstance(element, note.Note):
                element.volume.velocity = event.velocity
            part.append(element)
        score.append(part)

    return score


def export_score(spec: ScoreSpec, output_dir: Path | str) -> dict[str, str]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    score = build_score(spec)
    musicxml_path = directory / "score.musicxml"
    midi_path = directory / "score.mid"
    score.write("musicxml", fp=musicxml_path)
    score.write("midi", fp=midi_path)
    return {
        "musicxml": str(musicxml_path),
        "midi": str(midi_path),
    }


def export_score_node(state: State) -> dict[str, dict[str, str]]:
    spec = state.get("score_spec")
    output_dir = state.get("artifact_dir")
    if spec is None or output_dir is None:
        return {"score_artifacts": {}}
    return {"score_artifacts": export_score(spec, output_dir)}
