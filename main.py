# Third Party Libraries
from flask import Flask, jsonify, request, Response, send_file
from termcolor import colored
import requests
import os
import traceback
import time
import mimetypes
import base64
import uuid
import threading
# Custom Libraries
from config import models as models
import config
from lib import log as log

app = Flask(__name__)

accountid = config.Account_ID
temp_image_dir = os.path.join(config.Temporary_Image_Hosting_Location)
cf_base_url = config.Base_URL

os.makedirs(temp_image_dir, exist_ok=True)

log(colored(f"[STARTUP] Account ID: {accountid}", 'blue'))
log(colored("[STARTUP] Initializing Flask application...", 'blue'))

# Translate Messages from Cloudflare to OpenAI API
def transform_cloudflare_to_openai(cloudflare_response, model):
    content_type = cloudflare_response.headers.get('Content-Type', '').split(';')[0]
    
    if content_type == 'application/json':
        try:
            cf_data = cloudflare_response.json()
            if 'result' not in cf_data:
                return None
            
            if 'words' in cf_data['result']:
                result = cf_data['result']
                words = result.get('words', [])
                
                duration = words[-1]['end'] if words else 0.0
                
                # Insert Example Data that isn't provided by Cloudflare and assemble JSON response
                segments = [{
                    "id": 0,
                    "seek": 0,
                    "start": words[0]['start'] if words else 0.0,
                    "end": duration,
                    "text": result.get('text', ''),
                    "tokens": [],
                    "temperature": 0.0,
                    "avg_logprob": -0.522584597269694,
                    "compression_ratio": 0.8461538461538461,
                    "no_speech_prob": 0.34786054491996765,
                    "transient": False
                }]
                
                return {
                    "task": "transcribe",
                    "language": "english",
                    "duration": duration,
                    "segments": segments,
                    "text": result.get('text', '')
                }
            else:
                return {
                    "id": "cf-" + str(hash(id(cloudflare_response))),
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": f"{model}",
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": cf_data['result'].get('response', '')
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": {
                        "prompt_tokens": cf_data['result'].get('usage', {}).get('prompt_tokens', 0),
                        "completion_tokens": cf_data['result'].get('usage', {}).get('completion_tokens', 0),
                        "total_tokens": cf_data['result'].get('usage', {}).get('total_tokens', 0)
                    }
                }
        except Exception as e:
            log(colored(f"JSON transform error: {str(e)}", 'red'))
            return None
    
    elif content_type == 'text/plain':
        try:
            transcribed_text = cloudflare_response.text
            return {
                "id": "cf-" + str(hash(id(cloudflare_response))),
                "object": "audio.transcription",
                "created": int(time.time()),
                "model": f"{model}",
                "text": transcribed_text
            }
        except Exception as e:
            log(colored(f"Text transform error: {str(e)}", 'red'))
            return None
    
    return None

# Translate Messages from OpenAI API to Cloudflare
def convert_openai_to_cloudflare(body):
    messages = body.get('messages', [])
    model = body.get('model', [])
    if model:
        del body['model']
    if messages:
        prompt_parts = []
        for msg in messages:
            if msg.get('role') == 'user' and 'content' in msg:
                prompt_parts.append(msg['content'])
        body['prompt'] = "\n".join(prompt_parts)
        if 'messages' in body:
            del body['messages']
    return body

# Periodically Delete Old Files
def cleanup_temp_images():
    while True:
        time.sleep(config.Image_Cleanup_Interval)
        current_time = time.time()
        for filename in os.listdir(temp_image_dir):
            filepath = os.path.join(temp_image_dir, filename)
            if os.path.isfile(filepath):
                try:
                    timestamp_str = filename.split('_')[0]
                    timestamp = int(timestamp_str)
                    if current_time - timestamp > config.Image_Hosting_Duration:
                        os.remove(filepath)
                        log(colored(f"Cleaned up expired image: {filename}", 'yellow'))
                except (ValueError, IndexError):
                    os.remove(filepath)
                    log(colored(f"Deleted invalid file: {filename}", 'red'))


# Handle Images
@app.route('/temp_images/<path:path>', methods=['GET'])
def get_image(path):
    log(colored(f"\n=== File Access Requested ===", 'yellow'))
    log(colored("File Requested:", 'cyan') + f" {path}")
    log("---")
    image_url = f"{request.host_url}temp_images/{path}"
    return send_file(f"{config.Temporary_Image_Hosting_Location}/{path}", mimetype='image/png')
    
# Handle Images
@app.route('/temp_audio/<path:path>', methods=['GET'])
def get_audio(path):
    log(colored(f"\n=== File Access Requested ===", 'yellow'))
    log(colored("File Requested:", 'cyan') + f" {path}")
    log("---")
    image_url = f"{request.host_url}temp_images/{path}"
    return send_file(f"{config.Temporary_Image_Hosting_Location}/{path}", mimetype='image/png')
   
