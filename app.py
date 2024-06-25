# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify, g
import subprocess
import time
import logging
from logging.handlers import TimedRotatingFileHandler
import psycopg2
import os
import jwt
from functools import wraps


DB_HOST = os.environ.setdefault('DB_HOST','localhost')
DB_PORT = os.environ.setdefault('DB_PORT', '5432')
DATABASE = os.environ.setdefault('DATABASE','Husky')
DB_USER = os.environ.setdefault('DB_USER', 'husky')
DB_PASSWORD = os.environ.setdefault('DB_PASSWORD','husky')
SECRET_KEY = os.environ.setdefault('SECRET_KEY', 'Husky')
# token有效时间单位：小时
TOKEN_EXPIRE_TIME = os.environ.setdefault('TOKEN_EXPIRE_TIME','8')

app = Flask(__name__)
# 设置密钥，用于签名 JWT
app.config['SECRET_KEY'] = SECRET_KEY


# 生成Token
def generate_token(username: str) -> str:
    payload = {
        'username': username,
        'exp': int(time.time()) + 3600 * int(TOKEN_EXPIRE_TIME)
    }
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
    return token


# 身份验证装饰器
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Token')
        if not token:
            return jsonify({'message': 'Missing token'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            username = data['username']
        except jwt.PyJWTError:
            return jsonify({'message': 'Token is invalid or expired'}), 401
        # 将当前用户存储在Flask的上下文g中，以便后续视图函数使用
        g.username = username
        return f(*args, **kwargs)
    return decorated


def connect_db(sql, *args):
    conn = psycopg2.connect(database=DATABASE, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    cur = conn.cursor()
    cur.execute(sql, args)
    data = cur.fetchall()
    conn.close()
    return data


# 登录成功返回Token
@app.route('/api/login', methods=['POST'])
def login():
    username = request.get_json().get('username')
    password = request.get_json().get('password')
    app.logger.info("user <{}> request to login".format(username))
    result = connect_db("SELECT password FROM husky_user WHERE username=%s;", username)
    if result:
        if result[0][0] == password:
            # 登录成功，生成 Token
            token = generate_token(username)
            return jsonify({'token': token}), 201
        else:
            return jsonify({"message": "Invalid username or password"}), 401
    else:
        return jsonify({"message": "Invalid username or password"}), 401


# 获取用户分配的权限，去重返回
def get_user_permission(username: str, permission_name: str) -> list:
    result = connect_db("SELECT permission -> %s FROM husky_user WHERE username=%s;", permission_name, username)[0][0]
    return list(set(result))


# 检查用户是否具有某个权限
def check_user_permission(username: str, check_id: int, permission_name: str) -> bool:
    result = get_user_permission(username, permission_name)
    if len(result) == 0 or check_id in result:
        return True
    else:
        return False


# 根据用户权限获取相应的project信息
def get_projects_by_project_id(sql, *args) -> list:
    project_list = []
    result = connect_db(sql, *args)
    if result:
        for project in result:
            project_list.append({"project_id": project[0], "project_name": project[1], "latest_image": project[2]})
    return project_list


# 根据用户权限获取相应的registry信息
def get_registry_by_registry_id(sql, *args) -> list:
    registry_list = []
    result = connect_db(sql, *args)
    if result:
        for registry in result:
            registry_list.append({"registry_id": registry[0], "registry_name": registry[1]})
    return registry_list


@app.route('/api/projects', methods=['GET'])
@token_required
def get_projects():
    username = g.username
    app.logger.info("user <{}> request to get projects".format(username))
    user_project_id = get_user_permission(username, 'project_id')
    if user_project_id:
        return jsonify(
            get_projects_by_project_id("SELECT project_id, project_name, latest_image FROM build_project WHERE project_id in %s ORDER BY project_id ASC;", tuple(user_project_id))
        ), 200
    else:
        return jsonify(
            get_projects_by_project_id("SELECT project_id, project_name, latest_image FROM build_project ORDER BY project_id ASC;")
        ), 200


@app.route('/api/registry', methods=['GET'])
@token_required
def get_registry():
    username = g.username
    app.logger.info("user <{}> request to get registry".format(username))
    user_registry_id = get_user_permission(username, 'registry_id')
    if user_registry_id:
        return jsonify(
            get_registry_by_registry_id("SELECT registry_id, registry_name FROM build_registry WHERE registry_id in %s ORDER BY registry_id ASC;", tuple(user_registry_id))
        ), 200
    else:
        return jsonify(
            get_registry_by_registry_id("SELECT registry_id, registry_name FROM build_registry ORDER BY registry_id ASC;")
        ), 200


def build_image(registry: str, project_name: str, ref: str, repo: str, project_id: int) -> dict:
    date = time.strftime("%Y%m%d%H%M", time.localtime())
    tag = "{}/{}:{}-{}".format(registry, project_name, date, ref.split('/')[-1])
    try:
        cmd = subprocess.Popen(["/script/build.sh", tag, project_name, ref, repo])
        cmd.wait()
        if cmd.poll() == 0:
            out = subprocess.check_output(["/script/get_commit_id.sh", project_name])
            image = "{}-{}".format(tag.split('/')[-1], out.decode().replace("\n", ""))
            app.logger.info("build success image: {}".format(image))
            connect_db("UPDATE build_project SET latest_image = %s WHERE project_id = %s;", image, project_id)
            return {"result": image}
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        app.logger.error("build image failed: {}".format(e))
        return {"result": "failed"}


@app.route('/api/build',  methods=['POST'])
@token_required
def build():
    username = g.username
    app.logger.info("user <{}> request to build: {}".format(username, request.get_json()))
    if request.get_json():
        project_id = request.get_json()['project_id']
        ref = request.get_json()['ref']
        register_id = request.get_json()['register_id']
        # 判断是否具有打包的权限
        if check_user_permission(username, project_id, 'project_id') and check_user_permission(username, register_id,'registry_id'):
            result_project = connect_db(
                "SELECT project_name, repository_address FROM build_project WHERE project_id = %s;", project_id)
            result_registry = connect_db("SELECT registry_address FROM build_registry WHERE registry_id = %s;",
                                         register_id)
            # 如果删除项目或者更新项目ID，前端页面没有刷新需要判断
            if result_project and result_registry:
                project_name = result_project[0][0]
                repo = result_project[0][1]
                registry = result_registry[0][0]
                return jsonify(build_image(registry, project_name, ref, repo, project_id)), 201
            else:
                return jsonify({"result": "No permission for this project"}), 403
        else:
            return jsonify({"result": "No permission for this project"}), 403
    else:
        return jsonify({"result": "failed"}), 400


if __name__ == '__main__':
    handler = TimedRotatingFileHandler(
        "/var/log/nginx/app.log", when="D", interval=1, backupCount=30,
        encoding="UTF-8", delay=False)
    logging_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s ### %(message)s')
    handler.setFormatter(logging_format)
    app.logger.setLevel(logging.DEBUG)
    app.logger.addHandler(handler)
    app.run(host='0.0.0.0')