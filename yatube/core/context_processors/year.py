from datetime import datetime


def year(request: int):
    today = datetime.now().year
    return {
        'year': today
    }
