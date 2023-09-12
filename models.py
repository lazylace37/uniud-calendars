from datetime import datetime


class Event:
    start_date: datetime
    end_date: datetime


class Lesson(Event):
    id: str
    room: str
    nome_insegnamento: str
    docente: str
    # mail_docente: str


class Closure(Event):
    pass
