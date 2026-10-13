#!/bin/zsh
# Запускает локальный голосовой сервер и открывает калькулятор.
cd "$(dirname "$0")"

if curl -s --max-time 1 http://127.0.0.1:8765/api/ping >/dev/null 2>&1; then
  open "http://127.0.0.1:8765/index.html"
  exit 0
fi

PY=""
for c in /Library/Frameworks/Python.framework/Versions/Current/bin/python3 "$HOME/.local/bin/python3" /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
  if [[ -x "$c" ]] && "$c" -c 'import sys' 2>/dev/null; then
    PY="$c"
    break
  fi
done

if [[ -z "$PY" ]]; then
  osascript -e 'display alert "Сервер не запустился" message "Python3 не найден. Установи его с python.org (галочка «Add to PATH»)."'
  exit 1
fi

nohup "$PY" "сервер.py" >/dev/null 2>&1 &

for i in {1..25}; do
  sleep 0.4
  if curl -s --max-time 1 http://127.0.0.1:8765/api/ping >/dev/null 2>&1; then
    open "http://127.0.0.1:8765/index.html"
    exit 0
  fi
done

osascript -e 'display alert "Сервер не запустился" message "Проверь, что порт 8765 свободен."'