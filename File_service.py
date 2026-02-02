from datetime import datetime
import os
from uuid import uuid4
from flask import Flask, request, jsonify, send_from_directory, abort
from flask_cors import CORS  # 导入CORS
import tempfile
import mimetypes
import pymysql
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

# --- 配置 ---
UPLOAD_FOLDER = tempfile.gettempdir()
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# 初始化CORS，允许所有来源
# 注意：在生产环境中，你应该明确指定允许的域名，而不是使用 '*'
CORS(app, resources={r"/upload": {"origins": "*"}, 
r"/files/*": {"origins": "*"},
r"/api/user_assistants": {"origins": "*"},
r"/api/admin/users": {"origins": "*"},
r"/api/admin/users/*": {"origins": "*"},
r"/api/admin/assistants": {"origins": "*"},
r"/api/admin/assistants/*": {"origins": "*"}
})



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

def get_db_connection():
    """建立数据库连接"""
    connection = pymysql.connect(
        host=os.getenv('mysql_host', 'localhost'),  # 从环境变量获取，或使用默认值
        user=os.getenv('mysql_user', 'root'),
        password=os.getenv('mysql_pwd', '123456'),
        database=os.getenv('db_name', 'temp_base'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor # 返回字典格式的结果
    )
    print(os.getenv('db_name'))
    print("数据库连接已建立,连接信息:", connection)

    return connection

@app.route('/api/user_assistants', methods=['GET'])
def get_user_assistants():
    """
    根据 user_id 查询用户可以使用的 Assistant 信息
    """
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({'error': 'Missing user_id parameter'}), 400

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # SQL 查询语句：关联 login_users, user_assistants, assistant_info
            sql = """
            SELECT 
                ai.ASSISTANT_ID,
                ai.name AS assistant_name,
                ai.description AS assistant_description,
                ai.icon_url
            FROM Login_users lu
            INNER JOIN user_assistants ua ON lu.id = ua.user_id
            INNER JOIN assistant_info ai ON ua.assistant_info_id = ai.id
            WHERE lu.username = %s AND ua.is_active = TRUE
            ORDER BY ai.name; -- 可选：按名称排序
            """
            cursor.execute(sql, (user_id,))
            results = cursor.fetchall()

            # 如果没有找到结果
            if not results:
                return jsonify({'assistants':None}), 200

            # 构造返回数据
            assistants_list = []
            for row in results:
                assistant_data = {
                    "ASSISTANT_ID": row['ASSISTANT_ID'],
                    "name": row['assistant_name'],
                    "description": row['assistant_description'],
                    "icon_url": row['icon_url']
                }
                assistants_list.append(assistant_data)

            # print(assistants_list)

            return jsonify({'assistants': assistants_list}), 200

    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/admin/users', methods=['GET'])
def get_users():
    """
    查询用户列表 (支持分页)
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    print(request)
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 计算总数 (用于分页)
            count_sql = "SELECT COUNT(*) as total FROM Login_users"
            cursor.execute(count_sql)
            total_count = cursor.fetchone()['total']

            # 计算偏移量
            offset = (page - 1) * per_page

            # 查询用户列表
            sql = """
            SELECT id, username, real_name, email, created_at
            FROM Login_users
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """
            print("="*50)
            print(sql, (per_page, offset))
            print("="*50)

            cursor.execute(sql, (per_page, offset))
            users = cursor.fetchall()

            # 计算总页数
            total_pages = (total_count + per_page - 1) // per_page

            return jsonify({
                'success': True,
                'data': {
                    'users': users,
                    'pagination': {
                        'current_page': page,
                        'per_page': per_page,
                        'total': total_count,
                        'pages': total_pages
                    }
                }
            }), 200

    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return jsonify({'success': False, 'message': '数据库错误'}), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/admin/users', methods=['POST'])
def create_user():
    """
    新增用户
    """
    data = request.get_json()

    if not data or not data.get('username') or not data.get('real_name') or not data.get('email'):
        return jsonify({'success': False, 'message': '用户名、真实姓名和邮箱不能为空'}), 400

    username = data['username']
    real_name = data['real_name']
    email = data['email']
    # 自动生成一个默认密码或要求提供
    # 注意：实际应用中不应存储明文密码！这里仅作演示，需要加密。
    # 你应该在前端要求输入密码，或后端生成随机密码并发送邮件。
    # 这里我们先生成一个默认密码的哈希
    default_password = "DefaultPassword123!" # 实际应用中不应使用固定密码
    password_hash = generate_password_hash(default_password)

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 检查用户名或邮箱是否已存在
            check_sql = "SELECT id FROM Login_users WHERE username = %s OR email = %s"
            cursor.execute(check_sql, (username, email))
            existing_user = cursor.fetchone()
            if existing_user:
                return jsonify({'success': False, 'message': '用户名或邮箱已存在'}), 400

            # 插入新用户
            insert_sql = """
            INSERT INTO Login_users (username, real_name, email, password_hash)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_sql, (username, real_name, email, password_hash))
            connection.commit()

            # 获取插入的用户ID
            user_id = cursor.lastrowid

            return jsonify({
                'success': True,
                'message': '用户创建成功',
                'data': {
                    'id': user_id,
                    'username': username,
                    'real_name': real_name,
                    'email': email,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S') # 假设创建时间是现在
                }
            }), 201

    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        connection.rollback()
        return jsonify({'success': False, 'message': '数据库错误'}), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """
    修改用户信息
    """
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'message': '请求数据不能为空'}), 400

    # 只允许更新 username, real_name, email
    allowed_fields = {'username', 'real_name', 'email'}
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if not updates:
        return jsonify({'success': False, 'message': '没有提供有效的更新字段'}), 400

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 检查用户是否存在
            check_sql = "SELECT id FROM Login_users WHERE id = %s"
            cursor.execute(check_sql, (user_id,))
            existing_user = cursor.fetchone()
            if not existing_user:
                return jsonify({'success': False, 'message': '用户不存在'}), 404

            # 检查用户名或邮箱是否与其他用户冲突
            conflict_conditions = []
            conflict_params = []
            for field, value in updates.items():
                conflict_conditions.append(f"{field} = %s AND id != %s")
                conflict_params.extend([value, user_id])

            if conflict_conditions:
                conflict_sql = f"SELECT id FROM Login_users WHERE {' OR '.join(conflict_conditions)}"
                cursor.execute(conflict_sql, conflict_params)
                conflicting_user = cursor.fetchone()
                if conflicting_user:
                    return jsonify({'success': False, 'message': '用户名或邮箱已被其他用户使用'}), 400

            # 构建更新 SQL
            set_clause = ', '.join([f"{key} = %s" for key in updates.keys()])
            update_sql = f"UPDATE Login_users SET {set_clause} WHERE id = %s"
            params = list(updates.values()) + [user_id]

            cursor.execute(update_sql, params)
            connection.commit()

            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': '用户未找到或未更新'}), 404

            return jsonify({'success': True, 'message': '用户信息更新成功'})

    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        connection.rollback()
        return jsonify({'success': False, 'message': '数据库错误'}), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """
    删除用户
    """
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 检查用户是否存在
            check_sql = "SELECT id FROM Login_users WHERE id = %s"
            cursor.execute(check_sql, (user_id,))
            existing_user = cursor.fetchone()
            if not existing_user:
                return jsonify({'success': False, 'message': '用户不存在'}), 404

            # 删除用户
            delete_sql = "DELETE FROM Login_users WHERE id = %s"
            cursor.execute(delete_sql, (user_id,))
            connection.commit()

            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': '删除失败'}), 400

            return jsonify({'success': True, 'message': '用户删除成功'})

    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        connection.rollback()
        return jsonify({'success': False, 'message': '数据库错误'}), 500
    finally:
        if connection:
            connection.close()
