import random
from datetime import datetime, timedelta
import customtkinter as ctk
from tkinter import END, StringVar

# Проверка на пересечение временных интервалов
def is_time_overlap(start1, end1, start2, end2):
    return max(start1, start2) <= min(end1, end2)

# Вычисление времени окончания маршрута
def calculate_route_end(start_time, route_duration):
    full_datetime = datetime.combine(datetime.today(), start_time) + route_duration
    return full_datetime.time()

# Генерация времени маршрутов
def generate_route_times():
    route_times = []
    for start_hour, end_hour in peak_hours:
        current_time = datetime.strptime(f"{start_hour}:00", "%H:%M")
        while current_time.hour < end_hour:
            route_times.append(current_time.time())
            current_time += traffic_route_time
    for start_hour, end_hour in non_peak_hours:
        current_time = datetime.strptime(f"{start_hour}:00", "%H:%M")
        while current_time.hour < end_hour:
            route_times.append(current_time.time())
            current_time += traffic_route_time
    return route_times

# Проверка соблюдения условий для водителей типа A
def validate_driver_A_schedule(schedule):
    for driver, routes in schedule.items():
        work_time = timedelta()
        for start, end in routes:
            route_duration = datetime.combine(datetime.today(), end) - datetime.combine(datetime.today(), start)
            work_time += route_duration
            if work_time > shift_duration_A - timedelta(hours=1):  # Учитываем час на обед
                return False
    return True

# Проверка условий для водителей типа B
def validate_driver_B_schedule(schedule):
    for driver, routes in schedule.items():
        for i in range(1, len(routes)):
            prev_end = routes[i-1][1]
            curr_start = routes[i][0]
            break_duration = datetime.combine(datetime.today(), curr_start) - datetime.combine(datetime.today(), prev_end)
            if break_duration < timedelta(minutes=15):
                return False
    return True

# Функция оценки пригодности
def fitness(schedule, driver_type):
    penalties = 0
    for driver, routes in schedule.items():
        for i in range(len(routes)):
            for j in range(i + 1, len(routes)):
                if is_time_overlap(
                    routes[i][0], routes[i][1], routes[j][0], routes[j][1]
                ):
                    penalties += 1
    if driver_type == "A" and not validate_driver_A_schedule(schedule):
        penalties += 10
    if driver_type == "B" and not validate_driver_B_schedule(schedule):
        penalties += 10
    return -penalties

# Создание популяции
def create_population(driver_list):
    population = []
    for _ in range(population_size):
        schedule = {driver: [] for driver in driver_list}
        added_routes = 0
        while added_routes < num_routes:
            driver = random.choice(driver_list)
            start_time = random.choice(route_times)
            end_time = calculate_route_end(start_time, traffic_route_time)
            if not any(is_time_overlap(start_time, end_time, s, e) for s, e in schedule[driver]):
                schedule[driver].append((start_time, end_time))
                added_routes += 1
        population.append(schedule)
    return population

# Скрещивание
def crossover(parent1, parent2, driver_list):
    child = {driver: [] for driver in driver_list}
    for driver in driver_list:
        if random.random() > 0.5:
            child[driver] = parent1[driver][:]
        else:
            child[driver] = parent2[driver][:]
    return child

# Мутация
def mutate(schedule, driver_list):
    driver = random.choice(driver_list)
    if schedule[driver]:
        schedule[driver].pop(random.randint(0, len(schedule[driver]) - 1))  # Удаление случайного рейса
    start_time = random.choice(route_times)
    end_time = calculate_route_end(start_time, traffic_route_time)
    if not any(is_time_overlap(start_time, end_time, s, e) for s, e in schedule[driver]):
        schedule[driver].append((start_time, end_time))
    return schedule

