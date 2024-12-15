import random
from datetime import datetime, timedelta
import customtkinter as ctk
from tkinter import END, StringVar

# Параметры времени
traffic_route_time = timedelta(minutes=70)
break_time = timedelta(minutes=20)
work_limit_b = timedelta(hours=2)
break_time_a = timedelta(hours=1)

# Обработка времени
def parse_time(value):
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        raise ValueError(f"Некорректный формат времени: {value}. Ожидается формат HH:MM")

# Генерация маршрутов
def generate_route_times(num_routes):
    work_start = parse_time(work_start_entry.get())
    work_end = parse_time(work_end_entry.get())
    current_time = datetime.combine(datetime.today(), work_start)
    end_time = datetime.combine(datetime.today(), work_end)
    route_times = []

    while current_time.time() < end_time.time():
        route_times.append(current_time.time())
        current_time += traffic_route_time

    return random.sample(route_times, min(len(route_times), num_routes))

# Проверка пересечений времени
def is_time_overlap(start1, end1, routes):
    for start2, end2 in routes:
        if max(start1, start2) < min(end1, end2):
            return True
    return False

# Проверка на час пик
def is_peak_time(time):
    return 7 <= time.hour < 9 or 17 <= time.hour < 19

# Добавление перерыва для A и B
def add_break(schedule, driver, break_duration, work_end):
    last_end = schedule[driver][-1][1]
    if not is_peak_time(last_end):
        break_end = (datetime.combine(datetime.today(), last_end) + break_duration).time()
        if break_end <= work_end:
            schedule[driver].append(("break", break_end))  # Добавляем перерыв как метку
            return True
    return False

# Метод распределения маршрутов
def brute_force_schedule(driver_list, num_routes, driver_type):
    all_routes = generate_route_times(num_routes)
    schedule = {driver: [] for driver in driver_list}

    for route_start in all_routes:
        route_end = (datetime.combine(datetime.today(), route_start) + traffic_route_time).time()
        work_end = parse_time(work_end_entry.get())
        assigned = False

        for driver in driver_list:
            # Пропускаем водителя, если время пересекается или он на перерыве
            if is_time_overlap(route_start, route_end, [(s, e) for s, e in schedule[driver] if s != "break"]):
                continue

            # Добавляем перерывы для типа A каждые 4 часа
            if driver_type == "A":
                total_work = timedelta()
                for start, end in schedule[driver]:
                    if start != "break":
                        total_work += datetime.combine(datetime.today(), end) - datetime.combine(datetime.today(), start)
                if total_work >= timedelta(hours=4):
                    if add_break(schedule, driver, break_time_a, work_end):
                        continue

            # Добавляем перерывы для типа B каждые 2 часа
            if driver_type == "B" and len(schedule[driver]) > 0:
                last_end = schedule[driver][-1][1]
                time_since_last_route = datetime.combine(datetime.today(), route_start) - datetime.combine(datetime.today(), last_end)
                if time_since_last_route > work_limit_b:
                    if add_break(schedule, driver, break_time, work_end):
                        continue

            # Добавляем маршрут
            schedule[driver].append((route_start, route_end))
            assigned = True
            break

        # Добавляем нового водителя, если маршрут не назначен
        if not assigned:
            new_driver = f"Driver_{driver_type}{len(driver_list) + 1}"
            driver_list.append(new_driver)
            schedule[new_driver] = [(route_start, route_end)]

    return schedule

# Отображение расписания
def display_schedule(schedule):
    schedule_text.delete(1.0, END)
    for driver, routes in schedule.items():
        schedule_text.insert(END, f"Водитель: {driver}\n")
        # Фильтруем и сортируем маршруты, исключая перерывы
        valid_routes = [(start, end) for start, end in routes if start != "break"]
        valid_routes.sort(key=lambda x: x[0])  # Сортируем только по времени начала
        for start, end in valid_routes:
            schedule_text.insert(END, f"  Рейс с {start.strftime('%H:%M')} до {end.strftime('%H:%M')}\n")
        schedule_text.insert(END, "\n")

# Генерация расписания
def generate_schedule():
    try:
        num_routes = int(num_routes_entry.get())
        driver_type = driver_type_var.get()
        num_drivers = int(num_drivers_entry.get())

        drivers = [f"Driver_{driver_type}{i+1}" for i in range(num_drivers)]
        schedule = brute_force_schedule(drivers, num_routes, driver_type)
        display_schedule(schedule)
    except ValueError as e:
        schedule_text.insert(END, f"\nОшибка: {e}\n")

# GUI
ctk.set_appearance_mode("dark")  # Темная тема
ctk.set_default_color_theme("blue")  # Синий цвет

root = ctk.CTk()
root.title("Генератор расписания методом 'в лоб'")
root.geometry("350x700")

work_start_label = ctk.CTkLabel(root, text="Начало работы (HH:MM):")
work_start_label.pack(pady=5)
work_start_entry = ctk.CTkEntry(root, width=200)
work_start_entry.insert(0, "06:00")
work_start_entry.pack(pady=5)

work_end_label = ctk.CTkLabel(root, text="Конец работы (HH:MM):")
work_end_label.pack(pady=5)
work_end_entry = ctk.CTkEntry(root, width=200)
work_end_entry.insert(0, "23:00")
work_end_entry.pack(pady=5)

num_routes_label = ctk.CTkLabel(root, text="Количество маршрутов:")
num_routes_label.pack(pady=5)
num_routes_entry = ctk.CTkEntry(root, width=200)
num_routes_entry.insert(0, "10")
num_routes_entry.pack(pady=5)

driver_type_label = ctk.CTkLabel(root, text="Тип водителей:")
driver_type_label.pack(pady=5)
driver_type_var = StringVar(value="A")
driver_type_menu = ctk.CTkOptionMenu(root, variable=driver_type_var, values=["A", "B"], width=200)
driver_type_menu.pack(pady=5)

num_drivers_label = ctk.CTkLabel(root, text="Количество водителей:")
num_drivers_label.pack(pady=5)
num_drivers_entry = ctk.CTkEntry(root, width=200)
num_drivers_entry.insert(0, "3")
num_drivers_entry.pack(pady=5)

schedule_text = ctk.CTkTextbox(root, width=300, height=300)
schedule_text.pack(pady=10)

generate_button = ctk.CTkButton(root, text="Сгенерировать расписание", command=generate_schedule, width=200)
generate_button.pack(pady=10)

root.mainloop()
