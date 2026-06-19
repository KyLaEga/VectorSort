#!/bin/zsh
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
export PYTHONUNBUFFERED=1

# Переход в рабочую директорию проекта
cd ~/nsfw_tensor_env

# Активация изолированного окружения venv
source venv/bin/activate

# Запуск целевого скрипта
python3 nsfw_filter.py

echo "\n------------------------------------------"
echo "Процесс завершен. Нажмите любую клавишу для выхода."
read -k 1