import json
import logging
import os
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

# Загружаем переменные окружения из корневой папки
load_dotenv('../.env')

logger = logging.getLogger(__name__)


def handle_exception(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Ошибка в функции {func.__name__}: {str(e)}")
            raise

    return wrapper


def load_user_settings():
    """
    Загружает настройки пользователя из data/user_settings.json
    """
    try:
        # Получаем путь к корневой папке проекта (на уровень выше src)
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Основной путь к файлу настроек в папке data
        settings_path = os.path.join(root_dir, 'data', 'user_settings.json')

        logger.info(f"Попытка загрузить настройки из: {settings_path}")

        if not os.path.exists(settings_path):
            # Пробуем альтернативные пути (для обратной совместимости)
            possible_paths = [
                settings_path,  # Основной путь
                os.path.join(root_dir, 'user_settings.json'),  # Старое расположение
            ]

            for path in possible_paths[1:]:  # Проверяем альтернативные пути
                if os.path.exists(path):
                    settings_path = path
                    logger.info(f"Найден файл настроек по альтернативному пути: {settings_path}")
                    break
            else:
                raise FileNotFoundError(f"Файл user_settings.json не найден. Проверенные пути: {possible_paths}")

        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        logger.info("Настройки успешно загружены")

        # Возвращаем настройки с значениями по умолчанию
        return {
            'user_currencies': settings.get('user_currencies', ['USD', 'EUR', 'GBP']),
            'user_stocks': settings.get('user_stocks', ['AAPL', 'GOOGL', 'MSFT'])
        }

    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON в файле настроек: {str(e)}")
        # Возвращаем настройки по умолчанию
        return {
            'user_currencies': ['USD', 'EUR', 'GBP'],
            'user_stocks': ['AAPL', 'GOOGL', 'MSFT']
        }
    except Exception as e:
        logger.error(f"Ошибка загрузки настроек: {str(e)}")
        # Возвращаем настройки по умолчанию
        return {
            'user_currencies': ['USD', 'EUR', 'GBP'],
            'user_stocks': ['AAPL', 'GOOGL', 'MSFT']
        }


@handle_exception
def load_transactions_from_excel(file_path: str) -> pd.DataFrame:
    # Проверяем существование файла
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Файл не найден по пути: {file_path}")

    # Проверяем права доступа
    if not os.access(file_path, os.R_OK):
        raise PermissionError(f"Нет прав на чтение файла: {file_path}")

    logger.info(f"Загрузка данных из файла {file_path}")

    try:
        # Загружаем файл с правильным парсингом дат
        df = pd.read_excel(
            file_path,
            parse_dates=['Дата операции', 'Дата платежа'],
            date_format='%d.%m.%Y %H:%M:%S'  # Указываем формат даты
        )

        # Проверяем, что файл не пустой
        if df.empty:
            raise ValueError("Файл Excel пуст")

        # Точные названия столбцов из вашего файла
        required_columns = [
            'Дата операции',
            'Дата платежа',
            'Номер карты',
            'Статус',
            'Сумма операции',
            'Валюта операции',
            'Сумма платежа',
            'Валюта платежа',
            'Кэшбэк',
            'Категория',
            'MCC',
            'Описание',
            'Бонусы (включая кэшбэк)',
            'Округление на инвесткопилку',
            'Сумма операции с округлением'
        ]

        # Проверяем наличие всех обязательных столбцов
        missing_columns = []
        for column in required_columns:
            if column not in df.columns:
                missing_columns.append(column)

        if missing_columns:
            logger.error(f"Найденные столбцы: {list(df.columns)}")
            raise ValueError(
                f"В файле отсутствуют обязательные столбцы: {', '.join(missing_columns)}\n"
                f"Ожидаемые столбцы: {required_columns}"
            )

        logger.info(f"Файл успешно загружен. Столбцы: {list(df.columns)}")
        logger.info(f"Количество строк: {len(df)}")

        # Заполняем пропущенные значения для числовых столбцов
        numeric_columns = [
            'Сумма операции',
            'Сумма платежа',
            'Кэшбэк',
            'Бонусы (включая кэшбэк)',
            'Округление на инвесткопилку',
            'Сумма операции с округлением'
        ]

        for column in numeric_columns:
            if column in df.columns:
                df[column] = pd.to_numeric(df[column], errors='coerce').fillna(0)

        # Заполняем пропущенные строковые значения
        string_columns = ['Номер карты', 'Статус', 'Категория', 'Описание']
        for column in string_columns:
            if column in df.columns:
                df[column] = df[column].fillna('')

        return df

    except Exception as e:
        logger.error(f"Ошибка при загрузке Excel: {str(e)}")
        raise


def filter_transactions_by_date(df: pd.DataFrame, date: datetime) -> pd.DataFrame:
    logger.info(f"Фильтрация транзакций по дате: {date}")

    # Получаем первый день месяца
    start_date = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Приводим дату к концу дня для фильтрации
    end_date = date.replace(hour=23, minute=59, second=59, microsecond=999999)

    logger.info(f"Фильтрация от {start_date} до {end_date}")

    # Фильтруем транзакции за текущий месяц до указанной даты
    filtered_df = df[(df['Дата операции'] >= start_date) & (df['Дата операции'] <= end_date)]

    logger.info(f"Найдено транзакций после фильтрации: {len(filtered_df)}")

    return filtered_df


def get_time_greeting(date: datetime) -> str:
    """
    Возвращает приветствие в зависимости от времени суток
    """
    hour = date.hour
    if 4 <= hour < 12:
        return "Доброе утро"
    elif 12 <= hour < 17:
        return "Добрый день"
    elif 17 <= hour < 23:
        return "Добрый вечер"
    else:
        return "Доброй ночи"
