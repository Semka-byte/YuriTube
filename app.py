from flask import Flask, request, render_template, send_from_directory, redirect, url_for, abort, flash
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from flask import session
import re
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

# Конфигурация
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp4', 'webm', 'ogg', 'mov', 'avi'}
MAX_CONTENT_LENGTH = 5120 * 1024 * 1024  # 5 ГБ
SECRET_KEY = '!rIH0jo.UgxSe3yJmd_pAQzTDb9iKw?G1VBshn7P,catNfL8XuOZE2q6lkFvCW-54RYM'  # Замените на реальный секретный ключ
FORBIDDEN_KEYWORDS = ['наркотики', 'экстремизм', 'терроризм']

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['SECRET_KEY'] = SECRET_KEY

Talisman(app, content_security_policy={
    'default-src': "'self'",
    'script-src': ["'self'", 'cdnjs.cloudflare.com'],
    'style-src': ["'self'", 'cdnjs.cloudflare.com', "'unsafe-inline'"],
    'img-src': ["'self'", 'data:']
})

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["700 per day", "350 per hour"]
)

# Создание папки для видео, если не существует
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Проверка расширения файла
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Получение информации о файле
def get_file_info(filename):
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    size = os.path.getsize(path) / (1024 * 1024)  # Размер в MB
    created = datetime.fromtimestamp(os.path.getctime(path))
    return {
        'size': f"{size:.2f} MB",
        'created': created.strftime("%Y-%m-%d %H:%M:%S")
    }

def check_video_content(file_path):
    filename = os.path.basename(file_path)
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(keyword, filename, re.IGNORECASE):
            return False
    return True

# Главная страница
@app.route('/')
def index():
    try:
        videos = []
        for f in os.listdir(app.config['UPLOAD_FOLDER']):
            if allowed_file(f):
                file_info = get_file_info(f)
                videos.append({
                    'name': f,
                    'info': file_info
                })
        # Сортировка по дате создания (новые сначала)
        videos.sort(key=lambda x: x['info']['created'], reverse=True)
    except Exception as e:
        videos = []
    return render_template('index.html', videos=videos)

# Загрузка файла
@app.route('/upload', methods=['POST'])
def upload_file():
    # Проверяем наличие файла в запросе
    if 'video' not in request.files:
        flash('Файл не выбран', 'error')
        return redirect(url_for('index'))
    
    file = request.files['video']
    
    # Проверяем, что файл имеет имя и оно не пустое
    if not file or file.filename is None or file.filename.strip() == '':
        flash('Файл не выбран', 'error')
        return redirect(url_for('index'))

    # Создаем безопасное имя файла (с проверкой на None)
    filename = secure_filename(file.filename) if file.filename else None
    if not filename:
        flash('Недопустимое имя файла', 'error')
        return redirect(url_for('index'))

    # Формируем путь для сохранения
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Защита от перезаписи (исправлен синтаксис)
    base, ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(save_path):
        filename = f"{base}_{counter}{ext}"  # Исправлена строка с форматированием
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        counter += 1

    # Сохраняем файл
    try:
        file.save(save_path)
    except Exception as e:
        flash('Ошибка при сохранении файла', 'error')
        return redirect(url_for('index'))

    # Проверяем содержание файла
    if not check_video_content(save_path):
        try:
            os.remove(save_path)
        except:
            pass
        flash('Видео содержит запрещенный контент', 'error')
        return redirect(url_for('index'))

    flash('Видео успешно загружено!', 'success')
    return redirect(url_for('index'))

# Функция удаления файла (исправленный вариант)
@app.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    if not filename or not allowed_file(filename):
        abort(400, "Недопустимое имя файла")
    
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            flash('Файл успешно удален', 'success')
        else:
            flash('Файл не найден', 'error')
    except Exception as e:
        flash(f'Ошибка при удалении файла: {str(e)}', 'error')
    
    return redirect(url_for('index'))

# Отдача видео
@app.route('/videos/<path:filename>')
def uploaded_file(filename):
    if not allowed_file(filename):
        abort(403)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Запуск приложения
if __name__ == '__main__':

    app.run(debug=True)
