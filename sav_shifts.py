import csv
from dataclasses import dataclass, field as dc_field
import re
import pandas as pd


@dataclass
class SignupCell:
    content: str
    row: int
    column: int
    date: str
    time: str
    shift_type: str
    name: str = None
    phone: str = None


@dataclass(order=True)
class PersonSchedule:
    name: str
    phone: str
    walkthrough_shifts: list = dc_field(default_factory=list)
    phonebank_shifts: list = dc_field(default_factory=list)

    def to_list(self):
        return [
            self.name,
            self.first_name(),
            self.last_name(),
            self.phone,
            self.shifts_to_str(self.walkthrough_shifts),
            self.shifts_to_str(self.phonebank_shifts),
        ]

    @staticmethod
    def list_headers():
        return [
            "Full name",
            "First name",
            "Last name",
            "Phone",
            "Walkthrough shifts",
            "Phonebank shifts",
        ]

    @staticmethod
    def shifts_to_str(shift_list):
        return "\n".join(
            sorted([f"{shift[0]} from {shift[1]}" for shift in shift_list])
        )

    def first_name(self):
        return self.name.split()[0]

    def last_name(self):
        return " ".join(self.name.split()[1:])


@dataclass
class MailMergeRow:
    full_name: str
    first_name: str
    last_name: str
    phone: str
    walkthrough_shifts: list
    phonebank_shifts: list
    other_columns: dict

    def to_list(self):
        standard_columns = [
            self.full_name,
            self.first_name,
            self.last_name,
            self.phone,
            self.shifts_to_str(self.walkthrough_shifts),
            self.shifts_to_str(self.phonebank_shifts),
        ]
        additional_columns = list(self.other_columns.values())
        return standard_columns + additional_columns

    @staticmethod
    def shifts_to_list(shifts_str):
        if shifts_str == "":
            return []
        shifts_str_list = shifts_str.split("\n")
        return [x.split(" from ") for x in shifts_str_list]

    @staticmethod
    def shifts_to_str(shift_list):
        return "\n".join(
            sorted([f"{shift[0]} from {shift[1]}" for shift in shift_list])
        )

    def list_headers(self):
        standard_columns = [
            "Full name",
            "First name",
            "Last name",
            "cell",
            "Walkthrough shifts",
            "Phonebank shifts",
        ]
        additional_columns = list(self.other_columns.keys())
        return standard_columns + additional_columns

    def process_shifts_list(self):
        self.walkthrough_shifts = self.shifts_to_list(self.walkthrough_shifts)
        self.phonebank_shifts = self.shifts_to_list(self.phonebank_shifts)


def load_5year(filename):
    full_list = pd.read_csv(filename)
    required_fields = ["FullName", "Email"]
    return full_list[required_fields]


def columns_lookup(index):
    first_day = 8
    remainder = index % 5
    if remainder in (1, 2):
        base = index // 5
        day = first_day + base
        return f"11/{day:02d}"


good_columns = [x for x in range(59) if x % 5 in (1, 2)]


def rows_lookup(index):
    first_hour = 10
    walkthrough_start_row = 6
    num_rows_slot_10to11 = 6
    num_rows_slot_11to12 = 7
    num_rows_slot_12to1 = 6
    num_rows_slot_1to2 = 7
    num_rows_slot_2to3 = 7
    num_rows_slot_3to430 = 6
    num_rows_slot_debrief = 4
    num_rows_slot_5to6 = 5
    num_rows_slot_6to7 = 6
    num_rows_slot_7to8 = 4

    row_lengths = [
        walkthrough_start_row,
        num_rows_slot_10to11,
        num_rows_slot_11to12,
        num_rows_slot_12to1,
        num_rows_slot_1to2,
        num_rows_slot_2to3,
        num_rows_slot_3to430,
        num_rows_slot_debrief,
        num_rows_slot_5to6,
        num_rows_slot_6to7,
        num_rows_slot_7to8,
    ]

    row_boundaries = [sum(row_lengths[:i]) for i in range(1, len(row_lengths) + 1)]
    print(row_boundaries)

    if index < walkthrough_start_row:
        return (None, None)
    for i, boundary in enumerate(row_boundaries):
        if index < boundary:
            hour = i - 1 + first_hour
            break
    else:  # if no break
        raise ValueError("Couldn't find appropriate hour slot")
    if hour == 15:
        time_str = "3:00 - 4:30"
    else:
        time_str = f"{hour_24_to_12(hour)}:00 - {hour_24_to_12(hour + 1)}:00"
    if hour < 16:
        return ("walkthrough", time_str)
    elif hour == 16:
        return (None, None)
    else:
        return ("phonebank", time_str)

    # if index < 41:
    # hour_index = (index - 6) // 6
    # hour = first_hour + hour_index
    # if hour_index < 5:
    # time_str = f"{hour_24_to_12(hour)}:00 - {hour_24_to_12(hour + 1)}:00"
    # else:
    # time_str = f"{hour_24_to_12(hour)}:00 - {hour_24_to_12(hour + 1)}:30"
    # return ("walkthrough", time_str)
    # elif index >= 45 and index < 56:  # phonebanks
    # slot_5to6 = {45, 46, 47}
    # slot_6to7 = {48, 49, 50, 51, 52}
    # slot_7to8 = {53, 54, 55}
    # if index in slot_5to6:
    # time_str = "5:00 - 6:00"
    # elif index in slot_6to7:
    # time_str = "6:00 - 7:00"
    # elif index in slot_7to8:
    # time_str = "7:00 - 8:00"
    # else:
    # raise ValueError(
    # "Messed up row-to-time phone bank conversion: " + f"(row index {index})"
    # )
    # return ("phonebank", time_str)
    # else:
    # return (None, None)


