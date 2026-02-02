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
from fastapi.middleware.cors import CORSMiddleware

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
r"/api/*": {"origins": "*"},
# r"/api/user_assistants": {"origins": "*"},
# r"/api/admin/users": {"origins": "*"},
# r"/api/admin/users/*": {"origins": "*"},
# r"/api/admin/assistants": {"origins": "*"},
# r"/api/admin/assistants/*": {"origins": "*"},
# r"/api/admin/roles": {"origins": "*"},
# r"/api/admin/roles/*": {"origins": "*"},
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
            INNER JOIN user_roles ur on lu.id=ur.user_id
            INNER JOIN role_apps ra on ur.role_id=ra.role_id
            INNER JOIN assistant_info ai ON ra.app_id = ai.id
            WHERE lu.username = %s AND ai.in_use="ACTIVE"
            ORDER BY ai.id;
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
    查询用户列表 (支持分页), 包含用户角色信息
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 计算总数
            count_sql = "SELECT COUNT(*) as total FROM Login_users"
            cursor.execute(count_sql)
            total_count = cursor.fetchone()['total']

            offset = (page - 1) * per_page

            # 查询用户列表及角色（使用 GROUP_CONCAT 聚合角色信息，避免 N+1 查询）
            sql = """
            SELECT 
                u.id, u.username, u.real_name, u.email, u.created_at,
                GROUP_CONCAT(DISTINCT CONCAT(r.id, ':', r.name) SEPARATOR '|') as roles_str
            FROM Login_users u
            LEFT JOIN user_roles ur ON u.id = ur.user_id
            LEFT JOIN roles r ON ur.role_id = r.id
            GROUP BY u.id
            ORDER BY u.created_at DESC
            LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (per_page, offset))
            rows = cursor.fetchall()

            # 处理角色数据（将聚合字符串解析为数组）
            users = []
            for row in rows:
                user_data = {
                    'id': row['id'],
                    'username': row['username'],
                    'real_name': row['real_name'],
                    'email': row['email'],
                    'created_at': row['created_at'].strftime('%Y-%m-%d %H:%M:%S') if row['created_at'] else None,
                    'roles': []
                }
                
                # 解析角色字符串 "1:管理员|2:普通用户" → [{'id': 1, 'name': '管理员'}, ...]
                if row['roles_str']:
                    roles_list = []
                    for role_str in row['roles_str'].split('|'):
                        if ':' in role_str:
                            role_id, role_name = role_str.split(':', 1)
                            roles_list.append({
                                'id': int(role_id),
                                'name': role_name
                            })
                    user_data['roles'] = roles_list
                
                users.append(user_data)

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

@app.route('/api/admin/roles', methods=['GET'])
def get_roles():
    """获取角色列表（分页）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 计算总数
            cursor.execute("SELECT COUNT(*) as total FROM roles")
            total_count = cursor.fetchone()['total']
            
            offset = (page - 1) * per_page
            
            # 查询角色列表
            sql = """
                SELECT id, name, created_at 
                FROM roles 
                ORDER BY id ASC
                LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (per_page, offset))
            roles = cursor.fetchall()
            
            # 格式化日期
            for role in roles:
                if role['created_at']:
                    role['created_at'] = role['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            
            total_pages = (total_count + per_page - 1) // per_page
            
            return jsonify({
                "success": True,
                "data": {
                    "roles": roles,
                    "pagination": {
                        "current_page": page,
                        "per_page": per_page,
                        "total": total_count,
                        "pages": total_pages
                    }
                }
            })
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({"success": False, "message": "数据库错误"}), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/admin/roles', methods=['POST'])
def create_role():
    """创建角色"""
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({"success": False, "message": "角色名称不能为空"}), 400
    
    name = data['name'].strip()
    connection = None
    
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 检查角色名是否已存在
            cursor.execute("SELECT id FROM roles WHERE name = %s", (name,))
            if cursor.fetchone():
                return jsonify({"success": False, "message": "角色名称已存在"}), 400
            
            # 插入新角色
            cursor.execute("INSERT INTO roles (name) VALUES (%s)", (name,))
            connection.commit()
            
            role_id = cursor.lastrowid
            return jsonify({
                "success": True,
                "message": "角色创建成功",
                "data": {
                    "id": role_id,
                    "name": name,
                    "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }), 201
    except Exception as e:
        print(f"Database error: {e}")
        if connection:
            connection.rollback()
        return jsonify({"success": False, "message": "数据库错误"}), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/admin/roles/<int:role_id>', methods=['PUT'])
def update_role(role_id):
    """更新角色"""
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({"success": False, "message": "角色名称不能为空"}), 400
    
    name = data['name'].strip()
    connection = None
    
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 检查角色是否存在
            cursor.execute("SELECT id FROM roles WHERE id = %s", (role_id,))
            if not cursor.fetchone():
                return jsonify({"success": False, "message": "角色不存在"}), 404
            
            # 检查新名称是否与其他角色冲突
            cursor.execute("SELECT id FROM roles WHERE name = %s AND id != %s", (name, role_id))
            if cursor.fetchone():
                return jsonify({"success": False, "message": "角色名称已存在"}), 400
            
            # 更新角色
            cursor.execute("UPDATE roles SET name = %s WHERE id = %s", (name, role_id))
            connection.commit()
            
            return jsonify({
                "success": True,
                "message": "角色信息更新成功"
            })
    except Exception as e:
        print(f"Database error: {e}")
        if connection:
            connection.rollback()
        return jsonify({"success": False, "message": "数据库错误"}), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/admin/roles/<int:role_id>', methods=['DELETE'])
def delete_role(role_id):
    """删除角色"""
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 检查角色是否存在
            cursor.execute("SELECT id FROM roles WHERE id = %s", (role_id,))
            if not cursor.fetchone():
                return jsonify({"success": False, "message": "角色不存在"}), 404
            
            # 删除角色（关联表会自动级联删除）
            cursor.execute("DELETE FROM roles WHERE id = %s", (role_id,))
            connection.commit()
            
            return jsonify({
                "success": True,
                "message": "角色删除成功"
            })
    except Exception as e:
        print(f"Database error: {e}")
        if connection:
            connection.rollback()
        return jsonify({"success": False, "message": "数据库错误"}), 500
    finally:
        if connection:
            connection.close()


# ==================== 权限管理 API ====================

@app.route('/api/admin/roles/<int:role_id>/permissions', methods=['GET'])
def get_role_permissions(role_id):
    """获取角色的应用权限（已授权的APP ID列表）"""
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 验证角色存在
            cursor.execute("SELECT id FROM roles WHERE id = %s", (role_id,))
            if not cursor.fetchone():
                return jsonify({"success": False, "message": "角色不存在"}), 404
            
            # 获取已授权的应用ID列表
            cursor.execute(
                "SELECT app_id FROM role_apps WHERE role_id = %s", 
                (role_id,)
            )
            results = cursor.fetchall()
            authorized_apps = [r['app_id'] for r in results]
            
            return jsonify({
                "success": True,
                "data": {
                    "role_id": role_id,
                    "authorized_app_ids": authorized_apps
                }
            })
    except Exception as e:
        print(f"Database error: {e}")
        return jsonify({"success": False, "message": "数据库错误"}), 500
    finally:
        if connection:
            connection.close()


@app.route('/api/admin/role_apps', methods=['POST'])
def add_role_permission():
    """为角色添加应用授权"""
    data = request.get_json()
    if not data or not data.get('role_id') or not data.get('app_id'):
        return jsonify({"success": False, "message": "角色ID和应用ID不能为空"}), 400
    
    role_id = data['role_id']
    app_id = data['app_id']
    connection = None
    
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            # 检查是否已存在
            cursor.execute(
                "SELECT id FROM role_apps WHERE role_id = %s AND app_id = %s",
                (role_id, app_id)
            )
            if cursor.fetchone():
                return jsonify({
                    "success": True,
                    "message": "该授权已存在"
                })
            
            # 添加授权
            cursor.execute(
                "INSERT INTO role_apps (role_id, app_id) VALUES (%s, %s)",
                (role_id, app_id)
            )
            connection.commit()
            
            return jsonify({
                "success": True,
                "message": "授权成功"
            })
    except Exception as e:
        print(f"Database error: {e}")
        if connection:
            connection.rollback()
        return jsonify({"success": False, "message": "数据库错误"}), 500
    finally:
        if connection:
            connection.close()

@app.route('/api/admin/role_apps', methods=['DELETE'])
def remove_role_permission():
    """取消角色的应用授权"""
    data = request.get_json()
    if not data or not data.get('role_id') or not data.get('app_id'):
        return jsonify({"success": False, "message": "角色ID和应用ID不能为空"}), 400
    
    role_id = data['role_id']
    app_id = data['app_id']
    connection = None
    
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM role_apps WHERE role_id = %s AND app_id = %s",
                (role_id, app_id)
            )
            connection.commit()
            
            return jsonify({
                "success": True,
                "message": "取消授权成功"
            })
    except Exception as e:
        print(f"Database error: {e}")
        if connection:
            connection.rollback()
        return jsonify({"success": False, "message": "数据库错误"}), 500
    finally:
        if connection:
            connection.close()



# 获取用户角色
@app.route('/api/admin/users/<int:user_id>/roles', methods=['GET'])
def get_user_roles(user_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT r.id, r.name 
                FROM roles r
                INNER JOIN user_roles ur ON r.id = ur.role_id
                WHERE ur.user_id = %s
            """
            cursor.execute(sql, (user_id,))
            roles = cursor.fetchall()
            return jsonify({'success': True, 'data': {'roles': roles}})
    finally:
        connection.close()

