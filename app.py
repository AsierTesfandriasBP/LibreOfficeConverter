from flask import Flask, request, jsonify
import subprocess
import os
import shutil

app = Flask(__name__)

INPUT_DIR = "/data/input"
OUTPUT_DIR = "/data/output"
PROCESSED_DIR = "/data/processed"

os.makedirs(INPUT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok test"})

@app.route('/convert', methods=['POST'])
def convert():
    data = request.get_json(silent=True) or {}

    input_file = data.get("input_file")
    move_processed = data.get("move_processed", True)

    if not input_file:
        return jsonify({
            "success": False,
            "error": "input_file is required"
        }), 400

    if not os.path.isfile(input_file):
        return jsonify({
            "success": False,
            "error": f"file not found: {input_file}"
        }), 404

    base_name = os.path.basename(input_file)
    name_without_ext = os.path.splitext(base_name)[0]
    output_file = os.path.join(OUTPUT_DIR, f"{name_without_ext}.txt")

    try:
        result = subprocess.run(
            [
                "soffice",
                "--headless",
                "--convert-to", "txt:Text",
                "--outdir", OUTPUT_DIR,
                input_file
            ],
            capture_output=True,
            text=True,
            check=True
        )

        converted_exists = os.path.isfile(output_file)

        if move_processed and converted_exists:
            target_processed = os.path.join(PROCESSED_DIR, base_name)
            if os.path.exists(target_processed):
                os.remove(target_processed)
            shutil.move(input_file, target_processed)

        return jsonify({
            "success": True,
            "input_file": input_file,
            "output_file": output_file,
            "processed_file": os.path.join(PROCESSED_DIR, base_name) if move_processed and converted_exists else None,
            "stdout": result.stdout,
            "stderr": result.stderr
        })

    except subprocess.CalledProcessError as e:
        return jsonify({
            "success": False,
            "error": "conversion failed",
            "stdout": e.stdout,
            "stderr": e.stderr
        }), 500

@app.route('/convert-and-read', methods=['POST'])
def convert_and_read():
    data = request.get_json(silent=True) or {}

    input_file = data.get("input_file")
    move_processed = data.get("move_processed", True)
    encoding = data.get("encoding", "utf-8")

    if not input_file:
        return jsonify({
            "success": False,
            "error": "input_file is required"
        }), 400

    if not os.path.isfile(input_file):
        return jsonify({
            "success": False,
            "error": f"file not found: {input_file}"
        }), 404

    base_name = os.path.basename(input_file)
    name_without_ext = os.path.splitext(base_name)[0]
    output_file = os.path.join(OUTPUT_DIR, f"{name_without_ext}.txt")

    try:
        result = subprocess.run(
            [
                "soffice",
                "--headless",
                "--convert-to", "txt:Text",
                "--outdir", OUTPUT_DIR,
                input_file
            ],
            capture_output=True,
            text=True,
            check=True
        )

        if not os.path.isfile(output_file):
            return jsonify({
                "success": False,
                "error": "output file was not created",
                "stdout": result.stdout,
                "stderr": result.stderr
            }), 500

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
        return jsonify({
            "success": False,
            "error": "conversion failed",
            "stdout": e.stdout,
            "stderr": e.stderr
        }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
