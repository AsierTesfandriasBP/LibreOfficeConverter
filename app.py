from flask import Flask, request, jsonify
import subprocess
import os
import shutil
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)

INPUT_DIR = "/data/convert/input"
OUTPUT_DIR = "/data/convert/output"
ALLOWED_EXTENSIONS = {".doc", ".docx"}

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# Return a JSON error response with a given message and status code
def json_error(message, status_code=400, **extra):
    payload = {
        "success": False,
        "error": message
    }
    payload.update(extra)
    return jsonify(payload), status_code


# Check if the uploaded file has an allowed extension
def allowed_extension(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


# Build a safe filename for the uploaded file, ensuring it has an allowed extension
def build_safe_filename(original_filename=None, override_filename=None):
    filename = override_filename or original_filename or f"upload_{uuid.uuid4().hex}.docx"
    filename = secure_filename(filename)

    if not filename:
        filename = f"upload_{uuid.uuid4().hex}.docx"

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Only .doc and .docx files are allowed")

    return filename


# Convert Word file to text using LibreOffice
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

# Health check endpoint
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}, 200)

# Upload, convert, and read a Word file (doc or docx) and return the text content in JSON format
@app.route('/upload-convert-read', methods=['POST'])
def upload_convert_read():
    try:
        print("------------------------------------------------", flush=True)
        print("General Information about the request:", flush=True)
        print("request.content_type:", request.content_type, flush=True)
        print("request.files.keys:", list(request.files.keys()), flush=True)
        print("request.form.keys:", list(request.form.keys()), flush=True)
        print("------------------------------------------------", flush=True)
        uploaded_file = request.files.get("file")
        override_filename = request.form.get("filename")
        encoding = request.form.get("encoding", "utf-8")

        if uploaded_file is None:
            return json_error("missing uploaded file in form-data field 'file'", 400)
        print("Uploaded file exists", flush=True)
        
        original_filename = uploaded_file.filename
        if not original_filename and not override_filename:
            return json_error("uploaded file has no filename and no override filename was provided", 400)
        
        try:
            safe_filename = build_safe_filename(
                original_filename=original_filename,
                override_filename=override_filename
            )
            print("filename set", flush=True)
        except ValueError as e:
            return json_error(str(e), 400, original_filename=original_filename, override_filename=override_filename)

        input_file = os.path.join(INPUT_DIR, safe_filename)
        name_without_ext = os.path.splitext(safe_filename)[0]
        output_file = os.path.join(OUTPUT_DIR, f"{name_without_ext}.txt")

        # Cleanup any existing files with the same name before processing
        for path in [input_file, output_file]:
            if os.path.exists(path):
                os.remove(path)

        # save the uploaded file to the input directory
        try:
            uploaded_file.save(input_file)
        except Exception as e:
            return json_error(
                "failed to save uploaded file",
                500,
                input_file=input_file,
                details=str(e)
            )

        # Check if the uploaded file was saved correctly
        if not os.path.isfile(input_file):
            return json_error(
                "uploaded file was not saved correctly",
                500,
                input_file=input_file
            )

        print("Uploaded file saved successfully", flush=True)
        print("Converting Word file...", flush=True)
        # Convert Word to text using LibreOffice
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
            
        # Check if the output file was created
        if not os.path.isfile(output_file):
            return json_error(
                "output file was not created",
                500,
                input_file=input_file,
                output_file=output_file,
                stdout=result.stdout,
                stderr=result.stderr
            )

        print("Word file converted successfully", flush=True)
        
        # read the converted text file
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

        print("Text read successfully", flush=True)
        
        # Cleanup the txt file
        try:
            os.remove(input_file)
            os.remove(output_file)
        except Exception as e:
            return json_error(
                "Word file was converted, but cleanup failed",
                500,
                input_file=input_file,
                output_file=output_file,
                text=text_content,
                details=str(e)
            )
        
        return jsonify({
            "success": True,
            "message": "Word file uploaded, converted and read successfully",
            "original_filename": original_filename,
            "stored_filename": safe_filename,
            "input_file": input_file,
            "output_file": output_file,
            "text": text_content,
            "stdout": result.stdout,
            "stderr": result.stderr
        })
    except Exception as e:
        return json_error(
            "unexpected top-level error in upload-convert-read",
            500,
            details=str(e)
        )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)