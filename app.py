from flask import Flask, request, jsonify
import subprocess
import os
import shutil
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)

INPUT_DIR = "/data/input"
OUTPUT_DIR = "/data/output"
PROCESSED_DIR = "/data/processed"
ALLOWED_EXTENSIONS = {".doc", ".docx"}

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)


def json_error(message, status_code=400, **extra):
    payload = {
        "success": False,
        "error": message
    }
    payload.update(extra)
    return jsonify(payload), status_code


def allowed_extension(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def build_safe_filename(original_filename=None, override_filename=None):
    filename = override_filename or original_filename or f"upload_{uuid.uuid4().hex}.docx"
    filename = secure_filename(filename)

    if not filename:
        filename = f"upload_{uuid.uuid4().hex}.docx"

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Only .doc and .docx files are allowed")

    return filename


def convert_with_libreoffice(input_file, output_dir):
    result = subprocess.run(
        [
            "soffice",
            "--headless",
            "--convert-to", "txt:Text",
            "--outdir", output_dir,
            input_file
        ],
        capture_output=True,
        text=True,
        check=True
    )
    return result


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})


@app.route('/convert', methods=['POST'])
def convert():
    data = request.get_json(silent=True) or {}

    input_file = data.get("input_file")
    move_processed = data.get("move_processed", True)

    if not input_file:
        return json_error("input_file is required", 400)

    if not os.path.isfile(input_file):
        return json_error("file not found", 404, input_file=input_file)

    base_name = os.path.basename(input_file)
    name_without_ext = os.path.splitext(base_name)[0]
    output_file = os.path.join(OUTPUT_DIR, f"{name_without_ext}.txt")

    try:
        result = convert_with_libreoffice(input_file, OUTPUT_DIR)

        converted_exists = os.path.isfile(output_file)
        processed_file = None

        if move_processed and converted_exists:
            processed_file = os.path.join(PROCESSED_DIR, base_name)
            if os.path.exists(processed_file):
                os.remove(processed_file)
            shutil.move(input_file, processed_file)

        return jsonify({
            "success": True,
            "input_file": input_file,
            "output_file": output_file,
            "processed_file": processed_file,
            "stdout": result.stdout,
            "stderr": result.stderr
        })

    except subprocess.CalledProcessError as e:
        return json_error(
            "conversion failed",
            500,
            input_file=input_file,
            stdout=e.stdout,
            stderr=e.stderr
        )
    except Exception as e:
        return json_error(
            "unexpected error during conversion",
            500,
            input_file=input_file,
            details=str(e)
        )


@app.route('/convert-and-read', methods=['POST'])
def convert_and_read():
    data = request.get_json(silent=True) or {}

    input_file = data.get("input_file")
    move_processed = data.get("move_processed", True)
    encoding = data.get("encoding", "utf-8")

    if not input_file:
        return json_error("input_file is required", 400)

    if not os.path.isfile(input_file):
        return json_error("file not found", 404, input_file=input_file)

    base_name = os.path.basename(input_file)
    name_without_ext = os.path.splitext(base_name)[0]
    output_file = os.path.join(OUTPUT_DIR, f"{name_without_ext}.txt")

    try:
        result = convert_with_libreoffice(input_file, OUTPUT_DIR)

        if not os.path.isfile(output_file):
            return json_error(
                "output file was not created",
                500,
                input_file=input_file,
                output_file=output_file,
                stdout=result.stdout,
                stderr=result.stderr
            )

        with open(output_file, "r", encoding=encoding, errors="replace") as f:
            text_content = f.read()

        processed_file = None
        if move_processed:
            processed_file = os.path.join(PROCESSED_DIR, base_name)
            if os.path.exists(processed_file):
                os.remove(processed_file)
            shutil.move(input_file, processed_file)

        return jsonify({
            "success": True,
            "input_file": input_file,
            "output_file": output_file,
            "processed_file": processed_file,
            "text": text_content,
            "stdout": result.stdout,
            "stderr": result.stderr
        })

    except subprocess.CalledProcessError as e:
        return json_error(
            "conversion failed",
            500,
            input_file=input_file,
            stdout=e.stdout,
            stderr=e.stderr
        )
    except UnicodeDecodeError as e:
        return json_error(
            "text file could not be decoded",
            500,
            input_file=input_file,
            output_file=output_file,
            details=str(e)
        )
    except Exception as e:
        return json_error(
            "unexpected error during convert-and-read",
            500,
            input_file=input_file,
            details=str(e)
        )


