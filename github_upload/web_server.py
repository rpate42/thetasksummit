from __future__ import annotations

import argparse
import io
import mimetypes
import os
import shutil
from http import HTTPStatus
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from flask import Flask, Response, jsonify, request, send_file, send_from_directory
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import RequestEntityTooLarge

from report_converter import convert_transcript


WORKSPACE_ROOT = Path(__file__).resolve().parent
SERVER_TEMP_ROOT = WORKSPACE_ROOT / ".server_tmp"
STATIC_FILES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/app.js": "app.js",
    "/styles.css": "styles.css",
}
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MAX_TRANSCRIPT_BYTES = int(os.getenv("MAX_TRANSCRIPT_BYTES", str(100 * 1024)))
MAX_REQUEST_BYTES = MAX_TRANSCRIPT_BYTES + 512 * 1024
mimetypes.add_type(DOCX_MIME, ".docx")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES


def sanitize_filename(filename: str) -> str:
    candidate = Path(filename).name.strip()
    if not candidate:
        return "transcript.docx"
    return candidate


def create_job_root() -> Path:
    SERVER_TEMP_ROOT.mkdir(exist_ok=True)
    job_root = SERVER_TEMP_ROOT / f"job-{uuid4().hex}"
    job_root.mkdir()
    return job_root


class UploadTooLargeError(Exception):
    pass


def copy_with_size_limit(source: BinaryIO, destination: BinaryIO, max_bytes: int) -> None:
    total = 0
    while True:
        chunk = source.read(64 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise UploadTooLargeError
        destination.write(chunk)


def json_error(message: str, status: HTTPStatus) -> tuple[Response, int]:
    response = jsonify({"error": message})
    response.headers["Cache-Control"] = "no-store"
    return response, int(status)


def resolve_role_label(form_data) -> tuple[str, str]:
    role = (form_data.get("interviewRole") or "").strip().lower()
    role_label = (form_data.get("interviewRoleLabel") or "").strip()

    if role not in {"insured", "claimant", "witness", "other"}:
        raise ValueError("Choose who was interviewed before generating a report.")
    if role == "other" and not role_label:
        raise ValueError('Enter a name or title when "Other" is selected.')
    if not role_label:
        role_label = role.title()

    return role, role_label


def load_transcript_upload(upload: FileStorage) -> tuple[str, bytes]:
    filename = sanitize_filename(upload.filename or "")
    if not filename.lower().endswith(".docx"):
        raise ValueError("Only .docx transcript files are supported.")

    buffer = io.BytesIO()
    copy_with_size_limit(upload.stream, buffer, MAX_TRANSCRIPT_BYTES)
    return filename, buffer.getvalue()


def build_download_response(data: bytes, output_name: str) -> Response:
    response = send_file(
        io.BytesIO(data),
        mimetype=DOCX_MIME,
        as_attachment=True,
        download_name=output_name,
        max_age=0,
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.after_request
def apply_no_store_headers(response: Response) -> Response:
    if request.path.startswith("/api/") or response.mimetype == DOCX_MIME:
        response.headers["Cache-Control"] = "no-store"
    return response


@app.errorhandler(RequestEntityTooLarge)
def handle_request_too_large(_: RequestEntityTooLarge) -> tuple[Response, int]:
    return json_error("Transcript files must be 100 KB or smaller.", HTTPStatus.BAD_REQUEST)


@app.get("/health")
def health() -> Response:
    response = jsonify({"ok": True})
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/")
def serve_root() -> Response:
    return send_from_directory(WORKSPACE_ROOT, "index.html")


@app.get("/<path:requested_path>")
def serve_static(requested_path: str):
    static_name = STATIC_FILES.get(f"/{requested_path}")
    if not static_name:
        return json_error("Not found.", HTTPStatus.NOT_FOUND)

    file_path = WORKSPACE_ROOT / static_name
    if not file_path.exists():
        return json_error("Static file missing.", HTTPStatus.NOT_FOUND)

    return send_from_directory(WORKSPACE_ROOT, static_name)


@app.post("/api/generate")
def generate_report():
    if "transcriptFile" not in request.files:
        return json_error("Choose a transcript .docx file before continuing.", HTTPStatus.BAD_REQUEST)

    try:
        _, role_label = resolve_role_label(request.form)
    except ValueError as exc:
        return json_error(str(exc), HTTPStatus.BAD_REQUEST)

    upload = request.files["transcriptFile"]
    if not upload or not upload.filename:
        return json_error("Choose a transcript .docx file before continuing.", HTTPStatus.BAD_REQUEST)

    try:
        filename, upload_bytes = load_transcript_upload(upload)
    except UploadTooLargeError:
        return json_error("Transcript files must be 100 KB or smaller.", HTTPStatus.BAD_REQUEST)
    except ValueError as exc:
        return json_error(str(exc), HTTPStatus.BAD_REQUEST)

    temp_root = create_job_root()
    input_path = temp_root / filename
    output_name = f"{Path(filename).stem} - generated summary.docx"
    output_path = temp_root / output_name

    try:
        input_path.write_bytes(upload_bytes)
        convert_transcript(input_path, output_path, interviewee_role_label=role_label)
        data = output_path.read_bytes()
    except Exception:
        app.logger.exception("Report generation failed.")
        return json_error("Report generation failed.", HTTPStatus.INTERNAL_SERVER_ERROR)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    return build_download_response(data, output_name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the statement report builder website.")
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    args = parser.parse_args()

    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
