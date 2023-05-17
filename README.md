# Чат-клиент

Чат-клиент - это асинхронное приложение на Python для общения в чате. Клиент поддерживает авторизацию пользователя по токену или имени пользователя.

## Основные функции

- Подключение к чат-серверу
- Отправка и прием сообщений в реальном времени
- Авторизация пользователя
- Обновление статуса соединения и информации о пользователе
- Графический интерфейс пользователя

## Структура проекта

- `msg.py`: содержит класс `MessagesManager`, который управляет общением с чат-сервером. Он имеет методы для отправки и приема сообщений, а также управления состояниями соединения и учетными данными пользователя.
- `tools.py`: предоставляет утилиты для работы с сетевыми подключениями и обработкой текста.
- `gui.py`: обрабатывает графический интерфейс пользователя, включая ввод и вывод сообщений, обновления состояния соединения и ввод учетных данных пользователя.
- `db.py`: хранение и выгрузка истории сообщений в sqlite.

## Установка и запуск

1. Склонируйте репозиторий с проектом.
2. Установите все необходимые зависимости, используя `pip install -r requirements.txt`.
3. Запустите приложение, используя команду `python main.py`.

## Использование

- Введите ваше имя пользователя или токен в соответствующих полях ввода.
- Введите свое сообщение в поле ввода на нижней панели и нажмите "Отправить".
- Сообщения из чата будут отображаться в верхней панели.
- Текущее состояние подключения к серверу будет отображаться на нижней панели.