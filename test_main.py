import pytest
import json
import tempfile
from datetime import datetime
from main import read_logs, AverageReport, UserAgentReport


@pytest.fixture
def sample_logs():
    """Фикстура с тестовыми данными логов в формате, соответствующем реальным логам.

    Возвращает:
        list[dict]: Список словарей с логами, содержащими поля:
            - url: URL-адрес запроса
            - response_time: Время выполнения запроса
            - http_user_agent: User-Agent клиента
            - @timestamp: Временная метка в ISO-формате
    """
    return [
        {"url": "/api/users", "response_time": "0.123", "http_user_agent": "Chrome", "@timestamp": "2025-06-22T00:00:00+00:00"},
        {"url": "/api/users", "response_time": "0.456", "http_user_agent": "Firefox", "@timestamp": "2025-06-22T01:00:00+00:00"},
        {"url": "/api/products?id=1", "response_time": "0.789", "http_user_agent": "Chrome", "@timestamp": "2025-06-23T00:00:00+00:00"},
        {"url": "/api/context/...", "response_time": "0.321", "http_user_agent": "Safari", "@timestamp": "2025-06-22T02:00:00+00:00"},
    ]


@pytest.fixture
def log_file(sample_logs):
    """Фикстура, создающая временный файл с тестовыми логами.

    Args:
        sample_logs: Фикстура с тестовыми данными логов

    Возвращает:
        str: Путь к временному файлу с логами, содержащему:
            - 4 валидные JSON-записи
            - 1 невалидную JSON-строку
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        for log in sample_logs:
            f.write(json.dumps(log) + "\n")
        f.write("invalid json\n")  # Добавляем невалидную JSON-строку для тестирования обработки ошибок
        f.flush()
        yield f.name


def test_read_logs_with_date_filter(log_file, sample_logs):
    """Тестирует фильтрацию логов по дате.

    Проверяет, что функция read_logs:
    1. Корректно фильтрует логи по указанной дате
    2. Возвращает только логи за указанную дату
    """
    logs = read_logs([log_file], date_filter="2025-06-22")
    assert len(logs) == 3  # Должно быть 3 записи за 2025-06-22
    assert all(datetime.fromisoformat(log["@timestamp"]).date() == datetime(2025, 6, 22).date() for log in logs)


def test_read_logs_with_invalid_json(log_file, capsys):
    """Тестирует обработку невалидных JSON-строк в логах.

    Проверяет, что функция read_logs:
    1. Пропускает невалидные JSON-строки
    2. Выводит предупреждение в stderr
    3. Возвращает только валидные записи
    """
    logs = read_logs([log_file])
    assert len(logs) == 4  # Должно быть 4 валидных записи
    captured = capsys.readouterr()
    assert "Skipping invalid JSON line" in captured.out


def test_average_report(sample_logs):
    """Тестирует генерацию отчета по среднему времени ответа.

    Проверяет, что AverageReport:
    1. Возвращает корректные заголовки
    2. Группирует данные по endpoint
    3. Корректно вычисляет среднее время
    """
    report, headers = AverageReport().generate(sample_logs)
    assert headers == ["Endpoint", "Count", "Average Time"]
    assert len(report) == 3  # Должно быть 3 группы: /api/users, /api/products, /api/context/...

    # Проверяем расчет среднего для /api/users
    for row in report:
        if row[0] == "/api/users":
            assert row[1] == 2
            assert row[2] == "0.289"


def test_user_agent_report(sample_logs):
    """Тестирует генерацию отчета по User-Agent.

    Проверяет, что UserAgentReport:
    1. Возвращает корректные заголовки
    2. Корректно подсчитывает количество запросов для каждого User-Agent
    """
    report, headers = UserAgentReport().generate(sample_logs)
    assert headers == ["User-Agent", "Count"]
    assert len(report) == 3  # Должно быть 3 User-Agent: Chrome, Firefox, Safari

    ua_counts = {ua: count for ua, count in report}
    assert ua_counts["Chrome"] == 2  # 2 запроса с Chrome
    assert ua_counts["Firefox"] == 1  # 1 запрос с Firefox
    assert ua_counts["Safari"] == 1  # 1 запрос с Safari


def test_url_cleaning_in_average_report(sample_logs):
    """Тестирует очистку URL от параметров при генерации отчета.

    Проверяет, что AverageReport:
    1. Удаляет параметры из URL (все после ?)
    2. Корректно группирует запросы по очищенным URL
    """
    report, _ = AverageReport().generate(sample_logs)
    assert any(row[0] == "/api/products" for row in report)  # Должен быть URL без ?id=1
