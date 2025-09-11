import asyncio
import concurrent.futures
import json
import urllib.parse
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from ics import Calendar, Event
from jinja2 import Environment, FileSystemLoader

from uniud import Course, get_course_lessons, get_year_courses, get_years


def nesteddefaultdict():
    return defaultdict(nesteddefaultdict)


def get_course_timetables(course: Course, latest_year: int, now: datetime):
    course_dict: defaultdict = nesteddefaultdict()
    for anno in course["elenco_anni"]:
        lessons_map = defaultdict(list)
        anno_di_insegnamento: str = str(anno["valore"].split("|")[1])

        lessons, closures = get_course_lessons(
            course["valore"], latest_year, anno["valore"]
        )

        # region Create and save .ical file
        c = Calendar()
        for lesson in lessons:
            e = Event(
                summary=lesson.nome_insegnamento,
                uid=f"{(int)(lesson.start_date.timestamp())}",
                begin=lesson.start_date,
                end=lesson.end_date,
                last_modified=now,
                location=f"{lesson.docente} - {lesson.room}",
            )
            lessons_map[e.summary].append(e)
            c.events.append(e)
        for closure in closures:
            e = Event(
                summary="HOLIDAY: lessons not scheduled",
                uid=f"{(int)(closure.start_date.timestamp())}",
                begin=closure.start_date,
                end=closure.end_date,
                last_modified=now,
            )
            c.events.append(e)

        # Sort events
        c.events = sorted(c.events)

        ical_file_name = (
            f"{course['label']} - ANNO {anno['label']}.ics"
            if anno_di_insegnamento.isdigit()
            else f"{course['label']} - {anno['label']}.ics"
        )
        ical_file_path_name = (
            f"ical/{course['label']}/{course['tipo']}/{ical_file_name}"
        )
        ical_file_path = Path(ical_file_path_name)
        ical_file_path.parent.mkdir(exist_ok=True, parents=True)
        with open(str(ical_file_path), "w") as my_file:
            my_file.write(c.serialize())
        # endregion

        link = f"https://raw.githubusercontent.com/lazylace37/uniud-calendars/main/{urllib.parse.quote(ical_file_path_name)}"
        course_dict[anno_di_insegnamento][anno["label"]] = link

        # region Create and save .ical file for each lesson
        for lesson_name, events in lessons_map.items():
            c = Calendar()
            c.events = events
            ical_file_name = f"{lesson_name}.ics"
            ical_file_path_name = f"ical/{course['label']}/{course['tipo']}/{anno['label']}/{ical_file_name}"
            ical_file_path = Path(ical_file_path_name)
            ical_file_path.parent.mkdir(exist_ok=True, parents=True)
            with open(str(ical_file_path), "w") as my_file:
                my_file.write(c.serialize())
        # endregion
    print(f"Done {course['label']} - {course['tipo']}")
    return course["label"], course["tipo"], course_dict


def main():
    # Delete all calendars
    for f in Path("./ical").glob("**/*"):
        if f.is_file():
            f.unlink()

    ordered_years = sorted(get_years(), key=lambda y: int(y["valore"]), reverse=True)
    assert len(ordered_years) > 0

    latest_year = int(ordered_years[0]["valore"])
    lastest_year_courses = get_year_courses(latest_year)

    now = datetime.now()
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future = asyncio.gather(
            *[
                loop.run_in_executor(
                    executor, get_course_timetables, course, latest_year, now
                )
                for course in lastest_year_courses
            ]
        )
    results = loop.run_until_complete(future)
    print(f"Download courses timetables took {(datetime.now() - now).total_seconds()}s")

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
