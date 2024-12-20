import random
from datetime import datetime, timedelta
import customtkinter as ctk
from tkinter import END, StringVar

traffic_route_time = timedelta(minutes=70)  
base_break_b = timedelta(minutes=20)        
break_a = timedelta(hours=1)               
work_limit_b = timedelta(hours=2)           
max_work_a = timedelta(hours=8)             
post_break_delay = timedelta(0)             
rush_hours = [(7,9), (17,19)]               

# Параметры ГА
POPULATION_SIZE = 150
GENERATIONS = 200
MUTATION_RATE = 0.1

def parse_time(value):
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        raise ValueError("Некорректный формат времени: ожидается формат HH:MM")

def is_rush_hour(t: datetime.time):
    for start_h, end_h in rush_hours:
        if start_h <= t.hour < end_h:
            return True
    return False

def next_non_rush_time(t: datetime.time):
    dt = datetime.combine(datetime.today(), t)
    if not is_rush_hour(t):
        return t
    for start_h, end_h in rush_hours:
        if start_h <= t.hour < end_h:
            exit_dt = datetime(dt.year, dt.month, dt.day, end_h, 0)
            if exit_dt < dt:
                exit_dt += timedelta(days=1)
            return exit_dt.time()
    return t

def time_to_datetime(t: datetime.time):
    return datetime.combine(datetime.today(), t)

def datetime_to_time(d: datetime):
    return d.time()

def is_time_overlap(start1, end1, intervals):
    # Проверяем пересечение интервалов (рейсов или перерывов)
    for s2, e2, etype in intervals:
        if max(start1, s2) < min(end1, e2):
            return True
    return False

def generate_route_times(num_routes):
    # Генерируем список времён начала рейсов
    work_start = parse_time(work_start_entry.get())
    work_end = parse_time(work_end_entry.get())
    current_time = datetime.combine(datetime.today(), work_start)
    end_time = datetime.combine(datetime.today(), work_end)
    route_times = []
    while current_time.time() < end_time.time():
        route_times.append(current_time.time())
        current_time += traffic_route_time
    return random.sample(route_times, min(len(route_times), num_routes))

def due_for_break(driver_type, total_work, missed_breaks):
    if driver_type == 'A':
        return total_work >= timedelta(hours=4)
    else:
        required_hours = (missed_breaks+1)*2
        return total_work >= timedelta(hours=required_hours)

def get_break_duration(driver_type, missed_breaks):
    if driver_type == 'A':
        return break_a
    else:
        multiplier = missed_breaks + 1
        return base_break_b * multiplier

# Метод перебора

def add_driver(driver_list, driver_type, schedule, driver_state):
    new_driver = f"{driver_type}{len(driver_list)+1}"
    driver_list.append(new_driver)
    schedule[new_driver] = []
    driver_state[new_driver] = {
        'type': driver_type,
        'total_work': timedelta(),
        'missed_breaks': 0,
        'start_of_day': parse_time(work_start_entry.get()),
        'total_hours_a': timedelta(),
        'break_due': False
    }
    return new_driver

def schedule_break(driver, schedule, driver_state, work_end, preferred_start):
    ds = driver_state[driver]
    if schedule[driver]:
        last_end_time = schedule[driver][-1][1]
    else:
        last_end_time = ds['start_of_day']

    if last_end_time is None:
        last_end_time = parse_time(work_start_entry.get())

    start_break_dt = max(time_to_datetime(last_end_time), time_to_datetime(preferred_start))

    if ds['type'] == 'B' and is_rush_hour(start_break_dt.time()):
        return None

    if ds['type'] == 'A' and is_rush_hour(start_break_dt.time()):
        nr_time = next_non_rush_time(start_break_dt.time())
        start_break_dt = datetime.combine(datetime.today(), nr_time)

    b_duration = get_break_duration(ds['type'], ds['missed_breaks'])
    break_end_dt = start_break_dt + b_duration

    if break_end_dt.time() <= work_end:
        schedule[driver].append((start_break_dt.time(), break_end_dt.time(), 'break'))
        ds['total_work'] = timedelta()
        if ds['type'] == 'B':
            ds['missed_breaks'] = 0
        ds['break_due'] = False
        return break_end_dt.time()
    else:
        ds['break_due'] = False
        return None

