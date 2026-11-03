# SkyPilot: выбор ресурсов с ограничением числа машин

[Задание P17](https://distsys.ru/osukhoroslov/nis2/src/branch/main/project-tasks/p17-skypilot.md). Участники: Фёдор Александрович Титов, Дмитрий Витальевич Пугачев, Дмитрий Александрович Лубсанов.

[Описание проекта](nis/project.md) · [План эксперимента](nis/experiment-plan.md) · [Отчёт КТ-1](nis/checkpoints/01.md)

## Структура

- [src/skypilot_bench](src/skypilot_bench) — модель, валидатор, перебор, Greedy и адаптер SkyPilot.
- [checks](src/skypilot_bench/checks) — примеры и проверочные запуски.
- [tests](tests) — модульные тесты.
- [nis/data](nis/data) — входные данные.
- [nis/evidence](nis/evidence) — результаты проверок.

Адаптер применяет [патч](src/skypilot_bench/patches/capacity.patch) к временной копии закреплённого `optimizer.py`. Сначала ILP максимизирует число размещённых задач, затем минимизирует стоимость. Greedy также допускает частичное размещение. В этой версии поддерживаются независимые CPU-задачи и одна машина на задачу.

## Установка

Команды выполняются из корня репозитория. Нужны Git и Python; проверки выполнены на Python 3.12.

```bash
git init nis/skypilot
git -C nis/skypilot remote add origin https://github.com/skypilot-org/skypilot.git
git -C nis/skypilot fetch --depth 1 origin fff7b16adc0cad0626afbbcfa469d4704978d4e8
git -C nis/skypilot checkout --detach FETCH_HEAD
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-skypilot.txt
```

## Проверки

```bash
.venv/bin/python -m skypilot_bench.checks.model --output nis/evidence/model.json
.venv/bin/python -m skypilot_bench.checks.examples --output nis/evidence/examples.json
.venv/bin/python -m skypilot_bench.checks.source --output nis/evidence/dp.json
.venv/bin/python -m skypilot_bench.checks.extended --output nis/evidence/extended.json
.venv/bin/python -m skypilot_bench.checks.native --output nis/evidence/original-ilp.json
.venv/bin/python -m skypilot_bench.checks.capacity --output nis/evidence/capacity-ilp.json
.venv/bin/python -m unittest discover -s tests -v
```

Успешные проверки завершаются с кодом 0. В проверке исходного ILP ожидаются три превышения ёмкости. Адаптированный ILP сравнивается с полным перебором по числу размещённых задач и стоимости: 14 примеров и 30 случайных входов.

Проверки выполняются локально, без запуска облачных машин.

Замер времени и памяти на Linux или macOS:

```bash
.venv/bin/python -m skypilot_bench.checks.profile --repeats 3 --output nis/evidence/profile.json
```

Если SkyPilot лежит в другой папке, передайте её через `--source`. Для модульных тестов задайте `SKYPILOT_BENCH_SOURCE`.

## Проверка кода

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/ruff check src tests
.venv/bin/ruff format --check src tests
```
