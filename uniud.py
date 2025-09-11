import json
from datetime import datetime
from typing import Dict, List, Tuple, TypedDict

import requests

from models import Closure, Lesson

s = requests.Session()


class Year(TypedDict):
    label: str
    valore: str


def get_years() -> List[Year]:
    resp = s.get(
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
    resp = s.get(
        "https://planner.uniud.it/PortaleStudenti/combo.php",
        params={"aa": year, "page": "corsi"},
    ).text
    courses: List[Course] = extract_json_from_eval(resp)
    return courses


def get_course_lessons(
    courseId: str, year: int, courseYearCode: str
) -> Tuple[List[Lesson], List[Closure]]:
    data = s.post(
        "https://planner.uniud.it/PortaleStudenti/grid_call.php",
        data={
            "view": "easycourse",
            "form-type": "corso",
            "include": "corso",
            "anno": year,
            "corso": f"{courseId}",
            "anno2[]": f"{courseYearCode}",
            "date": "01-08-2025",
            "all_events": "1",
        },
    ).json()

    lessons: List[Lesson] = []
    closures: List[Closure] = []
    for cella in data["celle"]:
        tipo = cella["tipo"]
        if tipo == "Lezione":
            lesson = Lesson()
            lesson.id = cella["id"]
            lesson.room = cella["aula"]
            lesson.nome_insegnamento = cella["name_original"]
            lesson.docente = cella["docente"]
            # lesson.mail_docente = cella["mail_docente"]

            lesson.start_date = datetime.fromtimestamp(cella["timestamp"])

            start_time = datetime.strptime(cella["ora_inizio"], "%H:%M")
            end_time = datetime.strptime(cella["ora_fine"], "%H:%M")
            duration = end_time - start_time
            lesson.end_date = lesson.start_date + duration

            lessons.append(lesson)
        elif tipo == "chiusura_type":
            closure = Closure()
            closure.start_date = datetime.fromtimestamp(cella["timestamp"])

            start_time = datetime.strptime(cella["ora_inizio"], "%H:%M")
            end_time = datetime.strptime(
                cella["ora_fine"].replace("24:00", "23:59"), "%H:%M"
            )
            duration = end_time - start_time
            closure.end_date = closure.start_date + duration

            closures.append(closure)
    return lessons, closures


def extract_json_from_eval(dirty_string: str) -> Dict:
    return json.loads(dirty_string.split("=")[1].split(";")[0])
