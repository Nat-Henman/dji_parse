from dataclasses import dataclass
from datetime import timedelta, datetime
import re
import pathlib
from typing import List
import os

import ffmpeg
import pysrt
from pysrt.srtitem import SubRipItem, SubRipTime


TELEMETRY_PARSE_RE = r"GPS \(([\d.-]+), ([\d.-]+), [\d.-]+\), D ([\d.-]+)m, H ([\d.-]+)m, H.S ([\d.-]+)m\/s, V.S ([\d.-]+)"


@dataclass
class Metadata:
    creation_time: datetime
    duration: float
    location: str


@dataclass
class Position:
    time: str
    timestamp: str
    latitude: float | None
    longitude: float | None
    rel_elevation: float | None
    distance: float | None
    horizontal_velocity: float | None
    vertical_velocity: float | None


def parse_metadata_from_probe(probe_result: dict) -> Metadata:
    md = probe_result.get("format", {})
    duration = md.get("duration")

    md = md.get("tags", {})
    return Metadata(
        creation_time=datetime.fromisoformat(md.get("creation_time")),
        duration=float(duration),
        location=md.get("location"),
    )


def timestamp(ts: SubRipTime) -> timedelta:
    return timedelta(
        hours=ts.hours,
        minutes=ts.minutes,
        seconds=ts.seconds,
        milliseconds=ts.milliseconds,
    )


def position_from_subtitle(start_time: datetime, message: SubRipItem) -> Position:
    parsed = re.findall(TELEMETRY_PARSE_RE, message.text)
    parsed = parsed[0] if parsed else [None] * 6

    ts = timestamp(message.start)
    return Position(
        time=(start_time + ts).isoformat(),
        timestamp="{:0>8}".format(str(ts)),
        latitude=float(parsed[1]) if parsed[1] else None,
        longitude=float(parsed[0]) if parsed[0] else None,
        distance=float(parsed[2]) if parsed[2] else None,
        rel_elevation=float(parsed[3]) if parsed[3] else None,
        horizontal_velocity=float(parsed[4]) if parsed[4] else None,
        vertical_velocity=float(parsed[5]) if parsed[5] else None,
    )


def video_metadata(input_video: pathlib.Path) -> Metadata:
    return parse_metadata_from_probe(ffmpeg.probe(input_video.absolute()))


def parse_subtitles(input_video: pathlib.Path) -> List[SubRipItem]:
    out = input_video.with_name(input_video.name + ".tmp.srt")

    ffmpeg.input(input_video.absolute()).output(filename=out.absolute()).run(quiet=True)
    subtitles = pysrt.open(out.absolute())
    os.remove(out.absolute())
    return subtitles
