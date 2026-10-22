import os
import re
from pathlib import Path
from flask import request, Response


def stream_video(file_path: Path, content_type: str = "video/mp4") -> Response:
    """
    Serve a video file with HTTP 206 Partial Content support for seeking.
    """
    if not file_path.exists():
        return Response("Video file not found", status=404)

    file_size = file_path.stat().st_size
    range_header = request.headers.get("Range", None)

    if not range_header:
        # Full content response
        with open(file_path, "rb") as f:
            data = f.read()
        return Response(data, status=200, mimetype=content_type, headers={
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes"
        })

    # Range header pattern e.g. 'bytes=0-1048575' or 'bytes=1048576-'
    range_match = re.search(r"bytes=(\d+)-(\d*)", range_header)
    if not range_match:
        return Response("Invalid Range Request", status=416)

    byte_start = int(range_match.group(1))
    byte_end = int(range_match.group(2)) if range_match.group(2) else file_size - 1

    if byte_start >= file_size:
        return Response("Range not satisfiable", status=416, headers={
            "Content-Range": f"bytes */{file_size}"
        })

    byte_end = min(byte_end, file_size - 1)
    chunk_length = (byte_end - byte_start) + 1

    def generate_chunks():
        with open(file_path, "rb") as f:
            f.seek(byte_start)
            bytes_left = chunk_length
            while bytes_left > 0:
                read_size = min(bytes_left, 64 * 1024)
                data = f.read(read_size)
                if not data:
                    break
                bytes_left -= len(data)
                yield data

    headers = {
        "Content-Range": f"bytes {byte_start}-{byte_end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_length),
        "Content-Type": content_type,
    }

    return Response(generate_chunks(), status=206, headers=headers, direct_passthrough=True)
