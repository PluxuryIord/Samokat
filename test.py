from datetime import datetime, time


def is_in_night_period():
    now = datetime.now().time()
    start = time(19, 20)  # 19:20
    end = time(9, 40)     # 09:40

    # Если текущее время >= 19:20 ИЛИ <= 09:40 — значит ночь
    return now >= start or now <= end

a = is_in_night_period()
print(a)
if a:
    print('Ночь')
else:
    print('День')