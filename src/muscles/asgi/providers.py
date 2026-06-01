from __future__ import annotations

from pathlib import Path

from muscles.core import GenerationRequest


class AsgiGeneratorProvider:
    name = "muscles-asgi"

    def supports(self, generator_type: str) -> bool:
        return generator_type in {"asgi-api", "asgi-web"}

    def generate(self, project_root: Path, request: GenerationRequest) -> list[str]:
        app_dir = project_root / "app"
        slug = request.name.replace(".", "_").replace("-", "_").lower()

        if request.generator_type == "asgi-api":
            path = app_dir / "api" / f"{slug}.py"
            content = (
                "from muscles.asgi import JsonResponse\n\n"
                f"def {slug}_endpoint(request, *args, **kwargs):\n"
                f"    return JsonResponse({{'resource': '{request.name}'}})\n"
            )
        else:
            path = app_dir / "web" / f"{slug}.py"
            content = (
                "from muscles.asgi import HtmlResponse\n\n"
                f"def {slug}_page(request, *args, **kwargs):\n"
                f"    return HtmlResponse('<h1>{request.name}</h1>')\n"
            )

        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not request.force:
            raise FileExistsError(f"File `{path}` already exists. Use force=True to overwrite.")
        path.write_text(content, encoding="utf-8")
        return [str(path.relative_to(project_root))]

