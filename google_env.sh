#!/bin/zsh

# Список переменных, которые нужно экспортировать и выводить
allowed_vars=("SERVICE_ACCOUNT_PATH" "DRIVE_FOLDER_ID")

while IFS= read -r line || [[ -n "$line" ]]; do
  [[ "$line" =~ ^\s*$ ]] && continue
  [[ "$line" =~ ^\s*# ]] && continue

  # Убираем 'export ' если есть
  line=${line/#export /}

  # Получаем ключ и значение
  key=${line%%=*}
  val=${line#*=}

  # Проверяем, разрешена ли переменная к экспорту
  if [[ " ${allowed_vars[@]} " =~ " $key " ]]; then
    export $line
    echo "***********"
    last10=${val: -12}
    echo "$key = ....$last10"
  fi
done < .env

echo "***********"