@app.route('/upload-convert-read', methods=['POST', 'GET'])
def upload_convert_read():
    #try:
        if request.method == 'GET':
            return jsonify({
                "success": True,
                "message": "This endpoint accepts POST requests with a file upload."
            })
        else:
            return jsonify({
                            "success": True,
                            "message": "This endpoint accepts POST requests with a file upload."
                        })
            """
            print("Received request for upload-convert-read")
            print("request.content_type:", request.content_type)
            print("request.files keys:", list(request.files.keys()))
            print("request.form keys:", list(request.form.keys()))
            uploaded_file = request.files.get("file")
            print("File upload received")
            override_filename = request.form.get("filename")
            print("Filename override received")
            move_processed_raw = request.form.get("move_processed", "true")
            print("Move processed received")
            encoding = request.form.get("encoding", "utf-8")
            print("Encoding received")

            move_processed = str(move_processed_raw).lower() in ["true", "1", "yes", "on"]

            if uploaded_file is None:
                return json_error("missing uploaded file in form-data field 'file'", 400)
            print("Uploaded file exists")
            
            original_filename = uploaded_file.filename
            if not original_filename and not override_filename:
                return json_error("uploaded file has no filename and no override filename was provided", 400)
            print("Original filename set")
            
            try:
                safe_filename = build_safe_filename(
                    original_filename=original_filename,
                    override_filename=override_filename
                )
            except ValueError as e:
                return json_error(str(e), 400, original_filename=original_filename, override_filename=override_filename)

            input_file = os.path.join(INPUT_DIR, safe_filename)
            name_without_ext = os.path.splitext(safe_filename)[0]
            output_file = os.path.join(OUTPUT_DIR, f"{name_without_ext}.txt")
            processed_file = os.path.join(PROCESSED_DIR, safe_filename)

            # Alte Dateien mit gleichem Namen bereinigen
            for path in [input_file, output_file]:
                if os.path.exists(path):
                    os.remove(path)

            # Upload speichern
            try:
                uploaded_file.save(input_file)
            except Exception as e:
                return json_error(
                    "failed to save uploaded file",
                    500,
                    input_file=input_file,
                    details=str(e)
                )

            if not os.path.isfile(input_file):
                return json_error(
                    "uploaded file was not saved correctly",
                    500,
                    input_file=input_file
                )

            print("Uploaded file saved successfully")
            print("Converting file...")
            # Konvertieren
            try:
                result = convert_with_libreoffice(input_file, OUTPUT_DIR)
            except subprocess.CalledProcessError as e:
                return json_error(
                    "conversion failed",
                    500,
                    input_file=input_file,
                    stdout=e.stdout,
                    stderr=e.stderr
                )
            except Exception as e:
                return json_error(
                    "unexpected error during libreoffice conversion",
                    500,
                    input_file=input_file,
                    details=str(e)
                )

            if not os.path.isfile(output_file):
                return json_error(
                    "output file was not created",
                    500,
                    input_file=input_file,
                    output_file=output_file,
                    stdout=result.stdout,
                    stderr=result.stderr
                )

            print("File converted successfully")
            # Text lesen
            try:
                with open(output_file, "r", encoding=encoding, errors="replace") as f:
                    text_content = f.read()
            except Exception as e:
                return json_error(
                    "failed to read converted text file",
                    500,
                    input_file=input_file,
                    output_file=output_file,
                    details=str(e)
                )

            print("Text read successfully")
            # Originaldatei verschieben
            final_processed_file = None
            if move_processed:
                try:
                    if os.path.exists(processed_file):
                        os.remove(processed_file)
                    shutil.move(input_file, processed_file)
                    final_processed_file = processed_file
                except Exception as e:
                    return json_error(
                        "file was converted, but moving to processed failed",
                        500,
                        input_file=input_file,
                        output_file=output_file,
                        text=text_content,
                        details=str(e)
                    )
            print("File moved to processed successfully")
            return jsonify({
                "success": True,
                "message": "file uploaded, converted and read successfully",
                "original_filename": original_filename,
                "stored_filename": safe_filename,
                "input_file": input_file,
                "output_file": output_file,
                "processed_file": final_processed_file,
                "text": text_content,
                "stdout": result.stdout,
                "stderr": result.stderr
            })

    except Exception as e:
        return json_error(
            "unexpected top-level error in upload-convert-read",
            500,
            details=str(e)
        )"""


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)