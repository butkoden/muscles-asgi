from pathlib import Path

from muscles.asgi import AsgiGeneratorProvider, HtmlResponse, JsonResponse
from muscles.core import GenerationRequest


def test_json_and_html_response_helpers_set_content_type():
    jr = JsonResponse({"ok": True})
    hr = HtmlResponse("<h1>ok</h1>")

    assert any(header[0] == "Content-Type" and "application/json" in header[1] for header in jr.headers)
    assert any(header[0] == "Content-Type" and "text/html" in header[1] for header in hr.headers)


def test_asgi_generator_provider_generates_api_and_web(tmp_path):
    (tmp_path / "app" / "api").mkdir(parents=True, exist_ok=True)
    (tmp_path / "app" / "web").mkdir(parents=True, exist_ok=True)
    provider = AsgiGeneratorProvider()

    api_files = provider.generate(tmp_path, GenerationRequest(generator_type="asgi-api", name="Booking"))
    web_files = provider.generate(tmp_path, GenerationRequest(generator_type="asgi-web", name="Home"))

    assert api_files == ["app/api/booking.py"]
    assert web_files == ["app/web/home.py"]