# app.py 或 api.py (在之前的代码基础上添加)

@app.route('/api/admin/assistants', methods=['GET'])
def get_assistants():
    """
    查询助手列表 (支持分页)
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 计算总数
            count_sql = "SELECT COUNT(*) as total FROM assistant_info"
            cursor.execute(count_sql)
            total_count = cursor.fetchone()['total']

            offset = (page - 1) * per_page

            # 查询助手列表
            sql = """
            SELECT id, ASSISTANT_ID, name, description, icon_url, in_use, created_at
            FROM assistant_info
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (per_page, offset))
            assistants = cursor.fetchall()

            total_pages = (total_count + per_page - 1) // per_page

            return jsonify({
                'success': True,
                'data': {
                    'assistants': assistants,
                    'pagination': {
                        'current_page': page,
                        'per_page': per_page,
                        'total': total_count,
                        'pages': total_pages
                    }
                }
            }), 200

    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return jsonify({'success': False, 'message': '数据库错误'}), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/admin/assistants', methods=['POST'])
def create_assistant():
    """
    新增助手
    """
    data = request.get_json()

    if not data or not data.get('ASSISTANT_ID') or not data.get('name'):
        return jsonify({'success': False, 'message': 'ASSISTANT_ID 和名称不能为空'}), 400

    assistant_id = data['ASSISTANT_ID']
    name = data['name']
    description = data.get('description')
    icon_url = data.get('icon_url')
    in_use = data.get('in_use', 'active') # 默认设置为 active

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 检查 ASSISTANT_ID 是否已存在
            check_sql = "SELECT id FROM assistant_info WHERE ASSISTANT_ID = %s"
            cursor.execute(check_sql, (assistant_id,))
            existing_assistant = cursor.fetchone()
            if existing_assistant:
                return jsonify({'success': False, 'message': 'ASSISTANT_ID 已存在'}), 400

            # 插入新助手
            insert_sql = """
            INSERT INTO assistant_info (ASSISTANT_ID, name, description, icon_url, in_use)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(insert_sql, (assistant_id, name, description, icon_url, in_use))
            connection.commit()

            assistant_id_inserted = cursor.lastrowid

            return jsonify({
                'success': True,
                'message': '助手创建成功',
                'data': {
                    'id': assistant_id_inserted,
                    'ASSISTANT_ID': assistant_id,
                    'name': name,
                    'description': description,
                    'icon_url': icon_url,
                    'in_use': in_use,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }), 201

    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        connection.rollback()
        return jsonify({'success': False, 'message': '数据库错误'}), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/admin/assistants/<int:assistant_id>', methods=['PUT'])
def update_assistant(assistant_id):
    """
    修改助手信息 (包括更新 in_use 状态)
    """
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'message': '请求数据不能为空'}), 400

    # 允许更新的字段
    allowed_fields = {'name', 'description', 'icon_url', 'in_use'}
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if not updates:
        return jsonify({'success': False, 'message': '没有提供有效的更新字段'}), 400

    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 检查助手是否存在
            check_sql = "SELECT id FROM assistant_info WHERE id = %s"
            cursor.execute(check_sql, (assistant_id,))
            existing_assistant = cursor.fetchone()
            if not existing_assistant:
                return jsonify({'success': False, 'message': '助手不存在'}), 404

            # 检查 ASSISTANT_ID 是否与其他助手冲突 (如果尝试修改 ASSISTANT_ID)
            if 'ASSISTANT_ID' in updates:
                conflict_check_sql = "SELECT id FROM assistant_info WHERE ASSISTANT_ID = %s AND id != %s"
                cursor.execute(conflict_check_sql, (updates['ASSISTANT_ID'], assistant_id))
                conflicting_assistant = cursor.fetchone()
                if conflicting_assistant:
                    return jsonify({'success': False, 'message': 'ASSISTANT_ID 已被其他助手使用'}), 400

            # 构建更新 SQL
            set_clause = ', '.join([f"{key} = %s" for key in updates.keys()])
            update_sql = f"UPDATE assistant_info SET {set_clause} WHERE id = %s"
            params = list(updates.values()) + [assistant_id]

            cursor.execute(update_sql, params)
            connection.commit()

            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': '助手未找到或未更新'}), 404

            return jsonify({'success': True, 'message': '助手信息更新成功'})

    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        connection.rollback()
        return jsonify({'success': False, 'message': '数据库错误'}), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/admin/assistants/<int:assistant_id>', methods=['DELETE'])
def delete_assistant(assistant_id):
    """
    删除助手
    """
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 检查助手是否存在
            check_sql = "SELECT id FROM assistant_info WHERE id = %s"
            cursor.execute(check_sql, (assistant_id,))
            existing_assistant = cursor.fetchone()
            if not existing_assistant:
                return jsonify({'success': False, 'message': '助手不存在'}), 404

            # 删除助手
            delete_sql = "DELETE FROM assistant_info WHERE id = %s"
            cursor.execute(delete_sql, (assistant_id,))
            connection.commit()

            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': '删除失败'}), 400

            return jsonify({'success': True, 'message': '助手删除成功'})

    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        connection.rollback()
        return jsonify({'success': False, 'message': '数据库错误'}), 500
    finally:
        if connection:
            connection.close()

# 注意：确保在文件顶部已经导入了 datetime
# from datetime import datetime

if __name__ == '__main__':
    print(f"临时文件将被存储在: {UPLOAD_FOLDER}")
    print("CORS is enabled for /upload and /files/* routes.")
    app.run(debug=True, host='0.0.0.0', port=5000)