def bytes_to_mb(num_bytes):
    """
    Переводит байты в мегабайты.
    """
    return num_bytes / (1024.0 * 1024.0)


def format_time(seconds):
    """
    Форматирует время в виде ч:мм:сс.

    Например: 3725 -> "1:02:05".
    """
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return "{}:{:02d}:{:02d}".format(hours, minutes, secs)