def can_assign_route(driver, route_start, route_end, schedule, driver_state):
    ds = driver_state[driver]
    if ds['break_due'] and not is_rush_hour(route_start):
        return False

    if ds['type'] == 'A':
        potential_total = ds['total_hours_a'] + (time_to_datetime(route_end) - time_to_datetime(route_start))
        if potential_total > max_work_a:
            return False

    if is_time_overlap(route_start, route_end, schedule[driver]):
        return False

    if schedule[driver]:
        last_entry = schedule[driver][-1]
        if last_entry[2] == 'break' and last_entry[1] > route_start:
            return False

    return True

def assign_route_to_driver(driver, route_start, route_end, schedule, driver_state):
    ds = driver_state[driver]
    schedule[driver].append((route_start, route_end, 'route'))
    worked = time_to_datetime(route_end) - time_to_datetime(route_start)
    ds['total_work'] += worked
    if ds['type'] == 'A':
        ds['total_hours_a'] += worked

def handle_a_driver_route(drivers, driver, route_start, route_end, schedule, driver_state, work_end):
    ds = driver_state[driver]

    # Проверяем, нужен ли перерыв
    if due_for_break(ds['type'], ds['total_work'], ds['missed_breaks']):
        if is_rush_hour(route_start):
            ds['break_due'] = True
        else:
            old_schedule = schedule[driver][:]
            old_state = ds.copy()

            break_result = schedule_break(driver, schedule, driver_state, work_end, route_start)
            if break_result is not None:
                route_start = break_result
                route_end = (time_to_datetime(route_start) + traffic_route_time).time()

                if can_assign_route(driver, route_start, route_end, schedule, driver_state):
                    assign_route_to_driver(driver, route_start, route_end, schedule, driver_state)
                    return True
                else:
                    schedule[driver] = old_schedule
                    driver_state[driver] = old_state
                    return False
            else:
                # Перерыв не удалось взять, попробуем назначить рейс без перерыва
                pass

    if can_assign_route(driver, route_start, route_end, schedule, driver_state):
        assign_route_to_driver(driver, route_start, route_end, schedule, driver_state)
        return True
    return False

def handle_b_driver_route(driver, route_start, route_end, schedule, driver_state, work_end):
    ds = driver_state[driver]

    if due_for_break(ds['type'], ds['total_work'], ds['missed_breaks']):
        old_schedule = schedule[driver][:]
        old_state = ds.copy()

        break_result = schedule_break(driver, schedule, driver_state, work_end, route_start)
        if break_result is not None:
            route_start = break_result
            route_end = (time_to_datetime(route_start) + traffic_route_time).time()

            if can_assign_route(driver, route_start, route_end, schedule, driver_state):
                assign_route_to_driver(driver, route_start, route_end, schedule, driver_state)
                return True
            else:
                schedule[driver] = old_schedule
                driver_state[driver] = old_state
                return False
        else:
            return False

    if can_assign_route(driver, route_start, route_end, schedule, driver_state):
        assign_route_to_driver(driver, route_start, route_end, schedule, driver_state)
        return True
    else:
        return False

def brute_force_schedule(num_routes, driver_type):
    all_routes = generate_route_times(num_routes)
    schedule = {}
    driver_state = {}

    work_end = parse_time(work_end_entry.get())
    all_routes.sort()

    if driver_type == 'A':
        driver_list = []
    else:
        num_drivers = 3
        driver_list = [f"{driver_type}{i+1}" for i in range(num_drivers)]
        for drv in driver_list:
            schedule[drv] = []
            driver_state[drv] = {
                'type': driver_type,
                'total_work': timedelta(),
                'missed_breaks': 0,
                'start_of_day': parse_time(work_start_entry.get()),
                'total_hours_a': timedelta(),
                'break_due': False
            }

    for route_start_time in all_routes:
        route_start_dt = time_to_datetime(route_start_time)
        route_end_dt = route_start_dt + traffic_route_time
        route_start = route_start_dt.time()
        route_end = route_end_dt.time()

        assigned = False
        if driver_type == 'A':
            if len(driver_list) == 0:
                add_driver(driver_list, driver_type, schedule, driver_state)
            for d in driver_list:
                if handle_a_driver_route(driver_list, d, route_start, route_end, schedule, driver_state, work_end):
                    assigned = True
                    break
            if not assigned:
                new_driver = add_driver(driver_list, driver_type, schedule, driver_state)
                driver_state[new_driver]['start_of_day'] = route_start
                handle_a_driver_route(driver_list, new_driver, route_start, route_end, schedule, driver_state, work_end)
        else:
            for d in driver_list:
                if handle_b_driver_route(d, route_start, route_end, schedule, driver_state, work_end):
                    assigned = True
                    break

    final_schedule = {drv: sch for drv, sch in schedule.items() if len(sch) > 0}
    return final_schedule

