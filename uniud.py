from datetime import datetime
import json
from typing import Dict, List, Tuple, TypedDict
import requests

from models import Closure, Lesson


class Year(TypedDict):
    label: str
    valore: str


def get_years() -> List[Year]:
    resp = requests.get(
        "https://planner.uniud.it/PortaleStudenti/combo.php", params={"aa": 1}
    ).text
    years: Dict[str, Year] = extract_json_from_eval(resp)
    return list(years.values())


class Periodo(TypedDict):
    label: str
    valore: str


class Anno(TypedDict):
    label: str
    valore: str


class Course(TypedDict):
    label: str
    tipo: str
    valore: str
    periodi: List[Periodo]
    elenco_anni: List[Anno]


def get_year_courses(year: int):
    resp = requests.get(
        "https://planner.uniud.it/PortaleStudenti/combo.php",
        params={"aa": year, "page": "corsi"},
    ).text
    courses: List[Course] = extract_json_from_eval(resp)
    return courses


def get_course_lessons(
    courseId: int, year: int, courseYearCode: str
) -> Tuple[List[Lesson], List[Closure]]:
    data = requests.post(
        "https://planner.uniud.it/PortaleStudenti/grid_call.php",
        data={
            "view": "easycourse",
            "form-type": "corso",
            "include": "corso",
            "anno": year,
            "corso": f"{courseId}",
            "anno2[]": f"{courseYearCode}",
            "date": "01-09-2023",
            "all_events": "1",
        },
    ).json()

    lessons = []
    closures = []
    for cella in data["celle"]:
        tipo = cella["tipo"]
        if tipo == "Lezione":
            lesson = Lesson()
            lesson.id = cella["id"]
            lesson.room = cella["aula"]
            lesson.nome_insegnamento = cella["nome_insegnamento"]
            lesson.docente = cella["docente"]
            # lesson.mail_docente = cella["mail_docente"]
            lesson.start_date = datetime.strptime(
                f"{cella['data']} {cella['ora_inizio']}", "%d-%m-%Y %H:%M"
            )
            lesson.end_date = datetime.strptime(
                f"{cella['data']} {cella['ora_fine']}",
                "%d-%m-%Y %H:%M",
            )
            lessons.append(lesson)
        elif tipo == "chiusura_type":
            closure = Closure()
            closure.start_date = datetime.strptime(
                f"{cella['data']} {cella['ora_inizio']}", "%d-%m-%Y %H:%M"
            )
            closure.end_date = datetime.strptime(
                f"{cella['data']} {cella['ora_fine'].replace('24:00', '23:59')}",
                "%d-%m-%Y %H:%M",
            )
            closures.append(closure)
    return lessons, closures


def extract_json_from_eval(dirty_string: str) -> Dict:
    return json.loads(dirty_string.split("=")[1].split(";")[0])
