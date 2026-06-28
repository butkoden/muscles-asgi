import os

import pytest

from muscles.asgi.asgi.request import FileStorage


def test_file_storage_safe_filename_and_validation(tmp_path):
    storage = FileStorage("file", b"abc", filename="../unsafe name.txt", mime_type="text/plain")

    assert storage.safe_filename == "unsafe_name.txt"
    assert storage.validate(max_size=3, allowed_content_types={"text/plain"}) is storage

    target = storage.save(tmp_path, safe=True)

    assert os.path.basename(target) == "unsafe_name.txt"
    assert open(target, "rb").read() == b"abc"


def test_file_storage_validation_rejects_size_and_content_type():
    storage = FileStorage("file", b"abc", filename="a.txt", mime_type="text/plain")

    with pytest.raises(ValueError):
        storage.validate(max_size=2)

    with pytest.raises(ValueError):
        storage.validate(allowed_content_types={"image/png"})