# Методы генетического алгоритма

def schedule_chromosome(chromosome, routes, driver_type, work_start, work_end):
    if driver_type == 'A':
        max_drivers = 10
        driver_list = [f"{driver_type}{i+1}" for i in range(max_drivers)]
    else:
        max_drivers = 3
        driver_list = [f"{driver_type}{i+1}" for i in range(max_drivers)]

    schedule = {d: [] for d in driver_list}
    driver_state = {
        d: {
            'type': driver_type,
            'total_work': timedelta(),
            'missed_breaks': 0,
            'start_of_day': work_start,
            'total_hours_a': timedelta(),
            'break_due': False
        } for d in driver_list
    }

    assigned_routes = 0
    for route_time, drv_idx in zip(routes, chromosome):
        if drv_idx < 0 or drv_idx >= max_drivers:
            continue
        driver = driver_list[drv_idx]
        ds = driver_state[driver]
        route_start_dt = time_to_datetime(route_time)
        route_end_dt = route_start_dt + traffic_route_time
        route_start = route_start_dt.time()
        route_end = route_end_dt.time()

        if due_for_break(ds['type'], ds['total_work'], ds['missed_breaks']):
            start_break_dt = time_to_datetime(max(ds['start_of_day'], route_start))
            if ds['type'] == 'B' and is_rush_hour(route_start):
                continue
            if ds['type'] == 'A' and is_rush_hour(route_start):
                nr_time = next_non_rush_time(route_start)
                start_break_dt = time_to_datetime(nr_time)

            b_dur = get_break_duration(ds['type'], ds['missed_breaks'])
            break_end_dt = start_break_dt + b_dur
            if break_end_dt.time() <= work_end:
                schedule[driver].append((start_break_dt.time(), break_end_dt.time(), 'break'))
                ds['total_work'] = timedelta()
                if ds['type'] == 'B':
                    ds['missed_breaks'] = 0
                ds['break_due'] = False
                route_start_dt = break_end_dt
                route_end_dt = route_start_dt + traffic_route_time
                route_start = route_start_dt.time()
                route_end = route_end_dt.time()
            else:
                continue

        if ds['type'] == 'A':
            potential_total = ds['total_hours_a'] + (route_end_dt - route_start_dt)
            if potential_total > max_work_a:
                continue

        if is_time_overlap(route_start, route_end, schedule[driver]):
            continue

        if schedule[driver]:
            last_entry = schedule[driver][-1]
            if last_entry[2] == 'break' and last_entry[1] > route_start:
                continue

        schedule[driver].append((route_start, route_end, 'route'))
        worked = route_end_dt - route_start_dt
        ds['total_work'] += worked
        if ds['type'] == 'A':
            ds['total_hours_a'] += worked
        assigned_routes += 1

    used_drivers = sum(1 for d in driver_list if len(schedule[d]) > 0)
    fitness = assigned_routes*1000 + used_drivers
    return schedule, driver_state, fitness

def initialize_population(pop_size, routes, driver_type):
    if driver_type == 'A':
        max_drivers = 10
    else:
        max_drivers = 3
    population = []
    for _ in range(pop_size):
        chromosome = [random.randint(0, max_drivers-1) for _ in routes]
        population.append(chromosome)
    return population

def crossover(chromo1, chromo2):
    if len(chromo1) <= 1:
        return chromo1[:], chromo2[:]
    point = random.randint(1, len(chromo1)-1)
    new1 = chromo1[:point] + chromo2[point:]
    new2 = chromo2[:point] + chromo1[point:]
    return new1, new2

