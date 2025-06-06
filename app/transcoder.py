from json import loads

from google.auth.credentials import Credentials
from google.cloud.video import transcoder_v1
from google.cloud.video.transcoder_v1.types import (
    Job,
    JobConfig,
    ElementaryStream,
    VideoStream,
    AudioStream,
    MuxStream,
    SegmentSettings,
    Manifest,
)
from google.protobuf.duration_pb2 import Duration
from typing import Optional
from google.oauth2 import service_account


def make_even(x):
    return x if x % 2 == 0 else x - 1


class TranscoderService:
    def __init__(
        self,
        credentials_json: str,
        project_id: str,
        location: str,
    ):
        self.PROJECT_ID = project_id
        self.LOCATION = location

        self.credentials: Optional[Credentials] = None
        self.credentials_json = credentials_json

        try:
            self.credentials = service_account.Credentials.from_service_account_info(
                loads(self.credentials_json)
            )

        except Exception as e:
            raise ValueError(f"Invalid Google Cloud credentials: {e}")

        self.client = transcoder_v1.TranscoderServiceClient(
            credentials=self.credentials
        )

    def create_transcoder_job(
        self,
        input_uri,
        output_uri,
        width=1920,
        height=1080,
        duration: float = 0,
        fps: float = 60,
    ):
        parent = f"projects/{self.PROJECT_ID}/locations/{self.LOCATION}"

        resolution_steps = {}

        for i in range(5, 1, -1):
            scale_height = make_even(int(height * (i / 5)))
            scale_width = make_even(int(width * (i / 5)))

            resolution_steps[f"{scale_height}p"] = {
                "height": scale_height,
                "width": scale_width,
                "bitrate_bps": int(4500000 * (scale_height / 1080)),
                "frame_rate": fps if scale_height >= 720 else 30,
            }

        elementary_streams = [
            ElementaryStream(
                key=f"video_{key}",
                video_stream=VideoStream(
                    h264=VideoStream.H264CodecSettings(
                        height_pixels=resolution["height"],
                        width_pixels=resolution["width"],
                        bitrate_bps=resolution["bitrate_bps"],
                        frame_rate=resolution["frame_rate"],
                    )
                ),
            )
            for key, resolution in resolution_steps.items()
        ] + [
            ElementaryStream(
                key="audio",
                audio_stream=AudioStream(
                    codec="aac",
                    bitrate_bps=128000,
                ),
            )
        ]

        mux_streams = [
            MuxStream(
                key=f"dash_{key}",
                container="fmp4",
                elementary_streams=[f"video_{key}"],
                segment_settings=SegmentSettings(segment_duration=Duration(seconds=6)),
            )
            for key in resolution_steps
        ] + [
            MuxStream(
                key="dash_audio",
                container="fmp4",
                elementary_streams=["audio"],
                segment_settings=SegmentSettings(segment_duration=Duration(seconds=6)),
            )
        ]

        print(
            f"Creating transcoder job with {len(elementary_streams)} elementary streams and {len(mux_streams)} mux streams."
        )

        job = Job(
            input_uri=input_uri,
            output_uri=output_uri,
            config=JobConfig(
                elementary_streams=elementary_streams,
                    ),
                ],
                mux_streams=mux_streams,
                manifests=[
                    Manifest(
                        file_name="manifest.mpd",
                        type_="DASH",
                        mux_streams=[f"dash_{key}" for key in resolution_steps]
                        + ["dash_audio"],
                    )
                ],
            ),
        )

        return self.client.create_job(parent=parent, job=job)

    def get_transcoder_job_status(self, job_id):
        name = f"projects/{self.PROJECT_ID}/locations/{self.LOCATION}/jobs/{job_id}"
        job = self.client.get_job(name=name)
        return job.state.name