# 更新用户角色（批量）
@app.route('/api/admin/users/<int:user_id>/roles', methods=['PUT'])
def update_user_roles(user_id):
    data = request.get_json()
    role_ids = data.get('role_ids', [])
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 验证用户存在
            cursor.execute("SELECT id FROM Login_users WHERE id = %s", (user_id,))
            if not cursor.fetchone():
                return jsonify({'success': False, 'message': '用户不存在'}), 404
            
            # 删除旧的角色关联
            cursor.execute("DELETE FROM user_roles WHERE user_id = %s", (user_id,))
            
            # 插入新的角色关联
            for role_id in role_ids:
                cursor.execute(
                    "INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)",
                    (user_id, role_id)
                )
            
            connection.commit()
            return jsonify({'success': True, 'message': '角色更新成功'})
    except Exception as e:
        connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        connection.close()

# 修改创建用户接口，支持角色分配
@app.route('/api/admin/users', methods=['POST'])
def create_user():
    data = request.get_json()
    username = data.get('username')
    real_name = data.get('real_name')
    email = data.get('email')
    password = data.get('password', 'DefaultPassword123!')
    role_ids = data.get('role_ids', [])
    
    if not all([username, real_name, email]):
        return jsonify({'success': False, 'message': '必填字段不能为空'}), 400
    
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # 检查用户名/邮箱是否存在
            cursor.execute(
                "SELECT id FROM Login_users WHERE username = %s OR email = %s",
                (username, email)
            )
            if cursor.fetchone():
                return jsonify({'success': False, 'message': '用户名或邮箱已存在'}), 400
            
            # 创建用户
            password_hash = generate_password_hash(password)
            cursor.execute(
                "INSERT INTO Login_users (username, real_name, email, password_hash) VALUES (%s, %s, %s, %s)",
                (username, real_name, email, password_hash)
            )
            user_id = cursor.lastrowid
            
            # 分配角色
            for role_id in role_ids:
                cursor.execute(
                    "INSERT INTO user_roles (user_id, role_id) VALUES (%s, %s)",
                    (user_id, role_id)
                )
            
            connection.commit()
            return jsonify({
                'success': True,
                'message': '创建成功',
                'data': {'id': user_id, 'username': username}
            }), 201
    except Exception as e:
        connection.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
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

# 删除用户
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

# 获取助手列表
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

# 创建助手
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

# 修改助手信息
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



#删除助手
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