def mutate(chromosome, driver_type):
    if driver_type == 'A':
        max_drivers = 10
    else:
        max_drivers = 3
    for i in range(len(chromosome)):
        if random.random() < MUTATION_RATE:
            chromosome[i] = random.randint(0, max_drivers-1)

def genetic_algorithm(routes, driver_type, work_start, work_end):
    population = initialize_population(POPULATION_SIZE, routes, driver_type)
    best_solution = None
    best_fitness = float('-inf')

    for gen in range(GENERATIONS):
        fitnesses = []
        for chromo in population:
            _, _, fit = schedule_chromosome(chromo, routes, driver_type, work_start, work_end)
            fitnesses.append(fit)

        for c, f in zip(population, fitnesses):
            if f > best_fitness:
                best_fitness = f
                best_solution = c[:]

        new_population = []
        for _ in range(POPULATION_SIZE//2):
            c1 = random.choice(population)
            c2 = random.choice(population)
            _, _, f1 = schedule_chromosome(c1, routes, driver_type, work_start, work_end)
            _, _, f2 = schedule_chromosome(c2, routes, driver_type, work_start, work_end)
            winner1 = c1 if f1 > f2 else c2

            c3 = random.choice(population)
            c4 = random.choice(population)
            _, _, f3 = schedule_chromosome(c3, routes, driver_type, work_start, work_end)
            _, _, f4 = schedule_chromosome(c4, routes, driver_type, work_start, work_end)
            winner2 = c3 if f3 > f4 else c4

            offspring1, offspring2 = crossover(winner1, winner2)
            mutate(offspring1, driver_type)
            mutate(offspring2, driver_type)

            new_population.append(offspring1)
            new_population.append(offspring2)

        population = new_population

    final_schedule, final_state, final_fitness = schedule_chromosome(best_solution, routes, driver_type, work_start, work_end)
    final_schedule = {d: sch for d, sch in final_schedule.items() if len(sch) > 0}
    return final_schedule

def display_schedule(schedule):
    schedule_text.delete(1.0, END)
    num_drivers_needed = len(schedule)
    schedule_text.insert(END, f"Требуется водителей: {num_drivers_needed}\n\n")
    for driver, entries in schedule.items():
        schedule_text.insert(END, f"Водитель: {driver}\n")
        sorted_entries = sorted(entries, key=lambda x: x[0])
        for start, end, etype in sorted_entries:
            if etype == 'route':
                schedule_text.insert(END, f"  Рейс с {start.strftime('%H:%M')} до {end.strftime('%H:%M')}\n")
            else:
                schedule_text.insert(END, f"  Перерыв с {start.strftime('%H:%M')} до {end.strftime('%H:%M')}\n")
        schedule_text.insert(END, "\n")

def generate_schedule():
    try:
        num_routes = int(num_routes_entry.get())
        driver_type = driver_type_var.get()
        method_type = method_type_var.get()
        work_start = parse_time(work_start_entry.get())
        work_end = parse_time(work_end_entry.get())
        routes = generate_route_times(num_routes)

        if method_type == "Перебор":
            final_schedule = brute_force_schedule(num_routes, driver_type)
        else:
            # Генетический алгоритм
            final_schedule = genetic_algorithm(routes, driver_type, work_start, work_end)

        display_schedule(final_schedule)
    except ValueError as e:
        schedule_text.insert(END, f"\nОшибка: {e}\n")

ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("Генератор расписания")
root.geometry("350x800")

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

method_type_label = ctk.CTkLabel(root, text="Метод формирования:")
method_type_label.pack(pady=5)
method_type_var = StringVar(value="Перебор")
method_type_menu = ctk.CTkOptionMenu(root, variable=method_type_var, values=["Перебор", "Генетический"], width=200)
method_type_menu.pack(pady=5)

schedule_text = ctk.CTkTextbox(root, width=300, height=300)
schedule_text.pack(pady=10)

generate_button = ctk.CTkButton(root, text="Сгенерировать расписание", command=generate_schedule, width=200)
generate_button.pack(pady=10)

root.mainloop()
