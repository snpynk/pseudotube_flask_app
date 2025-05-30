from subprocess import Popen, PIPE
import subprocess
from json import loads
from typing import TypedDict

ALLOWED_VIDEO_CODECS = {"h264", "hevc", "h265", "avc", "av1"}
ALLOWED_AUDIO_CODECS = {"aac", "opus"}
ALLOWED_CONTAINERS = {"mp4", "webm"}


class VideoStreamInfo(TypedDict):
    codec_name: str
    codec_type: str
    duration: str


class VideoFormatInfo(TypedDict):
    format: dict[str, str]
    streams: list[VideoStreamInfo]


class VideoStreamingError(Exception):
    pass


def probe_ffprobe_process(file_bytes: bytes, stream) -> tuple[bytes, bytes]:
    process = Popen(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            stream,
            "-show_entries",
            "stream=index,codec_name,codec_type,duration",
            "-show_entries",
            "format=format_name",
            "-of",
            "json",
            "-i",
            "-",
        ],
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
    )

    output, err = process.communicate(input=file_bytes)
    if process.returncode != 0:
        raise RuntimeError(
            f"ffprobe failed with return code {process.returncode}.\n\n{err.decode('utf-8')}"
        )

    return output, err


def probe_video(file_bytes: bytes) -> VideoFormatInfo:
    output_probe_video, err = probe_ffprobe_process(file_bytes, "v")
    output_probe_audio, err = probe_ffprobe_process(file_bytes, "a")

    info = loads(output_probe_video.decode("utf-8"))
    audio_streams = loads(output_probe_audio.decode("utf-8")).get("streams", [])

    info["streams"].extend(audio_streams)

    if not info.get("streams"):
        raise ValueError("No video streams found in the file.")

    return info


def validate_video_duration(info: VideoFormatInfo) -> None:
    durations = [
        float(s.get("duration", 0)) for s in info["streams"] if "duration" in s
    ]
    if not durations or max(durations) < 1.0:
        raise VideoStreamingError("Video duration is too short.")


def validate_video_streamable(file_bytes: bytes) -> None:
    try:
        if not file_bytes:
            raise VideoStreamingError("Empty file provided")

        info = probe_video(file_bytes)

        format_name = info["format"].get("format_name", "").lower()
        if not any(fmt in format_name for fmt in ALLOWED_CONTAINERS):
            raise VideoStreamingError(f"Invalid container: {format_name}")

        has_valid_video = any(
            stream.get("codec_type") == "video"
            and stream.get("codec_name") in ALLOWED_VIDEO_CODECS
            for stream in info["streams"]
        )

        has_valid_audio = any(
            stream.get("codec_type") == "audio"
            and stream.get("codec_name") in ALLOWED_AUDIO_CODECS
            for stream in info["streams"]
        )

        if not has_valid_video:
            raise VideoStreamingError("Unsupported video codec")
        if not has_valid_audio:
            raise VideoStreamingError("Unsupported audio codec")

        if "mp4" in format_name or "mov" in format_name:
            if not has_faststart(file_bytes):
                raise VideoStreamingError("Missing faststart/moov atom")

        validate_video_duration(info)

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffprobe/ffmpeg error: {e.stderr}") from e


# WE SHOULD REALLY USE TO TRANSCODING!!!!!!!!!!!!!
def has_faststart(file_bytes: bytes) -> bool:
    # TODO: Implement actual faststart checking
    return True
