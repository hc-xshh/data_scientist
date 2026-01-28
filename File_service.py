import os
from uuid import uuid4
from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS  # 导入CORS
import tempfile
import mimetypes

# --- 配置 ---
UPLOAD_FOLDER = tempfile.gettempdir()
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# 初始化CORS，允许所有来源
# 注意：在生产环境中，你应该明确指定允许的域名，而不是使用 '*'
CORS(app, resources={r"/upload": {"origins": "*"}, r"/files/*": {"origins": "*"}})

# 如果你想允许所有路由跨域，可以直接这样写：
# CORS(app)

def get_unique_filename(original_filename):
    """生成一个唯一的临时文件名，保留原始扩展名"""
    ext = os.path.splitext(original_filename)[1].lower()
    unique_filename = f"{uuid4().hex}{ext}"
    return unique_filename

def get_file_mime_type(original_filename):
    """根据文件扩展名猜测MIME类型"""
    mime_type, _ = mimetypes.guess_type(original_filename)
    return mime_type or 'application/octet-stream'

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '没有找到名为 "file" 的字段'}), 400
    
    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400

    if file:
        filename = get_unique_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        file.save(filepath)

        # 获取文件的MIME类型
        file_mime_type = get_file_mime_type(file.filename)
        
        # 获取文件大小 (单位: 字节)
        file_size_bytes = os.path.getsize(filepath)

        # 构造返回给客户端的访问URL
        file_url = f"http://localhost:5000/files/{filename}"

        # 返回指定格式的JSON
        return jsonify({
            "file_type": file_mime_type,
            "filename": file.filename,
            "url": file_url,
            "size": file_size_bytes
        }), 201

@app.route('/files/<filename>')
def download_file(filename):
    try:
        if '..' in filename or '/' in filename or '\\' in filename:
             abort(404)
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=False)
    except FileNotFoundError:
        abort(404)

if __name__ == '__main__':
    print(f"临时文件将被存储在: {UPLOAD_FOLDER}")
    print("CORS is enabled for /upload and /files/* routes.")
    app.run(debug=True, host='0.0.0.0', port=5000)