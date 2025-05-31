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


def probe_ffprobe_process(file_path: bytes, stream) -> tuple[bytes, bytes]:
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
            file_path,
        ],
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
    )

    output, err = process.communicate()
    if process.returncode != 0:
        raise RuntimeError(
            f"ffprobe failed with return code {process.returncode}.\n\n{err.decode('utf-8')}"
        )

    return output, err


def probe_video(file_path: str) -> VideoFormatInfo:
    output_probe_video, err = probe_ffprobe_process(file_path, "v")
    output_probe_audio, err = probe_ffprobe_process(file_path, "a")

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


def validate_video_streamable(file_path: str) -> None:
    try:
        if not file_path:
            raise ValueError("File path cannot be empty.")

        info = probe_video(file_path)

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


        validate_video_duration(info)

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffprobe/ffmpeg error: {e.stderr}") from e


# WE SHOULD REALLY USE TO TRANSCODING!!!!!!!!!!!!!
def put_faststart(file_path: str) -> bool:
    file_extension = file_path.split(".")[-1].lower()
    file_name = file_path.replace(f".{file_extension}", "")

    process = Popen(
        [
            "ffmpeg",
            "-i",
            file_path,
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            f"{file_name}_fs.{file_extension}",
        ],
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
    )

    output, err = process.communicate()

    if process.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed with return code {process.returncode}.\n\n{err.decode('utf-8')}"
        )


def generate_thumbnail(file_path: str, ts=1) -> bytes:
    process = Popen(
        [
            "ffmpeg",
            "-ss",
            str(ts),
            "-i",
            file_path,
            "-frames:v",
            "1",
            "-q:v",
            "15",
            "-f",
            "image2",
            "-vcodec",
            "mjpeg",
            "pipe:1",
        ],
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
    )

    output, err = process.communicate()

    if process.returncode != 0:
        raise RuntimeError(
            f"ffprobe failed with return code {process.returncode}.\n\n{err.decode('utf-8')}"
        )

    return output
