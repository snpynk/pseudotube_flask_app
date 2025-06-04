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


class TranscoderService:
    def __init__(self, project_id, location, credentials_json):
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

    def create_transcoder_job(self, input_uri, output_uri, video_hash):
        parent = f"projects/{self.PROJECT_ID}/locations/{self.LOCATION}"

        job = Job(
            input_uri=input_uri,
            output_uri=output_uri,
            config=JobConfig(
                elementary_streams=[
                    ElementaryStream(
                        key="video_1080p",
                        video_stream=VideoStream(
                            h264=VideoStream.H264CodecSettings(
                                height_pixels=1080,
                                width_pixels=1920,
                                bitrate_bps=4500000,
                                frame_rate=30,
                            )
                        ),
                    ),
                    ElementaryStream(
                        key="video_720p",
                        video_stream=VideoStream(
                            h264=VideoStream.H264CodecSettings(
                                height_pixels=720,
                                width_pixels=1280,
                                bitrate_bps=2500000,
                                frame_rate=30,
                            )
                        ),
                    ),
                    ElementaryStream(
                        key="video_480p",
                        video_stream=VideoStream(
                            h264=VideoStream.H264CodecSettings(
                                height_pixels=480,
                                width_pixels=854,
                                bitrate_bps=1000000,
                                frame_rate=30,
                            )
                        ),
                    ),
                    ElementaryStream(
                        key="audio",
                        audio_stream=AudioStream(
                            codec="aac",
                            bitrate_bps=128000,
                        ),
                    ),
                ],
                mux_streams=[
                    MuxStream(
                        key="hls_1080p",
                        container="ts",
                        elementary_streams=["video_1080p", "audio"],
                        segment_settings=SegmentSettings(
                            segment_duration=Duration(seconds=6)
                        ),
                    ),
                    MuxStream(
                        key="hls_720p",
                        container="ts",
                        elementary_streams=["video_720p", "audio"],
                        segment_settings=SegmentSettings(
                            segment_duration=Duration(seconds=6)
                        ),
                    ),
                    MuxStream(
                        key="hls_480p",
                        container="ts",
                        elementary_streams=["video_480p", "audio"],
                        segment_settings=SegmentSettings(
                            segment_duration=Duration(seconds=6)
                        ),
                    ),
                ],
                manifests=[
                    Manifest(
                        file_name="manifest.m3u8",
                        type_="HLS",
                        mux_streams=["hls_1080p", "hls_720p", "hls_480p"],
                    )
                ],
            ),
        )

        return self.client.create_job(parent=parent, job=job)

    def get_transcoder_job_status(self, job_id):
        name = f"projects/{self.PROJECT_ID}/locations/{self.LOCATION}/jobs/{job_id}"
        job = self.client.get_job(name=name)
        return job.state.name
