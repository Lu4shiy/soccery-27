from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import subprocess
import sys

# ... (ваш существующий код) ...

# Добавляем в самый конец файла
security = HTTPBasic()

def run_seed_script():
    """Запускает наш скрипт seed_data.py в фоне."""
    print("Запуск скрипта seed_data.py в фоне...")
    # Используем sys.executable, чтобы взять тот же Python из виртуального окружения
    result = subprocess.run([sys.executable, "seed_data.py"], capture_output=True, text=True)
    print("Скрипт завершён.")
    print("Вывод (stdout):", result.stdout)
    if result.stderr:
        print("Ошибки (stderr):", result.stderr)

@app.post("/admin/seed")
def trigger_seed(background_tasks: BackgroundTasks, credentials: HTTPBasicCredentials = Depends(security)):
    # Простая защита, чтобы никто посторонний не мог запустить скрипт
    # В реальном проекте используйте более сложный пароль
    correct_username = secrets.compare_digest(credentials.username, "admin")
    correct_password = secrets.compare_digest(credentials.password, "soccery_secret_2026")
    
    if not (correct_username and correct_password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    background_tasks.add_task(run_seed_script)
    return {"message": "Загрузка данных запущена в фоновом режиме. Проверьте логи на Render и данные в Neon через несколько минут."}