def hour_24_to_12(hour_24):
    return (hour_24 - 1) % 12 + 1


### Regexes
NAME_REGEX = r"^[^0-9(\n]+[^0-9,?(\n- ]"
PHONE_REGEX = r"((\(?[0-9]\)?[-.]?){10})"


def scan_csv(filename):
    signups = []
    with open(filename, "r") as infile:
        csv_reader = csv.reader(infile)
        for row_number, row in enumerate(csv_reader):
            if row_number < 6:
                continue
            for column in good_columns:
                if len(row[column]) > 5:
                    content = row[column]
                    name = re.search(NAME_REGEX, content)
                    if name:
                        name = name.group(0)
                    phone = re.search(PHONE_REGEX, content)
                    if phone:
                        phone = phone.group(0)
                        phone = "".join([s for s in phone if s in "0123456789"])
                    date = columns_lookup(column)
                    shift_type, time = rows_lookup(row_number)
                    if time is not None:
                        signups.append(
                            SignupCell(
                                content,
                                row_number,
                                column,
                                date,
                                time,
                                shift_type,
                                name,
                                phone,
                            )
                        )
    return signups


def aggregate_signups(signups):
    people = {}
    for signup in signups:
        if signup.name in people:
            if signup.shift_type == "walkthrough":
                people[signup.name].walkthrough_shifts.append(
                    (signup.date, signup.time)
                )
            elif signup.shift_type == "phonebank":
                people[signup.name].phonebank_shifts.append((signup.date, signup.time))
            else:
                raise ValueError(f"Invalid shift_type: {signup.shift_type}")
        else:
            if signup.shift_type == "walkthrough":
                people[signup.name] = PersonSchedule(
                    signup.name,
                    signup.phone,
                    walkthrough_shifts=[(signup.date, signup.time)],
                )
            elif signup.shift_type == "phonebank":
                people[signup.name] = PersonSchedule(
                    signup.name,
                    signup.phone,
                    phonebank_shifts=[(signup.date, signup.time)],
                )
            else:
                raise ValueError(f"Invalid shift_type: {signup.shift_type}")
    return list(people.values())


def write_csv(filename, people):
    first_person = people[0]
    with open(filename, "w") as outfile:
        csv_writer = csv.writer(outfile)
        csv_writer.writerow(first_person.list_headers())
        for person in people:
            csv_writer.writerow(person.to_list())


def load_grid_schedule(filename):
    signup_cells = scan_csv(filename)
    people = aggregate_signups(signup_cells)
    return sorted(people)


def scan_mailmerge_csv(filename):
    people = {}
    with open(filename, "r") as infile:
        csv_reader = csv.reader(infile)
        for i, row in enumerate(csv_reader):
            if i == 0:
                header = row
                additional_columns = row[6:]
                print(header)
                continue
            additional_values = dict(zip(additional_columns, row[6:]))
            person_row = MailMergeRow(*row[:6], additional_values)
            person_row.process_shifts_list()
            people[person_row.full_name] = person_row
    return people


def update_csv(grid_filename, existing_mailmerge_filename, output_filename):
    new_version_people = load_grid_schedule(grid_filename)
    existing_people = scan_mailmerge_csv(existing_mailmerge_filename)
    for new_version_person in new_version_people:
        if new_version_person.name == "Sam Kohn":
            print(new_version_person)
            print(new_version_person.name in existing_people)
            print(new_version_person.walkthrough_shifts)
            print(new_version_person.phonebank_shifts)
        if new_version_person.name in existing_people:
            existing_row = existing_people[new_version_person.name]
            # update phonebank and walkthrough shifts
            existing_row.walkthrough_shifts = new_version_person.walkthrough_shifts
            existing_row.phonebank_shifts = new_version_person.phonebank_shifts
        else:
            new_mailmergerow = MailMergeRow(
                new_version_person.name,
                new_version_person.first_name(),
                new_version_person.last_name(),
                new_version_person.phone,
                new_version_person.walkthrough_shifts,
                new_version_person.phonebank_shifts,
                {},
            )
            existing_people[new_mailmergerow.full_name] = new_mailmergerow
    write_csv(output_filename, list(existing_people.values()))


if __name__ == "__main__":
    provided_filename = input("Enter file name: ")
    raw_signups = aggregate_signups(provided_filename)
    print(len(raw_signups))
