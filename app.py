from flask import Flask, request, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route('/convert', methods=['POST'])
def convert():
    data = request.json
    input_file = data.get('input_file')

    if not input_file:
        return jsonify({"error": "input_file is required"}), 400

    if not os.path.isfile(input_file):
        return jsonify({"error": f"file not found: {input_file}"}), 404

    output_dir = "/data/output"

    try:
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

        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_file = os.path.join(output_dir, base_name + ".txt")

        return jsonify({
            "success": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "output_file": output_file
        })

    except subprocess.CalledProcessError as e:
        return jsonify({
            "success": False,
            "stdout": e.stdout,
            "stderr": e.stderr
        }), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
