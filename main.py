from pathlib import Path
from uniud import get_course_lessons, get_year_courses, get_years
from ics import Calendar, Event


def main():
    ordered_years = sorted(get_years(), key=lambda y: int(y["valore"]), reverse=True)
    assert len(ordered_years) > 0

    latest_year = int(ordered_years[0]["valore"])

    for course in get_year_courses(latest_year):
        for anno in course["elenco_anni"]:
            anno_di_insegnamento: str = anno["valore"].split("|")[1]

            lessons, closures = get_course_lessons(
                course["valore"], latest_year, anno["valore"]
            )

            # region Create and save .ical file
            c = Calendar()
            for lesson in lessons:
                e = Event()
                e.name = lesson.nome_insegnamento
                e.begin = lesson.start_date
                e.end = lesson.end_date
                c.events.add(e)

            ical_file_name = (
                f'ANNO {anno["label"]}.ics'
                if anno_di_insegnamento.isdigit()
                else f'{anno["label"]}.ics'
            )
            ical_file_path = Path(
                f'ical/{course["label"]}/{course["tipo"]}/{ical_file_name}'
            )
            ical_file_path.parent.mkdir(exist_ok=True, parents=True)
            with open(str(ical_file_path), "w") as my_file:
                my_file.writelines(c.serialize_iter())
            # endregion


if __name__ == "__main__":
    main()
