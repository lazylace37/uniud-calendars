from datetime import datetime
import json
from pathlib import Path
from uniud import get_course_lessons, get_year_courses, get_years
from ics import Calendar, Event
import urllib.parse
from jinja2 import Environment, FileSystemLoader
import shutil


def main():
    shutil.rmtree("./ical", ignore_errors=True)

    ordered_years = sorted(get_years(), key=lambda y: int(y["valore"]), reverse=True)
    assert len(ordered_years) > 0

    latest_year = int(ordered_years[0]["valore"])

    all_courses = {}

    now = datetime.now()

    for course in get_year_courses(latest_year):
        if course["label"] not in all_courses:
            all_courses[course["label"]] = {}
        if not course["tipo"] in all_courses[course["label"]]:
            all_courses[course["label"]][course["tipo"]] = {}

        for anno in course["elenco_anni"]:
            anno_di_insegnamento: str = anno["valore"].split("|")[1]

            lessons, closures = get_course_lessons(
                course["valore"], latest_year, anno["valore"]
            )

            # region Create and save .ical file
            c = Calendar()
            for lesson in lessons:
                e = Event(
                    name=lesson.nome_insegnamento,
                    begin=lesson.start_date,
                    end=lesson.end_date,
                    last_modified=now,
                    location=lesson.room,
                )
                c.events.add(e)

            ical_file_name = (
                f'{course["label"]} - ANNO {anno["label"]}.ics'
                if anno_di_insegnamento.isdigit()
                else f'{course["label"]} - {anno["label"]}.ics'
            )
            ical_file_path_name = (
                f'ical/{course["label"]}/{course["tipo"]}/{ical_file_name}'
            )
            ical_file_path = Path(ical_file_path_name)
            ical_file_path.parent.mkdir(exist_ok=True, parents=True)
            with open(str(ical_file_path), "w") as my_file:
                my_file.writelines(c.serialize_iter())
            # endregion

            link = f"https://raw.githubusercontent.com/lazylace37/uniud-calendars/main/{urllib.parse.quote(ical_file_path_name)}"

            if not anno_di_insegnamento in all_courses[course["label"]][course["tipo"]]:
                all_courses[course["label"]][course["tipo"]][anno_di_insegnamento] = {}
            all_courses[course["label"]][course["tipo"]][anno_di_insegnamento][
                anno["label"]
            ] = link

        print(f'Downloaded {course["label"]}')

    # Write .json file
    with open("ical/calendars.json", "w") as f:
        f.write(json.dumps(all_courses))

    # Write README.md
    environment = Environment(loader=FileSystemLoader("./"))
    template = environment.get_template("README.md.template")
    content = template.render(
        all_courses=all_courses,
    )
    with open("README.md", mode="w", encoding="utf-8") as f:
        f.write(content)


if __name__ == "__main__":
    main()