# Генетический алгоритм
def genetic_schedule(driver_list, driver_type):
    population = create_population(driver_list)
    for generation in range(max_generations):
        population = sorted(population, key=lambda x: fitness(x, driver_type), reverse=True)
        next_population = population[:10]  # Топ-10 лучших решений
        while len(next_population) < population_size:
            parent1 = random.choice(population[:50])
            parent2 = random.choice(population[:50])
            child = crossover(parent1, parent2, driver_list)
            if random.random() < 0.2:
                child = mutate(child, driver_list)
            next_population.append(child)
        population = next_population
    best_schedule = max(population, key=lambda x: fitness(x, driver_type))
    return best_schedule

# Отображение расписания
def display_schedule(schedule):
    schedule_text.delete(1.0, END)
    total_routes = sum(len(routes) for routes in schedule.values())
    schedule_text.insert(END, f"Всего маршрутов: {total_routes}\n")
    for driver, routes in schedule.items():
        schedule_text.insert(END, f"Водитель: {driver}\n")
        for start, end in routes:
            schedule_text.insert(END, f"  Рейс с {start.strftime('%H:%M')} до {end.strftime('%H:%M')}\n")
        schedule_text.insert(END, "\n")

# Генерация расписания
def generate_schedule():
    try:
        global num_routes, route_times
        start_time = work_start_entry.get()
        end_time = work_end_entry.get()
        driver_type = driver_type_var.get()
        driver_count = int(num_drivers_entry.get())
        num_routes = int(num_routes_entry.get())

        if driver_type == "A":
            drivers = [f"Driver_A{i+1}" for i in range(driver_count)]
        else:
            drivers = [f"Driver_B{i+1}" for i in range(driver_count)]

        route_times = generate_route_times()
        best_schedule = genetic_schedule(drivers, driver_type)
        display_schedule(best_schedule)
    except ValueError:
        schedule_text.insert(END, "\nОшибка: Введите корректные параметры.\n")

# Пример данных
peak_hours = [(7, 9), (17, 19)]
non_peak_hours = [(6, 7), (9, 17), (19, 3)]
traffic_route_time = timedelta(minutes=70)
shift_duration_A = timedelta(hours=8)
shift_duration_B = timedelta(hours=24)
max_generations = 50
population_size = 100

# Создание интерфейса
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Метод генетического алгоритма")
root.geometry("350x700")

frame = ctk.CTkFrame(root)
frame.pack(pady=10, padx=10, fill="both", expand=True)

# Элементы
ctk.CTkLabel(frame, text="Начало работы (ЧЧ:ММ):").pack(pady=5)
work_start_entry = ctk.CTkEntry(frame, width=200)
work_start_entry.insert(0, "06:00")
work_start_entry.pack(pady=5)

ctk.CTkLabel(frame, text="Конец работы (ЧЧ:ММ):").pack(pady=5)
work_end_entry = ctk.CTkEntry(frame, width=200)
work_end_entry.insert(0, "23:00")
work_end_entry.pack(pady=5)

ctk.CTkLabel(frame, text="Количество маршрутов:").pack(pady=5)
num_routes_entry = ctk.CTkEntry(frame, width=200)
num_routes_entry.insert(0, "10")
num_routes_entry.pack(pady=5)

ctk.CTkLabel(frame, text="Количество водителей:").pack(pady=5)
num_drivers_entry = ctk.CTkEntry(frame, width=200)
num_drivers_entry.insert(0, "3")
num_drivers_entry.pack(pady=5)

ctk.CTkLabel(frame, text="Тип водителей:").pack(pady=5)
driver_type_var = StringVar(value="A")
driver_type_menu = ctk.CTkOptionMenu(frame, variable=driver_type_var, values=["A", "B"], width=200)
driver_type_menu.pack(pady=5)

schedule_text = ctk.CTkTextbox(frame, width=300, height=250)
schedule_text.pack(pady=10)

generate_button = ctk.CTkButton(frame, text="Сгенерировать расписание", command=generate_schedule, width=200)
generate_button.pack(pady=10)

root.mainloop()
