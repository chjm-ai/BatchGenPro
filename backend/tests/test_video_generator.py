import unittest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.video_generator import DoubaoVideoGenerator
from tasks import process_video_generate_sync


class DoubaoVideoGeneratorTests(unittest.TestCase):
    def test_generate_video_route_starts_background_task_and_returns_task_id(self):
        from backend.app import app

        client = app.test_client()
        task_data = {
            "task_id": "task-123",
            "items": [{"index": 0, "prompt": "make video", "status": "pending", "is_video": True}],
        }

        with patch("backend.app.task_manager.create_task", return_value=("task-123", task_data)):
            with patch("backend.app.task_manager.update_task_status") as mock_update_status:
                with patch("backend.app.start_video_generate_task") as mock_start_task:
                    response = client.post(
                        "/api/batch/generate-video",
                        data={
                            "prompt": "make video",
                            "api_type": "doubao",
                            "model_name": "doubao-seedance-2-0-260128",
                            "video_mode": "text",
                        },
                        headers={
                            "X-Session-ID": "session-123",
                            "X-API-Key": "key-123",
                            "X-API-Type": "doubao",
                        },
                    )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["task_id"], "task-123")
        mock_start_task.assert_called_once()
        mock_update_status.assert_called()

    def test_generate_uses_current_ark_task_endpoint_and_default_model(self):
        generator = DoubaoVideoGenerator("test-key", None)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "cgt-123", "status": "queued"}

        with patch("backend.video_generator.requests.post", return_value=mock_response) as mock_post:
            with patch.object(generator, "_process_response", return_value={"success": True}):
                generator.generate("test prompt", ["https://example.com/a.png"])

        called_url = mock_post.call_args[0][0]
        request_json = mock_post.call_args.kwargs["json"]

        self.assertEqual(
            called_url,
            "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks",
        )
        self.assertEqual(request_json["model"], "doubao-seedance-2-0-260128")
        self.assertEqual(request_json["content"][0]["role"], "reference_image")
        self.assertEqual(request_json["duration"], 5)

    def test_generate_uses_custom_duration_when_provided(self):
        generator = DoubaoVideoGenerator("test-key", None)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "cgt-123", "status": "queued"}

        with patch("backend.video_generator.requests.post", return_value=mock_response) as mock_post:
            with patch.object(generator, "_process_response", return_value={"success": True}):
                generator.generate("test prompt", [], duration=4)

        request_json = mock_post.call_args.kwargs["json"]
        self.assertEqual(request_json["duration"], 4)

    def test_generate_supports_multimodal_inputs_and_seedance_options(self):
        generator = DoubaoVideoGenerator("test-key", "doubao-seedance-2-0-260128")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "cgt-123", "status": "queued"}
        media_inputs = {
            "mode": "multimodal",
            "images": ["https://example.com/a.png"],
            "videos": ["https://example.com/b.mp4"],
            "audios": ["https://example.com/c.mp3"],
        }
        options = {
            "resolution": "480p",
            "ratio": "adaptive",
            "duration": -1,
            "seed": 123,
            "watermark": True,
            "generate_audio": True,
        }

        with patch("backend.video_generator.requests.post", return_value=mock_response) as mock_post:
            with patch.object(generator, "_process_response", return_value={"success": True}):
                generator.generate("test prompt", media_inputs=media_inputs, options=options)

        request_json = mock_post.call_args.kwargs["json"]

        self.assertEqual(request_json["resolution"], "480p")
        self.assertEqual(request_json["ratio"], "adaptive")
        self.assertEqual(request_json["duration"], -1)
        self.assertEqual(request_json["seed"], 123)
        self.assertTrue(request_json["watermark"])
        self.assertTrue(request_json["generate_audio"])
        self.assertEqual(request_json["content"][0]["type"], "image_url")
        self.assertEqual(request_json["content"][0]["role"], "reference_image")
        self.assertEqual(request_json["content"][1]["type"], "video_url")
        self.assertEqual(request_json["content"][1]["role"], "reference_video")
        self.assertEqual(request_json["content"][2]["type"], "audio_url")
        self.assertEqual(request_json["content"][2]["role"], "reference_audio")
        self.assertEqual(request_json["content"][3]["type"], "text")

    def test_generate_supports_first_and_last_frame_mode(self):
        generator = DoubaoVideoGenerator("test-key", "doubao-seedance-2-0-260128")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "cgt-123", "status": "queued"}
        media_inputs = {
            "mode": "first_last_frame",
            "first_frame": "https://example.com/first.png",
            "last_frame": "https://example.com/last.png",
        }

        with patch("backend.video_generator.requests.post", return_value=mock_response) as mock_post:
            with patch.object(generator, "_process_response", return_value={"success": True}):
                generator.generate("test prompt", media_inputs=media_inputs, options={})

        request_json = mock_post.call_args.kwargs["json"]
        self.assertEqual(request_json["content"][0]["role"], "first_frame")
        self.assertEqual(request_json["content"][1]["role"], "last_frame")
        self.assertEqual(request_json["content"][2]["type"], "text")

    def test_query_task_status_uses_current_ark_query_endpoint(self):
        generator = DoubaoVideoGenerator("test-key", "doubao-seedance-2-0-260128")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "cgt-123",
            "status": "succeeded",
            "content": {
                "video_url": "https://example.com/video.mp4",
            },
        }

        with patch("backend.video_generator.requests.get", return_value=mock_response) as mock_get:
            result = generator._query_task_status("cgt-123")

        called_url = mock_get.call_args[0][0]

        self.assertEqual(
            called_url,
            "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks/cgt-123",
        )
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["video_url"], "https://example.com/video.mp4")

    def test_query_task_status_returns_last_frame_and_output_metadata(self):
        generator = DoubaoVideoGenerator("test-key", "doubao-seedance-2-0-260128")
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "cgt-123",
            "status": "succeeded",
            "content": {
                "video_url": "https://example.com/video.mp4",
                "last_frame_url": "https://example.com/last.png",
            },
            "resolution": "720p",
            "ratio": "9:16",
            "duration": 6,
            "generate_audio": True,
        }

        with patch("backend.video_generator.requests.get", return_value=mock_response):
            result = generator._query_task_status("cgt-123")

        self.assertEqual(result["last_frame_url"], "https://example.com/last.png")
        self.assertEqual(result["resolution"], "720p")
        self.assertEqual(result["ratio"], "9:16")
        self.assertEqual(result["duration"], 6)
        self.assertTrue(result["generate_audio"])

    def test_process_video_generate_sync_returns_failed_when_generator_fails(self):
        fake_task_manager = Mock()
        fake_generator = Mock()
        fake_generator.generate.return_value = {
            "success": False,
            "error": "provider failed",
        }

        with patch("task_manager.task_manager", fake_task_manager):
            with patch("video_generator.create_video_generator", return_value=fake_generator):
                result = process_video_generate_sync(
                    "session-1",
                    "task-1",
                    [],
                    "test prompt",
                    "doubao",
                    "test-key",
                    "doubao-seedance-2-0-260128",
                    None,
                )

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "provider failed")


if __name__ == "__main__":
    unittest.main()