# Load a Favicon for Browsers
@app.route('/favicon.ico', methods=['GET'])
def get_favicon():
    log(colored("=== Favicon Requested ===", 'yellow'))
    log("---")
    return send_file(f"{config.Favicon}", mimetype='image/vnd')

# Return Available Models when Queried
@app.route('/models', methods=['GET'])
def get_models():
    log(colored("\n=== /models endpoint called ===", 'yellow'))
    log(colored("Returning available models list", 'green'))
    log(colored(f"{models}", 'cyan'))
    log("---")
    return jsonify(models)

# Handle Any Other Endpoint
@app.route('/<path:path>', methods=['POST', 'PUT', 'GET', 'DELETE'])
def catch_all(path):
    log(colored(f"\n=== New {request.method} Request ===", 'yellow'))
    log(colored(f"Request received for path: /{path}", 'yellow'))
    log(colored(f"Client IP: {request.remote_addr}", 'yellow'))
    headers = dict(request.headers)
    
    try:
        if 'Authorization' not in headers:
            log(colored("Authorization header missing", 'red'))

        content_type = request.content_type or ''
        
        # Handle Data Based Responses
        if content_type.startswith('multipart/form-data'):
            files = request.files
            form_data = request.form.to_dict()
            model = form_data.get('model')
            cf_files = {}
            for key in files:
                file = files[key]
                file.stream.seek(0)
                
                try:
                    original_filename = file.filename
                    timestamp = int(time.time())
                    unique_filename = f"{timestamp}_{original_filename}"
                    upload_dir = os.path.join('saved_files', 'uploaded')
                    os.makedirs(upload_dir, exist_ok=True)
                    save_path = os.path.join(upload_dir, unique_filename)
                    file.save(save_path)
                    log(colored(f"Saved uploaded file to {save_path}", 'green'))
                except Exception as e:
                    log(colored(f"Error saving uploaded file: {str(e)}", 'red'))
                    traceback.print_exc()
                finally:
                    file.stream.seek(0)
                cf_files[key] = (file.filename, file.stream, file.content_type)
            data = form_data
            body = None
        # Handle Text Responses from an LLM
        else:
            body = request.get_json(silent=True) or {}
            model = body.get('model')
            body = convert_openai_to_cloudflare(body)
            data = None
            cf_files = None

        if model:
            cf_path = f"ai/run/{model}"
        else:
            if path == 'v1/models':
                return jsonify({"error":"Not found"}), 404
            cf_path = f"ai/{path}"

        # Assemble Cloudflare URL
        cf_url = f"{cf_base_url}/{accountid}/{cf_path}"
        log(colored(f"Constructed Cloudflare URL: {cf_url}", 'cyan'))
        log("---")
        
        cf_headers = {
            "Authorization": headers["Authorization"]
        }
        if 'Content-Type' in cf_headers:
            del cf_headers['Content-Type']

        log(colored("\nRequest Details:", 'magenta'))
        log(colored("Method:", 'cyan') + f" {request.method}")
        log(colored("Headers:", 'cyan') + f" {dict(request.headers)}")
        log(colored(f"Request Data:",'cyan') + f"{request.data}")
        if content_type.startswith('multipart/form-data'):
            log(colored("Files uploaded:", 'cyan') + f" {list(files.keys())}")
            log(colored("Form data:", 'cyan') + f" {data}")
        else:
            log(colored("Cleaned Content:", 'cyan') + f" {str(body)[:200]}")
        log("---")

        # Assemble and Send Request to Cloudflare
        log(colored(f"\nMaking external {request.method} request to {cf_url}", 'yellow'))
        if request.method == 'GET':
            external_response = requests.get(cf_url, headers=cf_headers, params=request.args)
        else:
            if content_type.startswith('multipart/form-data'):
                external_response = requests.request(
                    method=request.method,
                    url=cf_url,
                    headers=cf_headers,
                    files=cf_files,
                    data=data,
                    params=request.args
                )
            else:
                external_response = requests.request(
                    method=request.method,
                    url=cf_url,
                    headers=cf_headers,
                    json=body,
                    params=request.args
                )
    
        # Handle Response from Cloudflare
        log(colored("\n=== Cloudflare API Response ===", 'magenta'))
        log(colored("Status Code:", 'cyan') + f" {external_response.status_code}")
        log(colored("Response Headers:", 'cyan') + f" {dict(external_response.headers)}")
        if hasattr(external_response, 'data'):
            log(colored("Data:", 'cyan') + f" {external_response.data}")
        if hasattr(external_response, 'json'):
            try:
                json_data = external_response.json()
                log(colored("JSON:", 'cyan') + f" {json_data}")
            except requests.exceptions.JSONDecodeError:
                log(colored("Response Content (non-JSON):", 'cyan') + f" {external_response.text[:200]}")
        log(colored("Content Length:", 'cyan') + f" {len(external_response.content)} bytes")
        log("---")

        response_content_type = external_response.headers.get('Content-Type', '')
        
        # Handle JSON Responses
        if 'application/json' in response_content_type:
            openai_format = transform_cloudflare_to_openai(external_response, model)
            if not openai_format:
                return jsonify({"error": "Failed to process response"}), 500
            return jsonify(openai_format)
        # Handle Data Responses
        else:
            content = external_response.content
            content_type = external_response.headers.get('Content-Type', '').split(';')[0].strip()

            try:
                ext = mimetypes.guess_extension(content_type)
                if ext:
                    ext = ext.lstrip('.')
                else:
                    content_disposition = external_response.headers.get('Content-Disposition', '')
                    filename = None
                    if 'filename=' in content_disposition:
                        filename = content_disposition.split('filename=')[1].strip('"\'').split(';')[0]
                        if '.' in filename:
                            ext = filename.split('.')[-1]
                        else:
                            ext = 'bin'
                    else:
                        ext = 'bin'
                timestamp = int(time.time())
                if config.Debug:
                    filename = f"{timestamp}_response.{ext}"
                    save_dir = os.path.join('saved_files', 'responses')
                    os.makedirs(save_dir, exist_ok=True)
                    save_path = os.path.join(save_dir, filename)
                    with open(save_path, 'wb') as f:
                        f.write(content)
                    log(colored(f"Saved response file to {save_path}", 'green'))
            except Exception as e:
                log(colored(f"Error saving response file: {str(e)}", 'red'))
                traceback.print_exc()
            
            # Handle Images
            if content_type.startswith('image/'):
                timestamp = int(time.time())
                unique_id = uuid.uuid4().hex[:6]
                ext = mimetypes.guess_extension(content_type)
                if ext:
                    ext = ext.lstrip('.')
                else:
                    ext = 'bin'

                filename = f"{timestamp}_{unique_id}.{ext}"
                temp_image_path = os.path.join(temp_image_dir, filename)

                with open(temp_image_path, 'wb') as f:
                    f.write(content)
                log(colored(f"Saved temporary image to {temp_image_path}", 'green'))

                image_url = f"{request.host_url}temp_images/{filename}"
                log(colored("URL Generated:", 'cyan') + f" {image_url}")

                base64_image = base64.b64encode(content).decode('utf-8')

                if config.Debug:
                    txt_path = os.path.splitext(temp_image_path)[0] + '.txt'
                    try:
                        with open(txt_path, 'w') as txt_file:
                            txt_file.write(base64_image)
                        log(colored(f"Saved base64 text file to {txt_path}", 'green'))
                    except Exception as e:
                        log(colored(f"Error saving base64 text file: {str(e)}", 'red'))
                        traceback.print_exc()

                openai_response = {
                    "created": int(time.time()),
                    "data": [{
                        "b64_json": base64_image,
                        "url": image_url
                    }]
                }
                response = jsonify(openai_response)
                response.headers['X-Image-URL'] = image_url
                return response
            
            else:
                safe_headers = {
                    k: v for k, v in external_response.headers.items()
                    if k.lower() not in [
                        'content-encoding',
                        'transfer-encoding',
                        'content-length',
                        'connection'
                    ]
                }

                if 'Content-Disposition' not in safe_headers:
                    safe_headers['Content-Disposition'] = 'inline'

                safe_headers['Content-Length'] = str(len(content))
                safe_headers['Access-Control-Allow-Origin'] = '*'
                safe_headers['Access-Control-Expose-Headers'] = '*'

                log(colored(f"Final response headers:", 'cyan') + f" {safe_headers}")
                
                return Response(
                    content,
                    status=external_response.status_code,
                    content_type=response_content_type,
                    headers=safe_headers
                )

    except Exception as e:
        log(colored("\n!!! ERROR HANDLER !!!", 'red'))
        log(colored(f"Error: {str(e)}", 'red'))
        traceback.print_exc()
        log("---")
        return jsonify({"error":"Internal server error"}), 500

if __name__ == '__main__':
    log(colored("\n=== Server Startup ===", 'blue'))
    cleanup_thread = threading.Thread(target=cleanup_temp_images, daemon=True)
    cleanup_thread.start()
    app.run(debug=config.Debug, host='0.0.0.0', port=config.Port, threaded=config.MultiThreaded)