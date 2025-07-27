import argparse
import json
from collections import defaultdict
from datetime import datetime
from tabulate import tabulate


class ReportStrategy:
    """Базовый класс для стратегий генерации отчетов."""

    def generate(self, logs):
        """Генерирует отчет на основе переданных логов.

        Args:
            logs (list): Список словарей с данными логов

        Returns:
            tuple: (данные отчета, заголовки столбцов)
        """
        raise NotImplementedError


class AverageReport(ReportStrategy):
    """Стратегия для генерации отчета о среднем времени ответа по endpoint'ам."""

    def generate(self, logs):
        """Генерирует отчет со статистикой по endpoint'ам.

        Args:
            logs (list): Список словарей с данными логов

        Returns:
            tuple: (данные отчета, заголовки столбцов)
                   Данные отчета: список списков [endpoint, count, average_time]
                   Заголовки: ["Endpoint", "Count", "Average Time"]
        """
        endpoint_stats = defaultdict(lambda: {"count": 0, "total_time": 0})

        for log in logs:
            # Очищаем URL от параметров и якорей
            endpoint = log["url"].split('?')[0].split('#')[0]
            time = float(log["response_time"])
            endpoint_stats[endpoint]["count"] += 1
            endpoint_stats[endpoint]["total_time"] += time

        report = []
        for endpoint, stats in endpoint_stats.items():
            avg_time = stats["total_time"] / stats["count"]
            report.append([endpoint, stats["count"], f"{avg_time:.3f}"])

        # Сортируем по имени endpoint'а
        return sorted(report, key=lambda x: x[0]), ["Endpoint", "Count", "Average Time"]


class UserAgentReport(ReportStrategy):
    """Стратегия для генерации отчета по статистике User-Agent."""

    def generate(self, logs):
        """Генерирует отчет по частоте использования User-Agent'ов.

        Args:
            logs (list): Список словарей с данными логов

        Returns:
            tuple: (данные отчета, заголовки столбцов)
                   Данные отчета: список списков [user_agent, count]
                   Заголовки: ["User-Agent", "Count"]
        """
        ua_stats = defaultdict(int)

        for log in logs:
            ua = log.get("http_user_agent", "Unknown")
            ua_stats[ua] += 1

        # Сортируем по имени User-Agent
        report = [[ua, count] for ua, count in sorted(ua_stats.items())]
        return report, ["User-Agent", "Count"]


def parse_args():
    """Парсит аргументы командной строки.

    Returns:
        Namespace: Объект с аргументами:
                   - file: список путей к файлам логов
                   - report: тип отчета (average/user_agent)
                   - date: опциональная дата для фильтрации
    """
    parser = argparse.ArgumentParser(description="Обработка лог-файлов и генерация отчетов.")
    parser.add_argument("--file", nargs="+", required=True, help="Путь к файлу(ам) логов")
    parser.add_argument(
        "--report", 
        choices=["average", "user_agent"], 
        required=True, 
        help="Тип отчета: average - по среднему времени, user_agent - по клиентам"
    )
    parser.add_argument(
        "--date", 
        help="Фильтровать логи по дате (формат: ГГГГ-ММ-ДД)"
    )
    return parser.parse_args()


def read_logs(file_paths, date_filter=None):
    """Читает и парсит логи из файлов.

    Args:
        file_paths (list): Список путей к файлам логов
        date_filter (str, optional): Дата для фильтрации в формате ГГГГ-ММ-ДД

    Returns:
        list: Список распарсенных логов
    """
    logs = []
    date_filter = datetime.strptime(date_filter, "%Y-%m-%d").date() if date_filter else None

    for file_path in file_paths:
        with open(file_path, "r") as f:
            for line in f:
                try:
                    log = json.loads(line)
                    if date_filter:
                        log_date = datetime.fromisoformat(log["@timestamp"]).date()
                        if log_date != date_filter:
                            continue
                    logs.append(log)
                except json.JSONDecodeError:
                    print(f"Skipping invalid JSON line: {line.strip()}")
    return logs


def get_report_strategy(report_type):
    """Возвращает стратегию генерации отчета по типу.

    Args:
        report_type (str): Тип отчета (average/user_agent)

    Returns:
        ReportStrategy: Объект стратегии генерации отчета
    """
    strategies = {
        "average": AverageReport(),
        "user_agent": UserAgentReport(),
    }
    return strategies.get(report_type)


def main():
    """Основная функция для запуска генерации отчетов."""
    args = parse_args()
    logs = read_logs(args.file, args.date)

    strategy = get_report_strategy(args.report)
    if not strategy:
        raise ValueError(f"Unknown report type: {args.report}")

    report_data, headers = strategy.generate(logs)
    print(tabulate(report_data, headers=headers, tablefmt="grid"))


if __name__ == "__main__":
    main()
