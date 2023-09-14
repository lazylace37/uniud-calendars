import asyncio
from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
import time
from uniud import Course, get_course_lessons, get_year_courses, get_years
from ics import Calendar, Event
import urllib.parse
from jinja2 import Environment, FileSystemLoader
import shutil


def nesteddefaultdict():
    return defaultdict(nesteddefaultdict)


def background(f):
    def wrapped(*args, **kwargs):
        return asyncio.get_event_loop().run_in_executor(None, f, *args, **kwargs)

    return wrapped


@background
def get_course_timetables(course: Course, latest_year: int, now: datetime):
    course_dict: defaultdict = nesteddefaultdict()
    for anno in course["elenco_anni"]:
        anno_di_insegnamento: str = str(anno["valore"].split("|")[1])

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
        for closure in closures:
            e = Event(
                name="HOLIDAY: lessons not scheduled",
                begin=closure.start_date,
                end=closure.end_date,
                last_modified=now,
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
        course_dict[anno_di_insegnamento][anno["label"]] = link
    return course["label"], course["tipo"], course_dict


def main():
    shutil.rmtree("./ical", ignore_errors=True)

    ordered_years = sorted(get_years(), key=lambda y: int(y["valore"]), reverse=True)
    assert len(ordered_years) > 0

    latest_year = int(ordered_years[0]["valore"])
    lastest_year_courses = get_year_courses(latest_year)

    now = datetime.now()
    loop = asyncio.get_event_loop()
    future = asyncio.gather(
        *[
            get_course_timetables(course, latest_year, now)
            for course in lastest_year_courses
        ]
    )
    results = loop.run_until_complete(future)
    print(f"Download courses timetables took {(datetime.now()-now).total_seconds()}s")

    all_courses: defaultdict = nesteddefaultdict()
    for course_label, course_type, course_dict in results:
        for anno_di_insegnamento, anno in course_dict.items():
            for anno_label, link in anno.items():
                all_courses[course_label][course_type][anno_di_insegnamento][
                    anno_label
                ] = link

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
